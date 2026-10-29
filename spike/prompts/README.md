# Prompt versions

One file per version: `extract_vN.txt` (S3, memory extraction) and `insight_vN.txt` (S4,
Insight proposals). `v0` is the baseline, copied verbatim from the prompts that produced
every earlier result. Versions are never edited after they have been scored: a change is a
new file. Each must stay under 2,000 tokens (enforced by `tests/test_prompts.py`).

`spike/tune.py` loads a prompt by version, so a result file always says which text produced it.
