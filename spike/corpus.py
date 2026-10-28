"""Hand-labelled transcripts for spike S3.

SYNTHETIC: written by the spike author, not recorded from anyone. The labels are
one person's judgement and should be reviewed before the numbers are trusted.

Cast: Giulia is the Owner, Marco and Anna are Housemates, Gino is a Friend.

Each expected memory has:
  source    the speaker who said it
  match     groups of alternatives. A memory matches when every group has at least
            one alternative as a substring (lowercase, accents stripped, tolerant of
            the model writing in English or Italian).
  optional  a reasonable memory the model may extract. Counts as correct when found
            but is not required for recall.
Noise conversations have no expected memories, so anything extracted is false.
"""

from __future__ import annotations

CORPUS: list[dict] = [
    # ---------------------------------------------------------------- English
    {
        "id": "en01",
        "lang": "en",
        "lines": [
            ("Marco", "I've got the dentist on Tuesday at 4pm, so I can't do the supermarket run."),
            ("Giulia", "No problem, I'll cover it. Do you need the car?"),
            ("Marco", "No, I'll walk."),
        ],
        "expected": [
            {"source": "Marco", "match": [["dentist"], ["tuesday"], ["4"]]},
            {
                "source": "Giulia",
                "match": [["supermarket", "shopping", "groceries"], ["cover", "will", "take"]],
                "optional": True,
            },
        ],
    },
    {
        "id": "en02",
        "lang": "en",
        "lines": [
            ("Anna", "The parcel from the neighbour still needs picking up."),
            ("Marco", "I'll grab the milk on my way home, I can get the parcel too."),
            ("Anna", "Great. And Gino said he'll come round Saturday to help with the shelves."),
        ],
        "expected": [
            {"source": "Anna", "match": [["parcel", "package"], ["neighbo"]]},
            {"source": "Marco", "match": [["milk"]]},
            {"source": "Anna", "match": [["gino"], ["saturday"], ["shelves", "shelf"]]},
        ],
    },
    {
        "id": "en03",
        "lang": "en",
        "lines": [
            ("Giulia", "This is my friend Gino. We met at university and he comes round a lot."),
            ("Anna", "Nice to meet you properly, Gino."),
        ],
        "expected": [
            {"source": "Giulia", "match": [["gino"], ["university", "college"]]},
        ],
    },
    {
        "id": "en04",
        "lang": "en",
        "lines": [
            ("Giulia", "I'm nervous about Thursday's meeting with the new client."),
            ("Giulia", "I keep going over the numbers in my head."),
        ],
        "expected": [
            {
                "source": "Giulia",
                "match": [["thursday"], ["meeting"], ["nervous", "anxious", "worried"]],
            },
        ],
    },
    {
        "id": "en05",
        "lang": "en",
        "lines": [
            ("Marco", "Do you remember where we left the spare keys?"),
            ("Anna", "No, I thought you had them."),
            ("Marco", "I haven't seen them since the holiday."),
        ],
        "expected": [
            {"source": "Marco", "match": [["key"], ["spare"]]},
            {
                "source": "Marco",
                "match": [["holiday", "vacation"], ["not seen", "haven't seen", "since"]],
                "optional": True,
            },
        ],
    },
    {
        "id": "en06",
        "lang": "en",
        "kind": "noise",
        "lines": [
            ("Marco", "Ugh, where are my glasses?"),
            ("Anna", "On your head."),
            ("Marco", "Ha. Thanks."),
            ("Anna", "This tea is too hot."),
        ],
        "expected": [],
    },
    {
        "id": "en07",
        "lang": "en",
        "lines": [
            ("Marco", "The dentist is on Tuesday."),
            ("Anna", "No, I'm fairly sure it's Wednesday."),
            ("Marco", "Hm. I'll check the email."),
        ],
        "expected": [
            {"source": "Marco", "match": [["dentist"], ["tuesday"]]},
            {"source": "Anna", "match": [["dentist", "appointment"], ["wednesday"]]},
        ],
    },
    {
        "id": "en08",
        "lang": "en",
        "long": True,
        "lines": [
            ("Anna", "Right, shall we go through the week?"),
            ("Giulia", "Go on."),
            ("Anna", "Elena arrives Friday evening and leaves Sunday morning."),
            ("Marco", "I'll pick her up from the station at 7."),
            ("Giulia", "Perfect. And the boiler engineer is coming Wednesday between 2 and 4."),
            ("Anna", "I can't be in on Wednesday, I have the audit."),
            ("Marco", "I'm working from home Wednesday, I'll let him in."),
            ("Giulia", "Thanks. Oh, and the bins go out Thursday night."),
            ("Marco", "Yes, I never forget the bins."),
            ("Anna", "Ha, you forgot last week."),
            ("Marco", "That was one time."),
            ("Giulia", "Also, Gino is bringing the big drill on Saturday for the shelves."),
            ("Anna", "Great. Do we have enough screws?"),
            ("Marco", "Not sure. I'll check the garage."),
            (
                "Giulia",
                "I'm a bit worried about the cost of all this. The boiler could be expensive.",
            ),
            ("Anna", "Let's wait and see what he says."),
        ],
        "expected": [
            {"source": "Anna", "match": [["elena"], ["friday", "venerdi"]]},
            {"source": "Marco", "match": [["station", "stazione"], ["7"]]},
            {"source": "Giulia", "match": [["boiler"], ["wednesday"]]},
            {"source": "Anna", "match": [["audit"]]},
            {"source": "Marco", "match": [["home", "remote"], ["let", "marco", "in"]]},
            {"source": "Giulia", "match": [["bin"]]},
            {"source": "Giulia", "match": [["gino"], ["drill"]]},
            {"source": "Marco", "match": [["screw"]]},
            {"source": "Giulia", "match": [["cost", "expensive"], ["boiler"]]},
            {"source": "Anna", "match": [["forgot", "forget"], ["bin"]], "optional": True},
        ],
    },
    # ---------------------------------------------------------------- Italian
    {
        "id": "it01",
        "lang": "it",
        "lines": [
            ("Marco", "L'appuntamento dal dentista è martedì alle 4."),
            ("Giulia", "Ok, ti accompagno io?"),
            ("Marco", "No, vado a piedi."),
        ],
        "expected": [
            {"source": "Marco", "match": [["dentist"], ["martedi", "tuesday"], ["4"]]},
        ],
    },
    {
        "id": "it02",
        "lang": "it",
        "lines": [
            (
                "Anna",
                "La festa di compleanno di Elena è il 14 marzo, vuole una torta al cioccolato.",
            ),
            ("Marco", "La torta la faccio io."),
            ("Anna", "Perfetto, grazie."),
        ],
        "expected": [
            {"source": "Anna", "match": [["elena"], ["14"], ["marzo", "march"]]},
            {"source": "Marco", "match": [["torta", "cake"]]},
            {"source": "Anna", "match": [["cioccolato", "chocolate"]], "optional": True},
        ],
    },
    {
        "id": "it03",
        "lang": "it",
        "lines": [
            ("Giulia", "Gino è un amico, ci conosciamo dall'università e viene spesso a trovarci."),
            ("Marco", "Sì, l'ho incontrato un paio di volte."),
        ],
        "expected": [
            {"source": "Giulia", "match": [["gino"], ["universit", "college"]]},
        ],
    },
    {
        "id": "it04",
        "lang": "it",
        "lines": [
            ("Giulia", "Sono un po' agitata per la riunione di giovedì con il nuovo cliente."),
            ("Giulia", "Continuo a ripassare i numeri."),
        ],
        "expected": [
            {
                "source": "Giulia",
                "match": [
                    ["giovedi", "thursday"],
                    ["riunione", "meeting"],
                    ["agitat", "nervos", "preoccupat", "ansi", "worried"],
                ],
            },
        ],
    },
    {
        "id": "it05",
        "lang": "it",
        "lines": [
            ("Anna", "La caldaia fa di nuovo quel rumore."),
            ("Marco", "Sì, dovremmo chiamare qualcuno prima dell'inverno."),
            ("Anna", "Lo faccio io domani."),
        ],
        "expected": [
            {"source": "Anna", "match": [["caldaia", "boiler"], ["rumore", "noise"]]},
            {"source": "Marco", "match": [["inverno", "winter"]]},
            {"source": "Anna", "match": [["domani", "tomorrow"]]},
        ],
    },
    {
        "id": "it06",
        "lang": "it",
        "kind": "noise",
        "lines": [
            ("Marco", "Che caldo oggi."),
            ("Anna", "Eh già."),
            ("Marco", "Che c'è per cena?"),
            ("Anna", "Non so, guarda in frigo."),
        ],
        "expected": [],
    },
    {
        "id": "it07",
        "lang": "it",
        "lines": [
            ("Giulia", "Ti ricordi come si chiama il tizio dell'idraulico?"),
            ("Anna", "Non mi viene, forse Bruno?"),
        ],
        "expected": [
            {"source": "Giulia", "match": [["idraulico", "plumber"]]},
            {"source": "Anna", "match": [["bruno"]], "optional": True},
        ],
    },
    {
        "id": "it08",
        "lang": "it",
        "long": True,
        "lines": [
            ("Giulia", "Allora, domenica pranzo da mia madre, saremo in 6."),
            ("Marco", "A che ora?"),
            ("Giulia", "Per le 13. Dobbiamo portare noi il dolce."),
            ("Anna", "Lo prendo io in pasticceria sabato."),
            ("Marco", "Io porto il vino, quello rosso che piace a tua madre."),
            ("Giulia", "Perfetto. Ah, mia madre ha detto che il medico le ha cambiato la terapia."),
            ("Anna", "Sta meglio?"),
            ("Giulia", "Dice di sì ma non so se sia vero. Sono preoccupata."),
            ("Marco", "Magari le telefoniamo venerdì sera."),
            ("Giulia", "Sì, la chiamo io."),
            ("Anna", "Ricordiamoci anche che lunedì è festa, le scuole sono chiuse."),
            ("Marco", "Quindi lunedì possiamo andare al lago?"),
            ("Giulia", "Se non piove. Guardiamo le previsioni."),
        ],
        "expected": [
            {"source": "Giulia", "match": [["pranzo", "lunch"], ["domenica", "sunday"]]},
            {"source": "Anna", "match": [["dolce", "dessert", "pasticceria"]]},
            {"source": "Marco", "match": [["vino", "wine"]]},
            {"source": "Giulia", "match": [["terapia", "therapy", "medic"]]},
            {"source": "Giulia", "match": [["preoccupat", "worried"]]},
            {
                "source": "Giulia",
                "match": [["venerdi", "friday"], ["chiam", "call", "telefon"]],
            },
            {"source": "Anna", "match": [["lunedi", "monday"], ["festa", "holiday", "chius"]]},
            {"source": "Marco", "match": [["lago", "lake"]], "optional": True},
        ],
    },
    # ------------------------------------------------------------------ Mixed
    {
        "id": "mx01",
        "lang": "mixed",
        "lines": [
            ("Giulia", "Ho prenotato il meeting per giovedì, ma I think Marco can't make it."),
            ("Marco", "Sì, giovedì ho il dentista, sorry."),
        ],
        "expected": [
            {"source": "Giulia", "match": [["giovedi", "thursday"], ["meeting"]]},
            {"source": "Marco", "match": [["dentist"], ["giovedi", "thursday"]]},
        ],
    },
    {
        "id": "mx02",
        "lang": "mixed",
        "lines": [
            ("Marco", "I'll buy milk and bread after lunch, ok? Poi passo in farmacia."),
            ("Anna", "Perfetto."),
        ],
        "expected": [
            {"source": "Marco", "match": [["latte", "milk"], ["pane", "bread"]]},
            {"source": "Marco", "match": [["farmacia", "pharmacy"]]},
        ],
    },
    {
        "id": "mx03",
        "lang": "mixed",
        "lines": [
            ("Gino", "La festa di Anna è sabato, so we need to decide cosa portare."),
            ("Anna", "Io porto il vino."),
            ("Gino", "Then I'll bring dessert."),
        ],
        "expected": [
            {"source": "Gino", "match": [["festa", "party"], ["sabato", "saturday"]]},
            {"source": "Anna", "match": [["vino", "wine"]]},
            {"source": "Gino", "match": [["dessert", "dolce"]]},
        ],
    },
    {
        "id": "mx04",
        "lang": "mixed",
        "lines": [
            ("Giulia", "Il plumber verrà domani mattina, I'll be out quindi apri tu."),
            ("Marco", "Ok, a che ora?"),
            ("Giulia", "Between 9 and 10."),
        ],
        "expected": [
            {"source": "Giulia", "match": [["plumber", "idraulico"], ["domani", "tomorrow"]]},
            {"source": "Giulia", "match": [["9"], ["10"]], "optional": True},
        ],
    },
    {
        "id": "mx05",
        "lang": "mixed",
        "kind": "noise",
        "lines": [
            ("Anna", "Oggi mi sento stanco, honestly I just want to stare at the wall."),
            ("Marco", "Mood."),
            ("Anna", "Ahah."),
        ],
        "expected": [],
    },
    {
        "id": "mx06",
        "lang": "mixed",
        "lines": [
            ("Marco", "Mia sorella Elena is coming to stay da venerdì to Sunday."),
            ("Giulia", "Perfetto, preparo la camera degli ospiti."),
        ],
        "expected": [
            {
                "source": "Marco",
                "match": [["elena"], ["venerdi", "friday"], ["domenica", "sunday"]],
            },
            {"source": "Marco", "match": [["elena"], ["sorella", "sister"]], "optional": True},
            {"source": "Giulia", "match": [["camera", "room"]], "optional": True},
        ],
    },
]
