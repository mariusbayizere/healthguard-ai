"""Seed vocabulary for synthetic symptom generation.

Phrases are composed from grammatical building blocks per language:

    opener + subject + symptom phrase + onset + closer

Subjects carry the verb ("Mfite" / "I have" / "J'ai" / "Nina"), so a subject
and a symptom phrase concatenate into a grammatical clause in every supported
language. Symptom phrases are grouped by clinical domain and urgency so that
class balance and domain coverage are properties of the generator rather than
something checked after the fact.
"""

from __future__ import annotations

LANGUAGES = ("kinyarwanda", "english", "french", "swahili")

# Clinical domains. Each is present at the urgencies where it is plausible.
DOMAINS = (
    "cardiac_respiratory",
    "haemorrhage_trauma",
    "neurological",
    "obstetric",
    "infectious_fever",
    "gastrointestinal",
    "paediatric",
    "chronic_care",
    "preventive",
)

# ── Sentence frames ───────────────────────────────────────────────────────
# Every slot value within a list must be DISTINCT: examples are generated from
# distinct combination indices, so a repeated value would make two different
# indices render the same sentence. `generate_large_dataset.py` asserts this.
OPENERS: dict[str, tuple[str, ...]] = {
    "kinyarwanda": ("", "Muganga, ", "Muraho, ", "Mfasha, ", "Ndakeneye ubufasha, ", "Nyabuneka, "),
    "english": ("", "Doctor, ", "Hello, ", "Please help, ", "Good morning, ", "Excuse me, "),
    "french": ("", "Docteur, ", "Bonjour, ", "Aidez-moi, ", "S'il vous plait, ", "Excusez-moi, "),
    "swahili": ("", "Daktari, ", "Habari, ", "Nisaidie, ", "Tafadhali, ", "Samahani, "),
}

SUBJECTS: dict[str, tuple[str, ...]] = {
    "kinyarwanda": (
        "Mfite", "Ndumva mfite", "Umwana wanjye afite", "Umugore wanjye afite",
        "Umugabo wanjye afite", "Mama afite", "Papa afite", "Mushiki wanjye afite",
        "Umuturanyi wanjye afite", "Umukecuru afite",
    ),
    "english": (
        "I have", "I am experiencing", "My child has", "My wife has",
        "My husband has", "My mother has", "My father has", "My sister has",
        "My neighbour has", "My grandmother has",
    ),
    "french": (
        "J'ai", "Je ressens", "Mon enfant a", "Ma femme a",
        "Mon mari a", "Ma mere a", "Mon pere a", "Ma soeur a",
        "Mon voisin a", "Ma grand-mere a",
    ),
    "swahili": (
        "Nina", "Ninahisi", "Mtoto wangu ana", "Mke wangu ana",
        "Mume wangu ana", "Mama ana", "Baba ana", "Dada yangu ana",
        "Jirani yangu ana", "Bibi ana",
    ),
}

ONSETS: dict[str, tuple[str, ...]] = {
    "kinyarwanda": (
        "", " kuva ejo", " kuva mu gitondo", " kuva ijoro ryashize",
        " kuva hashize iminsi ibiri", " kuva hashize iminsi itatu",
        " kuva hashize icyumweru", " kuva mu masaha abiri ashize",
        " kuva mu cyumweru gishize", " kuva ubu gitondo cya kare",
    ),
    "english": (
        "", " since yesterday", " since this morning", " since last night",
        " for two days now", " for three days", " for a week",
        " for the past two hours", " since last week", " since early today",
    ),
    "french": (
        "", " depuis hier", " depuis ce matin", " depuis la nuit derniere",
        " depuis deux jours", " depuis trois jours", " depuis une semaine",
        " depuis deux heures", " depuis la semaine derniere", " depuis tot ce matin",
    ),
    "swahili": (
        "", " tangu jana", " tangu asubuhi", " tangu usiku",
        " kwa siku mbili", " kwa siku tatu", " kwa wiki moja",
        " kwa masaa mawili", " tangu wiki iliyopita", " tangu alfajiri",
    ),
}

