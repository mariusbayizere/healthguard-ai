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

LANGUAGES = ("kinyarwanda",)


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
    "kinyarwanda": (
        '',
        'Muganga, ',
        'Muraho, ',
        'Mfasha, ',
        'Ndakeneye ubufasha, ',
        'Nyabuneka, ',
        'Ndashaka kukubwira ikibazo mfite. ',
        'Mumbabarire, ndashaka kubabwira ikibazo mfite. ',
        'Mfasha vuba, ',
        'Nzanye umwana wanjye, ',
        'Simbizi niba bikomeye ariko, ',
        'Naje hano mbere, ',
    ),
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
        '',
        ' kandi birushaho kuba bibi',
        ' kandi sinshobora gusinzira',
        ' kandi ndahangayitse',
        ' kandi nta miti mfite',
        '. Byatangiye gitunguranye.',
        ' biragenda bikagaruka',
        ' nta miti imfasha',
        ' bikarushaho nijoro',
        '. Abandi bana na bo bafite iki kibazo.',
    ),
}


CLOSERS: dict[str, tuple[str, ...]] = {
    "kinyarwanda": (
        '',
        '. Nkora iki?',
        '. Ndakeneye ubufasha vuba.',
        '. Mfasha muganga.',
        '. Murakoze.',
        '. Ese ibi birakomeye?',
        '. Ntegereze cyangwa nsuzumwe ubu?',
        '. Ni imiti ki nafata?',
        '. Ntabasha kubona amafaranga yo kongera kuza kwa muganga.',
        '. Naje mvuye kure.',
        '. Urakoze.',
    ),
}


