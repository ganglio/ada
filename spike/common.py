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


def _close_open_brackets(text: str) -> str | None:
    """Append the closing brackets a reply forgot, if that is the only thing wrong with it.

    The model sometimes ends `{"insights": [{...}]` without the last `}`. Scanning outside
    strings keeps a bracket inside a sentence from fooling it.
    """
    stack: list[str] = []
    in_string = escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            expected = stack.pop() if stack else None
            if expected != ch:
                return None
    if in_string or not stack:
        return None
    return text + "".join(reversed(stack))


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
    if start != -1:
        body = text[start:].split("```")[0].rstrip()
        closed = _close_open_brackets(body)
        if closed is not None:
            try:
                return Parsed(json.loads(closed), "recovered")
            except ValueError:
                pass
    return Parsed(None, "failed")


def recover_partial_memories(text: str) -> list[dict]:
    """Salvage complete {"who":..., "fact":...} objects from a reply that was cut off.

    Large-context runs can hit the reply budget mid-list. Counting the cut-off reply as a
    total failure would measure the budget, not the model.
    """
    found = []
    for match in re.finditer(r"\{[^{}]*\}", text):
        try:
            item = json.loads(match.group())
        except ValueError:
            continue
        if isinstance(item, dict) and "fact" in item:
            found.append(item)
    return found


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


def contains_keyword(text: str, keyword: str) -> bool:
    """Keyword match at a word start. A leading space in the keyword is redundant but harmless.

    Prefix matching is deliberate: "bollett" must still match "bolletta" and "bollette".
    """
    needle = normalise(keyword).strip()
    return re.search(r"(?<![a-z0-9])" + re.escape(needle), normalise(text)) is not None


def words(text: str) -> set[str]:
    return set(_WORD.findall(normalise(text)))


OLLAMA = "http://localhost:11434"


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def ollama_disk_bytes(model: str) -> int | None:
    """On-disk size of a pulled model, as Ollama lists it."""
    for entry in _get_json(f"{OLLAMA}/api/tags").get("models", []):
        if entry["name"] == model or entry["name"] == f"{model}:latest":
            return entry["size"]
    return None


def ollama_loaded(model: str) -> dict | None:
    """Memory Ollama reports for a loaded model: total bytes, GPU bytes, loaded context."""
    for entry in _get_json(f"{OLLAMA}/api/ps").get("models", []):
        if entry["name"] == model or entry["name"] == f"{model}:latest":
            return {
                "memory_bytes": entry["size"],
                "gpu_bytes": entry["size_vram"],
                "loaded_context": entry.get("context_length"),
            }
    return None


def ollama_max_context(model: str) -> int | None:
    """The model's own maximum context, from its metadata."""
    info = _post_json(f"{OLLAMA}/api/show", {"model": model}).get("model_info", {})
    values = [v for k, v in info.items() if k.endswith(".context_length")]
    return max(values) if values else None


def ollama_details(model: str) -> dict:
    d = _post_json(f"{OLLAMA}/api/show", {"model": model})
    return {
        "quantization": d["details"].get("quantization_level"),
        "parameter_size": d["details"].get("parameter_size"),
        "family": d["details"].get("family"),
        "capabilities": d.get("capabilities", []),
    }