CONTEXTS: dict[str, tuple[str, ...]] = {
    "kinyarwanda": (
        "", " kandi birushaho kuba bibi", " kandi sinshobora gusinzira",
        " kandi ndahangayitse", " kandi nta miti mfite",
    ),
    "english": (
        "", " and it is getting worse", " and I cannot sleep",
        " and I am worried", " and I have no medicine",
    ),
    "french": (
        "", " et cela empire", " et je ne peux pas dormir",
        " et je suis inquiet", " et je n'ai pas de medicament",
    ),
    "swahili": (
        "", " na inazidi kuwa mbaya", " na siwezi kulala",
        " na nina wasiwasi", " na sina dawa",
    ),
}

CLOSERS: dict[str, tuple[str, ...]] = {
    "kinyarwanda": (
        "", ". Nkora iki?", ". Ndakeneye ubufasha vuba.", ". Mfasha muganga.",
        ". Murakoze.",
    ),
    "english": (
        "", ". What should I do?", ". I need help quickly.", ". Please advise.",
        ". Thank you.",
    ),
    "french": (
        "", ". Que dois-je faire?", ". J'ai besoin d'aide vite.",
        ". Merci de m'aider.", ". Merci beaucoup.",
    ),
    "swahili": (
        "", ". Nifanye nini?", ". Nahitaji msaada haraka.", ". Tafadhali nisaidie.",
        ". Asante.",
    ),
}