SYMPTOMS: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {
    "kinyarwanda": {
        "CRITICAL": {
            "cardiac_respiratory": (
                '{REL} arumva igituza kimuremereye cyane kandi ububabare bukagera no ku rwasaya cyangwa ku kuboko.',
                'Guhumeka birangora cyane ku buryo ntabasha no kuvuga neza.',
                '{REL} ahumeka bimugora cyane ku buryo adashobora no kuvuga neza.',
                'Iminwa yanjye yahindutse ubururu.',
                '{REL} iminwa ye yahindutse ubururu.',
                'mu gituza harandya cyane kandi sinshobora guhumeka neza',
                '{REL} arababara cyane mu gituza kandi ntashobora guhumeka neza.',
                'Mfite ikibazo cyo guhumeka nabi cyane.',
                '{REL} afite ikibazo cyo guhumeka nabi cyane.',
                "umutima uratera cyane kandi nkumva umeze nk'aho uhagarara",
                "{REL} umutima we utera cyane kandi yumva umeze nk'aho uhagarara.",
                'guhumeka birangora cyane kandi iminwa yanjye yahindutse ibara',
                '{REL} ahumeka bimugora cyane kandi iminwa ye yahindutse ibara.',
                'mu gituza harandya cyane kandi ububabare bukagera no ku kuboko',
                '{REL} arababara cyane mu gituza kandi ububabare bukagera no ku kuboko.',
            ),
            "gastrointestinal": (
                'Ndaruka ibyo ndya byose kandi sinshobora no kunywa.',
                '{REL} araruka ibyo arya byose kandi ntashobora no kunywa.',
                'Ndaruka amaraso.',
                '{REL} araruka amaraso.',
                'Mfite umwanda usa umukara.',
                '{REL} afite impiswi zikomeye kandi yagize umwuma.',
            ),
            "haemorrhage_trauma": (
                'ndi kuva amaraso menshi kandi ntahagarara',
                '{REL} ari kuva amaraso menshi kandi ntahagarara.',
                'mfite igikomere gikomeye kirimo kuva amaraso menshi',
                '{REL} afite igikomere gikomeye kirimo kuva amaraso menshi.',
                'Amazuru yanjye arimo ariva imyuna myinshi kandi ntahagarara.',
                '{REL} arimo kuva imyuna mu mazuru kandi ntahagarara.',
                'mfite igikomere ku mutwe nyuma yo kugwa',
                '{REL} afite igikomere ku mutwe nyuma yo kugwa.',
                'Mfite igikomere gikomeye ku buryo igufa rigaragara.',
                '{REL} afite igikomere gikomeye ku buryo igufa rigaragara.',
                'Mfite ubushye bunini ku mubiri.',
                '{REL} afite ubushye bunini ku mubiri.',
            ),
            "infectious_fever": (
                'Mfite umuriro mwinshi kandi nagagaye.',
                '{REL} afite umuriro mwinshi kandi yaragagaye.',
            ),
            "neurological": (
                '{REL} yataye ubwenge kandi ntasubiza.',
                '{REL} yagagaye kandi arimo guhinda umushyitsi.',
                "Uruhande rumwe rw'umubiri we ntirukora.",
                '{REL} ntashobora kuvuga neza kandi umunwa we waragoramye.',
            ),
            "obstetric": (
                'ndatwite, ndababara cyane mu nda kandi ndava amaraso',
                '{REL} aratwite, arababara cyane mu nda kandi arava amaraso.',
                'ndava amaraso menshi nyuma yo kubyara',
                '{REL} arava amaraso menshi nyuma yo kubyara.',
                'Ndatwite kandi nagagaye.',
                '{REL} aratwite kandi yaragagaye.',
                'Ndatwite, umutwe urandya cyane kandi sinshobora kureba neza.',
                '{REL} aratwite kandi umutwe uramubabaza cyane, kandi ntashobora kureba neza.',
                "Ndabyara ariko habanje gusohoka umugozi w'umwana.",
                "{REL} ari kubyara ariko umugozi w'umwana wabanje gusohoka.",
                'Maze umunsi wose mbabara ngerageza kubyara ariko umwana ntarasohoka.',
                '{REL} amaze umunsi wose ari mu bubabare bwo kubyara ariko umwana ntarasohoka.',
                'Nyuma yo kubyara mfite umuriro kandi hari ibintu bisohoka bifite impumuro mbi.',
                'Nyuma yo kubyara, {REL} afite umuriro kandi hari ibintu bisohoka bifite impumuro mbi.',
            ),
            "paediatric": (
                '{REL} ari guhinda umushyitsi kandi afite umuriro uri hejuru ya dogere 40',
                '{REL} afite ikibazo cyo kutabasha guhumeka neza, kandi uruhu rwe rwahindutse ubururu',
            ),
        },
        "URGENT": {
            "cardiac_respiratory": (
                'Iyo mpumeka, numva igituza gifashe kandi mpumeka nkumva hari ijwi ridasanzwe.',
                'Maze ibyumweru birenga bibiri nkorora kandi natangiye no kunanuka.',
                '{REL} amaze ibyumweru birenga bibiri akorora kandi yatangiye no kunanuka.',
                'ndakorora cyane kandi guhumeka birangora',
                '{REL} arakorora cyane kandi ahumeka bimugora.',
                'iyo mpumetse cyane mu gituza harandya',
                'Iyo {REL} ahumetse cyane, arumva mu gituza hamubabaza.',
            ),
            "chronic_care": (
                "Umuvuduko w'amaraso wanjye wazamutse cyane kandi umutwe urandya cyane.",
                "{REL} umuvuduko w'amaraso we wazamutse cyane kandi umutwe uramubabaza cyane.",
                'Nabyimbye ibirenge kandi sinshobora guhumeka neza iyo ndagaramye.',
                '{REL} yabyimbye ibirenge kandi ntashobora guhumeka neza iyo aragaramye.',
                'Mfite igisebe ku kirenge kidakira kandi mfite diyabete.',
                '{REL} afite igisebe ku kirenge kidakira kandi afite diyabete.',
                'Nta miti ya SIDA mfite.',
                '{REL} nta miti ya SIDA afite.',
                "Nta miti y'igituntu mfite.",
                "{REL} nta miti y'igituntu afite.",
                'isukari yo mu maraso yanjye yazamutse cyane',
                '{REL} isukari yo mu maraso ye yazamutse cyane.',
                "Mfite umuvuduko w'amaraso wazamutse cyane.",
                "{REL} afite umuvuduko w'amaraso wazamutse cyane.",
            ),
            "gastrointestinal": (
                'maze iminsi itatu ndwaye impiswi zikomeye',
                '{REL} amaze iminsi itatu arwaye impiswi zikomeye.',
                'ndakomeza kuruka kandi sinshobora kurya',
                '{REL} arakomeza kuruka kandi ntashobora kurya.',
                'Mfite ububabare bukabije mu nda.',
                '{REL} afite ububabare bukabije mu nda.',
                'ndaruka cyane kandi numva mfite intege nke',
                '{REL} araruka cyane kandi yumva afite intege nke.',
                'Mfite impiswi zirimo amaraso.',
                '{REL} afite impiswi zirimo amaraso.',
                'Maze ibyumweru birenga bibiri ndwaye impiswi.',
                '{REL} amaze ibyumweru birenga bibiri arwaye impiswi.',
                'Inda irandya cyane kandi ububabare ntibuhagarara.',
                '{REL} arababara cyane mu nda kandi ububabare ntibuhagarara.',
            ),
            "haemorrhage_trauma": (
                'mfite igikomere cyanduye, kiratukura kandi kirimo amashyira',
                '{REL} afite igikomere cyanduye, kiratukura kandi kirimo amashyira.',
                'naraguye none ndababara cyane',
                '{REL} yaraguye none arababara cyane.',
                'Naguye, ukuguru kuragoramye ariko sinumva ko kuvunitse.',
                "Narumwe n'inzoka.",
                "{REL} yarumwe n'inzoka.",
            ),
            "infectious_fever": (
                'mfite umuriro wa dogere 39',
                '{REL} afite umuriro wa dogere 39.',
                'mfite umuriro mwinshi kandi ndakorora cyane',
                '{REL} afite umuriro mwinshi kandi arakorora cyane.',
                "Mfite ibimenyetso bya malariya, umuriro n'imbeho.",
                "{REL} afite ibimenyetso bya malariya, umuriro n'imbeho.",
                'mfite umuriro kandi numva mfite imbeho, nkeka ko ari malariya',
                'mfite umuriro kandi umutwe urandya cyane',
                '{REL} afite umuriro kandi umutwe uramubabaza cyane.',
                'Mfite umuriro kandi mfite uduheri ku mubiri wose.',
                "{REL} afite umuriro n'uduheri ku mubiri wose.",
            ),
            "neurological": (
                "Mfite ikibazo ku mutwe kandi kirimo guterwa n'urumuri.",
            ),
            "obstetric": (
                'Amazi yamenetse ariko igihe cyo kubyara ntikiragera.',
                '{REL} amazi ye yamenetse ariko igihe cyo kubyara ntikiragera.',
                "Ndumva mbabara nk'ugiye kubyara kandi igihe cyo kubyara kitaragera.",
                "{REL} arababara nk'ugiye kubyara kandi igihe cyo kubyara ntikiragera.",
                'Ndatwite kandi mfite umuriro.',
                '{REL} aratwite kandi afite umuriro.',
                'Ndatwite kandi ndaruka ibyo ndya byose.',
                '{REL} aratwite kandi araruka ibyo arya byose.',
            ),
            "paediatric": (
                '{REL} afite umuriro mwinshi kandi ntarya.',
                'Mfite umuhaha.',
                '{REL} afite umuhaha.',
            ),
            "preventive": (
                'Mu rugo hari umuntu urwaye igituntu kandi ndashaka kwisuzumisha.',
                'Mu rugo hari umuntu urwaye igituntu kandi {REL} ashaka kwisuzumisha.',
            ),
        },
        "ROUTINE": {
            "cardiac_respiratory": (
                'Nkorora gake ariko nta muriro mfite.',
                '{REL} akorora gake ariko nta muriro afite.',
            ),
            "chronic_care": (
                "Ndashaka kongererwa imiti y'umuvuduko w'amaraso.",
                'Ndashaka kujya kwa muganga kwisuzumisha diyabete.',
                'Ndashaka kujya kwa muganga kwisuzumisha SIDA.',
                'ndashaka kongererwa imiti mfata',
                'ndashaka gukomeza kujya kwa muganga kwisuzumisha',
            ),
            "gastrointestinal": (
                'iyo maze kurya numva inda itameze neza',
                'iyo maze kurya numva mu nda ntameze neza',
                'Iyo {REL} amaze kurya, yumva inda itameze neza.',
            ),
            "haemorrhage_trauma": (
                'Mfite igikomere gito kandi amaraso yarahagaze.',
                '{REL} afite igikomere gito kandi amaraso yarahagaze.',
            ),
            "infectious_fever": (
                'mfite umuriro woroheje umaze umunsi umwe, ariko nta kindi kibazo mfite',
                '{REL} afite umuriro woroheje umaze umunsi umwe, ariko nta kindi kibazo afite.',
                'amazuru arantemba gake',
                '{REL} amazuru ye aratemba gake.',
            ),
            "neurological": (
                'umutwe urandya ariko ntabwo cyane',
                'ndumva naniwe ariko si cyane',
            ),
            "obstetric": (
                'Ndatwite kandi ndashaka kujya kwa muganga kwisuzumisha.',
                '{REL} aratwite kandi ashaka kujya kwa muganga kwisuzumisha.',
                'Ndashaka kugirwa inama uko nakonsa umwana.',
            ),
            "paediatric": (
                "Ndashaka ko bapima ibiro by'umwana wanjye.",
                "{REL} ashaka ko bapima ibiro by'umwana we.",
            ),
            "preventive": (
                'Mfite gahunda yo kwisuzumisha buri mwaka.',
                'Ndashaka ko bapima amaraso.',
                'Mfite gahunda yo gukingiza umwana.',
                '{REL} afite gahunda yo gukingiza umwana.',
                'Ndashaka inama ku mirire myiza.',
                '{REL} ashaka inama ku mirire myiza.',
                'Ndashaka ko bapima SIDA.',
                '{REL} ashaka ko bapima SIDA.',
                'Ndashaka guhabwa inzitiramubu.',
                '{REL} ashaka guhabwa inzitiramubu.',
                'Ndatwite kandi ndashaka kwisuzumisha kwa muganga bwa mbere.',
                '{REL} aratwite kandi ashaka kwisuzumisha kwa muganga bwa mbere.',
                "Ndashaka ko bapima umuvuduko w'amaraso.",
                "Ndashaka kwisuzumisha kanseri y'inkondo y'umura.",
                'Ndashaka inama ku biryo byo kugaburira umwana wanjye.',
                '{REL} ashaka inama ku biryo byo kugaburira umwana we.',
                "Ndashaka imiti y'inzoka y'umwana wanjye.",
                "{REL} ashaka imiti y'inzoka y'umwana we.",
                'Ndashaka kugirwa inama ku mazi yo kunywa.',
                '{REL} ashaka kugirwa inama ku mazi yo kunywa.',
            ),
        },
    },
}


