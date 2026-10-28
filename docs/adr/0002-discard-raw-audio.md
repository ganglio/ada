---
status: partially superseded by ADR-0003 (transcript retention)
---

# Raw audio is discarded immediately after transcription

Ada hears everyone in the home, including guests who never agreed to be recorded. Raw audio is never written to disk: only transcripts of Segments that pass the meaningful gate, plus Voiceprints of recognised people, are kept. _(The meaningful gate and the transcript retention rules were replaced by ADR 0003. The no-raw-audio rule stands.)_ Quiet or meaningless audio leaves no trace. The cost is that a bad transcription cannot be re-run later and debugging has no recordings to replay.

The one exception is the V0 spike, which measures speech and speaker models against scripted clips recorded with the speakers' consent. They live in a git-ignored `spike/fixtures/` folder, are never read by the application, and never contain recordings of the home made without consent.
