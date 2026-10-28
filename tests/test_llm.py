import pytest

from ada.llm import (
    CONTEXT_TOKENS,
    ContextTooLarge,
    Message,
    OpenAICompatibleEngine,
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