MIXED_PAIRS: tuple[tuple[str, str], ...] = ()


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

# Materialised at the v2 freeze from the brief's form column. Every v2 phrase is an utterance; a blank here defaults to noun_phrase and prefixes a subject onto a complete sentence.
PHRASE_FORMS: dict[str, str] = {
    'Amazi yamenetse ariko igihe cyo kubyara ntikiragera.':
        'utterance',
    'Amazuru yanjye arimo ariva imyuna myinshi kandi ntahagarara.':
        'utterance',
    'Guhumeka birangora cyane ku buryo ntabasha no kuvuga neza.':
        'utterance',
    'Iminwa yanjye yahindutse ubururu.':
        'utterance',
    'Inda irandya cyane kandi ububabare ntibuhagarara.':
        'utterance',
    'Iyo mpumeka, numva igituza gifashe kandi mpumeka nkumva hari ijwi ridasanzwe.':
        'utterance',
    'Iyo {REL} ahumetse cyane, arumva mu gituza hamubabaza.':
        'utterance',
    'Iyo {REL} amaze kurya, yumva inda itameze neza.':
        'utterance',
    'Maze ibyumweru birenga bibiri ndwaye impiswi.':
        'utterance',
    'Maze ibyumweru birenga bibiri nkorora kandi natangiye no kunanuka.':
        'utterance',
    'Maze umunsi wose mbabara ngerageza kubyara ariko umwana ntarasohoka.':
        'utterance',
    'Mfite gahunda yo gukingiza umwana.':
        'utterance',
    'Mfite gahunda yo kwisuzumisha buri mwaka.':
        'utterance',
    "Mfite ibimenyetso bya malariya, umuriro n'imbeho.":
        'utterance',
    'Mfite igikomere gikomeye ku buryo igufa rigaragara.':
        'utterance',
    'Mfite igikomere gito kandi amaraso yarahagaze.':
        'utterance',
    'Mfite igisebe ku kirenge kidakira kandi mfite diyabete.':
        'utterance',
    'Mfite ikibazo cyo guhumeka nabi cyane.':
        'utterance',
    "Mfite ikibazo ku mutwe kandi kirimo guterwa n'urumuri.":
        'utterance',
    'Mfite impiswi zirimo amaraso.':
        'utterance',
    'Mfite ububabare bukabije mu nda.':
        'utterance',
    'Mfite ubushye bunini ku mubiri.':
        'utterance',
    'Mfite umuhaha.':
        'utterance',
    'Mfite umuriro kandi mfite uduheri ku mubiri wose.':
        'utterance',
    'Mfite umuriro mwinshi kandi nagagaye.':
        'utterance',
    "Mfite umuvuduko w'amaraso wazamutse cyane.":
        'utterance',
    'Mfite umwanda usa umukara.':
        'utterance',
    'Mu rugo hari umuntu urwaye igituntu kandi ndashaka kwisuzumisha.':
        'utterance',
    'Mu rugo hari umuntu urwaye igituntu kandi {REL} ashaka kwisuzumisha.':
        'utterance',
    'Nabyimbye ibirenge kandi sinshobora guhumeka neza iyo ndagaramye.':
        'utterance',
    'Naguye, ukuguru kuragoramye ariko sinumva ko kuvunitse.':
        'utterance',
    "Narumwe n'inzoka.":
        'utterance',
    "Ndabyara ariko habanje gusohoka umugozi w'umwana.":
        'utterance',
    'Ndaruka amaraso.':
        'utterance',
    'Ndaruka ibyo ndya byose kandi sinshobora no kunywa.':
        'utterance',
    'Ndashaka guhabwa inzitiramubu.':
        'utterance',
    "Ndashaka imiti y'inzoka y'umwana wanjye.":
        'utterance',
    'Ndashaka inama ku biryo byo kugaburira umwana wanjye.':
        'utterance',
    'Ndashaka inama ku mirire myiza.':
        'utterance',
    'Ndashaka ko bapima SIDA.':
        'utterance',
    'Ndashaka ko bapima amaraso.':
        'utterance',
    "Ndashaka ko bapima ibiro by'umwana wanjye.":
        'utterance',
    "Ndashaka ko bapima umuvuduko w'amaraso.":
        'utterance',
    "Ndashaka kongererwa imiti y'umuvuduko w'amaraso.":
        'utterance',
    'Ndashaka kugirwa inama ku mazi yo kunywa.':
        'utterance',
    'Ndashaka kugirwa inama uko nakonsa umwana.':
        'utterance',
    'Ndashaka kujya kwa muganga kwisuzumisha SIDA.':
        'utterance',
    'Ndashaka kujya kwa muganga kwisuzumisha diyabete.':
        'utterance',
    "Ndashaka kwisuzumisha kanseri y'inkondo y'umura.":
        'utterance',
    'Ndatwite kandi mfite umuriro.':
        'utterance',
    'Ndatwite kandi nagagaye.':
        'utterance',
    'Ndatwite kandi ndaruka ibyo ndya byose.':
        'utterance',
    'Ndatwite kandi ndashaka kujya kwa muganga kwisuzumisha.':
        'utterance',
    'Ndatwite kandi ndashaka kwisuzumisha kwa muganga bwa mbere.':
        'utterance',
    'Ndatwite, umutwe urandya cyane kandi sinshobora kureba neza.':
        'utterance',
    "Ndumva mbabara nk'ugiye kubyara kandi igihe cyo kubyara kitaragera.":
        'utterance',
    'Nkorora gake ariko nta muriro mfite.':
        'utterance',
    "Nta miti y'igituntu mfite.":
        'utterance',
    'Nta miti ya SIDA mfite.':
        'utterance',
    'Nyuma yo kubyara mfite umuriro kandi hari ibintu bisohoka bifite impumuro mbi.':
        'utterance',
    'Nyuma yo kubyara, {REL} afite umuriro kandi hari ibintu bisohoka bifite impumuro mbi.':
        'utterance',
    "Umuvuduko w'amaraso wanjye wazamutse cyane kandi umutwe urandya cyane.":
        'utterance',
    "Uruhande rumwe rw'umubiri we ntirukora.":
        'utterance',
    'amazuru arantemba gake':
        'utterance',
    'guhumeka birangora cyane kandi iminwa yanjye yahindutse ibara':
        'utterance',
    'isukari yo mu maraso yanjye yazamutse cyane':
        'utterance',
    'iyo maze kurya numva inda itameze neza':
        'utterance',
    'iyo maze kurya numva mu nda ntameze neza':
        'utterance',
    'iyo mpumetse cyane mu gituza harandya':
        'utterance',
    'maze iminsi itatu ndwaye impiswi zikomeye':
        'utterance',
    'mfite igikomere cyanduye, kiratukura kandi kirimo amashyira':
        'utterance',
    'mfite igikomere gikomeye kirimo kuva amaraso menshi':
        'utterance',
    'mfite igikomere ku mutwe nyuma yo kugwa':
        'utterance',
    'mfite umuriro kandi numva mfite imbeho, nkeka ko ari malariya':
        'utterance',
    'mfite umuriro kandi umutwe urandya cyane':
        'utterance',
    'mfite umuriro mwinshi kandi ndakorora cyane':
        'utterance',
    'mfite umuriro wa dogere 39':
        'utterance',
    'mfite umuriro woroheje umaze umunsi umwe, ariko nta kindi kibazo mfite':
        'utterance',
    'mu gituza harandya cyane kandi sinshobora guhumeka neza':
        'utterance',
    'mu gituza harandya cyane kandi ububabare bukagera no ku kuboko':
        'utterance',
    'naraguye none ndababara cyane':
        'utterance',
    'ndakomeza kuruka kandi sinshobora kurya':
        'utterance',
    'ndakorora cyane kandi guhumeka birangora':
        'utterance',
    'ndaruka cyane kandi numva mfite intege nke':
        'utterance',
    'ndashaka gukomeza kujya kwa muganga kwisuzumisha':
        'utterance',
    'ndashaka kongererwa imiti mfata':
        'utterance',
    'ndatwite, ndababara cyane mu nda kandi ndava amaraso':
        'utterance',
    'ndava amaraso menshi nyuma yo kubyara':
        'utterance',
    'ndi kuva amaraso menshi kandi ntahagarara':
        'utterance',
    'ndumva naniwe ariko si cyane':
        'utterance',
    "umutima uratera cyane kandi nkumva umeze nk'aho uhagarara":
        'utterance',
    'umutwe urandya ariko ntabwo cyane':
        'utterance',
    '{REL} afite gahunda yo gukingiza umwana.':
        'utterance',
    "{REL} afite ibimenyetso bya malariya, umuriro n'imbeho.":
        'utterance',
    '{REL} afite igikomere cyanduye, kiratukura kandi kirimo amashyira.':
        'utterance',
    '{REL} afite igikomere gikomeye kirimo kuva amaraso menshi.':
        'utterance',
    '{REL} afite igikomere gikomeye ku buryo igufa rigaragara.':
        'utterance',
    '{REL} afite igikomere gito kandi amaraso yarahagaze.':
        'utterance',
    '{REL} afite igikomere ku mutwe nyuma yo kugwa.':
        'utterance',
    '{REL} afite igisebe ku kirenge kidakira kandi afite diyabete.':
        'utterance',
    '{REL} afite ikibazo cyo guhumeka nabi cyane.':
        'utterance',
    '{REL} afite ikibazo cyo kutabasha guhumeka neza, kandi uruhu rwe rwahindutse ubururu':
        'utterance',
    '{REL} afite impiswi zikomeye kandi yagize umwuma.':
        'utterance',
    '{REL} afite impiswi zirimo amaraso.':
        'utterance',
    '{REL} afite ububabare bukabije mu nda.':
        'utterance',
    '{REL} afite ubushye bunini ku mubiri.':
        'utterance',
    '{REL} afite umuhaha.':
        'utterance',
    '{REL} afite umuriro kandi umutwe uramubabaza cyane.':
        'utterance',
    '{REL} afite umuriro mwinshi kandi arakorora cyane.':
        'utterance',
    '{REL} afite umuriro mwinshi kandi ntarya.':
        'utterance',
    '{REL} afite umuriro mwinshi kandi yaragagaye.':
        'utterance',
    "{REL} afite umuriro n'uduheri ku mubiri wose.":
        'utterance',
    '{REL} afite umuriro wa dogere 39.':
        'utterance',
    '{REL} afite umuriro woroheje umaze umunsi umwe, ariko nta kindi kibazo afite.':
        'utterance',
    "{REL} afite umuvuduko w'amaraso wazamutse cyane.":
        'utterance',
    '{REL} ahumeka bimugora cyane kandi iminwa ye yahindutse ibara.':
        'utterance',
    '{REL} ahumeka bimugora cyane ku buryo adashobora no kuvuga neza.':
        'utterance',
    '{REL} akorora gake ariko nta muriro afite.':
        'utterance',
    '{REL} amaze ibyumweru birenga bibiri akorora kandi yatangiye no kunanuka.':
        'utterance',
    '{REL} amaze ibyumweru birenga bibiri arwaye impiswi.':
        'utterance',
    '{REL} amaze iminsi itatu arwaye impiswi zikomeye.':
        'utterance',
    '{REL} amaze umunsi wose ari mu bubabare bwo kubyara ariko umwana ntarasohoka.':
        'utterance',
    '{REL} amazi ye yamenetse ariko igihe cyo kubyara ntikiragera.':
        'utterance',
    '{REL} amazuru ye aratemba gake.':
        'utterance',
    '{REL} arababara cyane mu gituza kandi ntashobora guhumeka neza.':
        'utterance',
    '{REL} arababara cyane mu gituza kandi ububabare bukagera no ku kuboko.':
        'utterance',
    '{REL} arababara cyane mu nda kandi ububabare ntibuhagarara.':
        'utterance',
    "{REL} arababara nk'ugiye kubyara kandi igihe cyo kubyara ntikiragera.":
        'utterance',
    '{REL} arakomeza kuruka kandi ntashobora kurya.':
        'utterance',
    '{REL} arakorora cyane kandi ahumeka bimugora.':
        'utterance',
    '{REL} araruka amaraso.':
        'utterance',
    '{REL} araruka cyane kandi yumva afite intege nke.':
        'utterance',
    '{REL} araruka ibyo arya byose kandi ntashobora no kunywa.':
        'utterance',
    '{REL} aratwite kandi afite umuriro.':
        'utterance',
    '{REL} aratwite kandi araruka ibyo arya byose.':
        'utterance',
    '{REL} aratwite kandi ashaka kujya kwa muganga kwisuzumisha.':
        'utterance',
    '{REL} aratwite kandi ashaka kwisuzumisha kwa muganga bwa mbere.':
        'utterance',
    '{REL} aratwite kandi umutwe uramubabaza cyane, kandi ntashobora kureba neza.':
        'utterance',
    '{REL} aratwite kandi yaragagaye.':
        'utterance',
    '{REL} aratwite, arababara cyane mu nda kandi arava amaraso.':
        'utterance',
    '{REL} arava amaraso menshi nyuma yo kubyara.':
        'utterance',
    '{REL} ari guhinda umushyitsi kandi afite umuriro uri hejuru ya dogere 40':
        'utterance',
    "{REL} ari kubyara ariko umugozi w'umwana wabanje gusohoka.":
        'utterance',
    '{REL} ari kuva amaraso menshi kandi ntahagarara.':
        'utterance',
    '{REL} arimo kuva imyuna mu mazuru kandi ntahagarara.':
        'utterance',
    '{REL} arumva igituza kimuremereye cyane kandi ububabare bukagera no ku rwasaya cyangwa ku kuboko.':
        'utterance',
    '{REL} ashaka guhabwa inzitiramubu.':
        'utterance',
    "{REL} ashaka imiti y'inzoka y'umwana we.":
        'utterance',
    '{REL} ashaka inama ku biryo byo kugaburira umwana we.':
        'utterance',
    '{REL} ashaka inama ku mirire myiza.':
        'utterance',
    '{REL} ashaka ko bapima SIDA.':
        'utterance',
    "{REL} ashaka ko bapima ibiro by'umwana we.":
        'utterance',
    '{REL} ashaka kugirwa inama ku mazi yo kunywa.':
        'utterance',
    '{REL} iminwa ye yahindutse ubururu.':
        'utterance',
    '{REL} isukari yo mu maraso ye yazamutse cyane.':
        'utterance',
    "{REL} nta miti y'igituntu afite.":
        'utterance',
    '{REL} nta miti ya SIDA afite.':
        'utterance',
    '{REL} ntashobora kuvuga neza kandi umunwa we waragoramye.':
        'utterance',
    "{REL} umutima we utera cyane kandi yumva umeze nk'aho uhagarara.":
        'utterance',
    "{REL} umuvuduko w'amaraso we wazamutse cyane kandi umutwe uramubabaza cyane.":
        'utterance',
    '{REL} yabyimbye ibirenge kandi ntashobora guhumeka neza iyo aragaramye.':
        'utterance',
    '{REL} yagagaye kandi arimo guhinda umushyitsi.':
        'utterance',
    '{REL} yaraguye none arababara cyane.':
        'utterance',
    "{REL} yarumwe n'inzoka.":
        'utterance',
    '{REL} yataye ubwenge kandi ntasubiza.':
        'utterance',
}


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

