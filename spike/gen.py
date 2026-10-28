"""Deterministic generator of labelled household Conversations (S3) and Insight scenarios (S4).

SYNTHETIC. Every fact is rendered from a template in English, Italian or a code-switched
mix, and its label is built from the same pool entry that produced the text, so the label
cannot drift from the transcript. Matching is by keyword groups (see corpus.py): a memory
covers a fact when every group has at least one alternative in it.

Design rules that keep the labels unambiguous (checked by tests/test_gen.py):
  * every fact is first person ("I have...", "I'll buy..."), so the source is the speaker;
  * the entity that identifies a fact (a name, an item, a place) is drawn without
    replacement within a Conversation;
  * no entity keyword appears in any other fact template or in any noise line;
  * noise and acknowledgements carry no information, so any memory built from them is
    a false positive.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

OWNER = "Giulia"
SPEAKERS = [("Giulia", 35), ("Marco", 25), ("Anna", 25), ("Gino", 15)]


@dataclass(frozen=True)
class Item:
    en: str
    it: str
    alts: tuple[str, ...]


def item(en: str, it: str, *alts: str) -> Item:
    return Item(en, it, alts)


DAYS = [
    item("Monday", "lunedì", "monday", "lunedi"),
    item("Tuesday", "martedì", "tuesday", "martedi"),
    item("Wednesday", "mercoledì", "wednesday", "mercoledi"),
    item("Thursday", "giovedì", "thursday", "giovedi"),
    item("Friday", "venerdì", "friday", "venerdi"),
    item("Saturday", "sabato", "saturday", "sabato"),
    item("Sunday", "domenica", "sunday", "domenica"),
]

# ---------------------------------------------------------------------------- pools

APPOINTMENTS = [
    item("the dentist", "il dentista", "dentist"),
    item("the doctor", "il medico", "doctor", "medico"),
    item("the vet", "il veterinario", "vet"),
    item("the mechanic", "il meccanico", "mechanic", "meccanico"),
    item("the hairdresser", "il parrucchiere", "hairdress", "parrucchier"),
    item("the optician", "l'ottico", "optician", "ottico"),
    item("the accountant", "il commercialista", "accountant", "commercialista"),
    item("the physio", "il fisioterapista", "physio", "fisioterap"),
    item("the electrician", "l'elettricista", "electrician", "elettricist"),
    item("the notary", "il notaio", "notary", "notaio"),
    item("the bank", "la banca", "bank", "banca"),
    item("the tax office", "l'agenzia delle entrate", "tax office", "entrate"),
    item("the parents meeting", "il colloquio con i professori", "parents meeting", "professori"),
    item("the car inspection", "la revisione dell'auto", "inspection", "revisione"),
    item("the eye test", "la visita oculistica", "eye test", "oculist"),
]

VISIT_PURPOSES = [
    item("help with the shelves", "aiutarci con le mensole", "shelves"),
    item("bring the big drill", "portare il trapano grande", "drill"),
    item("borrow the ladder", "prendere in prestito la scala", "ladder"),
    item("drop off the boxes", "lasciare le scatole", "boxes"),
    item("water the plants", "annaffiare le piante", "plants"),
    item("look at the router", "dare un'occhiata al router", "router"),
    item("bring the folding table", "portare il tavolo pieghevole", "folding table"),
    item("help with the move", "aiutarci con il trasloco", "the move"),
]

PURCHASES = [
    item("milk", "il latte", "milk", "latte"),
    item("bread", "il pane", "bread", " pane"),
    item("coffee", "il caffè", "coffee", "caffe"),
    item("batteries", "le batterie", "batter"),
    item("light bulbs", "le lampadine", "bulb", "lampadin"),
    item("stamps", "i francobolli", "stamp", "francobol"),
    item("detergent", "il detersivo", "detergent", "detersivo"),
    item("cat food", "il cibo per il gatto", "cat food", "gatto"),
    item("candles", "le candele", "candle", "candel"),
    item("sugar", "lo zucchero", "sugar", "zucchero"),
    item("brown rice", "il riso integrale", "brown rice", "riso integrale"),
    item("olive oil", "l'olio d'oliva", "olive oil", "olio"),
    item("tomatoes", "i pomodori", "tomato", "pomodor"),
    item("flour", "la farina", "flour", "farina"),
    item("toilet paper", "la carta igienica", "toilet paper", "carta igienica"),
]

COLLECTIONS = [
    item("the parcel", "il pacco", "parcel", "package", "pacco"),
    item("the dry cleaning", "i vestiti in lavanderia", "dry clean", "lavander"),
    item("the library books", "i libri in biblioteca", "library", "bibliotec"),
    item("the ID pictures", "le foto tessera", "id picture", "tessera"),
    item("the new bike", "la bici nuova", "bike", "bici"),
    item("the new glasses", "gli occhiali nuovi", "glasses", "occhiali"),
    item("the concert tickets", "i biglietti del concerto", "ticket", "bigliett"),
    item("the tax forms", "i moduli delle tasse", "tax form", "moduli"),
    item("the prescription", "la ricetta", "prescription", "ricetta"),
    item("the suitcase", "la valigia", "suitcase", "valigia"),
]

WORRIES = [
    item("Thursday's presentation", "la presentazione di giovedì", "presentation", "presentazione"),
    item("the electricity bill", "la bolletta della luce", "electricity", "bolletta"),
    item("my mother's test results", "gli esami di mia madre", "mother", "madre"),
    item("the exam next week", "l'esame della prossima settimana", "exam", "esame"),
    item("the cost of the car work", "il costo dei lavori sull'auto", "car work", "lavori"),
    item("the landlord's visit", "la visita del padrone di casa", "landlord", "padrone"),
    item("my annual review", "la valutazione annuale", "annual review", "valutazione"),
    item("the class trip", "la gita scolastica", "class trip", "gita"),
    item("the surgery on Monday", "l'intervento di lunedì", "surgery", "intervento"),
    item("the wedding speech", "il discorso al matrimonio", "speech", "discorso"),
    item("the new job", "il nuovo lavoro", "new job", "nuovo lavoro"),
]

RELATIONSHIPS = [
    item("my cousin", "mio cugino", "cousin", "cugin"),
    item("my neighbour", "il mio vicino di casa", "neighbo", "vicino"),
    item("my old colleague", "il mio ex collega", "colleague", "collega"),
    item("my childhood friend", "il mio amico d'infanzia", "childhood", "infanzia"),
    item("my godfather", "il mio padrino", "godfather", "padrino"),
    item("my barber", "il mio barbiere", "barber", "barbier"),
    item("my piano teacher", "il mio insegnante di pianoforte", "piano", "pianoforte"),
    item("my flatmate from uni", "il mio coinquilino dell'università", "flatmate", "coinquilin"),
    item("my personal trainer", "il mio personal trainer", "trainer"),
    item("my brother-in-law", "mio cognato", "brother-in-law", "cognato"),
    item("my uncle", "mio zio", "uncle", " zio"),
    item("my boss", "il mio capo", "boss", " capo"),
    item("my best man", "il mio testimone di nozze", "best man", "testimone"),
]

LOCATION_ITEMS = [
    item("the spare keys", "le chiavi di scorta", "spare key", "scorta"),
    item("the passport", "il passaporto", "passport", "passaporto"),
    item("the warranty papers", "i documenti della garanzia", "warranty", "garanzia"),
    item("the Christmas lights", "le luci di Natale", "christmas", "natale"),
    item(
        "the first-aid kit", "la cassetta di pronto soccorso", "first-aid", "first aid", "soccorso"
    ),
    item("the sleeping bags", "i sacchi a pelo", "sleeping bag", "sacchi a pelo"),
    item("the toolbox", "la cassetta degli attrezzi", "toolbox", "attrezzi"),
    item("the old photo albums", "gli album di famiglia", "album"),
]

LOCATION_PLACES = [
    item("in the garage", "nel garage", "garage"),
    item("in the top drawer", "nel primo cassetto", "drawer", "cassetto"),
    item("in the wardrobe", "nell'armadio", "wardrobe", "armadio"),
    item("in the attic", "in soffitta", "attic", "soffitta"),
    item("in the cellar", "in cantina", "cellar", "cantina"),
    item("in the blue box", "nella scatola blu", "blue", " blu"),
    item("in the kitchen cupboard", "nella credenza della cucina", "cupboard", "credenza"),
    item("in the hall chest", "nella cassapanca dell'ingresso", "chest", "cassapanca"),
]

ALLERGENS = [
    item("tree nuts", "la frutta secca", "tree nut", "frutta secca"),
    item("shellfish", "i crostacei", "shellfish", "crostace"),
    item("eggs", "le uova", "egg", " uova"),
    item("gluten", "il glutine", "gluten", "glutine"),
    item("lactose", "il lattosio", "lactose", "lattosio"),
    item("peanuts", "le arachidi", "peanut", "arachid"),
    item("soy", "la soia", "soy", "soia"),
    item("kiwi", "il kiwi", "kiwi"),
    item("strawberries", "le fragole", "strawberr", "fragol"),
    item("mushrooms", "i funghi", "mushroom", "fung"),
]

# Names must not be substrings of each other or of any keyword (checked by the tests).
REL_NAMES = [
    "Alberto", "Dario", "Edoardo", "Fabrizio", "Jacopo", "Lorenzo", "Nicola",
    "Pietro", "Stefano", "Tommaso", "Umberto", "Achille", "Cesare", "Emanuele",
]  # fmt: skip
VISIT_NAMES = [
    "Gaetano", "Leonardo", "Orlando", "Riccardo", "Ubaldo", "Bruno", "Domenico",
    "Filippo", "Gabriele", "Mauro", "Oscar", "Teodoro", "Ettore",
    "Bianca", "Carlotta", "Giorgia", "Ilaria", "Matilde", "Ottavia", "Raffaella",
    "Valeria", "Viviana", "Barbara", "Donatella", "Federica", "Ginevra", "Isabella",
    "Margherita", "Nadia", "Patrizia", "Silvia", "Tiziana", "Vittoria", "Zaira",
    "Agnese", "Camilla", "Elisa", "Irene", "Livia", "Noemi", "Paola",
]  # fmt: skip

# Largest number of facts of each kind one Conversation can hold without reusing an entity.
CAPS = {
    "appointment": len(APPOINTMENTS),
    "purchase": len(PURCHASES),
    "collect": len(COLLECTIONS),
    "worry": len(WORRIES),
    "relationship": len(REL_NAMES),
    "location": len(LOCATION_ITEMS),
    "allergy": len(ALLERGENS),
    "visit": len(VISIT_NAMES),
}
WEIGHTS = {
    "appointment": 14,
    "purchase": 14,
    "collect": 9,
    "worry": 9,
    "relationship": 10,
    "location": 8,
    "allergy": 8,
    "visit": 28,
}

# ------------------------------------------------------------------------- templates

TEMPLATES: dict[str, dict[str, list[str]]] = {
    "appointment": {
        "en": [
            "I have {what_en} on {day_en} at {t_en}.",
            "I've got {what_en} on {day_en} at {t_en}, so I can't do anything then.",
            "Remember I have {what_en} on {day_en} at {t_en}.",
        ],
        "it": [
            "Ho {what_it} {day_it} alle {t_it}.",
            "{day_it} alle {t_it} ho {what_it}, quindi non ci sono.",
            "Ricordatevi che ho {what_it} {day_it} alle {t_it}.",
        ],
        "cs": [
            "Ho {what_it} on {day_en} at {t_en}.",
            "I have {what_en} {day_it} alle {t_it}.",
        ],
    },
    "visit": {
        "en": [
            "{name} is coming round on {day_en} to {purpose_en}.",
            "{name} said they'll drop by on {day_en} to {purpose_en}.",
        ],
        "it": [
            "{name} passa {day_it} per {purpose_it}.",
            "{name} ha detto che viene {day_it} per {purpose_it}.",
        ],
        "cs": [
            "{name} is coming {day_it} per {purpose_it}.",
            "{name} passa on {day_en} to {purpose_en}.",
        ],
    },
    "purchase": {
        "en": [
            "I'll buy {item_en} on the way home.",
            "We're out of {item_en}, I'll get some tomorrow.",
        ],
        "it": [
            "Compro io {item_it} tornando a casa.",
            "Abbiamo finito {item_it}, domani ci penso io.",
        ],
        "cs": [
            "Compro io {item_en} on the way home.",
            "We're out of {item_it}, domani ci penso io.",
        ],
    },
    "collect": {
        "en": [
            "I'll go and collect {item_en} tomorrow.",
            "I'll swing by and pick up {item_en} after dinner.",
        ],
        "it": ["Domani vado a ritirare {item_it}.", "Passo a ritirare {item_it} dopo cena."],
        "cs": [
            "Domani vado a ritirare {item_en}, I'll be quick.",
            "I'll pick up {item_it} dopo cena.",
        ],
    },
    "worry": {
        "en": [
            "I'm worried about {item_en}.",
            "I keep thinking about {item_en}, I can't switch off.",
        ],
        "it": [
            "Sono preoccupata per {item_it}.",
            "Ho in testa solo una cosa: {item_it}, e sono in ansia.",
        ],
        "cs": [
            "I'm worried about {item_it}, davvero.",
            "Sono in ansia, I keep thinking about {item_en}.",
        ],
    },
    "relationship": {
        "en": ["{name} is {rel_en}, we go way back.", "Did I tell you? {name} is {rel_en}."],
        "it": [
            "{name} è {rel_it}, ci conosciamo da una vita.",
            "Te l'avevo detto? {name} è {rel_it}.",
        ],
        "cs": ["{name} è {rel_en}, we go way back.", "Did I tell you? {name} is {rel_it}."],
    },
    "location": {
        "en": ["I left {item_en} {place_en}.", "Remember: I left {item_en} {place_en}."],
        "it": ["Ho lasciato {item_it} {place_it}.", "Ricordate: ho lasciato {item_it} {place_it}."],
        "cs": ["I left {item_en} {place_it}.", "Ho lasciato {item_it} {place_en}."],
    },
    "allergy": {
        "en": [
            "I can't eat {item_en}, I'm allergic.",
            "Please remember I'm allergic to {item_en}.",
        ],
        "it": [
            "Non posso mangiare {item_it}, ho un'allergia.",
            "Ricordatevi che non posso mangiare {item_it}, ho un'allergia.",
        ],
        "cs": [
            "I can't eat {item_en}, ho un'allergia.",
            "Non posso mangiare {item_it}, I'm allergic.",
        ],
    },
}

NOISE = {
    "en": [
        "Ugh, it's so hot today.",
        "What's for dinner?",
        "Did you see the match last night?",
        "I can't find the remote.",
        "This tea is too hot.",
        "Is anyone watching this?",
        "I really need a holiday.",
        "It looks like rain.",
        "Can you turn the music down a bit?",
        "Honestly, I'm not hungry.",
        "That film was way too long.",
        "Did you hear that noise outside?",
        "The traffic was terrible this morning.",
        "I love this song.",
        "Pass me the salt, please.",
        "Can someone open the window?",
        "I'm going to have a shower.",
        "Ha, that's funny.",
        "Oh, come on!",
        "Yes, exactly.",
        "Hm, I'm not sure.",
        "It's freezing in here.",
        "Has anyone seen the news?",
        "I think I'll go to bed early.",
        "Good morning!",
        "Good night, everyone.",
        "What time is it?",
        "Ha, that's true.",
        "Don't make me laugh.",
        "That reminds me of last summer.",
        "I'm so bored.",
        "Wow, look at that sky.",
        "Whatever you want is fine.",
        "I might watch something later.",
        "Not again.",
        "I can't believe how fast this week went.",
        "Shh, I'm trying to listen.",
        "Right, where was I?",
        "Mm, that smells good.",
        "It's all a bit much, isn't it?",
    ],
    "it": [
        "Che caldo oggi.",
        "Cosa c'è per cena?",
        "Hai visto la partita ieri sera?",
        "Non trovo il telecomando.",
        "Questo tè è troppo caldo.",
        "Qualcuno sta guardando questa roba?",
        "Ho proprio bisogno di una vacanza.",
        "Sembra che stia per piovere.",
        "Puoi abbassare un po' la musica?",
        "Che film lungo.",
        "Ma sì, dai.",
        "Boh, non saprei.",
        "Qui si gela.",
        "Hai sentito il telegiornale?",
        "Credo che andrò a letto presto.",
        "Buongiorno!",
        "Buonanotte a tutti.",
        "Che ore sono?",
        "Ah, è vero.",
        "Che rumore fuori, hai sentito?",
        "C'era un traffico terribile stamattina.",
        "Adoro questa canzone.",
        "Passami il sale, per favore.",
        "Qualcuno può aprire la finestra?",
        "Faccio una doccia.",
        "Che ridere.",
        "Dai, su!",
        "Esatto.",
        "Mah.",
        "Che noia.",
        "Mi ricorda l'estate scorsa.",
        "Guarda che cielo.",
        "Va bene tutto quello che volete.",
        "Magari guardo qualcosa dopo.",
        "Di nuovo no.",
        "Non ci credo, questa settimana è volata.",
        "Zitti, sto cercando di sentire.",
        "Allora, dov'ero rimasto?",
        "Mm, che profumino.",
        "È tutto un po' troppo, no?",
    ],
    "cs": [
        "Che caldo, honestly I can't stand it.",
        "Boh, I don't know, forse domani.",
        "Ok, va bene, whatever you want.",
        "That was un film troppo lungo.",
        "Mamma mia, what a day.",
        "Dai, let's go.",
        "Ma sì, why not.",
        "Che noia, I'm so bored.",
        "Hai visto? That's insane.",
        "Allora, shall we?",
        "Che freddo, it's freezing in here.",
        "Esatto, that's what I said.",
        "Ma dai, seriously?",
        "Mah, I'm not sure.",
        "Buonanotte, see you tomorrow.",
    ],
}

ACKS = {
    "en": ["Ok.", "Sure.", "Got it.", "Thanks.", "Right.", "Perfect.", "Alright, noted."],
    "it": ["Ok.", "Certo.", "Va bene.", "Grazie.", "Perfetto.", "D'accordo."],
    "cs": ["Ok, va bene.", "Perfetto, thanks.", "Sure, grazie."],
}


# ------------------------------------------------------------------------- rendering


@dataclass(frozen=True)
class Fact:
    kind: str
    text: str
    source: str
    match: list[list[str]]  # what a memory must contain to cover this fact
    disc: list[list[str]]  # the entity groups alone, used by the collision tests


def _time(hour: int) -> tuple[str, str]:
    en = "noon" if hour == 12 else (f"{hour - 12}pm" if hour > 12 else f"{hour}am")
    return en, str(hour)


def _cap(text: str) -> str:
    return text[0].upper() + text[1:]


def render(
    kind: str,
    spec: object,
    lang: str,
    variant: int,
    source: str,
    day: Item | None = None,
    hour: int = 10,
    purpose: Item | None = None,
) -> Fact:
    """Render one fact. `spec` is the identifying entity: an Item, a name, or a tuple."""
    day = day or DAYS[0]
    purpose = purpose or VISIT_PURPOSES[0]
    t_en, t_it = _time(hour)
    keys = {
        "day_en": day.en,
        "day_it": day.it,
        "t_en": t_en,
        "t_it": t_it,
        "purpose_en": purpose.en,
        "purpose_it": purpose.it,
    }
    day_group = list(day.alts)
    if kind == "appointment":
        keys |= {"what_en": spec.en, "what_it": spec.it}
        disc = [list(spec.alts)]
        match = disc + [day_group]
    elif kind == "visit":
        keys["name"] = spec
        disc = [[spec.lower()]]
        match = disc + [day_group]
    elif kind in ("purchase", "collect", "worry", "allergy"):
        keys |= {"item_en": spec.en, "item_it": spec.it}
        disc = [list(spec.alts)]
        match = disc
    elif kind == "relationship":
        name, rel = spec
        keys |= {"name": name, "rel_en": rel.en, "rel_it": rel.it}
        disc = [[name.lower()], list(rel.alts)]
        match = disc
    elif kind == "location":
        thing, place = spec
        keys |= {
            "item_en": thing.en,
            "item_it": thing.it,
            "place_en": place.en,
            "place_it": place.it,
        }
        disc = [list(thing.alts), list(place.alts)]
        match = disc
    else:
        raise ValueError(kind)
    options = TEMPLATES[kind][lang]
    text = _cap(options[variant % len(options)].format(**keys))
    return Fact(kind, text, source, match, disc)


def all_entries() -> list[tuple[str, object]]:
    """Every identifying entity of every kind, for exhaustive collision tests."""
    pools = {
        "appointment": APPOINTMENTS,
        "purchase": PURCHASES,
        "collect": COLLECTIONS,
        "worry": WORRIES,
        "allergy": ALLERGENS,
    }
    entries: list[tuple[str, object]] = [(k, s) for k, pool in pools.items() for s in pool]
    entries += [("visit", n) for n in VISIT_NAMES]
    entries += [
        ("relationship", (n, RELATIONSHIPS[i % len(RELATIONSHIPS)]))
        for i, n in enumerate(REL_NAMES)
    ]
    entries += [("relationship", (REL_NAMES[0], r)) for r in RELATIONSHIPS]
    entries += [
        ("location", (t, LOCATION_PLACES[i % len(LOCATION_PLACES)]))
        for i, t in enumerate(LOCATION_ITEMS)
    ]
    entries += [("location", (LOCATION_ITEMS[0], p)) for p in LOCATION_PLACES]
    return entries


# ----------------------------------------------------------------- conversation builder


def _weighted(rng: random.Random, options: list[tuple[str, int]]) -> str:
    names, weights = zip(*options, strict=True)
    return rng.choices(names, weights)[0]


def plan_kinds(rng: random.Random, n: int, fixed: dict[str, int] | None = None) -> list[str]:
    """Which kinds of facts a Conversation holds, never exceeding what the pools allow."""
    if fixed:
        kinds = [k for k, count in fixed.items() for _ in range(min(count, CAPS[k]))]
        rng.shuffle(kinds)
        return kinds
    counts = dict.fromkeys(CAPS, 0)
    for _ in range(n):
        open_kinds = [(k, w) for k, w in WEIGHTS.items() if counts[k] < CAPS[k]]
        if not open_kinds:
            break
        counts[_weighted(rng, open_kinds)] += 1
    return [k for k, c in counts.items() for _ in range(c)]


class _Bags:
    """Shuffled pools handed out one entity at a time, so none repeats in a Conversation."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._bags = {
            "appointment": rng.sample(APPOINTMENTS, len(APPOINTMENTS)),
            "purchase": rng.sample(PURCHASES, len(PURCHASES)),
            "collect": rng.sample(COLLECTIONS, len(COLLECTIONS)),
            "worry": rng.sample(WORRIES, len(WORRIES)),
            "allergy": rng.sample(ALLERGENS, len(ALLERGENS)),
            "visit": rng.sample(VISIT_NAMES, len(VISIT_NAMES)),
            "rel_name": rng.sample(REL_NAMES, len(REL_NAMES)),
            "loc_item": rng.sample(LOCATION_ITEMS, len(LOCATION_ITEMS)),
        }

    def take(self, kind: str) -> object:
        rng = self._rng
        if kind == "relationship":
            return (self._bags["rel_name"].pop(), rng.choice(RELATIONSHIPS))
        if kind == "location":
            return (self._bags["loc_item"].pop(), rng.choice(LOCATION_PLACES))
        return self._bags[kind].pop()


