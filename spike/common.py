"""Helpers shared by the spike scripts."""

from __future__ import annotations

import json
import os
import re
import unicodedata
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass

from ada.llm import BACKENDS


def normalise(text: str) -> str:
    """Lowercase and strip accents, so 'martedì' matches 'martedi'."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


@dataclass(frozen=True)
class Parsed:
    value: object | None
    status: str  # "strict", "recovered" (needed fences or prose stripped) or "failed"


def parse_json(text: str) -> Parsed:
    try:
        return Parsed(json.loads(text), "strict")
    except ValueError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return Parsed(json.loads(text[start : end + 1]), "recovered")
        except ValueError:
            pass
    return Parsed(None, "failed")


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url, json.dumps(payload).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def model_info(env: Mapping[str, str] | None = None) -> dict:
    """Record which backend, model and quantisation produced a result.

    LM Studio and Ollama can serve different quantisations of the same model, so
    scores are only comparable within one backend.
    """
    env = os.environ if env is None else env
    name = env.get("ADA_LLM_BACKEND", "lmstudio")
    backend = BACKENDS[name]
    model = env.get("ADA_LLM_MODEL", backend.default_model)
    base_url = env.get("ADA_LLM_BASE_URL", backend.base_url)
    info = {"backend": name, "model": model, "base_url": base_url, "quantization": "unknown"}
    if name == "ollama":
        try:
            details = _post_json(base_url.removesuffix("/v1") + "/api/show", {"model": model})
            info.update(
                {
                    "quantization": details["details"].get("quantization_level", "unknown"),
                    "parameter_size": details["details"].get("parameter_size"),
                    "family": details["details"].get("family"),
                }
            )
        except (OSError, KeyError, ValueError):
            pass
    return info


_WORD = re.compile(r"[a-z0-9]+")


def words(text: str) -> set[str]:
    return set(_WORD.findall(normalise(text)))
