"""Prompt tuning harness for gemma4:e2b.

Scores one (extraction prompt, Insight prompt, sampling) configuration on a split, at one or
more context windows. Only the system prompts are tuned: the user-message framing, the
chunking and the scoring are fixed, so a score change is attributable to the prompt.

Fixed success metrics, chosen before any tuned result was seen:
  S3  F1 over memories. Recall = required facts found with the right speaker. Precision
      = memories that match a real fact, among non-duplicate memories (small talk counts
      against it). Duplicates are ignored by F1 but reported, and a guardrail watches them.
  S4  Balanced accuracy = mean of (real Insights found) and (scenarios with nothing to raise
      where no proposal survives the code-side checks).

  uv run python -m spike.tune --split dev --extract v0 --insight v0 --label baseline
  uv run python -m spike.tune --split dev --extract v2 --windows 16384 --only s3 --label try2

Results go to spike/results/tune/ (git-ignored). The durable record is spike/prompts/LOG.md.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from ada.llm import Message, OllamaEngine, estimate_tokens
from spike import dataset
from spike.common import ollama_loaded
from spike.s3_consolidation import run_s3
from spike.s4_insights import run_s4

MODEL = "gemma4:e2b"
HERE = Path(__file__).parent
PROMPTS = HERE / "prompts"
RESULTS = HERE / "results" / "tune"
WINDOWS = [8192, 16384, 24576, 32768]
PROMPT_TOKEN_LIMIT = 2000
# Room kept for the carried summary, the chat template and estimator error.
SUMMARY_RESERVE = 400
# Sampling the model's own card recommends, seeded so reruns agree.
RECOMMENDED = {"temperature": 1.0, "top_p": 0.95, "top_k": 64, "seed": 42}
GREEDY = {"temperature": 0.0}
BUDGET_SECONDS = 60 * 60


def load_prompt(kind: str, version: str) -> str:
    text = (PROMPTS / f"{kind}_{version}.txt").read_text().strip()
    tokens = estimate_tokens(text)
    if tokens > PROMPT_TOKEN_LIMIT:
        raise ValueError(f"{kind}_{version} is ~{tokens} tokens, limit {PROMPT_TOKEN_LIMIT}")
    return text


def plan(window: int, system: str) -> tuple[int, int]:
    """(transcript tokens per call, reply budget) for a window and a system prompt."""
    reply = min(8192, window // 4)
    chunk = window - reply - estimate_tokens(system) - 32 - SUMMARY_RESERVE
    return max(chunk, 500), reply


def parse_options(items: list[str]) -> dict:
    out: dict = {}
    for item in items:
        key, _, value = item.partition("=")
        out[key] = float(value) if "." in value or "e" in value else int(value)
    return out


def _ratio(num: float, den: float) -> float | None:
    return round(num / den, 3) if den else None


def s3_metrics(rows: list[dict]) -> dict:
    required = sum(r["required"] for r in rows)
    hit = sum(r["hit"] for r in rows)
    memories = sum(r["memories"] for r in rows)
    duplicates = sum(r["duplicates"] for r in rows)
    false_pos = sum(r["false_positives"] for r in rows)
    distinct = memories - duplicates
    recall = hit / required if required else None
    precision = 1 - false_pos / distinct if distinct else None
    f1 = None
    if recall is not None and precision is not None:
        f1 = 0.0 if recall + precision == 0 else 2 * recall * precision / (recall + precision)
    # Strict precision charges duplicates as well as false positives: of everything the model
    # emitted, what share was a distinct correct fact. A model that repeats one right answer
    # 400 times scores near zero here, where plain precision would call it excellent.
    strict_precision = (memories - duplicates - false_pos) / memories if memories else None
    f1_strict = None
    if recall is not None and strict_precision is not None:
        denom = recall + strict_precision
        f1_strict = 0.0 if denom == 0 else 2 * recall * strict_precision / denom
    return {
        "f1_strict": None if f1_strict is None else round(f1_strict, 3),
        "strict_precision": None if strict_precision is None else round(strict_precision, 3),
        "f1": None if f1 is None else round(f1, 3),
        "recall": None if recall is None else round(recall, 3),
        "precision": None if precision is None else round(precision, 3),
        "duplicate_rate": _ratio(duplicates, memories),
        "wrong_source_rate": _ratio(sum(r["wrong_source"] for r in rows), required),
        "memories": memories,
        "noise_memories": sum(r["memories"] for r in rows if r["noise"]),
        "required": required,
    }


def s3_breakdown(rows: list[dict]) -> dict:
    return {
        "overall": s3_metrics(rows),
        "by_set": {n: s3_metrics([r for r in rows if r["set"] == n]) for n in _unique(rows, "set")},
        "by_lang": {
            n: s3_metrics([r for r in rows if r["lang"] == n and not r["noise"]])
            for n in _unique(rows, "lang")
        },
    }


def _unique(rows: list[dict], key: str) -> list[str]:
    return list(dict.fromkeys(r[key] for r in rows))


def s4_metrics(rows: list[dict]) -> dict:
    wanted = [r for r in rows if r["kind"] in ("pattern", "single")]
    unwanted = [r for r in rows if r["kind"] in ("none", "known")]
    found = _ratio(sum(r["detected"] for r in wanted), len(wanted))
    clean = _ratio(sum(r["survive"] == 0 for r in unwanted), len(unwanted))
    proposed_clean = _ratio(sum(r["proposed"] == 0 for r in unwanted), len(unwanted))

    def kind_rate(kind: str) -> float | None:
        sub = [r for r in rows if r["kind"] == kind]
        return _ratio(sum(r["detected"] for r in sub), len(sub))

    balanced = None if found is None or clean is None else round((found + clean) / 2, 3)
    return {
        "balanced_accuracy": balanced,
        "insights_found": found,
        "pattern_found": kind_rate("pattern"),
        "single_found": kind_rate("single"),
        "nothing_to_raise_clean": clean,
        "nothing_to_raise_clean_before_code_checks": proposed_clean,
        "known_repeated": _ratio(
            sum(r["proposed"] > 0 for r in rows if r["kind"] == "known"),
            sum(r["kind"] == "known" for r in rows),
        ),
        "scenarios": len(rows),
    }


def run_config(
    extract: str,
    insight: str,
    split: str,
    window: int,
    options: dict,
    parts: set[str],
    sets: list[str] | None,
    reply_cap: int | None = None,
) -> dict:
    # Ollama keeps a loaded model at the context it was first loaded with and ignores a
    # different num_ctx on later requests, so a run silently inherits the previous window and
    # truncates its prompts. Unload first, then verify what was actually loaded.
    subprocess.run(["ollama", "stop", MODEL], capture_output=True, check=False)
    engine = OllamaEngine(
        MODEL, context_tokens=window, timeout=1800, beyond_pi=True, think=False, options=options
    )
    started = time.time()
    engine.complete([Message("user", "Reply with the word: ok")], max_tokens=8)
    loaded = ollama_loaded(MODEL) or {}
    if loaded.get("loaded_context") != window:
        raise RuntimeError(
            f"asked for a {window} window, Ollama loaded {loaded.get('loaded_context')}"
        )
    out: dict = {
        "model": MODEL,
        "split": split,
        "window": window,
        "options": options,
        "extract": extract,
        "insight": insight,
        "load_seconds": round(time.time() - started, 1),
        "memory": loaded,
    }
    if "s3" in parts:
        system = load_prompt("extract", extract)
        chunk, reply = plan(window, system)
        if reply_cap:
            chunk, reply = chunk + (reply - min(reply, reply_cap)), min(reply, reply_cap)
        corpus = dataset.tuning_set(split, sets)
        t0 = time.time()
        result = run_s3(
            engine,
            corpus,
            chunk,
            reply,
            deadline=t0 + BUDGET_SECONDS,
            system=system,
            progress=lambda c: (
                print(f"    s3 {c['id']} ({len(c['lines'])} lines)", flush=True)
                if len(c["lines"]) >= 1000
                else None
            ),
        )
        calls = result["calls"]
        out["s3"] = s3_breakdown(result["rows"]) | {
            "chunk_tokens": chunk,
            "reply_tokens": reply,
            "prompt_tokens": estimate_tokens(system),
            "seconds": round(time.time() - t0, 1),
            "calls": {
                k: calls[k]
                for k in ("calls", "strict", "recovered", "partial", "failed", "truncated")
            },
            "skipped": result["skipped"],
            "output_tokens_per_s": _ratio(calls["output_tokens"], calls["output_ns"] / 1e9),
            "prompt_tokens_per_s": _ratio(calls["prompt_tokens"], calls["prompt_ns"] / 1e9),
        }
        out["s3_rows"] = result["rows"]
        out["s3_extracted"] = result["extracted"]
    if "s4" in parts:
        system = load_prompt("insight", insight)
        t0 = time.time()
        result = run_s4(engine, dataset.insight_set(split), reply_tokens=900, system=system)
        out["s4"] = s4_metrics(result["rows"]) | {
            "json": result["json"],
            "prompt_tokens": estimate_tokens(system),
            "seconds": round(time.time() - t0, 1),
        }
        out["s4_rows"] = result["rows"]
    out["memory_after"] = ollama_loaded(MODEL)
    return out


def headline(result: dict) -> str:
    bits = [f"{result['window'] // 1024}k"]
    if "s3" in result:
        o = result["s3"]["overall"]
        bits.append(
            f"S3 F1 {o['f1']} (R {o['recall']} P {o['precision']} dup {o['duplicate_rate']} "
            f"noise {o['noise_memories']}) {result['s3']['seconds']:.0f}s"
        )
    if "s4" in result:
        m = result["s4"]
        bits.append(
            f"S4 bal {m['balanced_accuracy']} (found {m['insights_found']} "
            f"clean {m['nothing_to_raise_clean']})"
        )
    return " | ".join(bits)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--extract", default="v0")
    parser.add_argument("--insight", default="v0")
    parser.add_argument("--windows", nargs="+", type=int, default=[16384])
    parser.add_argument("--only", choices=["s3", "s4", "both"], default="both")
    parser.add_argument("--sets", nargs="+", help="restrict S3 to these tuning sets")
    parser.add_argument("--sampling", choices=["greedy", "recommended"], default="recommended")
    parser.add_argument("--option", nargs="*", default=[], help="extra Ollama options k=v")
    parser.add_argument("--reply-tokens", type=int, help="cap the reply budget (S3)")
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    options = (RECOMMENDED if args.sampling == "recommended" else GREEDY) | parse_options(
        args.option
    )
    parts = {"s3", "s4"} if args.only == "both" else {args.only}
    RESULTS.mkdir(parents=True, exist_ok=True)
    for window in args.windows:
        print(f"[{time.strftime('%H:%M:%S')}] {args.label} @ {window} {options}", flush=True)
        result = run_config(
            args.extract, args.insight, args.split, window, options, parts, args.sets
        )
        path = RESULTS / f"{args.label}__{args.split}__{window}.json"
        path.write_text(json.dumps(result, indent=1, ensure_ascii=False))
        print(f"[{time.strftime('%H:%M:%S')}] {headline(result)}", flush=True)


if __name__ == "__main__":
    main()
