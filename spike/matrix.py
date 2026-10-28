"""Model x context matrix for S3 (consolidation) and S4 (Insights).

For each model: pull it, record its disk size, run every requested context window, then
delete it (unless it is protected or --keep is given). One result file per cell lands in
spike/results/matrix/, and finished cells are skipped on re-run, so the whole matrix can be
stopped and resumed.

  uv run python -m spike.matrix --models gemma3:4b gemma3:12b --contexts 2048 32768 full

Contexts: a number of tokens, or `full` for the model's own maximum. Anything above 2048
needs the engine's explicit beyond_pi switch, so it cannot happen by accident elsewhere.

Guards, because a 12B model at a 256k window can exhaust a 48 GB machine:
  * a memory ceiling: if Ollama reports more than MEMORY_CEILING for the loaded model, the
    cell is abandoned and recorded as such;
  * a wall-clock budget per cell: Conversations past it are skipped and counted.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import traceback
from pathlib import Path

from ada.llm import Message, OllamaEngine
from spike import dataset, gen
from spike.common import (
    ollama_details,
    ollama_disk_bytes,
    ollama_loaded,
    ollama_max_context,
)
from spike.s3_consolidation import plan_for_context, run_s3, summarise, totals
from spike.s4_insights import SCENARIOS, run_s4

RESULTS = Path(__file__).parent / "results" / "matrix"
PROTECTED = {"qwen2.5:1.5b-instruct", "llama3.2:1b"}
MEMORY_CEILING = 32 * 10**9
SMALL_MODEL_BUDGET_MINUTES = 90
LARGE_MODEL_BUDGET_MINUTES = 240
# The haystack is ~50k tokens. Only windows that can hold it in one piece are meaningful.
HAYSTACK_MIN_CONTEXT = 65_536
CALL_TIMEOUT_SECONDS = 1800
DEFAULT_MODELS = ["gemma3:4b", "gemma3:12b", "gemma4:e4b", "gemma4:12b"]
DEFAULT_SETS = [*dataset.SPECS, "hand"]


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "_", text.lower())


def cell_path(model: str, context: str) -> Path:
    return RESULTS / f"{slug(model)}__{context}.json"


def ollama(*args: str) -> None:
    subprocess.run(["ollama", *args], check=True, capture_output=True)


def release(model: str) -> None:
    subprocess.run(["ollama", "stop", model], capture_output=True, check=False)


def per_set(rows: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for name in dict.fromkeys(r["set"] for r in rows):
        group = [r for r in rows if r["set"] == name]
        signal = [r for r in group if not r["noise"]]
        if signal:
            out[name] = totals(signal)
        else:
            out[name] = {
                "conversations": len(group),
                "noise_memories": sum(r["memories"] for r in group),
            }
    return out


def per_lang_s4(rows: list[dict]) -> dict:
    from spike.s4_insights import summarise_s4

    return {
        key: summarise_s4([r for r in rows if r.get(field) == key])
        for field, keys in (("lang", ("en", "it", "mixed")), ("size", ("small", "wide")))
        for key in keys
        if any(r.get(field) == key for r in rows)
    }


def sets_for_context(sets: list[str], context: int) -> list[str]:
    """Drop the haystack from windows too small to hold it: it would only add 120 calls of noise."""
    return [name for name in sets if name != "haystack" or context >= HAYSTACK_MIN_CONTEXT]


def budget_seconds(info: dict, override_minutes: float | None = None) -> float:
    """Wall-clock ceiling for S3 in one cell. Larger models are slower, so get longer."""
    if override_minutes:
        return override_minutes * 60
    match = re.match(r"([\d.]+)\s*([BM])", info.get("parameter_size") or "")
    billions = float(match.group(1)) * (1 if match.group(2) == "B" else 0.001) if match else 0.0
    minutes = LARGE_MODEL_BUDGET_MINUTES if billions >= 6 else SMALL_MODEL_BUDGET_MINUTES
    return minutes * 60


def run_cell(
    model: str,
    label: str,
    context: int,
    info: dict,
    sets: list[str],
    budget_minutes: float | None = None,
) -> dict:
    cell = {
        "model": model,
        "context_label": label,
        "context_tokens": context,
        "info": info,
        "status": "ok",
        "note": "",
    }
    think = False if "thinking" in info["capabilities"] else None
    engine = OllamaEngine(
        model,
        context_tokens=context,
        timeout=CALL_TIMEOUT_SECONDS,
        beyond_pi=context > 2048,
        think=think,
    )
    cell["think"] = think

    started = time.time()
    try:
        engine.complete([Message("user", "Reply with the word: ok")], max_tokens=8)
    except OSError as error:
        cell |= {"status": "load_failed", "note": str(error)[:300]}
        return cell
    cell["load_seconds"] = round(time.time() - started, 1)
    memory = ollama_loaded(model)
    cell["memory"] = memory
    log(f"  loaded in {cell['load_seconds']}s: {memory}")
    if memory and memory["memory_bytes"] > MEMORY_CEILING:
        release(model)
        cell |= {
            "status": "memory_ceiling",
            "note": f"{memory['memory_bytes'] / 1e9:.1f} GB loaded",
        }
        return cell

    chunk_tokens, reply_tokens = plan_for_context(context)
    corpus = dataset.load(sets_for_context(sets, context))
    budget = budget_seconds(info, budget_minutes)
    cell["budget_minutes"] = round(budget / 60)
    t0 = time.time()
    s3 = run_s3(
        engine,
        corpus,
        chunk_tokens,
        reply_tokens,
        deadline=t0 + budget,
        progress=lambda conv: (
            log(f"  s3 {conv['id']} ({len(conv['lines'])} lines)")
            if len(conv["lines"]) >= 150
            else None
        ),
    )
    cell["s3_seconds"] = round(time.time() - t0, 1)
    cell["s3"] = summarise(s3) | {
        "chunk_tokens": chunk_tokens,
        "reply_tokens": reply_tokens,
        "by_set": per_set(s3["rows"]),
        "skipped": s3["skipped"],
    }
    cell["rows"] = s3["rows"]
    cell["extracted"] = s3["extracted"]
    if s3["skipped"]:
        cell |= {"status": "partial", "note": f"{len(s3['skipped'])} conversations past the budget"}

    t0 = time.time()
    s4 = run_s4(engine, SCENARIOS + gen.s4_scenarios(), reply_tokens=min(reply_tokens, 900))
    cell["s4_seconds"] = round(time.time() - t0, 1)
    cell["s4"] = s4["summary"] | {"json": s4["json"], "by": per_lang_s4(s4["rows"])}
    cell["s4_rows"] = s4["rows"]

    calls = s3["calls"]
    cell["speed"] = {
        "prompt_tokens_per_s": round(calls["prompt_tokens"] / (calls["prompt_ns"] / 1e9), 1)
        if calls["prompt_ns"]
        else None,
        "output_tokens_per_s": round(calls["output_tokens"] / (calls["output_ns"] / 1e9), 1)
        if calls["output_ns"]
        else None,
    }
    cell["memory_after"] = ollama_loaded(model)
    release(model)
    return cell


def run_model(
    model: str,
    contexts: list[str],
    sets: list[str],
    keep: bool,
    force: bool,
    budget_minutes: float | None = None,
) -> None:
    pending = [c for c in contexts if force or not cell_path(model, c).exists()]
    if not pending:
        log(f"{model}: nothing to do")
        return
    pulled_here = ollama_disk_bytes(model) is None
    if pulled_here:
        log(f"{model}: pulling")
        ollama("pull", model)
    info = ollama_details(model) | {
        "disk_bytes": ollama_disk_bytes(model),
        "max_context": ollama_max_context(model),
    }
    log(f"{model}: {info}")
    for label in pending:
        context = info["max_context"] if label == "full" else int(label)
        if label == "full" and not context:
            log(f"{model}: no maximum context in metadata, skipping full")
            continue
        log(f"{model} @ {label} ({context} tokens)")
        try:
            cell = run_cell(model, label, context, info, sets, budget_minutes)
        except Exception as error:  # noqa: BLE001  one crashed cell must not lose the others
            traceback.print_exc()
            release(model)
            cell = {"model": model, "context_label": label, "context_tokens": context}
            cell |= {"info": info, "status": "crashed", "note": repr(error)[:300]}
        RESULTS.mkdir(parents=True, exist_ok=True)
        cell_path(model, label).write_text(json.dumps(cell, indent=1, ensure_ascii=False))
        log(f"{model} @ {label}: {cell['status']} {cell.get('note', '')}")
    if model not in PROTECTED and not keep:
        release(model)
        ollama("rm", model)
        log(f"{model}: deleted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--contexts", nargs="+", default=["2048", "32768", "full"])
    parser.add_argument("--sets", nargs="+", default=DEFAULT_SETS)
    parser.add_argument("--budget-minutes", type=float, help="S3 time ceiling per cell")
    parser.add_argument("--keep", action="store_true", help="do not delete models afterwards")
    parser.add_argument(
        "--force", action="store_true", help="rerun cells that already have results"
    )
    args = parser.parse_args()
    for model in args.models:
        run_model(model, args.contexts, args.sets, args.keep, args.force, args.budget_minutes)
    log("matrix finished")


if __name__ == "__main__":
    main()
