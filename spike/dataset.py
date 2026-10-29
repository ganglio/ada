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
from spike.gen import DEV, Pools, build_conversation, s4_scenarios
from spike.heldout import HELD

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


def generated_set(name: str, pools: Pools | None = None, prefix: str = "") -> list[dict]:
    lines, facts, count, modes = SPECS[name]
    out = []
    for mode in modes:
        for i in range(count):
            conv_id = f"{prefix}{name}-{mode}-{i:02d}"
            out.append(build_conversation(conv_id, name, conv_id, mode, lines, facts, pools=pools))
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


# ------------------------------------------------------------------ tuning splits
#
# `dev` is what prompts are tuned against. `test` is held out: different seeds (prefix
# "ho-"), different phrasing, small talk and Insight topics (heldout.HELD). Only the
# baseline and the final prompts are ever scored on it.
#
# Window-sized sets: the same prompt behaves differently once a Conversation no longer fits
# one call. At 8k, 16k, 24k and 32k a 12k, 26k and 50k-token Conversation chunk into
# different numbers of pieces, so the window actually matters.

# set name: (lines, facts, conversations per language, languages)
TUNING_SPECS = {
    "t_short": (10, 4, 4, MODES),
    "t_medium": (40, 10, 3, MODES),
    "t_long": (240, 40, 2, MODES),  # ~3k tokens: one call at every window
    "t_xl": (1200, 60, 1, MODES),  # ~13k tokens: one call at 24k+, two at 8k/16k
    "t_xxl": (2600, 80, 1, ("mixed",)),  # ~28k tokens: needs chunking below 32k
    "t_noise": (30, 0, 3, MODES),
}


def tuning_set(split: str, names: list[str] | None = None) -> list[dict]:
    """The window-sized Conversations for the dev or held-out split."""
    if split not in ("dev", "test"):
        raise ValueError(split)
    pools, prefix = (DEV, "dv-") if split == "dev" else (HELD, "ho-")
    out: list[dict] = []
    for name in names or list(TUNING_SPECS):
        lines, facts, count, modes = TUNING_SPECS[name]
        for mode in modes:
            for i in range(count):
                conv_id = f"{prefix}{name}-{mode}-{i:02d}"
                conv = build_conversation(conv_id, name, conv_id, mode, lines, facts, pools=pools)
                out.append(conv)
    return out


def insight_set(split: str) -> list[dict]:
    """S4 scenarios for the dev or held-out split (held-out uses unseen Insight topics)."""
    if split == "dev":
        return s4_scenarios(DEV, "dv4")
    if split == "test":
        return s4_scenarios(HELD, "ho4")
    raise ValueError(split)