def _speaker(rng: random.Random, exclude: str | None = None) -> str:
    return _weighted(rng, [(n, w) for n, w in SPEAKERS if n != exclude])


def _lang_for(rng: random.Random, mode: str) -> str:
    return mode if mode != "mixed" else rng.choices(["en", "it", "cs"], [35, 35, 30])[0]


def build_conversation(
    conv_id: str,
    set_name: str,
    seed: str,
    mode: str,
    n_lines: int,
    n_facts: int,
    fixed: dict[str, int] | None = None,
) -> dict:
    rng = random.Random(seed)
    kinds = plan_kinds(rng, n_facts, fixed)
    bags = _Bags(rng)
    n_facts = min(len(kinds), max(n_lines - 1, 0))
    positions = sorted(rng.sample(range(max(n_lines - 1, 1)), n_facts)) if n_facts else []
    seq: list[tuple[str, str] | None] = [None] * n_lines
    expected = []
    for pos, kind in zip(positions, kinds, strict=False):
        source = OWNER if kind == "worry" else _speaker(rng)
        lang = _lang_for(rng, mode)
        fact = render(
            kind,
            bags.take(kind),
            lang,
            rng.randrange(3),
            source,
            day=rng.choice(DAYS),
            hour=rng.randint(9, 18),
            purpose=rng.choice(VISIT_PURPOSES),
        )
        seq[pos] = (source, fact.text)
        expected.append(
            {
                "source": source,
                "match": fact.match,
                "kind": kind,
                "line": pos,
                "lines_total": n_lines,
            }
        )
        nxt = pos + 1
        if nxt < n_lines and seq[nxt] is None and rng.random() < 0.6:
            seq[nxt] = (_speaker(rng, exclude=source), rng.choice(ACKS[_lang_for(rng, mode)]))
    lines = [
        entry if entry is not None else (_speaker(rng), rng.choice(NOISE[_lang_for(rng, mode)]))
        for entry in seq
    ]
    return {
        "id": conv_id,
        "set": set_name,
        "lang": mode,
        "kind": "noise" if not expected else "signal",
        "lines": lines,
        "expected": expected,
    }


