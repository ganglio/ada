"""The inference engine behind a narrow interface (ADR 0001).

V0 talks to an OpenAI-compatible server, LM Studio or Ollama. A Hailo backend
can replace `OpenAICompatibleEngine` later without touching callers.
"""

from __future__ import annotations

import os
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


# Both servers speak the OpenAI protocol. The Ollama default is a Modelfile
# build (see models/) because its OpenAI endpoint cannot set the context size.
BACKENDS = {
    "lmstudio": Backend("http://localhost:1234/v1", "qwen2.5-1.5b-instruct"),
    "ollama": Backend("http://localhost:11434/v1", "ada-qwen2.5-1.5b"),
}


def engine_from_env(env: Mapping[str, str] | None = None) -> OpenAICompatibleEngine:
    """Build the engine from ADA_LLM_BACKEND, ADA_LLM_MODEL and ADA_LLM_BASE_URL."""
    env = os.environ if env is None else env
    name = env.get("ADA_LLM_BACKEND", "lmstudio")
    if name not in BACKENDS:
        raise ValueError(f"unknown ADA_LLM_BACKEND {name!r}, expected one of {sorted(BACKENDS)}")
    backend = BACKENDS[name]
    return OpenAICompatibleEngine(
        model=env.get("ADA_LLM_MODEL", backend.default_model),
        base_url=env.get("ADA_LLM_BASE_URL", backend.base_url),
    )


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
        prompt_tokens = sum(estimate_tokens(m.content) for m in messages)
        if prompt_tokens + max_tokens > self._context_tokens:
            raise ContextTooLarge(
                f"~{prompt_tokens} prompt + {max_tokens} reply exceeds {self._context_tokens}"
            )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=max_tokens,
            temperature=0,
        )
        return response.choices[0].message.content or ""
