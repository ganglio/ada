# Spike fixtures: recording script

These clips feed spikes S1 (speech-to-text), S2 (speaker recognition), S5 (wake word) and S6 (VAD). They are the one exception to "no raw audio on disk" (ADR 0002): they live in `spike/fixtures/`, which is git-ignored, and the application never reads them.

## Before anyone records

- **Consent.** Read this aloud or show it, and get a yes from each speaker before they record: *"These recordings will be stored on this laptop only, used to test speech and voice recognition for the Ada project, never uploaded or shared, and deleted when the spike ends. You can ask me to delete yours at any time."*
- **Names stay out of the files.** Use the labels below. Keep the label-to-person mapping somewhere outside the repo.
- **No children, and no one who hasn't agreed.** Skip anyone who can't give consent for themselves.

## Speakers

Record **at least 4, ideally 5**, so the speaker tests have unenrolled voices:

| Label | Plays the part of | Enrolled in S2? |
|---|---|---|
| `S1` | Owner | yes |
| `S2` | Housemate | yes |
| `S3` | Housemate or Friend | yes |
| `S4` | Friend (the "Gino" case) | held back, to test promotion from Stranger |
| `S5` | Stranger | never |

If you only have 3 people, drop `S5`. `S4` still gives one unenrolled voice.

## Recording setup

- Use the laptop microphone, since that is the V0 device. Sit about 1 m away in a normal room, as you would talk to Ada.
- Format: **16 kHz, mono, 16-bit WAV**. List the input devices, then record:
  ```sh
  ffmpeg -f avfoundation -list_devices true -i ""
  ffmpeg -f avfoundation -i ":0" -ar 16000 -ac 1 -t 120 spike/fixtures/S1_A_01.wav
  ```
  Replace `:0` with your microphone's index. macOS will ask the terminal for microphone access the first time.
- **Naming:** `<speaker>_<set>_<id>.wav`, for example `S2_C_04.wav`. Environment clips use `ENV_<kind>_<n>.wav`.
- Read naturally, at normal speed, with no theatrical enunciation. If you stumble, record the line again.

## Set A: English (each speaker, ~2 min)

| ID | Sentence |
|---|---|
| A01 | Marco's dentist appointment is on Tuesday at four in the afternoon. |
| A02 | We're out of milk, and someone needs to pick up the parcel from the neighbour. |
| A03 | Anna's birthday party is on the fourteenth of March, and she wants a chocolate cake. |
| A04 | I'm a bit nervous about Thursday's meeting with the new client. |
| A05 | The boiler is making that noise again, I think we should call someone before winter. |
| A06 | Gino said he'd come round on Saturday to help with the shelves. |
| A07 | Do you remember where we left the spare keys? |
| A08 | It's been much hotter this year than last year, hasn't it? |

## Set B: Italian (each speaker who speaks Italian, ~2 min)

| ID | Sentence |
|---|---|
| B01 | L'appuntamento dal dentista di Marco è martedì alle quattro del pomeriggio. |
| B02 | Abbiamo finito il latte, e qualcuno deve ritirare il pacco dalla vicina. |
| B03 | La festa di compleanno di Anna è il quattordici marzo e vuole una torta al cioccolato. |
| B04 | Sono un po' agitato per la riunione di giovedì con il nuovo cliente. |
| B05 | La caldaia fa di nuovo quel rumore, forse dovremmo chiamare qualcuno prima dell'inverno. |
| B06 | Gino ha detto che passa sabato ad aiutarci con le mensole. |
| B07 | Ti ricordi dove abbiamo messo le chiavi di scorta? |
| B08 | Quest'anno fa molto più caldo dell'anno scorso, non trovi? |

## Set C: code-switching (each speaker who is comfortable in both, ~1.5 min)

Switch mid-sentence, the way people do at home.

