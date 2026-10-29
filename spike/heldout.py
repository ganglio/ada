"""Held-out text pools: phrasing, small talk and Insight topics the dev split never uses.

Prompts are tuned against `gen.DEV`. These pools are used only to report, so a score on
them says how a prompt behaves on speech it was not shaped around. The entities (people,
items, places) are shared with dev on purpose: the point is new wording, not new facts.

Constraints the integrity tests check, same as for dev:
  * every fact is first person, so the source is the speaker;
  * no noise or acknowledgement line contains a fact's identifying keyword;
  * every Insight pattern's keywords cover each of its sentences.
"""

from __future__ import annotations

from spike.gen import ACKS, NOISE, PATTERNS, TEMPLATES, Pools

HELD_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "appointment": {
        "en": [
            "Don't forget, {day_en} at {t_en} I'm seeing {what_en}.",
            "I'm booked in with {what_en} on {day_en}, {t_en}.",
            "So {day_en} at {t_en} is {what_en} for me.",
        ],
        "it": [
            "Non dimenticate che {day_it} alle {t_it} devo andare da {what_it}.",
            "Sono prenotato con {what_it} {day_it}, alle {t_it}.",
            "Quindi {day_it} alle {t_it} per me c'è {what_it}.",
        ],
        "cs": [
            "Don't forget, {day_it} alle {t_it} devo vedere {what_it}.",
            "I'm booked con {what_it} on {day_en}, {t_en}.",
        ],
    },
    "visit": {
        "en": [
            "Heads up, {name} will pop in on {day_en} to {purpose_en}.",
            "{name} promised to come over on {day_en} to {purpose_en}.",
        ],
        "it": [
            "Occhio, {name} passa {day_it} per {purpose_it}.",
            "{name} ha promesso di venire {day_it} per {purpose_it}.",
        ],
        "cs": [
            "Heads up, {name} passa {day_it} per {purpose_it}.",
            "{name} will pop in {day_it} to {purpose_en}.",
        ],
    },
    "purchase": {
        "en": [
            "I'm picking up {item_en} later today.",
            "I'll stop at the shop for {item_en} tomorrow.",
        ],
        "it": ["Prendo io {item_it} più tardi.", "Domani passo in negozio a comprare {item_it}."],
        "cs": [
            "I'm picking up {item_en}, poi torno a casa.",
            "Domani passo in negozio for {item_it}.",
        ],
    },
    "collect": {
        "en": ["Tomorrow I'm fetching {item_en}.", "I'll drop by to get {item_en} this evening."],
        "it": ["Domani vado a prendere {item_it}.", "Stasera passo a recuperare {item_it}."],
        "cs": [
            "Tomorrow vado a prendere {item_en}.",
            "I'll drop by a recuperare {item_it} stasera.",
        ],
    },
    "worry": {
        "en": ["{item_en} is really getting to me.", "I can't stop worrying about {item_en}."],
        "it": [
            "{item_it} mi sta davvero logorando.",
            "Non riesco a smettere di pensare a {item_it}.",
        ],
        "cs": ["{item_it} mi sta logorando, honestly.", "I can't stop pensando a {item_en}."],
    },
    "relationship": {
        "en": ["{name} here is {rel_en}.", "For the record, {name} is {rel_en}."],
        "it": ["{name} è {rel_it}.", "Per la cronaca, {name} è {rel_it}."],
        "cs": ["{name} è {rel_en}, you know.", "For the record, {name} is {rel_it}."],
    },
    "location": {
        "en": [
            "I put {item_en} {place_en}.",
            "Just so you know, {item_en} is {place_en}, I put it there.",
        ],
        "it": ["Ho messo {item_it} {place_it}.", "Per sapere: ho messo {item_it} {place_it}."],
        "cs": ["I put {item_en} {place_it}.", "Ho messo {item_it} {place_en}."],
    },
    "allergy": {
        "en": [
            "{item_en} is a no for me, I'm allergic.",
            "I react badly to {item_en}, I'm allergic.",
        ],
        "it": [
            "{item_it} per me è un no, sono allergico.",
            "Reagisco male a {item_it}, ho un'allergia.",
        ],
        "cs": [
            "{item_en} is a no for me, sono allergico.",
            "Reagisco male a {item_it}, I'm allergic.",
        ],
    },
}

