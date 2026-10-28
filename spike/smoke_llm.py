"""Smoke test: does engine_from_env() reach a model, answer sensibly, and honour 2048 context?

Run:  ADA_LLM_BACKEND=ollama uv run python -m spike.smoke_llm [model ...]
Writes spike/results/smoke_llm.json recording backend, model and timings.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from ada.llm import BACKENDS, ContextTooLarge, Message, engine_from_env

QUESTIONS = [
    ("en", "Reply with only the word: ready."),
    ("it", "Rispondi con una sola parola: la capitale d'Italia."),
    (
        "extract",
        (
            'From "Marco says the dentist is on Tuesday at 4pm" reply with JSON only: '
            '{"who": ..., "what": ..., "when": ...}'
        ),
    ),
]


def run(model: str | None) -> dict:
    env = dict(os.environ)
    if model:
        env["ADA_LLM_MODEL"] = model
    engine = engine_from_env(env)
    out = {
        "backend": env.get("ADA_LLM_BACKEND", "lmstudio"),
        "model": engine._model,
        "base_url": str(engine._client.base_url),
        "answers": [],
    }
    for tag, prompt in QUESTIONS:
        start = time.perf_counter()
        reply = engine.complete([Message("user", prompt)], max_tokens=80)
        out["answers"].append(
            {"tag": tag, "seconds": round(time.perf_counter() - start, 2), "reply": reply.strip()}
        )
    try:
        engine.complete([Message("user", "x" * 7000)], max_tokens=64)
        out["oversize_guard"] = "NOT TRIGGERED"
    except ContextTooLarge:
        out["oversize_guard"] = "ok"
    return out


if __name__ == "__main__":
    assert os.environ.get("ADA_LLM_BACKEND", "lmstudio") in BACKENDS
    results = [run(m) for m in (sys.argv[1:] or [None])]
    path = Path(__file__).parent / "results" / "smoke_llm.json"
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(json.dumps(results, indent=2, ensure_ascii=False))
