import pytest

from ada.llm import (
    CONTEXT_TOKENS,
    ContextTooLarge,
    Message,
    OllamaEngine,
    OpenAICompatibleEngine,
    engine_from_env,
    estimate_tokens,
)


def test_rejects_a_context_larger_than_the_pi_can_carry():
    with pytest.raises(ValueError):
        OpenAICompatibleEngine("m", context_tokens=CONTEXT_TOKENS + 1)


def test_rejects_a_prompt_that_would_not_fit_before_calling_the_model():
    engine = OpenAICompatibleEngine("m", base_url="http://127.0.0.1:1/v1")
    too_long = Message("user", "x" * (CONTEXT_TOKENS * 3))
    with pytest.raises(ContextTooLarge):
        engine.complete([too_long], max_tokens=64)


def test_token_estimate_rounds_up():
    assert estimate_tokens("") == 0
    assert estimate_tokens("ab") == 1
    assert estimate_tokens("abcd") == 2


def test_defaults_to_lmstudio():
    engine = engine_from_env({})
    assert isinstance(engine, OpenAICompatibleEngine)
    assert engine._client.base_url.port == 1234


def test_selects_ollama_native_engine_with_the_unrenamed_model():
    engine = engine_from_env({"ADA_LLM_BACKEND": "ollama"})
    assert isinstance(engine, OllamaEngine)
    assert engine._base_url == "http://localhost:11434"
    assert engine._model == "qwen2.5:1.5b-instruct"


def test_model_and_url_can_be_overridden():
    engine = engine_from_env(
        {
            "ADA_LLM_BACKEND": "ollama",
            "ADA_LLM_MODEL": "gemma3:4b",
            "ADA_LLM_BASE_URL": "http://10.0.0.5:11434",
        }
    )
    assert engine._model == "gemma3:4b"
    assert engine._base_url == "http://10.0.0.5:11434"


def test_rejects_an_unknown_backend():
    with pytest.raises(ValueError):
        engine_from_env({"ADA_LLM_BACKEND": "openai"})


def test_ollama_engine_rejects_a_context_larger_than_the_pi_can_carry():
    with pytest.raises(ValueError):
        OllamaEngine("m", context_tokens=CONTEXT_TOKENS + 1)


def test_ollama_engine_rejects_an_oversize_prompt_before_calling_the_model():
    engine = OllamaEngine("m", base_url="http://127.0.0.1:1")
    with pytest.raises(ContextTooLarge):
        engine.complete([Message("user", "x" * (CONTEXT_TOKENS * 3))], max_tokens=64)
