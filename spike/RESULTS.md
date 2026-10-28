# Spike results

Status: **partial.** Only the text-only spikes (S3, S4) have run. Everything that needs audio is blocked on the fixture recordings in `FIXTURES.md`.

All numbers come from one run at temperature 0 on a MacBook (Apple M5 Pro), through Ollama 0.40.11, with the context capped at 2048 tokens. Timings say nothing about a Raspberry Pi. The result files in `spike/results/` are git-ignored, so the numbers that matter are copied here. Re-run with:

```sh
ADA_LLM_BACKEND=ollama ADA_LLM_MODEL=ada-qwen2.5-1.5b uv run python -m spike.s3_consolidation
ADA_LLM_BACKEND=ollama ADA_LLM_MODEL=ada-qwen2.5-1.5b uv run python -m spike.s4_insights
```

## Verdicts

| Spike | Question | Verdict |
|---|---|---|
| S3 | Can a 1–1.5B model consolidate Conversations into correct Memories? | **Not as designed.** Qwen is partly usable under supervision. Llama is not. |
| S4 | Does "model proposes, code verifies" keep Insights honest? | **No.** The code checks as designed let false Insights through. |
| S1 | Speech-to-text in Italian, English and mixed | Not run (needs recordings) |
| S2 | Speaker recognition across 3–5 voices | Not run (needs recordings) |
| S5 | Wake word "Ada" | Not run (needs recordings) |
| S6 | VAD and the "first gate" | Not run (needs recordings) |
| S7 | End-to-end voice latency | Not run (needs S1 and a TTS choice) |

Smoke test (`smoke_llm.py`): both models load with the full 2048 context, and the oversize-prompt guard works. On three prompts, Qwen followed a one-word instruction and Llama did not.

## Caveats that apply to every number below

- **The corpus is synthetic.** I wrote the 21 transcripts and their labels (`spike/corpus.py`) and the 9 Insight scenarios (`spike/s4_insights.py`). They have not been reviewed by anyone else, and real household speech is messier.
- **The samples are small.** A single memory changes recall by 2–3 points, and S4 has 9 scenarios. Treat the figures as a smoke signal.
- **The quantisations differ.** Qwen ran as Q4_K_M and Llama as Q8_0, because those are what Ollama serves. Llama losing at the higher precision makes the gap more notable, but the comparison is not like-for-like.
- **Scoring is mechanical** (keyword matching, no LLM judge), so it is reproducible but blunt. It undercounts invented content (see S3).
- **I changed the scorer after seeing results.** The first version flagged sentence-initial pronouns ("She is nervous") and translated day names ("Thursday" for "giovedì") as invented details. I fixed both, and Qwen's invented-detail rate went from 22% to 0%. Anyone checking these numbers should read `invented_details()` in `s3_consolidation.py`.
- **Chunk size was tested at one value** (about 350 tokens of transcript per call).

## S3: consolidation

Setup: 21 Conversations (8 English, 8 Italian, 5 mixed), including 2 long ones and 3 noise-only ones. Each Conversation is chunked, and one narrow extraction call runs per chunk with a short running summary carried across.

| | Qwen2.5-1.5B (Q4_K_M) | Llama-3.2-1B (Q8_0) |
|---|---|---|
| Recall of required memories | **67%** | 42% |
| Precision | **80%** | 55% |
| Right fact, wrong speaker | 12% | 5% |
| Valid JSON from the model | 22 of 22 calls | 21 of 22 |
| Memories extracted from the 3 noise Conversations (should be 0) | 6 | 7 |
| Mean seconds per call (on the M5 Pro) | 0.37 | 0.39 |

By language:

| | Qwen recall | Qwen precision | Llama recall | Llama precision |
|---|---|---|---|---|
| English | 72% | 86% | 22% | 46% |
| Italian | 56% | 78% | 56% | 55% |
| Mixed | 78% | 73% | 56% | 67% |
| Long Conversations (2) | 69% | 79% | 31% | 67% |

What the outputs show:

- **Qwen is the better extractor.** It gets roughly two thirds of the facts, and it wrote clean memories ("Marco has an appointment with the dentist on Tuesday at 4pm").
- **Qwen is weakest in Italian.** Recall is 56%, and wrong-speaker attribution is highest there (19%).
- **Llama largely copies lines instead of extracting facts.** It returned "Che caldo oggi.", "Ha. Thanks." and "This tea is too hot." as memories, and for the dentist Conversation it returned "vado a piedi" and not the appointment.
- **Neither model reliably ignores small talk.** Both extracted memories from noise-only Conversations.
- **The invented-detail figure is an undercount.** Both models score 0%, but the scorer only catches invented numbers and names. Qwen merged unrelated lines into one invented story ("Anna mentioned the coffee is too hot, suggesting it might be raining") and wrote "She prenounced a meeting for Thursday". Neither is flagged.

## S4: Insight proposals

Setup: 9 scenarios: 3 patterns across days, 1 single Owner concern, 4 "nothing here" cases, and 1 pattern that is already known. The model proposes Insights with the segment numbers it cites, and code then checks the citations. The code check passes an Insight if it cites segments from two or more different days, or a single Owner segment.

| | Qwen2.5-1.5B | Llama-3.2-1B |
|---|---|---|
| Real Insights detected (of 4) | 3 | 2 |
| "Nothing here" or already-known scenarios where it still proposed an Insight (of 5) | 3 | 5 |
| False Insights proposed | 3 | 5 |
| False Insights that **passed** the code checks | 2 | 4 |
| Valid JSON | 9 of 9 | 9 of 9 |

What the outputs show:

- **The code checks as designed catch very little.** Models cite segments from several days with ease, even when the text is nonsense. Llama's "Make sure to book the dentist appointment in advance" passed. So did Qwen's weather and coffee story.
- **The single-Owner-concern rule did not trigger.** Both models missed "I'm nervous about Thursday's meeting" (scenario s1).
- **Neither model respected the already-known list.** Both re-proposed the sleep pattern that was listed as known.
- **Qwen's real detections were readable but padded** with unrequested advice ("may indicate a need for a conversation about her health").

## What this means for the design

These follow from the numbers above, but they are my reading, not measurements.

1. **ADR 0001's compensation plan ("structured memory and a narrow task per model call") is not enough on its own** at this model size. Even with narrow calls and chunking, Qwen misses a third of facts and Llama most of them.
2. **A stronger verifier is needed for Insights.** Candidates include a second yes/no call per candidate (round 6 already proposed this for relevance), a lexical-overlap check between the Insight text and the cited segments, and a novelty check that compares against known Memories in code.
3. **A "worth keeping?" gate before extraction** could cut the noise memories. It adds one call per chunk, so it has a cost.
4. **Italian needs separate attention.** If the household speaks Italian, the 1.5B class is at its weakest there. A model chosen for Italian may matter more than a model chosen for size.
5. **Every part of the Memory design depends on this extraction step.** Weighting by Standing, Confidences, fading and permanence all assume Memories are mostly right. At 67% recall and 80% precision, they would not be.

## Not yet tested

- Chunk size sweep (150, 350, 700 tokens)
- Larger models, as the labelled side comparison the plan allows. Without one, we cannot tell whether the limit is the model class or the task design.
- Prompt variants, few-shot examples and Italian-specific prompts
- Everything needing audio: S1, S2, S5, S6, S7
- Hailo NPU behaviour, whisper on the Hailo, and thermals (needs the hardware)