# ── Symptom phrases: language -> urgency -> domain -> phrases ─────────────
# Phrases follow a subject, so they begin with the object of "have".
SYMPTOMS: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {
    "kinyarwanda": {
        "CRITICAL": {
            "cardiac_respiratory": (
                "ububabare bukabije mu gituza kandi sinshobora guhumeka",
                "ikibazo cyo guhumeka nabi cyane",
                "umutima utera cyane nk'aho uhagarara",
                "guhumeka nabi n'iminwa ihindura ibara",
                "agahinda gakabije mu gituza kanyura mu kuboko",
            ),
            "haemorrhage_trauma": (
                "amaraso menshi adahagarara",
                "igikomere gikomeye cyavuye amaraso menshi",
                "kuva amaraso mu mazuru bidahagarara",
                "igikomere mu mutwe nyuma yo kugwa",
            ),
            "neurological": (
                "yataye ubwenge ntiyasubiza",
                "kugagara no guhinda umushyitsi",
                "uruhande rumwe rw'umubiri rutagikora",
                "kutabasha kuvuga neza n'umunwa wagoramye",
            ),
            "obstetric": (
                "ububabare bukabije mu nda ndi utwite kandi ndavuye amaraso",
                "kuva amaraso menshi nyuma yo kubyara",
            ),
            "paediatric": (
                "umwana ufite guhinda umushyitsi n'umuriro urenga dogere 40",
                "umwana utagihumeka neza kandi ahindutse ubururu",
            ),
        },
        "URGENT": {
            "infectious_fever": (
                "umuriro mwinshi wa dogere 39",
                "umuriro n'inkorora bikabije",
                "ibimenyetso bya malariya, umuriro n'imbeho",
                "umuriro n'ububabare bw'umubiri wose",
                "umuriro n'uburibwe mu mutwe bukabije",
            ),
            "gastrointestinal": (
                "impiswi zikaze kuva hashize iminsi itatu",
                "kuruka kenshi kandi sindya",
                "ububabare bukabije mu nda",
                "kuruka no gucika intege bikabije",
            ),
            "cardiac_respiratory": (
                "inkorora ikaze n'ibibazo byo guhumeka",
                "ububabare mu gituza iyo mpumeka cyane",
            ),
            "haemorrhage_trauma": (
                "igikomere cyanduye kitukura kandi kirimo amashyira",
                "ububabare bukabije nyuma yo kugwa",
            ),
            "paediatric": (
                "umwana ufite umuriro n'uduheri ku mubiri",
                "umwana ufite umuriro mwinshi kandi ntarya",
            ),
            "chronic_care": (
                "isukari nyinshi mu maraso birenze urugero",
                "umuvuduko w'amaraso uri hejuru cyane",
            ),
        },
        "ROUTINE": {
            "preventive": (
                "gahunda yo gusuzumwa buri mwaka",
                "icyifuzo cyo gupima amaraso",
                "gahunda yo gukingiza umwana",
                "ubujyanama ku mirire myiza",
            ),
            "chronic_care": (
                "icyifuzo cyo kongererwa imiti yanjye",
                "gahunda yo gukurikirana ubuvuzi bwahise",
            ),
            "infectious_fever": (
                "inkorora yoroheje nta muriro",
                "amazuru atemba yoroheje",
            ),
            "gastrointestinal": (
                "kutamererwa neza mu nda nyuma yo kurya",
                "ububabare buke mu nda budakabije",
            ),
            "neurological": (
                "uburibwe buke mu mutwe budakabije",
                "umunaniro woroheje",
            ),
        },
    },
    "english": {
        "CRITICAL": {
            "cardiac_respiratory": (
                "severe chest pain and cannot breathe",
                "serious difficulty breathing",
                "a racing heart that feels like it will stop",
                "breathing trouble and lips turning blue",
                "crushing chest pain spreading to the arm",
            ),
            "haemorrhage_trauma": (
                "heavy bleeding that will not stop",
                "a deep wound losing a lot of blood",
                "a nosebleed that will not stop",
                "a head injury after a bad fall",
            ),
            "neurological": (
                "lost consciousness and is not responding",
                "convulsions and shaking",
                "one side of the body not working",
                "slurred speech and a drooping face",
            ),
            "obstetric": (
                "severe abdominal pain in pregnancy with bleeding",
                "heavy bleeding after giving birth",
            ),
            "paediatric": (
                "convulsions with a fever above 40 degrees",
                "a child struggling to breathe and turning blue",
            ),
        },
        "URGENT": {
            "infectious_fever": (
                "a high fever of 39 degrees",
                "fever with a bad cough",
                "malaria symptoms, fever and chills",
                "fever and aching all over",
                "fever with a severe headache",
            ),
            "gastrointestinal": (
                "severe diarrhoea for three days",
                "repeated vomiting and cannot eat",
                "severe abdominal pain",
                "vomiting and signs of dehydration",
            ),
            "cardiac_respiratory": (
                "a bad cough and trouble breathing",
                "chest pain when breathing deeply",
            ),
            "haemorrhage_trauma": (
                "an infected wound, red and full of pus",
                "severe pain after a fall",
            ),
            "paediatric": (
                "a fever and a rash spreading on the body",
                "a high fever and refusing to eat",
            ),
            "chronic_care": (
                "very high blood sugar readings",
                "a very high blood pressure reading",
            ),
        },
        "ROUTINE": {
            "preventive": (
                "an annual checkup appointment",
                "a request for a blood test",
                "a child vaccination appointment",
                "a question about healthy diet",
            ),
            "chronic_care": (
                "a prescription refill request",
                "a follow up after previous treatment",
            ),
            "infectious_fever": (
                "a mild cough with no fever",
                "a mild runny nose",
            ),
            "gastrointestinal": (
                "mild stomach discomfort after eating",
                "slight stomach pain that is not severe",
            ),
            "neurological": (
                "a mild headache that is not severe",
                "mild tiredness during the day",
            ),
        },
    },
    "french": {
        "CRITICAL": {
            "cardiac_respiratory": (
                "une douleur thoracique severe et je ne peux pas respirer",
                "de grandes difficultes a respirer",
                "un coeur qui bat tres vite comme s'il allait s'arreter",
                "du mal a respirer et les levres bleues",
                "une douleur ecrasante dans la poitrine qui va vers le bras",
            ),
            "haemorrhage_trauma": (
                "un saignement abondant qui ne s'arrete pas",
                "une plaie profonde qui saigne beaucoup",
                "un saignement de nez qui ne s'arrete pas",
                "une blessure a la tete apres une chute",
            ),
            "neurological": (
                "perdu connaissance et ne repond plus",
                "des convulsions et des tremblements",
                "un cote du corps qui ne bouge plus",
                "des difficultes a parler et le visage deforme",
            ),
            "obstetric": (
                "de fortes douleurs au ventre pendant la grossesse avec saignement",
                "un saignement important apres l'accouchement",
            ),
            "paediatric": (
                "des convulsions avec une fievre au dessus de 40 degres",
                "un enfant qui respire mal et devient bleu",
            ),
        },
        "URGENT": {
            "infectious_fever": (
                "une forte fievre de 39 degres",
                "de la fievre avec une mauvaise toux",
                "des symptomes de paludisme, fievre et frissons",
                "de la fievre et des courbatures partout",
                "de la fievre avec un mal de tete severe",
            ),
            "gastrointestinal": (
                "une diarrhee severe depuis trois jours",
                "des vomissements repetes et je ne peux pas manger",
                "de fortes douleurs au ventre",
                "des vomissements et des signes de deshydratation",
            ),
            "cardiac_respiratory": (
                "une mauvaise toux et du mal a respirer",
                "une douleur a la poitrine en respirant fort",
            ),
            "haemorrhage_trauma": (
                "une plaie infectee, rouge et avec du pus",
                "de fortes douleurs apres une chute",
            ),
            "paediatric": (
                "de la fievre et des boutons qui se propagent",
                "une forte fievre et refuse de manger",
            ),
            "chronic_care": (
                "un taux de sucre tres eleve dans le sang",
                "une tension arterielle tres elevee",
            ),
        },
        "ROUTINE": {
            "preventive": (
                "un rendez vous pour un bilan annuel",
                "une demande d'analyse de sang",
                "un rendez vous de vaccination pour l'enfant",
                "une question sur une alimentation saine",
            ),
            "chronic_care": (
                "une demande de renouvellement d'ordonnance",
                "un suivi apres un traitement precedent",
            ),
            "infectious_fever": (
                "une toux legere sans fievre",
                "un nez qui coule legerement",
            ),
            "gastrointestinal": (
                "une gene legere a l'estomac apres avoir mange",
                "une legere douleur au ventre sans gravite",
            ),
            "neurological": (
                "un mal de tete leger sans gravite",
                "une legere fatigue pendant la journee",
            ),
        },
    },
    "swahili": {
        "CRITICAL": {
            "cardiac_respiratory": (
                "maumivu makali ya kifua na siwezi kupumua",
                "shida kubwa ya kupumua",
                "moyo unaopiga haraka kama utasimama",
                "shida ya kupumua na midomo inabadilika bluu",
                "maumivu makali ya kifua yanayoenea mkononi",
            ),
            "haemorrhage_trauma": (
                "kutokwa damu nyingi kusikoisha",
                "jeraha kubwa linalotoa damu nyingi",
                "damu puani isiyoisha",
                "jeraha la kichwa baada ya kuanguka",
            ),
            "neurological": (
                "amepoteza fahamu na hajibu",
                "kifafa na kutetemeka",
                "upande mmoja wa mwili haufanyi kazi",
                "shida ya kuongea na uso umepinda",
            ),
            "obstetric": (
                "maumivu makali ya tumbo wakati wa ujauzito na damu",
                "kutokwa damu nyingi baada ya kujifungua",
            ),
            "paediatric": (
                "kifafa na homa zaidi ya digrii 40",
                "mtoto anayeshindwa kupumua na kuwa bluu",
            ),
        },
        "URGENT": {
            "infectious_fever": (
                "homa kali ya digrii 39",
                "homa na kikohozi kikali",
                "dalili za malaria, homa na baridi",
                "homa na maumivu ya mwili mzima",
                "homa na maumivu makali ya kichwa",
            ),
            "gastrointestinal": (
                "kuhara sana kwa siku tatu",
                "kutapika mara kwa mara na siwezi kula",
                "maumivu makali ya tumbo",
                "kutapika na dalili za upungufu wa maji",
            ),
            "cardiac_respiratory": (
                "kikohozi kikali na shida ya kupumua",
                "maumivu ya kifua ninapopumua sana",
            ),
            "haemorrhage_trauma": (
                "jeraha lililoambukizwa, jekundu na usaha",
                "maumivu makali baada ya kuanguka",
            ),
            "paediatric": (
                "homa na vipele vinavyoenea mwilini",
                "homa kali na anakataa kula",
            ),
            "chronic_care": (
                "sukari nyingi sana katika damu",
                "shinikizo la damu liko juu sana",
            ),
        },
        "ROUTINE": {
            "preventive": (
                "miadi ya uchunguzi wa mwaka",
                "ombi la kupima damu",
                "miadi ya chanjo ya mtoto",
                "swali kuhusu lishe bora",
            ),
            "chronic_care": (
                "ombi la kuongezewa dawa zangu",
                "ufuatiliaji baada ya matibabu ya awali",
            ),
            "infectious_fever": (
                "kikohozi kidogo bila homa",
                "mafua kidogo puani",
            ),
            "gastrointestinal": (
                "usumbufu kidogo wa tumbo baada ya kula",
                "maumivu kidogo ya tumbo yasiyo makali",
            ),
            "neurological": (
                "maumivu kidogo ya kichwa yasiyo makali",
                "uchovu kidogo wakati wa mchana",
            ),
        },
    },
}


