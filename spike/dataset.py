"""The expanded S3 corpus: the hand-written set plus generated sets of growing length.

Sets (generated ones are deterministic, seeded by id):
  hand      the 22 hand-written Conversations from corpus.py
  short     6 lines, 3 facts        (EN/IT/mixed, 12 each)
  medium    20 lines, 6 facts       (EN/IT/mixed, 8 each)
  long      60 lines, 15 facts      (EN/IT/mixed, 4 each)
  day12     150 lines, 30 facts     (EN/IT/mixed, 2 each)
  day100    500 lines, 100 facts    (EN/IT/mixed, 1 each): a busy day in one Conversation
  noise     pure small talk         (EN/IT/mixed, 4 each): every extracted memory is false
  haystack  4800 lines, 120 facts   (mixed, 1): about 50k tokens, past a 32k window

`day100` separates 2048 from larger windows. `haystack` is the only set that separates a
32k window from the full one.
"""

from __future__ import annotations

from spike.corpus import CORPUS
from spike.gen import build_conversation

MODES = ("en", "it", "mixed")

# set name: (lines, facts, conversations per language, languages)
SPECS = {
    "short": (6, 3, 12, MODES),
    "medium": (20, 6, 8, MODES),
    "long": (60, 15, 4, MODES),
    "day12": (150, 30, 2, MODES),
    "day100": (500, 100, 1, MODES),
    "noise": (12, 0, 4, MODES),
    "haystack": (4800, 120, 1, ("mixed",)),
}


def hand_set() -> list[dict]:
    out = []
    for conv in CORPUS:
        expected = [
            {"source": e["source"], "match": e["match"], "optional": e.get("optional", False)}
            for e in conv["expected"]
        ]
        out.append(
            {
                "id": conv["id"],
                "set": "hand",
                "lang": conv["lang"],
                "kind": conv.get("kind", "signal"),
                "long": bool(conv.get("long")),
                "lines": conv["lines"],
                "expected": expected,
            }
        )
    return out


def generated_set(name: str) -> list[dict]:
    lines, facts, count, modes = SPECS[name]
    out = []
    for mode in modes:
        for i in range(count):
            conv_id = f"{name}-{mode}-{i:02d}"
            out.append(build_conversation(conv_id, name, conv_id, mode, lines, facts))
    return out


def load(sets: list[str] | None = None) -> list[dict]:
    wanted = sets or ["hand", *SPECS]
    out: list[dict] = []
    for name in wanted:
        out += hand_set() if name == "hand" else generated_set(name)
    return out


def summary() -> dict:
    corpus = load()
    by_set: dict[str, dict] = {}
    for conv in corpus:
        row = by_set.setdefault(conv["set"], {"conversations": 0, "lines": 0, "facts": 0})
        row["conversations"] += 1
        row["lines"] += len(conv["lines"])
        row["facts"] += sum(1 for e in conv["expected"] if not e.get("optional"))
    return by_set


if __name__ == "__main__":
    total = {"conversations": 0, "lines": 0, "facts": 0}
    for name, row in summary().items():
        print(f"{name:<8} {row}")
        for k in total:
            total[k] += row[k]
    print(f"{'total':<8} {total}")