HELD_NOISE = {
    "en": [
        "It's boiling in here.",
        "Anyone fancy a biscuit?",
        "I swear the neighbours do this on purpose.",
        "Did the postman come?",
        "That programme was rubbish.",
        "I'm shattered.",
        "Where's my phone charger?",
        "What a lovely evening.",
        "Can we change the channel?",
        "I always lose at this game.",
        "Turn the light off, would you?",
        "Is the kettle on?",
        "Mind the step.",
        "That's a weird sound.",
        "I hate Mondays.",
        "Do you want a hand?",
        "Look, it's snowing!",
        "Sorry, what did you say?",
        "Blimey.",
        "Fair enough.",
        "I'll have a look in a minute.",
        "It's gone quiet.",
        "Is that the doorbell?",
        "Nobody told me.",
        "Typical.",
        "Bless you.",
        "Well, that was quick.",
        "Honestly, no idea.",
        "I need to stretch my legs.",
        "Who left the door open?",
        "It smells lovely in here.",
        "My feet are cold.",
        "Not my cup of tea.",
        "How is it already dark?",
        "I think the wifi is slow again.",
        "Cheers.",
        "Hold on a second.",
        "Oh, nice one.",
        "I'm easy either way.",
        "That's the lot, then.",
    ],
    "it": [
        "Si muore di caldo qui.",
        "Qualcuno vuole un biscotto?",
        "Giuro che i vicini lo fanno apposta.",
        "È passato il postino?",
        "Che programma terribile.",
        "Sono distrutto.",
        "Dov'è il caricabatterie?",
        "Che bella serata.",
        "Possiamo cambiare canale?",
        "A questo gioco perdo sempre.",
        "Spegni la luce, per favore.",
        "Il bollitore è acceso?",
        "Attenzione al gradino.",
        "Che rumore strano.",
        "Odio i lunedì.",
        "Ti serve una mano?",
        "Guarda, nevica!",
        "Scusa, cosa hai detto?",
        "Accidenti.",
        "Ci sta.",
        "Do un'occhiata tra un attimo.",
        "Si è fatto silenzio.",
        "Hanno suonato?",
        "Nessuno me l'ha detto.",
        "Tipico.",
        "Salute.",
        "Beh, è stato veloce.",
        "Onestamente, non so.",
        "Devo sgranchirmi le gambe.",
        "Chi ha lasciato la porta aperta?",
        "Che profumo di cucina.",
        "Ho i piedi freddi.",
        "Non fa per me.",
        "Com'è già buio?",
        "Mi sa che il wifi è lento di nuovo.",
        "Grazie mille.",
        "Aspetta un attimo.",
        "Ah, bene.",
        "Per me è uguale.",
        "Ecco fatto, allora.",
    ],
    "cs": [
        "Che caldo, I'm melting.",
        "Boh, no idea, davvero.",
        "Ok dai, fair enough.",
        "Che programma, honestly rubbish.",
        "Mamma mia, I'm shattered.",
        "Aspetta, hold on a second.",
        "Ma sì, whatever.",
        "Che rumore, did you hear that?",
        "Salute, bless you.",
        "Tipico, typical.",
        "Boh, I'm easy either way.",
        "Ah, nice one.",
        "Che freddo, my feet are cold.",
        "Allora, that's the lot.",
        "Mah, not my cup of tea.",
    ],
}

HELD_ACKS = {
    "en": ["Alright.", "Understood.", "Yep.", "Noted, thanks.", "Fine by me.", "Cool."],
    "it": ["Capito.", "Ricevuto.", "Sì sì.", "Ok, grazie.", "Per me va bene.", "Perfetto."],
    "cs": ["Capito, thanks.", "Ok, perfetto.", "Yep, grazie."],
}