# Relations within one household, for services a family member can plausibly
# request on another's behalf. Excludes the neighbour and the unrelated elder.
HOUSEHOLD_RELATIONS: tuple[str, ...] = (
    "Umugore wanjye", "Umugabo wanjye", "Mama", "Papa",
    "Mushiki wanjye", "Umwana wanjye",
)

# Every relation except a child. For concepts whose valid population excludes
# children on SCOPE rather than rarity - a diabetic foot ulcer is a complication
# of years of disease and neuropathy, so it is not that paediatric cases are rare,
# it is that they are not the concept. Contrast NE03/NE04/CC03, where children are
# kept precisely because rarity is not invalidity and under-triage is the failure
# that matters.
#
# Ruled by the speaker 2026-09-04. Umukecuru is included: an elderly woman is an
# adult, and for several of these concepts the most apt one.
ADULT_RELATIONS: tuple[str, ...] = (
    "Umugore wanjye", "Umugabo wanjye", "Mama", "Papa",
    "Mushiki wanjye", "Umuturanyi wanjye", "Umukecuru",
)

# An explicitly empty set means this concept has no third-person form: nobody
# presents on another's behalf for it. That is different from the concept being
# absent, and different from a misconfiguration - see build_families.
NO_RELATIONS: tuple[str, ...] = ()

