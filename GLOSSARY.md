# Ada

An always-listening voice companion that runs entirely on a Raspberry Pi 5 with an AI HAT+ 2, bonds with one person, and keeps learning from what it hears.

## Language

**Ada**:
The agent itself: the persona that listens, remembers, reflects and talks to people.
_Avoid_: Assistant, bot, harness (when meaning the persona rather than the software that runs it)

**Owner**:
The one person Ada is bonded with, whom she may ask for help, confides in and is confided in by, and who she contacts when they are away from home. The bond is permanent: only a Reset ends it.
_Avoid_: Master, admin, primary user

**Reset**:
Erasing everything Ada has learned and starting again from first-boot setup. It is the only way for Ada to come to have a different Owner, and it can only be done on the host machine's command line, never through Ada herself.
_Avoid_: Handover, transfer of ownership, factory reset

**Housemate**:
Any person other than the Owner who lives in the household and whose voice Ada recognises and has a name for.
_Avoid_: Guest, secondary user, known speaker

**Friend**:
A person who does not live in the household but visits often, whose voice Ada recognises and has a name for.
_Avoid_: Visitor, acquaintance, guest

**Stranger**:
A voice Ada does not recognise, or recognises as recurring but has not yet been told the name of.
_Avoid_: Guest, unknown speaker, anonymous

**Standing**:
The rank of a person in Ada's eyes: Owner, then Housemate, then Friend, then Stranger. It sets how much weight their Segments carry and how much Ada trusts and shares with them. Only the Owner can set or change it; Ada may propose a change through a Help request.
_Avoid_: Trust level, permission, role

**Stranger file**:
The 14-day holding area for Stranger Segments and their provisional Voiceprints, used only to work out who a voice is. The Monologue never forms Memories from it, and what is not identified in time is deleted.
_Avoid_: Quarantine, unknown queue, guest log

**Introduction**:
The Owner telling Ada that a person is a Housemate or Friend. Ada notes it and starts learning to recognise that person's voice. It is the only way, besides a Help request the Owner answers, that anyone gains or changes Standing.
_Avoid_: Registration, enrolment, onboarding

**Voiceprint**:
The stored acoustic signature Ada uses to recognise a person's voice. It is kept instead of any raw audio.
_Avoid_: Voice profile, speaker embedding

**Wake word**:
The spoken name "Ada" that tells her she is being addressed and opens a short follow-up window for conversation. Only a recognised voice can wake her. Any recognised voice that speaks during the window joins the conversation and restarts it.
_Avoid_: Trigger phrase, hotword

## Listening and thinking

**Segment**:
One continuous stretch of speech that has passed the first gate and been transcribed.
_Avoid_: Utterance, clip, chunk

**Conversation**:
A run of Segments between the same people that belongs together in time, and that the Monologue consolidates as a whole, in order, because its parts stop making sense apart. It may or may not involve Ada. It ends after a lull or when the set of speakers changes.
_Avoid_: Thread, session, dialogue

**Backlog**:
The queue of Segments from recognised voices awaiting consolidation by the Monologue, which decides what is worth keeping. Segments carry their speaker's Standing and whether they were addressed to Ada. Stranger Segments never enter it, and Segments not consolidated within 48 hours expire.
_Avoid_: Inbox, buffer, transcript log

**Monologue**:
Ada's idle-time internal reflection, in which she consolidates what she has heard and been told and looks for Insights. It yields to any direct call.
_Avoid_: Dream, background loop, reflection pass

**Memory**:
A distilled fact, plan, relationship or open question that the Monologue keeps after the Segments behind it are deleted. It records who it came from, which may be Ada herself when it is her own opinion, and is short-term by default: it fades if not reinforced, the way a person's memory does, until it is forgotten. A Memory that keeps coming up across many Conversations over months becomes permanent and stops fading, and the Owner can also pin one. Conflicting Memories from different people are both kept. Ada never forgets a person on command: the Memories about someone fade naturally.
_Avoid_: Note, record, knowledge entry

**Confidence**:
What a person says in a one-to-one Conversation with Ada. It is shared only with the Owner, the speaker, or whoever it concerns, unless the speaker or Owner allows more. Anything said in a Conversation with several people, or overheard, is household knowledge instead.
_Avoid_: Secret, private message

**Household map**:
Ada's evolving picture of the people, relationships, places and routines of the home, made of Memories linked to one another rather than a separate store.
_Avoid_: Mind map, knowledge graph, world model

**Help request**:
A question Ada puts to the Owner because she needs their help, such as who a name belongs to, whether a recurring Stranger is a Friend, or what to do with Segments about to expire. It shares the Owner's daily cap on unprompted contact, by voice or Telegram, with Insights.
_Avoid_: Clarification, prompt, nag

**Insight**:
A conclusion the Monologue produces that is new, supported by multiple Segments, and actionable or emotionally relevant to the Owner. A single Owner-sourced Segment suffices when it is a concern or an upcoming event. Besides Help requests, Insights are the only thing Ada ever raises with the Owner unprompted.
_Avoid_: Finding, observation, thought

**Rebuke**:
The Owner telling Ada she is being too forward, such as "not now", "quiet now" or a plain telling-off. It overrides her at once, and she becomes more reserved in response. "Quiet now" silences her unprompted contact for a couple of hours.
_Avoid_: Mute, snooze, punishment
