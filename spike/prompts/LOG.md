# Prompt tuning log

Model: `gemma4:e2b` (nvfp4, 5.2B). Sampling: temperature 1.0, top-p 0.95, top-k 64, seed 42
(the model card's recommendation). **Not comparable with the earlier matrix cell**, which
used greedy decoding.

Every prompt version tried is listed here, including the ones that did not help. Scores are on
the **dev** split only. The held-out split is scored for the baseline and the final prompts and
nowhere else. Metrics were fixed before any tuned result was seen:

- **S3 F1**: recall (required facts found, right speaker) against precision (memories matching
  a real fact, among non-duplicates; small talk counts against it). Duplicates are reported
  separately.
- **S4 balanced accuracy**: mean of "real Insights found" and "nothing-to-raise scenarios where
  no proposal passes the code checks".

## Invalid runs (read this first)

**Every number in the first version of this log, except 16k, was measured at the wrong window
and has been removed.** Ollama keeps a model at the context size it was first loaded with and
ignores a different `num_ctx` on later requests. The first tuning run loaded `gemma4:e2b` at
16k, and every following run inherited that, whatever window the harness asked for. The harness
sent prompts sized for 8k, 24k and 32k to a model that was really running at 16k.

- **18 of 24 runs were affected**: everything at 8k, 24k and 32k. Only the 16k runs were valid.
- **It would have been invisible in the results**, because the model does not fail loudly. It
  truncates the prompt and answers anyway.
- **Found by** comparing the context Ollama reported as loaded against the window each run
  requested, after an identical-input comparison gave a window effect that did not add up.
- **Fixed in `spike/tune.py`**: each run now unloads the model first and stops with an error if
  the loaded context is not the one requested. The invalid runs are kept, unreported, in
  `spike/results/tune/invalid/`.
- **The earlier matrix cells are not affected.** `gemma3:4b` @ 2k and `gemma4:e2b` @ 32k were
  each the first load of a fresh model. The memory figures in the matrix were checked against
  the context Ollama reported.

The tables below are being rebuilt from clean runs.

## Results (clean runs only, dev split)

All runs below were checked to have been served at the window they name. **Strict F1** charges
duplicates as errors (share of emitted memories that were a distinct correct fact, against
recall). It was added after the first clean runs showed that plain F1 rewards a model that
repeats a few correct facts hundreds of times: at 32k, v1 scored the best plain F1 (0.408) with
77% duplicates and 6% recall on the longest Conversation. Treat plain F1 as the lesser metric.

### Single seed (42), all four windows

| Prompt | Window | F1 | Strict F1 | Recall | Duplicates | Noise memories | S4 balanced |
|---|---|---|---|---|---|---|---|
| v0 | 8k | 0.468 | 0.358 | 0.65 | 33% | 103 | 0.418 |
| v0 | 16k | 0.292 | 0.244 | 0.50 | 22% | 103 | 0.410 |
| v0 | 24k | 0.225 | 0.166 | 0.40 | 33% | 105 | 0.463 |
| v0 | 32k | 0.238 | 0.146 | 0.44 | 46% | 98 | 0.458 |
| v1 | 8k | 0.377 | 0.296 | 0.54 | 29% | 57 | 0.360 |
| v1 | 16k | 0.365 | 0.250 | 0.49 | 51% | 62 | 0.379 |
| v1 | 24k | 0.275 | 0.150 | 0.38 | 56% | 65 | 0.373 |
| v1 | 32k | 0.408 | 0.154 | 0.41 | 77% | 67 | 0.360 |

### Three seeds at 8k (seeds 42, 7, 99): mean and range

| Metric | v0 | v1 |
|---|---|---|
| F1 | 0.441 (0.389 to 0.468) | 0.402 (0.375 to 0.454) |
| Strict F1 | **0.362** (0.330 to 0.398) | 0.314 (0.296 to 0.342) |
| Recall | **0.627** (0.592 to 0.647) | 0.545 (0.539 to 0.553) |
| Duplicates | 25% (21% to 33%) | 30% (26% to 36%) |
| Memories from small talk | 94 (83 to 103) | **60** (54 to 69) |
| S4 balanced accuracy | **0.479** (0.418 to 0.522) | 0.381 (0.360 to 0.420) |
| S4 nothing-to-raise handled cleanly | **0.530** (0.487 to 0.615) | 0.308 (0.282 to 0.333) |

### What this shows

- **Seed noise is large.** The same prompt, window and corpus moved by up to 0.08 in F1 and 0.07
  in strict F1 between seeds, and the S4 detection rate for v0 ranged from 0.22 to 0.56. Any
  difference smaller than about 0.08 is not evidence.
- **v1 did not beat v0.** Across seeds v1 is lower on recall (0.55 against 0.63), strict F1 and
  both S4 measures. The ranges barely overlap on recall and S4 clean, so those differences look
  real. The F1 difference does not (the ranges overlap).
- **The one thing v1 did well is small talk.** It extracts about 35% fewer memories from small
  talk (60 against 94 per run), and that held in every seed. The cost was recall: it also
  dropped real facts. Telling the model what not to list seems to make it list less of
  everything.
- **A larger window is worse for this model, with these prompts.** v0 falls from 0.36 strict F1
  at 8k to 0.15 at 32k; v1 from 0.30 to 0.15. Only about 9% of what either prompt emits at 24k
  and 32k is a distinct correct fact, against 20% to 25% at 8k. Short and medium Conversations
  are fine at every window (v1 strict-scores 0.86 to 0.89 on them at 32k). The failure is in
  long ones, where the model repeats itself.
- **The cause is not established.** The pattern fits "one call covering a lot of transcript",
  and I have not yet tested chunking at 8k inside a 32k window, which would test that directly.
- **Insights are poor under both prompts.** S4 balanced accuracy is 0.38 to 0.48 where 0.50 is
  chance for a coin flip on those two measures. The numbered-steps prompt (v1) was worse.

### Not yet done

- A prompt aimed at the repetition, and chunking at a fixed 8k regardless of window.
- A prompt version for Insights that is not worse than v0.
- The held-out split has not been scored at all.