| ID | Sentence |
|---|---|
| C01 | Ho prenotato il meeting per giovedì, ma I think Marco can't make it. |
| C02 | Can you ricordarmi di comprare il latte quando esci? |
| C03 | La festa di Anna è sabato, so we need to decide cosa portare. |
| C04 | Il plumber verrà domani mattina, I'll be out quindi apri tu. |
| C05 | Oggi mi sento stanco, honestly I just want to stare at the wall. |
| C06 | Gino mi ha scritto che he's bringing the drill, e anche il trapano grande. |

## Set D: the wake word (each enrolled speaker)

**D-real: 10 real wake-ups.** Say each as an actual request, with a natural pause after "Ada". Vary the distance: five at about 1 m, five at 3–4 m, or with the TV on low.

| ID | Utterance |
|---|---|
| D01 | Ada, what's on today? |
| D02 | Ada, che ore sono? |
| D03 | Ada, remind me about the dentist. |
| D04 | Ada, ti ricordi cosa ha detto Marco? |
| D05 | Hey Ada, how was your day? |
| D06 | Ada. |
| D07 | Ada, can you hear me? |
| D08 | Ada, come va? |
| D09 | Scusa Ada, one question. |
| D10 | Ada, ci sei? |

**D-decoy: things that must *not* wake her.** Say each in a normal sentence, not as a request to Ada.

| ID | Utterance |
|---|---|
| D11 | I need to update the data before the meeting. |
| D12 | Ida is coming to dinner tonight. |
| D13 | Have you seen Aida at the opera? |
| D14 | Adam left his jacket here. |
| D15 | The ada-ga-da-vida song was on the radio. |
| D16 | Una dada di fagioli, per favore. |
| D17 | Ha fatto una cosa a dadi con le ragazze. |
| D18 | We were reading about Ada Lovelace. |
| D19 | Oh, that was a bad idea, a day to forget. |
| D20 | Sono andata a Ravenna da Ida, ada... aspetta, come si chiama? |

`D18` and `D20` are deliberate edge cases: they name or half-say "Ada". Record whether the detector fires, not whether it should. We decide how to treat them once we see the numbers.

## Set E: enrolment and free speech (each speaker)

- **E01:** 60 seconds of free speech in the speaker's usual language: describe your day, or what you'd cook this week. No script.
- **E02:** 30 seconds in the other language, if they speak it.

Speaker enrolment uses E01. The rest are the test material.

## Set F: voice-activity and awkward audio (any one or two speakers)

| ID | What to record |
|---|---|
| F01 | A sentence with a 2-second pause in the middle. |
| F02 | A sentence that trails off, unfinished. |
| F03 | The same sentence at normal volume, then whispered. |
| F04 | A cough, a throat clear and a laugh, with no words. |
| F05 | Two speakers talking over each other for about 10 seconds. |
| F06 | A speaker talking with a tap running or a kettle boiling. |
| F07 | A speaker talking from another room, about 5 m away. |

## Environment clips (no scripted speech)

Record these only when everyone present has agreed, or when no one is talking.

| File | What to record |
|---|---|
| `ENV_tv_en_1.wav`, `ENV_tv_it_1.wav` | 10 minutes each of TV or radio dialogue in each language. This tests the claim that a TV never becomes a Stranger Segment in the Backlog. |
| `ENV_quiet_1.wav` | 30 minutes of an empty room's normal noise. |
| `ENV_house_1.wav` … `_3.wav` | 1 hour each of ordinary household sound while the clip's only speech is people who consented. This is the false-accept test for the wake word. |

## Checklist

- [ ] Every speaker consented
- [ ] 4–5 speakers recorded Sets A, B, C, D and E (B and C only where the speaker is comfortable in both languages)
- [ ] Set F recorded
- [ ] TV, radio and environment clips recorded
- [ ] `spike/fixtures/` is not tracked: `git status` shows nothing from it
- [ ] The label-to-person mapping is kept outside the repo

## Reference text for scoring

The sentence tables above are the reference text for word-error-rate scoring. When the S1 harness is built, it will read them from this file, so keep the IDs and wording as written. If you change a sentence, change it here before recording.
