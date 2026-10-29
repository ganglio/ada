from spike.common import parse_json


def test_strict_json_is_strict():
    assert parse_json('{"a": 1}').status == "strict"


def test_a_fenced_reply_is_recovered():
    assert parse_json('```json\n{"a": 1}\n```').status == "recovered"


def test_a_missing_final_brace_is_repaired():
    reply = '```json\n{"insights": [{"text": "x", "support": [3, 4]}]\n```'
    parsed = parse_json(reply)
    assert parsed.status == "recovered"
    assert parsed.value == {"insights": [{"text": "x", "support": [3, 4]}]}


def test_a_bracket_inside_a_sentence_does_not_fool_the_repair():
    reply = '{"insights": [{"text": "uses a } and a ] in text", "support": [1]}]'
    assert parse_json(reply).value["insights"][0]["text"] == "uses a } and a ] in text"


def test_garbage_still_fails():
    assert parse_json("no json here").status == "failed"
    assert parse_json('{"a": [1, 2}').status == "failed"
