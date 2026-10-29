"""S3: can a model consolidate a Conversation into correct Memories?

One narrow task per call (extract memories from one chunk of transcript). Short context
windows force small chunks with a short running summary carried between them. Large windows
take the whole Conversation in one call. Scoring is mechanical (keyword matching on labels
that the generator builds from the same pool entry as the text).

Run:  ADA_LLM_BACKEND=ollama ADA_LLM_MODEL=qwen2.5:1.5b-instruct uv run python -m spike.s3_consolidation
Runs the hand-written set and writes spike/results/s3_<model>.json. The model-by-context
matrix lives in spike/matrix.py.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from ada.llm import ContextTooLarge, Message, engine_from_env, estimate_tokens
from spike import dataset
from spike.common import (
    contains_keyword,
    model_info,
    normalise,
    parse_json,
    recover_partial_memories,
)

CHUNK_TOKENS = int(os.environ.get("ADA_S3_CHUNK_TOKENS", "350"))
REPLY_TOKENS = int(os.environ.get("ADA_S3_REPLY_TOKENS", "900"))
LARGE_REPLY_TOKENS = 8192
# System prompt, carried summary, chat-template overhead and a margin.
PROMPT_RESERVE = 700
MAX_CHUNK_TOKENS = 150_000
SUMMARY_CHARS = 300

SYSTEM = (
    "You extract memories from a transcript of people talking at home. "
    "A memory is a concrete fact, plan, appointment, relationship or open question. "
    "Ignore small talk, complaints and chit-chat. Never invent details that are not in the "
    "transcript. Attribute each memory to the person who said it. "
    'Reply with JSON only: {"memories": [{"who": "<speaker>", "fact": "<short sentence>"}]}. '
    'If there is nothing worth remembering, reply {"memories": []}.'
)


def plan_for_context(context_tokens: int) -> tuple[int, int]:
    """(chunk tokens, reply tokens) for a context window.

    The 2048 plan is the one the Pi would use. Larger windows take as much transcript per
    call as fits next to a generous reply budget, which is what the app would do with them.
    """
    if context_tokens <= 2048:
        return CHUNK_TOKENS, REPLY_TOKENS
    chunk = min(context_tokens - LARGE_REPLY_TOKENS - PROMPT_RESERVE, MAX_CHUNK_TOKENS)
    return chunk, LARGE_REPLY_TOKENS


def chunk_lines(
    lines: list[tuple[str, str]], chunk_tokens: int = CHUNK_TOKENS
) -> list[list[tuple[str, str]]]:
    chunks: list[list[tuple[str, str]]] = [[]]
    used = 0
    for speaker, text in lines:
        cost = estimate_tokens(f"{speaker}: {text}\n")
        if chunks[-1] and used + cost > chunk_tokens:
            chunks.append([])
            used = 0
        chunks[-1].append((speaker, text))
        used += cost
    return chunks


def _new_stats() -> dict:
    return {
        "calls": 0,
        "strict": 0,
        "recovered": 0,
        "partial": 0,
        "failed": 0,
        "truncated": 0,
        "errors": 0,
        "seconds": 0.0,
        "prompt_tokens": 0,
        "output_tokens": 0,
        "prompt_ns": 0,
        "output_ns": 0,
    }


def consolidate(
    engine,
    lines,
    chunk_tokens: int = CHUNK_TOKENS,
    reply_tokens: int = REPLY_TOKENS,
    system: str = SYSTEM,
):
    memories: list[dict] = []
    stats = _new_stats()
    summary = ""
    for chunk in chunk_lines(lines, chunk_tokens):
        transcript = "\n".join(f"{speaker}: {text}" for speaker, text in chunk)
        user = (f"Earlier in this conversation: {summary}\n\n" if summary else "") + (
            f"Transcript:\n{transcript}"
        )
        start = time.perf_counter()
        try:
            reply = engine.complete(
                [Message("system", system), Message("user", user)], max_tokens=reply_tokens
            )
        except ContextTooLarge:
            stats["failed"] += 1
            continue
        except OSError:
            stats["errors"] += 1
            continue
        stats["seconds"] += time.perf_counter() - start
        stats["calls"] += 1
        call = getattr(engine, "last_stats", {}) or {}
        stats["prompt_tokens"] += call.get("prompt_eval_count") or 0
        stats["output_tokens"] += call.get("eval_count") or 0
        stats["prompt_ns"] += call.get("prompt_eval_duration") or 0
        stats["output_ns"] += call.get("eval_duration") or 0
        if call.get("done_reason") == "length":
            stats["truncated"] += 1
        parsed = parse_json(reply)
        items = parsed.value.get("memories") if isinstance(parsed.value, dict) else None
        if parsed.status == "failed":
            items = recover_partial_memories(reply)
            stats["partial" if items else "failed"] += 1
        else:
            stats[parsed.status] += 1
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and isinstance(item.get("fact"), str):
                memories.append({"who": str(item.get("who", "")), "fact": item["fact"]})
        summary = " ".join(f"{s}: {t}" for s, t in chunk)[-SUMMARY_CHARS:]
    return memories, stats


def covers(memory: dict, expected: dict) -> bool:
    text = f"{memory['who']} {memory['fact']}"
    return all(any(contains_keyword(text, alt) for alt in group) for group in expected["match"])


# English and Italian names for the same day or month count as the same detail, since the
# model may translate. Without this, "Thursday" for "giovedì" would be flagged as invented.
_EQUIVALENT = [
    {"monday", "lunedi"},
    {"tuesday", "martedi"},
    {"wednesday", "mercoledi"},
    {"thursday", "giovedi"},
    {"friday", "venerdi"},
    {"saturday", "sabato"},
    {"sunday", "domenica"},
    {"march", "marzo"},
]


def _in_source(detail: str, source: str) -> bool:
    d = normalise(detail)
    names = next((group for group in _EQUIVALENT if d in group), {d})
    return any(name in source for name in names)


def invented_details(memory: dict, transcript: str, cast: set[str]) -> list[str]:
    """Numbers and capitalised names in a memory that appear nowhere in the transcript.

    A capitalised word at the start of the fact is skipped: it is a sentence opener or a
    pronoun ("She is nervous"), not a name the model introduced. Only meaningful on short
    transcripts: in a long one almost every number appears somewhere.
    """
    source = normalise(transcript)
    fact = memory["fact"]
    names = [m.group() for m in re.finditer(r"\b[A-Z][a-z]{2,}\b", fact) if m.start() > 0]
    found = re.findall(r"\d+", fact) + names
    return [d for d in found if not _in_source(d, source) and normalise(d) not in cast]


def score(conv: dict, memories: list[dict]) -> dict:
    transcript = "\n".join(f"{s}: {t}" for s, t in conv["lines"])
    cast = {normalise(s) for s, _ in conv["lines"]}
    expected = conv["expected"]
    required = [e for e in expected if not e.get("optional")]
    hit = wrong_source = 0
    position = [[0, 0] for _ in range(3)]  # per third of the Conversation: [hit, required]
    for exp in required:
        matching = [m for m in memories if covers(m, exp)]
        ok = any(normalise(exp["source"]) in normalise(m["who"]) for m in matching)
        hit += ok
        wrong_source += (not ok) and bool(matching)
        if "line" in exp:
            third = min(2, exp["line"] * 3 // exp["lines_total"])
            position[third][1] += 1
            position[third][0] += ok
    covered: set[int] = set()
    duplicates = false_positives = 0
    false_examples = []
    for m in memories:
        ids = {i for i, e in enumerate(expected) if covers(m, e)}
        if not ids:
            false_positives += 1
            if len(false_examples) < 3:
                false_examples.append(m)
        elif ids <= covered:
            duplicates += 1
        covered |= ids
    invented = [
        {"fact": m["fact"], "details": d}
        for m in memories
        if (d := invented_details(m, transcript, cast))
    ]
    return {
        "required": len(required),
        "hit": hit,
        "wrong_source": wrong_source,
        "memories": len(memories),
        "false_positives": false_positives,
        "duplicates": duplicates,
        "invented": len(invented),
        "position": position,
        "false_positive_examples": false_examples,
        "invented_examples": invented[:3],
    }


def _ratio(num: float, den: float) -> float | None:
    return round(num / den, 3) if den else None


def totals(rows: list[dict]) -> dict:
    required = sum(r["required"] for r in rows)
    memories = sum(r["memories"] for r in rows)
    third = [
        _ratio(sum(r["position"][i][0] for r in rows), sum(r["position"][i][1] for r in rows))
        for i in range(3)
    ]
    return {
        "conversations": len(rows),
        "required": required,
        "recall": _ratio(sum(r["hit"] for r in rows), required),
        "wrong_source_rate": _ratio(sum(r["wrong_source"] for r in rows), required),
        "precision": None
        if not memories
        else round(1 - sum(r["false_positives"] for r in rows) / memories, 3),
        "duplicate_rate": _ratio(sum(r["duplicates"] for r in rows), memories),
        "invented_detail_rate": _ratio(sum(r["invented"] for r in rows), memories),
        "memories": memories,
        "recall_by_third": third,
    }


def run_s3(
    engine,
    corpus: list[dict],
    chunk_tokens: int,
    reply_tokens: int,
    deadline: float | None = None,
    progress=None,
    system: str = SYSTEM,
) -> dict:
    """Consolidate every Conversation in `corpus` and score it.

    Past `deadline` (a time.time() value) the remaining Conversations are skipped and
    counted, so a slow configuration yields a partial result and says so.
    """
    rows, extracted, skipped = [], {}, []
    calls = _new_stats()
    for conv in corpus:
        if deadline is not None and time.time() > deadline:
            skipped.append(conv["id"])
            continue
        if progress:
            progress(conv)
        memories, stats = consolidate(engine, conv["lines"], chunk_tokens, reply_tokens, system)
        for key, value in stats.items():
            calls[key] += value
        row = score(conv, memories) | {"id": conv["id"], "lang": conv["lang"], "set": conv["set"]}
        row["noise"] = conv.get("kind") == "noise"
        row["long"] = bool(conv.get("long"))
        row["lines"] = len(conv["lines"])
        rows.append(row)
        extracted[conv["id"]] = memories
    return {
        "chunk_tokens": chunk_tokens,
        "reply_tokens": reply_tokens,
        "calls": calls,
        "rows": rows,
        "extracted": extracted,
        "skipped": skipped,
    }


def summarise(result: dict) -> dict:
    rows = result["rows"]
    signal = [r for r in rows if not r["noise"]]
    noise = [r for r in rows if r["noise"]]
    return {
        "overall": totals(signal),
        "by_lang": {
            lang: totals([r for r in signal if r["lang"] == lang])
            for lang in ("en", "it", "mixed")
            if any(r["lang"] == lang for r in signal)
        },
        "noise": {"count": len(noise), "memories": sum(r["memories"] for r in noise)},
        "calls": result["calls"],
    }


def main() -> None:
    engine = engine_from_env()
    corpus = dataset.load(["hand"])
    result = run_s3(engine, corpus, CHUNK_TOKENS, REPLY_TOKENS)
    summary = summarise(result) | {"model": model_info(), "chunk_tokens": CHUNK_TOKENS}
    name = re.sub(r"[^a-z0-9.]+", "_", summary["model"]["model"].lower())
    path = Path(__file__).parent / "results" / f"s3_{name}.json"
    path.write_text(json.dumps(summary | {"rows": result["rows"]}, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
