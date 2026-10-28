"""Integrity tests for the generated corpus: a wrong label would silently corrupt every result."""

from __future__ import annotations

import itertools

from spike import gen
from spike.common import contains_keyword
from spike.dataset import load, summary


def _covers(text: str, match: list[list[str]]) -> bool:
    return all(any(contains_keyword(text, alt) for alt in group) for group in match)


def test_generation_is_deterministic():
    assert load(["short", "medium"]) == load(["short", "medium"])


def test_every_fact_is_present_in_its_own_transcript_line():
    for conv in load():
        if conv["set"] == "hand":
            continue
        for exp in conv["expected"]:
            speaker, text = conv["lines"][exp["line"]]
            assert speaker == exp["source"], conv["id"]
            assert _covers(f"{speaker} {text}", exp["match"]), (conv["id"], text, exp["match"])


def test_a_fact_label_matches_no_other_line_in_the_conversation():
    """If a label also matched an unrelated line, a wrong memory could be scored as right."""
    for conv in load():
        if conv["set"] == "hand":
            continue
        for exp in conv["expected"]:
            clashes = [
                i
                for i, (_, text) in enumerate(conv["lines"])
                if i != exp["line"] and _covers(text, exp["match"])
            ]
            assert not clashes, (conv["id"], exp["match"], clashes)


def test_noise_conversations_have_no_facts():
    for conv in load(["noise"]):
        assert conv["expected"] == [] and conv["kind"] == "noise"


def test_entities_do_not_collide_across_kinds():
    """No identifying keyword may appear in a template or entity of a different fact."""
    rendered = []
    for kind, spec in gen.all_entries():
        for lang in ("en", "it", "cs"):
            for variant in range(3):
                rendered.append(gen.render(kind, spec, lang, variant, "Marco"))
    for a, b in itertools.combinations({id(f): f for f in rendered}.values(), 2):
        if (a.kind, a.disc) == (b.kind, b.disc):
            continue
        for first, second in ((a, b), (b, a)):
            # Only the entity groups can cause a false match; days are shared on purpose.
            assert not _covers(second.text, first.disc) or first.disc == second.disc, (
                first.text,
                second.text,
                first.disc,
            )


def test_noise_and_acks_never_match_a_fact_label():
    lines = [line for lines in gen.NOISE.values() for line in lines]
    lines += [line for lines in gen.ACKS.values() for line in lines]
    for kind, spec in gen.all_entries():
        fact = gen.render(kind, spec, "en", 0, "Marco")
        for line in lines:
            assert not _covers(line, fact.disc), (line, fact.disc)


def test_the_pools_are_big_enough_for_the_largest_conversation():
    totals = {k: 0 for k in gen.CAPS}
    for conv in load(["day100"]):
        for exp in conv["expected"]:
            totals[exp["kind"]] += 1
        for kind, used in totals.items():
            assert used <= gen.CAPS[kind] * 2
        totals = {k: 0 for k in gen.CAPS}


def test_facts_are_first_person_so_the_source_is_the_speaker():
    for conv in load(["short", "medium"]):
        for exp in conv["expected"]:
            assert exp["source"] == conv["lines"][exp["line"]][0]


def test_corpus_size():
    rows = summary()
    assert rows["day100"]["facts"] > 150
    assert sum(r["conversations"] for r in rows.values()) >= 100


def test_s4_scenarios_are_consistent():
    scenarios = gen.s4_scenarios()
    assert {s["kind"] for s in scenarios} == {"pattern", "single", "none", "known"}
    for s in scenarios:
        if s["kind"] in ("pattern", "known", "single"):
            assert s["support"], s["id"]
            for n in s["support"]:
                text = next(t for num, _, _, t in s["segments"] if num == n)
                assert _covers(text, s["match"]), (s["id"], text, s["match"])
        else:
            assert not s["support"]
        if s["kind"] in ("pattern", "known"):
            days = {d for num, d, _, _ in s["segments"] if num in s["support"]}
            assert len(days) >= 2, s["id"]