# ---------------------------------------------------------------------- S4 scenarios

PATTERNS = [
    {
        "key": "sleep",
        "owner": True,
        "en": [
            "I'm exhausted, I barely slept last night.",
            "Another bad night, I keep waking up at three.",
            "I'm so tired, I haven't slept properly all week.",
        ],
        "it": [
            "Sono distrutta, stanotte ho dormito pochissimo.",
            "Un'altra brutta notte, mi sveglio sempre alle tre.",
            "Sono stanchissima, non dormo bene da giorni.",
        ],
        "alts": [
            "sleep",
            "slept",
            "tired",
            "exhaust",
            "insomnia",
            "bad night",
            "waking up",
            "dorm",
            "stanc",
            "sveglia",
            "brutta notte",
        ],
        "known_en": "Giulia has been sleeping badly this week.",
        "known_it": "Giulia dorme male da questa settimana.",
    },
    {
        "key": "boiler",
        "owner": False,
        "en": [
            "The boiler made that noise again last night.",
            "That boiler noise is back.",
            "Has anyone called someone about the boiler yet?",
        ],
        "it": [
            "La caldaia ha fatto di nuovo quel rumore stanotte.",
            "Quel rumore della caldaia è tornato.",
            "Qualcuno ha chiamato per la caldaia?",
        ],
        "alts": ["boiler", "caldaia"],
        "known_en": "The boiler has been making a noise for days.",
        "known_it": "La caldaia fa rumore da giorni.",
    },
    {
        "key": "money",
        "owner": True,
        "en": [
            "I'm worried about money again.",
            "I keep thinking about the bills, we don't have much left.",
            "I'm scared we won't make it to the end of the month.",
        ],
        "it": [
            "Sono di nuovo preoccupata per i soldi.",
            "Continuo a pensare alle bollette, ci è rimasto poco.",
            "Ho paura che non arriveremo a fine mese.",
        ],
        "alts": ["money", "bill", "financ", "soldi", "bollett", "fine mese", "end of the month"],
        "known_en": "Giulia is worried about money.",
        "known_it": "Giulia è preoccupata per i soldi.",
    },
    {
        "key": "back",
        "owner": False,
        "en": [
            "My back is killing me again.",
            "I can't sit for long, my back hurts.",
            "My back is no better today.",
        ],
        "it": [
            "Mi fa di nuovo male la schiena.",
            "Non riesco a stare seduto, ho mal di schiena.",
            "La schiena non va meglio oggi.",
        ],
        "alts": ["my back", "schiena"],
        "known_en": "Someone in the house has a bad back.",
        "known_it": "Qualcuno in casa ha mal di schiena.",
    },
    {
        "key": "neighbours",
        "owner": False,
        "en": [
            "The neighbours upstairs were loud again last night.",
            "More noise from the neighbours upstairs.",
            "I can't take the neighbours' noise any more.",
        ],
        "it": [
            "I vicini di sopra erano di nuovo rumorosi stanotte.",
            "Ancora rumore dai vicini di sopra.",
            "Non sopporto più il rumore dei vicini.",
        ],
        "alts": ["neighbo", "vicini"],
        "known_en": "The upstairs neighbours are noisy.",
        "known_it": "I vicini di sopra sono rumorosi.",
    },
    {
        "key": "car",
        "owner": False,
        "en": [
            "The car wouldn't start again this morning.",
            "Another problem with the car today.",
            "I think the car needs a proper look.",
        ],
        "it": [
            "La macchina non è partita di nuovo stamattina.",
            "Un altro problema con la macchina oggi.",
            "Secondo me la macchina va controllata bene.",
        ],
        "alts": ["the car", "macchina", "l'auto"],
        "known_en": "The car keeps having problems.",
        "known_it": "La macchina ha di continuo problemi.",
    },
    {
        "key": "headaches",
        "owner": False,
        "en": [
            "I've got another headache.",
            "These headaches are getting worse.",
            "Headache again, third time this week.",
        ],
        "it": [
            "Ho di nuovo mal di testa.",
            "Questi mal di testa peggiorano.",
            "Ancora mal di testa, la terza volta questa settimana.",
        ],
        "alts": ["headache", "mal di testa"],
        "known_en": "Someone keeps getting headaches.",
        "known_it": "Qualcuno ha spesso mal di testa.",
    },
]


