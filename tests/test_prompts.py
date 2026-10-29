"""Every prompt version must respect the 2k-token ceiling and keep its reply format."""

from __future__ import annotations

from pathlib import Path

import pytest
from spike.s3_consolidation import SYSTEM as S3_SYSTEM
from spike.s4_insights import SYSTEM as S4_SYSTEM
from spike.tune import PROMPT_TOKEN_LIMIT, load_prompt, plan

from ada.llm import estimate_tokens

PROMPTS = Path(__file__).parent.parent / "spike" / "prompts"
FILES = sorted(PROMPTS.glob("*_v*.txt"))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_prompt_is_under_the_token_limit(path):
    kind, version = path.stem.split("_", 1)
    assert estimate_tokens(load_prompt(kind, version)) <= PROMPT_TOKEN_LIMIT


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_prompt_names_its_json_reply_key(path):
    key = '"memories"' if path.name.startswith("extract") else '"insights"'
    assert key in path.read_text()


def test_baseline_prompts_are_the_ones_every_earlier_result_used():
    assert load_prompt("extract", "v0") == S3_SYSTEM
    assert load_prompt("insight", "v0") == S4_SYSTEM


def test_chunk_plan_leaves_room_in_every_window():
    system = "x" * 6000  # a 2,000-token prompt
    for window in (8192, 16384, 24576, 32768):
        chunk, reply = plan(window, system)
        assert chunk + reply + estimate_tokens(system) + 32 + 400 <= window
        assert chunk >= 500