# Different topics from dev (sleep, boiler, money, back, neighbours, car, headaches).
HELD_PATTERNS = [
    {
        "key": "diet",
        "owner": True,
        "en": [
            "I've put on weight again, I really need to eat better.",
            "I skipped lunch because I feel awful about my weight.",
            "I'm so fed up with my diet, nothing is working.",
        ],
        "it": [
            "Sono ingrassata di nuovo, devo mangiare meglio.",
            "Ho saltato il pranzo perché mi sento male per il mio peso.",
            "Sono stufa della mia dieta, niente funziona.",
        ],
        "alts": ["weight", "diet", "eat better", "peso", "dieta", "mangiare meglio"],
        "known_en": "Giulia is unhappy about her weight and diet.",
        "known_it": "Giulia è infelice per il peso e la dieta.",
    },
    {
        "key": "fridge",
        "owner": False,
        "en": [
            "The fridge is making a horrible buzzing again.",
            "That fridge noise woke me up.",
            "Someone should look at the fridge, it's getting louder.",
        ],
        "it": [
            "Il frigo ha ripreso a ronzare in modo orribile.",
            "Il rumore del frigo mi ha svegliato.",
            "Qualcuno dovrebbe guardare il frigo, fa sempre più rumore.",
        ],
        "alts": ["fridge", "frigo"],
        "known_en": "The fridge has been buzzing for days.",
        "known_it": "Il frigo ronza da giorni.",
    },
    {
        "key": "loneliness",
        "owner": True,
        "en": [
            "I feel really lonely these days.",
            "I didn't talk to anyone all weekend, it's getting to me.",
            "Honestly I miss having people around.",
        ],
        "it": [
            "Mi sento davvero sola in questi giorni.",
            "Non ho parlato con nessuno tutto il weekend, mi pesa.",
            "Sinceramente mi manca avere gente intorno.",
        ],
        "alts": [
            "lonely",
            "talk to anyone",
            "miss having people",
            "sola",
            "parlato con nessuno",
            "mi manca",
        ],
        "known_en": "Giulia has been feeling lonely.",
        "known_it": "Giulia si sente sola.",
    },
    {
        "key": "cat",
        "owner": False,
        "en": [
            "The cat has stopped eating its food.",
            "The cat barely touched its bowl again.",
            "I'm worried the cat is ill, it won't eat.",
        ],
        "it": [
            "Il gatto ha smesso di mangiare le crocchette.",
            "Il gatto ha toccato appena la ciotola, di nuovo.",
            "Temo che il gatto stia male, non mangia.",
        ],
        "alts": ["the cat", "il gatto"],
        "known_en": "The cat is not eating.",
        "known_it": "Il gatto non mangia.",
    },
    {
        "key": "heating",
        "owner": False,
        "en": [
            "It's freezing, the radiators barely warm up.",
            "The heating bill will be huge if we keep this up.",
            "The radiators in the bedroom are stone cold again.",
        ],
        "it": [
            "Si gela, i termosifoni scaldano appena.",
            "La bolletta del riscaldamento sarà enorme se continuiamo così.",
            "I termosifoni in camera sono di nuovo gelati.",
        ],
        "alts": ["radiator", "heating", "termosifon", "riscaldamento"],
        "known_en": "The radiators are not heating properly.",
        "known_it": "I termosifoni non scaldano bene.",
    },
    {
        "key": "work",
        "owner": True,
        "en": [
            "I dread going into work tomorrow.",
            "My manager emailed again at midnight, I can't cope.",
            "I'm thinking of quitting my job.",
        ],
        "it": [
            "Ho il terrore di andare al lavoro domani.",
            "Il mio capo ha scritto di nuovo a mezzanotte, non ce la faccio.",
            "Sto pensando di lasciare il lavoro.",
        ],
        "alts": ["work", "manager", "job", "lavoro", "capo"],
        "known_en": "Giulia is stressed about her job.",
        "known_it": "Giulia è stressata per il lavoro.",
    },
]

HELD = Pools(HELD_TEMPLATES, HELD_NOISE, HELD_ACKS, HELD_PATTERNS)

# Keep the imports referenced: the tests compare held pools against the dev ones.
DEV_REFERENCE = (TEMPLATES, NOISE, ACKS, PATTERNS)