REL_PLACEHOLDER = "{REL}"

# Sentence-terminal punctuation. The generator drops a phrase's final stop when
# the next slot continues the sentence, and attribution has to know the same set
# so it can match a phrase whose stop was dropped.
SENTENCE_END = ".!?"


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
#
# EMPTY IS NOT "NO RULINGS". The speaker's rulings live in
# review/routine_relation_sets.csv, keyed by concept id; this map is keyed by
# phrase string, because there are no concept ids in this file. Nothing bridged
# the two, so every consumer silently fell back to DOMAIN_RELATIONS - which is
# how EX16 was rendered across eight relations for ruling when its own ruling
# allows five.
#
# Populate it at v2 build time from the rulings:
#
#     python review/relation_sets.py --materialise
#
# That refuses to emit while a ruling would silently discard an authored phrase,
# and tests/test_relation_sets.py pins the behaviour. Do not hand-write entries
# here; the CSV is the record.
# Materialised at the v2 freeze from routine_relation_sets.csv, through the same
# resolver render_third_person.py used to show the speaker each rendering. A
# phrase absent here takes its domain default.
CONCEPT_RELATIONS: dict[str, tuple[str, ...]] = {
    'Iyo {REL} amaze kurya, yumva inda itameze neza.':
        ('Umwana wanjye', 'Umuhungu wanjye', 'Umukobwa wanjye', 'Umwuzukuru wanjye', "Umwana w'umuturanyi"),
    '{REL} afite gahunda yo gukingiza umwana.':
        ('Umugore wanjye', 'Umugabo wanjye', 'Mama', 'Papa', 'Mushiki wanjye', 'Umuturanyi wanjye', 'Umukecuru'),
    '{REL} afite igikomere gito kandi amaraso yarahagaze.':
        ('Umwana wanjye', 'Umuhungu wanjye', 'Umukobwa wanjye', 'Umwuzukuru wanjye', "Umwana w'umuturanyi"),
    '{REL} afite igisebe ku kirenge kidakira kandi afite diyabete.':
        ('Umugore wanjye', 'Umugabo wanjye', 'Mama', 'Papa', 'Mushiki wanjye', 'Umuturanyi wanjye', 'Umukecuru'),
    '{REL} afite umuriro woroheje umaze umunsi umwe, ariko nta kindi kibazo afite.':
        ('Umwana wanjye', 'Umuhungu wanjye', 'Umukobwa wanjye', 'Umwuzukuru wanjye', "Umwana w'umuturanyi"),
    '{REL} akorora gake ariko nta muriro afite.':
        ('Umwana wanjye', 'Umuhungu wanjye', 'Umukobwa wanjye', 'Umwuzukuru wanjye', "Umwana w'umuturanyi"),
    '{REL} amazuru ye aratemba gake.':
        ('Umwana wanjye', 'Umuhungu wanjye', 'Umukobwa wanjye', 'Umwuzukuru wanjye', "Umwana w'umuturanyi"),
    '{REL} aratwite kandi ashaka kwisuzumisha kwa muganga bwa mbere.':
        ('Umugore wanjye', 'Mama', 'Mushiki wanjye', 'Umuturanyi wanjye'),
    '{REL} ashaka guhabwa inzitiramubu.':
        ('Umugore wanjye', 'Umugabo wanjye', 'Mama', 'Papa', 'Mushiki wanjye', 'Umwana wanjye'),
    "{REL} ashaka imiti y'inzoka y'umwana we.":
        ('Umugore wanjye', 'Umugabo wanjye', 'Mama', 'Papa', 'Mushiki wanjye', 'Umuturanyi wanjye', 'Umukecuru'),
    '{REL} ashaka inama ku biryo byo kugaburira umwana we.':
        ('Umugore wanjye', 'Umugabo wanjye', 'Mama', 'Papa', 'Mushiki wanjye', 'Umuturanyi wanjye', 'Umukecuru'),
    '{REL} ashaka ko bapima SIDA.':
        ('Umugore wanjye', 'Umugabo wanjye', 'Mama', 'Papa', 'Mushiki wanjye', 'Umwana wanjye'),
    "{REL} ashaka ko bapima ibiro by'umwana we.":
        ('Umugore wanjye', 'Umugabo wanjye', 'Mama', 'Papa', 'Mushiki wanjye', 'Umuturanyi wanjye', 'Umukecuru'),
    '{REL} ashaka kugirwa inama ku mazi yo kunywa.':
        ('Umugore wanjye', 'Umugabo wanjye', 'Mama', 'Papa', 'Mushiki wanjye', 'Umwana wanjye'),
}


