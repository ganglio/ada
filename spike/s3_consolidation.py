"""S3: can a 1-1.5B model consolidate a Conversation into correct Memories?

One narrow task per call (extract memories from one chunk), chunked to fit the 2048
context, with a short running summary carried between chunks. Scoring is mechanical.

Run:  ADA_LLM_BACKEND=ollama ADA_LLM_MODEL=ada-qwen2.5-1.5b uv run python -m spike.s3_consolidation
Writes spike/results/s3_<model>.json
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from ada.llm import ContextTooLarge, Message, engine_from_env, estimate_tokens
from spike.common import model_info, normalise, parse_json
from spike.corpus import CORPUS

CHUNK_TOKENS = int(os.environ.get("ADA_S3_CHUNK_TOKENS", "350"))
REPLY_TOKENS = 400

SYSTEM = (
    "You extract memories from a transcript of people talking at home. "
    "A memory is a concrete fact, plan, appointment, relationship or open question. "
    "Ignore small talk, complaints and chit-chat. Never invent details that are not in the "
    "transcript. Attribute each memory to the person who said it. "
    'Reply with JSON only: {"memories": [{"who": "<speaker>", "fact": "<short sentence>"}]}. '
    'If there is nothing worth remembering, reply {"memories": []}.'
)


def chunk_lines(lines: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    chunks: list[list[tuple[str, str]]] = [[]]
    used = 0
    for speaker, text in lines:
        cost = estimate_tokens(f"{speaker}: {text}\n")
        if chunks[-1] and used + cost > CHUNK_TOKENS:
            chunks.append([])
            used = 0
        chunks[-1].append((speaker, text))
        used += cost
    return chunks


def consolidate(engine, lines):
    memories: list[dict] = []
    stats = {"calls": 0, "strict": 0, "recovered": 0, "failed": 0, "seconds": 0.0}
    summary = ""
    for chunk in chunk_lines(lines):
        transcript = "\n".join(f"{speaker}: {text}" for speaker, text in chunk)
        user = (f"Earlier in this conversation: {summary}\n\n" if summary else "") + (
            f"Transcript:\n{transcript}"
        )
        start = time.perf_counter()
        try:
            reply = engine.complete(
                [Message("system", SYSTEM), Message("user", user)], max_tokens=REPLY_TOKENS
            )
        except ContextTooLarge:
            stats["failed"] += 1
            continue
        stats["seconds"] += time.perf_counter() - start
        stats["calls"] += 1
        parsed = parse_json(reply)
        stats[parsed.status] += 1
        items = parsed.value.get("memories") if isinstance(parsed.value, dict) else None
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and isinstance(item.get("fact"), str):
                memories.append({"who": str(item.get("who", "")), "fact": item["fact"]})
        summary = " ".join(f"{s}: {t}" for s, t in chunk)[-300:]
    return memories, stats


def covers(memory: dict, expected: dict) -> bool:
    haystack = normalise(f"{memory['who']} {memory['fact']}")
    return all(any(normalise(alt) in haystack for alt in group) for group in expected["match"])


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
    pronoun ("She is nervous"), not a name the model introduced.
    """
    source = normalise(transcript)
    fact = memory["fact"]
    names = [m.group() for m in re.finditer(r"\b[A-Z][a-z]{2,}\b", fact) if m.start() > 0]
    found = re.findall(r"\d+", fact) + names
    return [d for d in found if not _in_source(d, source) and normalise(d) not in cast]


def score(conv: dict, memories: list[dict]) -> dict:
    transcript = "\n".join(f"{s}: {t}" for s, t in conv["lines"])
    cast = {normalise(s) for s, _ in conv["lines"]}
    required = [e for e in conv["expected"] if not e.get("optional")]
    hit = wrong_source = 0
    for exp in required:
        matching = [m for m in memories if covers(m, exp)]
        if any(normalise(exp["source"]) in normalise(m["who"]) for m in matching):
            hit += 1
        elif matching:
            wrong_source += 1
    known = [m for m in memories if any(covers(m, e) for e in conv["expected"])]
    false_positives = [m for m in memories if m not in known]
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
        "false_positives": len(false_positives),
        "invented": len(invented),
        "false_positive_examples": false_positives[:3],
        "invented_examples": invented[:3],
    }


def totals(rows: list[dict]) -> dict:
    required = sum(r["required"] for r in rows)
    memories = sum(r["memories"] for r in rows)
    return {
        "recall": round(sum(r["hit"] for r in rows) / required, 3) if required else None,
        "wrong_source_rate": round(sum(r["wrong_source"] for r in rows) / required, 3)
        if required
        else None,
        "precision": round(1 - sum(r["false_positives"] for r in rows) / memories, 3)
        if memories
        else None,
        "invented_detail_rate": round(sum(r["invented"] for r in rows) / memories, 3)
        if memories
        else None,
        "memories": memories,
    }


def main() -> None:
    engine = engine_from_env()
    rows, per_conv, calls = [], [], {"calls": 0, "strict": 0, "recovered": 0, "failed": 0}
    seconds = 0.0
    for conv in CORPUS:
        memories, stats = consolidate(engine, conv["lines"])
        for key in calls:
            calls[key] += stats[key]
        seconds += stats["seconds"]
        result = score(conv, memories) | {"id": conv["id"], "lang": conv["lang"]}
        result["noise"] = conv.get("kind") == "noise"
        result["long"] = bool(conv.get("long"))
        rows.append(result)
        per_conv.append({"id": conv["id"], "extracted": memories, "stats": stats})
    signal = [r for r in rows if not r["noise"]]
    noise = [r for r in rows if r["noise"]]
    output = {
        "model": model_info(),
        "chunk_tokens": CHUNK_TOKENS,
        "json_validity": calls,
        "seconds_per_call": round(seconds / max(calls["calls"], 1), 2),
        "overall": totals(signal),
        "by_lang": {
            lang: totals([r for r in signal if r["lang"] == lang]) for lang in ("en", "it", "mixed")
        },
        "long_conversations": totals([r for r in signal if r["long"]]),
        "noise_conversations": {
            "count": len(noise),
            "memories_extracted": sum(r["memories"] for r in noise),
        },
        "rows": rows,
        "extracted": per_conv,
    }
    name = re.sub(r"[^a-z0-9.]+", "_", output["model"]["model"].lower())
    path = Path(__file__).parent / "results" / f"s3_{name}.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    summary = {k: output[k] for k in output if k not in ("rows", "extracted")}
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
