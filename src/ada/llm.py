"""The inference engine behind a narrow interface (ADR 0001).

V0 talks to an OpenAI-compatible server, LM Studio or Ollama. A Hailo backend
can replace `OpenAICompatibleEngine` later without touching callers.
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI

# The Pi's models carry a 2048-token context. The dev machine must not exceed it,
# or results would not transfer to the hardware.
CONTEXT_TOKENS = 2048

# Rough budget for estimating prompt size without a tokenizer. Deliberately
# pessimistic so a prompt that passes here fits on the real model.
_CHARS_PER_TOKEN = 3


class ContextTooLarge(Exception):
    """The prompt plus the reply budget would not fit the 2048-token context."""


@dataclass(frozen=True)
class Message:
    role: str
    content: str


class LLMEngine(Protocol):
    def complete(self, messages: list[Message], *, max_tokens: int = 256) -> str: ...


def estimate_tokens(text: str) -> int:
    return -(-len(text) // _CHARS_PER_TOKEN)


@dataclass(frozen=True)
class Backend:
    base_url: str
    default_model: str


# LM Studio speaks the OpenAI protocol. Ollama is called through its native API,
# because its OpenAI-compatible endpoint ignores a per-request context size and
# would load the model's full context instead of the Pi's 2048 tokens.
BACKENDS = {
    "lmstudio": Backend("http://localhost:1234/v1", "qwen2.5-1.5b-instruct"),
    "ollama": Backend("http://localhost:11434", "qwen2.5:1.5b-instruct"),
}


def engine_from_env(env: Mapping[str, str] | None = None) -> LLMEngine:
    """Build the engine from ADA_LLM_BACKEND, ADA_LLM_MODEL and ADA_LLM_BASE_URL."""
    env = os.environ if env is None else env
    name = env.get("ADA_LLM_BACKEND", "lmstudio")
    if name not in BACKENDS:
        raise ValueError(f"unknown ADA_LLM_BACKEND {name!r}, expected one of {sorted(BACKENDS)}")
    backend = BACKENDS[name]
    model = env.get("ADA_LLM_MODEL", backend.default_model)
    base_url = env.get("ADA_LLM_BASE_URL", backend.base_url)
    if name == "ollama":
        return OllamaEngine(model=model, base_url=base_url)
    return OpenAICompatibleEngine(model=model, base_url=base_url)


# Chat templates add tokens the character count does not see (Qwen injects a default system
# prompt when none is given). Measured: the estimate ran ~25% low on a 235-character prompt
# and ~5% high on long text, so a flat allowance covers the short case.
_TEMPLATE_OVERHEAD_TOKENS = 32


def _check_fits(messages: list[Message], max_tokens: int, context_tokens: int) -> None:
    prompt_tokens = _TEMPLATE_OVERHEAD_TOKENS + sum(estimate_tokens(m.content) for m in messages)
    if prompt_tokens + max_tokens > context_tokens:
        raise ContextTooLarge(
            f"~{prompt_tokens} prompt + {max_tokens} reply exceeds {context_tokens}"
        )


class OllamaEngine:
    """Ollama's native chat API, which honours the context size per request."""

    def __init__(
        self,
        model: str,
        base_url: str = BACKENDS["ollama"].base_url,
        context_tokens: int = CONTEXT_TOKENS,
        timeout: float = 300,
        *,
        beyond_pi: bool = False,
        think: bool | None = None,
        options: Mapping[str, float] | None = None,
    ) -> None:
        # Only the context-size experiments may exceed the Pi's 2048 tokens, and they
        # must say so explicitly, so ordinary code can never do it by accident.
        if context_tokens > CONTEXT_TOKENS and not beyond_pi:
            raise ValueError(f"context cap is {CONTEXT_TOKENS} tokens, got {context_tokens}")
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._context_tokens = context_tokens
        self._timeout = timeout
        self._think = think
        # Sampling overrides (temperature, repeat_penalty, ...). They can never change the
        # context size or the reply budget, which the guard above depends on.
        self._options = {
            k: v for k, v in (options or {}).items() if k not in ("num_ctx", "num_predict")
        }
        # Server-reported counts and timings of the most recent call, for experiments.
        self.last_stats: dict = {}

    def complete(self, messages: list[Message], *, max_tokens: int = 256) -> str:
        _check_fits(messages, max_tokens, self._context_tokens)
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": 0,
                **self._options,
                "num_ctx": self._context_tokens,
                "num_predict": max_tokens,
            },
        }
        if self._think is not None:
            payload["think"] = self._think
        request = urllib.request.Request(
            f"{self._base_url}/api/chat",
            json.dumps(payload).encode(),
            {"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            body = json.load(response)
        self.last_stats = {
            key: body.get(key)
            for key in (
                "prompt_eval_count",
                "eval_count",
                "load_duration",
                "prompt_eval_duration",
                "eval_duration",
                "total_duration",
                "done_reason",
            )
        }
        return body["message"]["content"] or ""


class OpenAICompatibleEngine:
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:1234/v1",
        context_tokens: int = CONTEXT_TOKENS,
    ) -> None:
        if context_tokens > CONTEXT_TOKENS:
            raise ValueError(f"context cap is {CONTEXT_TOKENS} tokens, got {context_tokens}")
        self._model = model
        self._context_tokens = context_tokens
        self._client = OpenAI(base_url=base_url, api_key="not-needed")

    def complete(self, messages: list[Message], *, max_tokens: int = 256) -> str:
        _check_fits(messages, max_tokens, self._context_tokens)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=max_tokens,
            temperature=0,
        )
        return response.choices[0].message.content or ""