CONTEXTS_BY_URGENCY: dict[str, dict[str, tuple[str, ...]]] = {}
# Materialised at the v2 freeze. CRITICAL loses the pure sign-offs: thanking
# someone trivialises an emergency. '. Nkora iki?' stays - asking what to do is
# a real question in one. URGENT and ROUTINE are deliberately unrestricted.
CLOSERS_BY_URGENCY: dict[str, dict[str, tuple[str, ...]]] = {
    "CRITICAL": {
        "kinyarwanda": (
            '',
            '. Nkora iki?',
            '. Ndakeneye ubufasha vuba.',
            '. Mfasha muganga.',
            '. Ese ibi birakomeye?',
            '. Ntegereze cyangwa nsuzumwe ubu?',
            '. Ni imiti ki nafata?',
            '. Ntabasha kubona amafaranga yo kongera kuza kwa muganga.',
            '. Naje mvuye kure.',
        ),
    },
}


# The ruled CRITICAL closer exclusions, kept as the record of WHY
# CLOSERS_BY_URGENCY looks as it does. '. Murakoze.' was ruled out on
# 2026-09-03: thanking someone trivialises an emergency. '. Urakoze.' arrived
# with the frame fragments at the v2 freeze and is the same sign-off, which the
# original ruling anticipated in as many words. '. Nkora iki?' stays - asking
# what to do is a real question in an emergency.
V2_CRITICAL_CLOSER_EXCLUSIONS: tuple[str, ...] = (". Murakoze.", ". Urakoze.")


PHRASE_VARIANTS: dict[str, str] = {
    'iyo maze kurya numva mu nda ntameze neza':
        'iyo maze kurya numva inda itameze neza',
}