def _segment_text(rng: random.Random, mode: str, en: list[str], it: list[str]) -> str:
    lang = _lang_for(rng, mode)
    return rng.choice(it if lang == "it" else en)


_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _scenario(kind: str, mode: str, size: str, index: int, fields: dict) -> dict:
    return {
        "id": f"{kind}-{mode}-{size}-{index}",
        "kind": kind,
        "lang": mode,
        "size": size,
    } | fields


def s4_scenarios() -> list[dict]:
    """Insight scenarios: patterns, single Owner concerns, nothing-to-see, already-known."""
    out: list[dict] = []
    for mode in ("en", "it", "mixed"):
        for size, n_fill in (("small", 3), ("wide", 22)):
            small = size == "small"
            patterns = PATTERNS if small else PATTERNS[:3]
            built: list[tuple[str, dict]] = []
            for p in patterns:
                rng = random.Random(f"s4-pattern-{mode}-{size}-{p['key']}")
                built.append(
                    ("pattern", _build_pattern(rng, mode, n_fill, p, rng.choice([2, 3]), False))
                )
            for i in range(4 if small else 2):
                rng = random.Random(f"s4-single-{mode}-{size}-{i}")
                built.append(("single", _build_single(rng, mode, n_fill, i)))
            for i in range(6 if small else 2):
                rng = random.Random(f"s4-none-{mode}-{size}-{i}")
                built.append(("none", _build_none(rng, mode, n_fill, i)))
            for p in PATTERNS[: 3 if small else 0]:
                rng = random.Random(f"s4-known-{mode}-{size}-{p['key']}")
                built.append(("known", _build_pattern(rng, mode, n_fill, p, 3, True)))
            out += [_scenario(k, mode, size, i, f) for i, (k, f) in enumerate(built, 1)]
    return out


