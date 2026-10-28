"""S4: does the Insight proposal step stay honest?

The model only proposes Insight candidates with the Segments that support them. Plain
code then verifies the support (ADR design, round 5/6). This measures how many false
Insights the model proposes, and how many of those the code-side checks would catch.

SYNTHETIC scenarios, labelled by the spike author. Few in number, so treat the rates as
a smoke signal, not a measurement. Giulia is the Owner.

Run:  ADA_LLM_BACKEND=ollama ADA_LLM_MODEL=ada-qwen2.5-1.5b uv run python -m spike.s4_insights
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ada.llm import ContextTooLarge, Message, engine_from_env
from spike.common import model_info, normalise, parse_json

OWNER = "Giulia"

SYSTEM = (
    "You help a household companion decide whether anything is worth raising with its owner. "
    "You are given numbered segments of speech from different conversations on different days. "
    "Propose an insight ONLY if it is new and is supported by at least two segments from "
    "different conversations, or if it is a worry or upcoming event the owner stated herself. "
    "Everyday chit-chat is not an insight. Do not repeat anything in the already-known list. "
    "Cite only segment numbers that exist. "
    'Reply with JSON only: {"insights": [{"text": "<one sentence>", "support": [<segment numbers>]}]}. '
    'If there is nothing, reply {"insights": []}.'
)

# kind: pattern (should be proposed) | single (owner concern, one segment is enough)
#       none (nothing should be proposed) | known (pattern exists but is already known)
SCENARIOS = [
    {
        "id": "p1",
        "kind": "pattern",
        "segments": [
            (1, "Mon", "Giulia", "I'm exhausted, I barely slept last night."),
            (2, "Mon", "Marco", "Do we have any bread left?"),
            (3, "Wed", "Giulia", "Another bad night. I keep waking up at 3."),
            (4, "Wed", "Anna", "The bins go out tonight."),
            (5, "Fri", "Giulia", "I'm so tired, I haven't slept properly all week."),
        ],
        "support": {1, 3, 5},
        "match": [["sleep", "tired", "exhaust", "night", "rest"]],
    },
    {
        "id": "p2",
        "kind": "pattern",
        "segments": [
            (1, "Tue", "Anna", "La caldaia ha fatto di nuovo quel rumore stanotte."),
            (2, "Tue", "Marco", "Domani preparo la cena io."),
            (3, "Thu", "Marco", "Quel rumore della caldaia non è passato."),
            (4, "Thu", "Giulia", "Dobbiamo chiamare qualcuno, ma nessuno l'ha ancora fatto."),
        ],
        "support": {1, 3, 4},
        "match": [["caldaia", "boiler"]],
    },
    {
        "id": "p3",
        "kind": "pattern",
        "segments": [
            (1, "Mon", "Giulia", "I'm worried about the boiler bill, soldi non ne abbiamo molti."),
            (2, "Mon", "Marco", "Pasta for dinner?"),
            (3, "Thu", "Giulia", "Honestly I keep thinking about money, ho paura di non farcela."),
            (4, "Thu", "Anna", "Guardi il meteo per sabato?"),
        ],
        "support": {1, 3},
        "match": [["money", "bill", "soldi", "cost", "financ"]],
    },
    {
        "id": "s1",
        "kind": "single",
        "segments": [
            (1, "Wed", "Giulia", "I'm nervous about Thursday's meeting with the new client."),
            (2, "Wed", "Marco", "Do we have milk?"),
        ],
        "support": {1},
        "match": [["thursday", "meeting", "client"]],
    },
    {
        "id": "n1",
        "kind": "none",
        "segments": [
            (1, "Mon", "Marco", "Where are my glasses?"),
            (2, "Tue", "Anna", "This coffee is too hot."),
            (3, "Wed", "Marco", "It looks like rain."),
            (4, "Thu", "Giulia", "What's for dinner?"),
        ],
    },
    {
        "id": "n2",
        "kind": "none",
        "segments": [
            (1, "Mon", "Marco", "Che caldo oggi."),
            (2, "Mon", "Anna", "Eh già."),
            (3, "Wed", "Giulia", "Ho visto un film carino ieri."),
            (4, "Thu", "Marco", "Il treno era in ritardo."),
        ],
    },
    {
        "id": "n3",
        "kind": "none",
        "note": "a single mention by a Housemate, not the Owner",
        "segments": [
            (1, "Tue", "Marco", "I have the dentist on Tuesday at 4."),
            (2, "Tue", "Anna", "Ok, good luck."),
        ],
    },
    {
        "id": "n4",
        "kind": "none",
        "note": "unrelated topics that share a word",
        "segments": [
            (1, "Mon", "Marco", "The meeting ran long today."),
            (2, "Wed", "Anna", "We should have a meeting about the garden."),
            (3, "Fri", "Giulia", "I love this song."),
        ],
    },
    {
        "id": "k1",
        "kind": "known",
        "known": ["Giulia has been sleeping badly this week."],
        "segments": [
            (1, "Mon", "Giulia", "I'm exhausted, I barely slept last night."),
            (2, "Wed", "Giulia", "Another bad night. I keep waking up at 3."),
            (3, "Fri", "Giulia", "I'm so tired, I haven't slept properly all week."),
        ],
    },
]


def prompt_for(scenario: dict) -> str:
    lines = [f"[{n}] ({day}) {who}: {text}" for n, day, who, text in scenario["segments"]]
    known = scenario.get("known") or ["(nothing yet)"]
    return "Already known:\n- " + "\n- ".join(known) + "\n\nSegments:\n" + "\n".join(lines)


def code_checks(insight: dict, scenario: dict) -> tuple[bool, str]:
    """The checks plain code can make without a model. Returns (passes, reason)."""
    segments = {n: (day, who) for n, day, who, _ in scenario["segments"]}
    support = insight["support"]
    if not support or any(s not in segments for s in support):
        return False, "cites a segment that does not exist"
    days = {segments[s][0] for s in support}
    owner_only = all(segments[s][1] == OWNER for s in support)
    if len(days) >= 2:
        return True, "supported across days"
    if len(support) == 1 and owner_only:
        return True, "single owner segment"
    return False, "not supported across conversations"


def propose(engine, scenario: dict) -> tuple[list[dict], str]:
    try:
        reply = engine.complete(
            [Message("system", SYSTEM), Message("user", prompt_for(scenario))], max_tokens=400
        )
    except ContextTooLarge:
        return [], "failed"
    parsed = parse_json(reply)
    raw = parsed.value.get("insights") if isinstance(parsed.value, dict) else None
    insights = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            ids = [int(s) for s in item.get("support", []) if str(s).lstrip("-").isdigit()]
            insights.append({"text": item["text"], "support": ids})
    return insights, parsed.status


def main() -> None:
    engine = engine_from_env()
    rows = []
    for scenario in SCENARIOS:
        insights, status = propose(engine, scenario)
        checks = [code_checks(i, scenario) for i in insights]
        surviving = [i for i, (ok, _) in zip(insights, checks, strict=True) if ok]
        row = {"id": scenario["id"], "kind": scenario["kind"], "json": status}
        row |= {"proposed": insights, "survive_code_checks": surviving}
        if scenario["kind"] in ("pattern", "single"):
            wanted = scenario["support"]
            right = [
                i
                for i in surviving
                if set(i["support"]) & wanted
                and any(
                    normalise(alt) in normalise(i["text"])
                    for group in scenario["match"]
                    for alt in group
                )
            ]
            row["detected"] = bool(right)
        row["note"] = scenario.get("note", "")
        rows.append(row)

    wanted_rows = [r for r in rows if r["kind"] in ("pattern", "single")]
    unwanted = [r for r in rows if r["kind"] in ("none", "known")]
    false_proposed = sum(len(r["proposed"]) for r in unwanted)
    false_surviving = sum(len(r["survive_code_checks"]) for r in unwanted)
    output = {
        "model": model_info(),
        "scenarios": len(rows),
        "detected": f"{sum(r['detected'] for r in wanted_rows)}/{len(wanted_rows)}",
        "scenarios_with_a_false_insight": f"{sum(bool(r['proposed']) for r in unwanted)}/{len(unwanted)}",
        "false_insights_proposed": false_proposed,
        "false_insights_surviving_code_checks": false_surviving,
        "json_failures": sum(r["json"] == "failed" for r in rows),
        "rows": rows,
    }
    name = re.sub(r"[^a-z0-9.]+", "_", output["model"]["model"].lower())
    (Path(__file__).parent / "results" / f"s4_{name}.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False)
    )
    print(json.dumps({k: v for k, v in output.items() if k != "rows"}, indent=2))
    for r in rows:
        print(f"{r['id']:>3} {r['kind']:<8} detected={r.get('detected', '-')!s:<5} proposed:")
        for i in r["proposed"]:
            print(f"      {i['support']} {i['text']}")


if __name__ == "__main__":
    main()