# Materialised at the v2 freeze, from the GENERATING set only - held phrases are not in the inventory and declaring one would make phrase_components raise.
PHRASE_CONCEPTS: dict[str, str] = {
    'Amazi yamenetse ariko igihe cyo kubyara ntikiragera.':
        'OB07',
    'Amazuru yanjye arimo ariva imyuna myinshi kandi ntahagarara.':
        'EX20',
    'Guhumeka birangora cyane ku buryo ntabasha no kuvuga neza.':
        'CR02',
    'Iminwa yanjye yahindutse ubururu.':
        'CR03',
    'Inda irandya cyane kandi ububabare ntibuhagarara.':
        'GI07',
    'Iyo mpumeka, numva igituza gifashe kandi mpumeka nkumva hari ijwi ridasanzwe.':
        'CR05',
    'Iyo {REL} ahumetse cyane, arumva mu gituza hamubabaza.':
        'EX07',
    'Iyo {REL} amaze kurya, yumva inda itameze neza.':
        'EX16',
    'Maze ibyumweru birenga bibiri ndwaye impiswi.':
        'GI06',
    'Maze ibyumweru birenga bibiri nkorora kandi natangiye no kunanuka.':
        'CR06',
    'Maze umunsi wose mbabara ngerageza kubyara ariko umwana ntarasohoka.':
        'OB04',
    'Mfite gahunda yo gukingiza umwana.':
        'EX46',
    'Mfite gahunda yo kwisuzumisha buri mwaka.':
        'EX44',
    "Mfite ibimenyetso bya malariya, umuriro n'imbeho.":
        'EX26',
    'Mfite igikomere gikomeye ku buryo igufa rigaragara.':
        'HT02',
    'Mfite igikomere gito kandi amaraso yarahagaze.':
        'HT08',
    'Mfite igisebe ku kirenge kidakira kandi mfite diyabete.':
        'CC05',
    'Mfite ikibazo cyo guhumeka nabi cyane.':
        'EX02',
    "Mfite ikibazo ku mutwe kandi kirimo guterwa n'urumuri.":
        'NE05',
    'Mfite impiswi zirimo amaraso.':
        'GI05',
    'Mfite ububabare bukabije mu nda.':
        'EX14',
    'Mfite ubushye bunini ku mubiri.':
        'HT04',
    'Mfite umuhaha.':
        'PA08',
    'Mfite umuriro kandi mfite uduheri ku mubiri wose.':
        'IF05',
    'Mfite umuriro mwinshi kandi nagagaye.':
        'IF02',
    "Mfite umuvuduko w'amaraso wazamutse cyane.":
        'EX09',
    'Mfite umwanda usa umukara.':
        'GI03',
    'Mu rugo hari umuntu urwaye igituntu kandi ndashaka kwisuzumisha.':
        'PR01',
    'Mu rugo hari umuntu urwaye igituntu kandi {REL} ashaka kwisuzumisha.':
        'PR01',
    'Nabyimbye ibirenge kandi sinshobora guhumeka neza iyo ndagaramye.':
        'CC04',
    'Naguye, ukuguru kuragoramye ariko sinumva ko kuvunitse.':
        'HT05',
    "Narumwe n'inzoka.":
        'HT07',
    "Ndabyara ariko habanje gusohoka umugozi w'umwana.":
        'OB03',
    'Ndaruka amaraso.':
        'GI02',
    'Ndaruka ibyo ndya byose kandi sinshobora no kunywa.':
        'GI01',
    'Ndashaka guhabwa inzitiramubu.':
        'PR04',
    "Ndashaka imiti y'inzoka y'umwana wanjye.":
        'PR09',
    'Ndashaka inama ku biryo byo kugaburira umwana wanjye.':
        'PR08',
    'Ndashaka inama ku mirire myiza.':
        'EX47',
    'Ndashaka ko bapima SIDA.':
        'PR03',
    'Ndashaka ko bapima amaraso.':
        'EX45',
    "Ndashaka ko bapima ibiro by'umwana wanjye.":
        'PA09',
    "Ndashaka ko bapima umuvuduko w'amaraso.":
        'PR06',
    "Ndashaka kongererwa imiti y'umuvuduko w'amaraso.":
        'CC08',
    'Ndashaka kugirwa inama ku mazi yo kunywa.':
        'PR10',
    'Ndashaka kugirwa inama uko nakonsa umwana.':
        'OB12',
    'Ndashaka kujya kwa muganga kwisuzumisha SIDA.':
        'CC10',
    'Ndashaka kujya kwa muganga kwisuzumisha diyabete.':
        'CC09',
    "Ndashaka kwisuzumisha kanseri y'inkondo y'umura.":
        'PR07',
    'Ndatwite kandi mfite umuriro.':
        'OB09',
    'Ndatwite kandi nagagaye.':
        'OB01',
    'Ndatwite kandi ndaruka ibyo ndya byose.':
        'OB10',
    'Ndatwite kandi ndashaka kujya kwa muganga kwisuzumisha.':
        'OB11',
    'Ndatwite kandi ndashaka kwisuzumisha kwa muganga bwa mbere.':
        'PR05',
    'Ndatwite, umutwe urandya cyane kandi sinshobora kureba neza.':
        'OB02',
    "Ndumva mbabara nk'ugiye kubyara kandi igihe cyo kubyara kitaragera.":
        'OB08',
    'Nkorora gake ariko nta muriro mfite.':
        'CR07',
    "Nta miti y'igituntu mfite.":
        'CC07',
    'Nta miti ya SIDA mfite.':
        'CC06',
    'Nyuma yo kubyara mfite umuriro kandi hari ibintu bisohoka bifite impumuro mbi.':
        'OB05',
    'Nyuma yo kubyara, {REL} afite umuriro kandi hari ibintu bisohoka bifite impumuro mbi.':
        'OB05',
    "Umuvuduko w'amaraso wanjye wazamutse cyane kandi umutwe urandya cyane.":
        'CC03',
    "Uruhande rumwe rw'umubiri we ntirukora.":
        'EX34',
    'amazuru arantemba gake':
        'EX31',
    'guhumeka birangora cyane kandi iminwa yanjye yahindutse ibara':
        'EX04',
    'isukari yo mu maraso yanjye yazamutse cyane':
        'EX08',
    'iyo maze kurya numva inda itameze neza':
        'EX16',
    'iyo maze kurya numva mu nda ntameze neza':
        'EX16',
    'iyo mpumetse cyane mu gituza harandya':
        'EX07',
    'maze iminsi itatu ndwaye impiswi zikomeye':
        'EX12',
    'mfite igikomere cyanduye, kiratukura kandi kirimo amashyira':
        'EX22',
    'mfite igikomere gikomeye kirimo kuva amaraso menshi':
        'EX19',
    'mfite igikomere ku mutwe nyuma yo kugwa':
        'EX21',
    'mfite umuriro kandi numva mfite imbeho, nkeka ko ari malariya':
        'EX27',
    'mfite umuriro kandi umutwe urandya cyane':
        'EX28',
    'mfite umuriro mwinshi kandi ndakorora cyane':
        'EX25',
    'mfite umuriro wa dogere 39':
        'EX24',
    'mfite umuriro woroheje umaze umunsi umwe, ariko nta kindi kibazo mfite':
        'EX29',
    'mu gituza harandya cyane kandi sinshobora guhumeka neza':
        'EX01',
    'mu gituza harandya cyane kandi ububabare bukagera no ku kuboko':
        'EX05',
    'naraguye none ndababara cyane':
        'EX23',
    'ndakomeza kuruka kandi sinshobora kurya':
        'EX13',
    'ndakorora cyane kandi guhumeka birangora':
        'EX06',
    'ndaruka cyane kandi numva mfite intege nke':
        'EX15',
    'ndashaka gukomeza kujya kwa muganga kwisuzumisha':
        'EX11',
    'ndashaka kongererwa imiti mfata':
        'EX10',
    'ndatwite, ndababara cyane mu nda kandi ndava amaraso':
        'EX38',
    'ndava amaraso menshi nyuma yo kubyara':
        'EX39',
    'ndi kuva amaraso menshi kandi ntahagarara':
        'EX18',
    'ndumva naniwe ariko si cyane':
        'EX37',
    "umutima uratera cyane kandi nkumva umeze nk'aho uhagarara":
        'EX03',
    'umutwe urandya ariko ntabwo cyane':
        'EX36',
    '{REL} afite gahunda yo gukingiza umwana.':
        'EX46',
    "{REL} afite ibimenyetso bya malariya, umuriro n'imbeho.":
        'EX26',
    '{REL} afite igikomere cyanduye, kiratukura kandi kirimo amashyira.':
        'EX22',
    '{REL} afite igikomere gikomeye kirimo kuva amaraso menshi.':
        'EX19',
    '{REL} afite igikomere gikomeye ku buryo igufa rigaragara.':
        'HT02',
    '{REL} afite igikomere gito kandi amaraso yarahagaze.':
        'HT08',
    '{REL} afite igikomere ku mutwe nyuma yo kugwa.':
        'EX21',
    '{REL} afite igisebe ku kirenge kidakira kandi afite diyabete.':
        'CC05',
    '{REL} afite ikibazo cyo guhumeka nabi cyane.':
        'EX02',
    '{REL} afite ikibazo cyo kutabasha guhumeka neza, kandi uruhu rwe rwahindutse ubururu':
        'EX41',
    '{REL} afite impiswi zikomeye kandi yagize umwuma.':
        'GI04',
    '{REL} afite impiswi zirimo amaraso.':
        'GI05',
    '{REL} afite ububabare bukabije mu nda.':
        'EX14',
    '{REL} afite ubushye bunini ku mubiri.':
        'HT04',
    '{REL} afite umuhaha.':
        'PA08',
    '{REL} afite umuriro kandi umutwe uramubabaza cyane.':
        'EX28',
    '{REL} afite umuriro mwinshi kandi arakorora cyane.':
        'EX25',
    '{REL} afite umuriro mwinshi kandi ntarya.':
        'EX43',
    '{REL} afite umuriro mwinshi kandi yaragagaye.':
        'IF02',
    "{REL} afite umuriro n'uduheri ku mubiri wose.":
        'IF05',
    '{REL} afite umuriro wa dogere 39.':
        'EX24',
    '{REL} afite umuriro woroheje umaze umunsi umwe, ariko nta kindi kibazo afite.':
        'EX29',
    "{REL} afite umuvuduko w'amaraso wazamutse cyane.":
        'EX09',
    '{REL} ahumeka bimugora cyane kandi iminwa ye yahindutse ibara.':
        'EX04',
    '{REL} ahumeka bimugora cyane ku buryo adashobora no kuvuga neza.':
        'CR02',
    '{REL} akorora gake ariko nta muriro afite.':
        'CR07',
    '{REL} amaze ibyumweru birenga bibiri akorora kandi yatangiye no kunanuka.':
        'CR06',
    '{REL} amaze ibyumweru birenga bibiri arwaye impiswi.':
        'GI06',
    '{REL} amaze iminsi itatu arwaye impiswi zikomeye.':
        'EX12',
    '{REL} amaze umunsi wose ari mu bubabare bwo kubyara ariko umwana ntarasohoka.':
        'OB04',
    '{REL} amazi ye yamenetse ariko igihe cyo kubyara ntikiragera.':
        'OB07',
    '{REL} amazuru ye aratemba gake.':
        'EX31',
    '{REL} arababara cyane mu gituza kandi ntashobora guhumeka neza.':
        'EX01',
    '{REL} arababara cyane mu gituza kandi ububabare bukagera no ku kuboko.':
        'EX05',
    '{REL} arababara cyane mu nda kandi ububabare ntibuhagarara.':
        'GI07',
    "{REL} arababara nk'ugiye kubyara kandi igihe cyo kubyara ntikiragera.":
        'OB08',
    '{REL} arakomeza kuruka kandi ntashobora kurya.':
        'EX13',
    '{REL} arakorora cyane kandi ahumeka bimugora.':
        'EX06',
    '{REL} araruka amaraso.':
        'GI02',
    '{REL} araruka cyane kandi yumva afite intege nke.':
        'EX15',
    '{REL} araruka ibyo arya byose kandi ntashobora no kunywa.':
        'GI01',
    '{REL} aratwite kandi afite umuriro.':
        'OB09',
    '{REL} aratwite kandi araruka ibyo arya byose.':
        'OB10',
    '{REL} aratwite kandi ashaka kujya kwa muganga kwisuzumisha.':
        'OB11',
    '{REL} aratwite kandi ashaka kwisuzumisha kwa muganga bwa mbere.':
        'PR05',
    '{REL} aratwite kandi umutwe uramubabaza cyane, kandi ntashobora kureba neza.':
        'OB02',
    '{REL} aratwite kandi yaragagaye.':
        'OB01',
    '{REL} aratwite, arababara cyane mu nda kandi arava amaraso.':
        'EX38',
    '{REL} arava amaraso menshi nyuma yo kubyara.':
        'EX39',
    '{REL} ari guhinda umushyitsi kandi afite umuriro uri hejuru ya dogere 40':
        'EX40',
    "{REL} ari kubyara ariko umugozi w'umwana wabanje gusohoka.":
        'OB03',
    '{REL} ari kuva amaraso menshi kandi ntahagarara.':
        'EX18',
    '{REL} arimo kuva imyuna mu mazuru kandi ntahagarara.':
        'EX20',
    '{REL} arumva igituza kimuremereye cyane kandi ububabare bukagera no ku rwasaya cyangwa ku kuboko.':
        'CR01',
    '{REL} ashaka guhabwa inzitiramubu.':
        'PR04',
    "{REL} ashaka imiti y'inzoka y'umwana we.":
        'PR09',
    '{REL} ashaka inama ku biryo byo kugaburira umwana we.':
        'PR08',
    '{REL} ashaka inama ku mirire myiza.':
        'EX47',
    '{REL} ashaka ko bapima SIDA.':
        'PR03',
    "{REL} ashaka ko bapima ibiro by'umwana we.":
        'PA09',
    '{REL} ashaka kugirwa inama ku mazi yo kunywa.':
        'PR10',
    '{REL} iminwa ye yahindutse ubururu.':
        'CR03',
    '{REL} isukari yo mu maraso ye yazamutse cyane.':
        'EX08',
    "{REL} nta miti y'igituntu afite.":
        'CC07',
    '{REL} nta miti ya SIDA afite.':
        'CC06',
    '{REL} ntashobora kuvuga neza kandi umunwa we waragoramye.':
        'EX35',
    "{REL} umutima we utera cyane kandi yumva umeze nk'aho uhagarara.":
        'EX03',
    "{REL} umuvuduko w'amaraso we wazamutse cyane kandi umutwe uramubabaza cyane.":
        'CC03',
    '{REL} yabyimbye ibirenge kandi ntashobora guhumeka neza iyo aragaramye.':
        'CC04',
    '{REL} yagagaye kandi arimo guhinda umushyitsi.':
        'EX33',
    '{REL} yaraguye none arababara cyane.':
        'EX23',
    "{REL} yarumwe n'inzoka.":
        'HT07',
    '{REL} yataye ubwenge kandi ntasubiza.':
        'EX32',
}


GROUPED_CONCEPTS: tuple[tuple[str, ...], ...] = (
    ("CC09", "CC10"),
)