def _assemble(rng, mode, n_fill, planted: list[tuple[str, str]]) -> tuple[list[tuple], set[int]]:
    """Interleave planted segments (who, text) with filler.

    Days advance with position through the week, and the planted slots are redrawn until
    the first and last fall on different days, so a pattern always spans two or more days.
    """
    total = n_fill + len(planted)
    days = [_WEEK[min(6, i * 7 // total)] for i in range(total)]
    while True:
        slots = sorted(rng.sample(range(total), len(planted)))
        if len(planted) < 2 or days[slots[0]] != days[slots[-1]]:
            break
    segments, support, planted_iter = [], set(), iter(planted)
    for i in range(total):
        if i in slots:
            who, text = next(planted_iter)
            support.add(i + 1)
        else:
            who, text = _speaker(rng), rng.choice(NOISE[_lang_for(rng, mode)])
        segments.append((i + 1, days[i], who, text))
    return segments, support


def _build_pattern(rng, mode, n_fill, p, n_mentions: int, known: bool) -> dict:
    speakers = [OWNER] * n_mentions if p["owner"] else [_speaker(rng) for _ in range(n_mentions)]
    texts = [_segment_text(rng, mode, p["en"], p["it"]) for _ in range(n_mentions)]
    segments, support = _assemble(rng, mode, n_fill, list(zip(speakers, texts, strict=True)))
    out = {"segments": segments, "support": support, "match": [list(p["alts"])], "topic": p["key"]}
    if known:
        out["known"] = [p["known_it"] if mode == "it" else p["known_en"]]
    return out


def _build_single(rng, mode, n_fill, i: int) -> dict:
    if i % 2 == 0:
        spec = rng.choice(WORRIES)
        fact = render("worry", spec, _lang_for(rng, mode), rng.randrange(2), OWNER)
    else:
        spec = rng.choice(APPOINTMENTS)
        fact = render(
            "appointment", spec, _lang_for(rng, mode), rng.randrange(3), OWNER, day=rng.choice(DAYS)
        )
    segments, support = _assemble(rng, mode, n_fill, [(OWNER, fact.text)])
    return {
        "segments": segments,
        "support": support,
        "match": [list(fact.disc[0])],
        "topic": fact.kind,
    }


def _build_none(rng, mode, n_fill, i: int) -> dict:
    flavour = i % 3
    if flavour == 0:
        planted = []
    elif flavour == 1:
        spec = rng.choice(APPOINTMENTS)
        fact = render(
            "appointment",
            spec,
            _lang_for(rng, mode),
            rng.randrange(3),
            "Marco",
            day=rng.choice(DAYS),
        )
        planted = [("Marco", fact.text)]
    else:
        first, second = rng.sample(PATTERNS, 2)
        planted = [
            (_speaker(rng), _segment_text(rng, mode, first["en"], first["it"])),
            (_speaker(rng), _segment_text(rng, mode, second["en"], second["it"])),
        ]
    if planted:
        segments, _ = _assemble(rng, mode, max(n_fill, 2), planted)
    else:
        total = n_fill + 2
        segments = [
            (
                k + 1,
                _WEEK[min(6, k * 7 // total)],
                _speaker(rng),
                rng.choice(NOISE[_lang_for(rng, mode)]),
            )
            for k in range(total)
        ]
    return {"segments": segments, "support": set(), "match": [], "topic": f"none{flavour}"}