# Code-switching pairs seen in Rwandan clinics: the frame comes from the first
# language, the clinical phrase from the second.
MIXED_PAIRS: tuple[tuple[str, str], ...] = (
    ("kinyarwanda", "english"),
    ("english", "kinyarwanda"),
    ("kinyarwanda", "french"),
    ("french", "kinyarwanda"),
    ("swahili", "english"),
    ("english", "swahili"),
)


# --- phrase form and person declarations (option C) -------------------------
#
# A phrase is either a NOUN PHRASE, which the generator places after a subject
# ("Umwana wanjye afite <phrase>"), or a complete patient UTTERANCE, which takes
# no subject ("Ndakorora cyane").
#
# Anything absent from these maps defaults to a noun phrase with no declared
# person, which is exactly v1 behaviour. v2 populates them from the speaker
# briefs.
#
# PERSON records whose symptom it is relative to the speaker:
#   "first" - the speaker has it            ndakorora cyane
#   "third" - someone else has it           umwana wanjye arakorora cyane
# These are different sentences, not one sentence with two subjects, which is
# why person belongs to the phrase rather than to the frame.

PHRASE_FORMS: dict[str, str] = {}
PHRASE_PERSON: dict[str, str] = {}


# Relations a third-person utterance can be about. A phrase written with the
# {REL} placeholder is expanded over all of these at render time, which restores
# the variety the old subject slot supplied without injecting a subject in front
# of a complete sentence.
#
# The speaker confirms the verb phrase is invariant across all eight: only the
# relation itself changes, so one authored sentence fits every one.
RELATIONS: dict[str, tuple[str, ...]] = {
    "kinyarwanda": (
        "Umwana wanjye", "Umugore wanjye", "Umugabo wanjye", "Mama",
        "Papa", "Mushiki wanjye", "Umuturanyi wanjye", "Umukecuru",
    ),
}

# Relations naming a child, for paediatric presentations where the patient is
# the child. Authored by the Kinyarwanda speaker; do not extend without them.
CHILD_RELATIONS: tuple[str, ...] = (
    "Umwana wanjye", "Umuhungu wanjye", "Umukobwa wanjye",
    "Umwuzukuru wanjye", "Umwana w'umuturanyi",
)

REL_PLACEHOLDER = "{REL}"


# Which relations a third-person utterance may be about, per domain.
#
# This is a data-validity constraint, not a grammatical one: {REL} substitutes
# cleanly everywhere, but some substitutions describe patients who do not exist.
# "Umugabo wanjye aratwite" is "my husband is pregnant". A row like that is not
# merely odd - the classifier learns it as a real presentation, and in obstetric
# CRITICAL, the cell where under-triage kills someone, it weakens exactly what
# can least afford weakening.
#
# A domain absent from this map accepts every relation.
DOMAIN_RELATIONS: dict[str, tuple[str, ...]] = {
    # Decided by the Kinyarwanda speaker. Umukecuru is excluded as past
    # childbearing age; umwana wanjye, umugabo wanjye and papa cannot be
    # pregnant or newly delivered.
    "obstetric": ("Umugore wanjye", "Mama", "Mushiki wanjye", "Umuturanyi wanjye"),
    # The patient is the child, so only child relations name them. No adult
    # relation belongs here unless a concept explicitly describes someone
    # reporting about the child.
    "paediatric": CHILD_RELATIONS,
}


# Per-concept override, consulted before DOMAIN_RELATIONS.
#
# Standing distinction from the speaker: linguistic validity is not clinical
# applicability. A domain accepting all eight relations does not mean every
# concept in it applies to every relation - a blood-pressure refill and a
# cervical screening sit in the same domain as a mosquito net.
#
# Where a concept's valid population is narrower than its domain's, name it
# here. Where it is uncertain, flag it for the clinician rather than defaulting
# to the wide set: a wrong wide set puts impossible patients into the corpus,
# and a wrong narrow one only costs variety.
CONCEPT_RELATIONS: dict[str, tuple[str, ...]] = {}
