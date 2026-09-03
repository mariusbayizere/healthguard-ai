"""Language-independent triage concept taxonomy.

Clinical structure follows WHO IMCI (Integrated Management of Childhood Illness,
Chart Booklet, WHO 2014, ISBN 978 92 4 150682 3) where the presentation is one
IMCI covers. IMCI addresses children under five, so adult presentations are
marked as outside its scope rather than mapped to it spuriously.

The 2014 chart booklet is "All rights reserved"; no text is reproduced from it.
Clinical concepts are facts and are cited, not copied. All phrasings here are
drafted for this project.
"""

# (domain, urgency, concept_id, english_gloss, imci_reference, english, french)
CONCEPTS = [
 # ---- cardiac_respiratory : 7 new ----
 ("cardiac_respiratory","CRITICAL","CR01","crushing central chest pain spreading to jaw or arm","not IMCI (adult presentation)",
  "a crushing pain in my chest that spreads to my jaw","une douleur ecrasante dans la poitrine qui monte vers la machoire"),
 ("cardiac_respiratory","CRITICAL","CR02","too breathless to complete a sentence","not IMCI (adult presentation)",
  "so breathless I cannot finish a sentence","essouffle au point de ne pas finir une phrase"),
 ("cardiac_respiratory","CRITICAL","CR03","central cyanosis - blue lips or fingertips","IMCI: central cyanosis, severe respiratory distress",
  "my lips and fingertips have turned blue","mes levres et le bout des doigts sont devenus bleus"),
 ("cardiac_respiratory","URGENT","CR04","fast breathing with lower chest wall indrawing","IMCI: chest indrawing -> SEVERE PNEUMONIA",
  "breathing fast with the lower chest pulling in","une respiration rapide avec le bas du thorax qui se creuse"),
 ("cardiac_respiratory","URGENT","CR05","wheeze with chest tightness","IMCI: wheeze (assess for asthma)",
  "wheezing and a tight chest","une respiration sifflante et la poitrine serree"),
 ("cardiac_respiratory","URGENT","CR06","cough over two weeks with weight loss","not IMCI (TB screening, adult)",
  "coughing for more than two weeks and losing weight","une toux depuis plus de deux semaines avec une perte de poids"),
 # EX30 (infectious_fever) collapsed into CR07: the same utterance, and "no fever" is
 # the absence of the infectious sign rather than a reason to file it under fever.
 # CR07 carries the speaker's EX30 wording. See docs/session-state.md.
 ("cardiac_respiratory","ROUTINE","CR07","short mild cough, no fever","IMCI: cough, no pneumonia (green)",
  "a mild cough for a few days without fever","une toux legere depuis quelques jours sans fievre"),

 # ---- infectious_fever : 6 new ----
 # IF07 removed: it was the same concept as EX29 (IMCI fever, no danger sign),
 # which already carries the speaker's own phrasing. See docs/session-state.md.
 ("infectious_fever","CRITICAL","IF01","fever with stiff neck","IMCI: stiff neck -> VERY SEVERE FEBRILE DISEASE",
  "a fever and my neck is stiff","de la fievre et la nuque raide"),
 ("infectious_fever","CRITICAL","IF02","fever with convulsions","IMCI general danger sign: convulsions",
  "a high fever and then a fit","une forte fievre puis des convulsions"),
 ("infectious_fever","CRITICAL","IF03","fever and unable to drink","IMCI general danger sign: not able to drink or breastfeed",
  "feverish and unable to drink anything","de la fievre et incapable de boire quoi que ce soit"),
 ("infectious_fever","URGENT","IF04","fever with chills and sweats for days","IMCI: fever, malaria risk",
  "fever with shivering and sweating for three days","de la fievre avec des frissons et des sueurs depuis trois jours"),
 ("infectious_fever","URGENT","IF05","fever with generalised rash","IMCI: generalised rash -> MEASLES",
  "a fever and a rash all over the body","de la fievre et une eruption sur tout le corps"),
 ("infectious_fever","URGENT","IF06","fever with pain passing urine","not IMCI (adult presentation)",
  "a fever and it burns when I pass urine","de la fievre et des brulures en urinant"),

 # ---- gastrointestinal : 8 new ----
 ("gastrointestinal","CRITICAL","GI01","vomiting everything, cannot keep fluids down","IMCI general danger sign: vomits everything",
  "vomiting everything, I cannot keep water down","je vomis tout, je ne garde meme pas l'eau"),
 ("gastrointestinal","CRITICAL","GI02","vomiting blood","not IMCI (adult presentation)",
  "vomiting blood","je vomis du sang"),
 ("gastrointestinal","CRITICAL","GI03","black tarry stool","not IMCI (adult presentation)",
  "my stool is black like tar","mes selles sont noires comme du goudron"),
 ("gastrointestinal","CRITICAL","GI04","watery diarrhoea with sunken eyes and very slow skin pinch","IMCI: SEVERE DEHYDRATION",
  "watery diarrhoea with sunken eyes and the skin stays pinched","une diarrhee liquide avec les yeux enfonces et la peau qui reste plissee"),
 ("gastrointestinal","URGENT","GI05","blood in the stool","IMCI: blood in stool -> DYSENTERY",
  "blood in my stool","du sang dans les selles"),
 ("gastrointestinal","URGENT","GI06","diarrhoea lasting more than fourteen days","IMCI: PERSISTENT DIARRHOEA",
  "diarrhoea for more than two weeks","une diarrhee depuis plus de deux semaines"),
 ("gastrointestinal","URGENT","GI07","severe abdominal pain that will not settle","not IMCI (adult presentation)",
  "severe stomach pain that will not settle","une douleur au ventre tres forte qui ne passe pas"),
 # GI08 collapsed into EX16/EX17: the same concept, "mild indigestion after
 # eating", already carried by the speaker's own first-pass phrasings. Its
 # anchor was "not IMCI (minor complaint)", so nothing held it apart.

 # ---- haemorrhage_trauma : 6 new ----  (HT01 -> EX18, HT06 -> EX22, both collapsed)
 ("haemorrhage_trauma","CRITICAL","HT02","deep wound with bone visible","not IMCI (trauma)",
  "a deep wound and I can see the bone","une plaie profonde ou l'os est visible"),
 ("haemorrhage_trauma","CRITICAL","HT03","head injury with vomiting and confusion","not IMCI (trauma)",
  "hit my head and now I am vomiting and confused","un coup a la tete puis des vomissements et de la confusion"),
 ("haemorrhage_trauma","CRITICAL","HT04","large burn","not IMCI (trauma)",
  "a burn covering a large part of the body","une brulure sur une grande partie du corps"),
 ("haemorrhage_trauma","URGENT","HT05","limb deformed after a fall","not IMCI (trauma)",
  "my arm is bent out of shape after a fall","le bras est deforme apres une chute"),
 ("haemorrhage_trauma","URGENT","HT07","snake bite","not IMCI (envenomation)",
  "bitten by a snake","mordu par un serpent"),
 ("haemorrhage_trauma","ROUTINE","HT08","small cut, bleeding stopped","not IMCI (minor injury)",
  "a small cut that has stopped bleeding","une petite coupure qui ne saigne plus"),

 # ---- neurological : 3 new ----  (NE01->EX33, NE02->EX32, NE03->EX34, NE04->EX35, NE08->EX36, all collapsed)
 ("neurological","URGENT","NE05","severe headache with vomiting and photophobia","not IMCI (adult presentation)",
  "a severe headache with vomiting and the light hurts my eyes","un mal de tete violent avec vomissements et la lumiere qui fait mal"),
 ("neurological","URGENT","NE06","new confusion today","not IMCI (adult presentation)",
  "confused since this morning, not making sense","confus depuis ce matin, des propos incoherents"),
 ("neurological","URGENT","NE07","repeated fainting","not IMCI (adult presentation)",
  "fainting again and again","des evanouissements a repetition"),

 # ---- chronic_care : 10 new ----
 ("chronic_care","CRITICAL","CC01","diabetic with vomiting, deep breathing and drowsiness","not IMCI (adult DKA)",
  "diabetic, vomiting, breathing deeply and very drowsy","diabetique, je vomis, je respire profondement et je suis tres somnolent"),
 ("chronic_care","CRITICAL","CC02","hypoglycaemia with sweating and confusion","not IMCI (adult)",
  "shaking, sweating and confused, my sugar is low","tremblements, sueurs et confusion, mon sucre est bas"),
 ("chronic_care","URGENT","CC03","very high blood pressure with headache","not IMCI (adult)",
  "my blood pressure is very high and my head aches","ma tension est tres elevee et j'ai mal a la tete"),
 ("chronic_care","URGENT","CC04","swollen legs and breathless lying flat","not IMCI (adult heart failure)",
  "my legs are swollen and I cannot breathe lying down","les jambes enflees et je ne peux pas respirer allonge"),
 ("chronic_care","URGENT","CC05","diabetic foot ulcer not healing","not IMCI (adult)",
  "a sore on my foot that will not heal, I am diabetic","une plaie au pied qui ne guerit pas, je suis diabetique"),
 ("chronic_care","URGENT","CC06","ran out of antiretroviral medicine","not IMCI (adult ART adherence)",
  "I finished my HIV medicine several days ago","j'ai fini mes medicaments contre le VIH il y a plusieurs jours"),
 ("chronic_care","URGENT","CC07","ran out of TB medicine","not IMCI (adult TB adherence)",
  "I have run out of my TB tablets","je n'ai plus mes comprimes contre la tuberculose"),
 ("chronic_care","ROUTINE","CC08","blood pressure medicine refill","not IMCI (routine)",
  "I need a refill of my blood pressure tablets","j'ai besoin de renouveler mes comprimes pour la tension"),
 ("chronic_care","ROUTINE","CC09","routine diabetes review","not IMCI (routine)",
  "my routine diabetes check-up","mon controle habituel du diabete"),
 ("chronic_care","ROUTINE","CC10","routine HIV clinic follow-up","not IMCI (routine)",
  "my routine visit at the HIV clinic","ma visite de routine a la clinique VIH"),

 # ---- paediatric : 10 new ----
 ("paediatric","CRITICAL","PA01","child convulsing","IMCI general danger sign: convulsions",
  "my child is having a fit","mon enfant fait une crise convulsive"),
 ("paediatric","CRITICAL","PA02","child too weak to breastfeed","IMCI general danger sign: not able to drink or breastfeed",
  "my baby is too weak to breastfeed","mon bebe est trop faible pour teter"),
 ("paediatric","CRITICAL","PA03","child unconscious or floppy","IMCI general danger sign: lethargic or unconscious",
  "my child is floppy and will not wake","mon enfant est mou et ne se reveille pas"),
 ("paediatric","CRITICAL","PA04","child breathing fast with chest indrawing","IMCI: chest indrawing -> SEVERE PNEUMONIA",
  "my child breathes fast and the chest pulls in","mon enfant respire vite et le thorax se creuse"),
 ("paediatric","URGENT","PA05","child with diarrhoea and sunken eyes","IMCI: SOME/SEVERE DEHYDRATION",
  "my child has diarrhoea and the eyes look sunken","mon enfant a la diarrhee et les yeux enfonces"),
 ("paediatric","URGENT","PA06","child with fever and rash","IMCI: MEASLES",
  "my child has a fever and spots all over","mon enfant a de la fievre et des boutons partout"),
 ("paediatric","URGENT","PA07","child very thin, not gaining weight","IMCI: ACUTE MALNUTRITION (MUAC/oedema)",
  "my child is very thin and not gaining weight","mon enfant est tres maigre et ne prend pas de poids"),
 ("paediatric","URGENT","PA08","child with ear pain and discharge","IMCI: ACUTE EAR INFECTION",
  "my child's ear hurts and is draining","l'oreille de mon enfant fait mal et coule"),
 ("paediatric","ROUTINE","PA09","child growth monitoring visit","IMCI: care of the well child",
  "bringing my child for growth monitoring","j'amene mon enfant pour le suivi de la croissance"),
 ("paediatric","ROUTINE","PA10","child due for vaccination","IMCI: immunisation schedule",
  "my child is due for vaccination","mon enfant doit recevoir ses vaccins"),

 # ---- preventive : 10 new ----
 ("preventive","URGENT","PR01","household contact of a TB patient","not IMCI (contact tracing)",
  "someone at home has TB and I want to be checked","quelqu'un a la maison a la tuberculose et je veux etre depiste"),
 ("preventive","ROUTINE","PR02","family planning advice","not IMCI (routine)",
  "advice about family planning","des conseils sur la planification familiale"),
 ("preventive","ROUTINE","PR03","HIV test request","not IMCI (routine)",
  "I would like an HIV test","je voudrais faire un test de depistage du VIH"),
 ("preventive","ROUTINE","PR04","collecting a mosquito net","not IMCI (routine)",
  "I came to collect a mosquito net","je viens chercher une moustiquaire"),
 ("preventive","ROUTINE","PR05","first antenatal booking visit","not IMCI (routine, maternal)",
  "my first antenatal visit","ma premiere consultation prenatale"),
 ("preventive","ROUTINE","PR06","blood pressure screening","not IMCI (routine)",
  "I want my blood pressure checked","je veux faire verifier ma tension"),
 ("preventive","ROUTINE","PR07","cervical screening appointment","not IMCI (routine)",
  "an appointment for cervical screening","un rendez-vous pour le depistage du col de l'uterus"),
 ("preventive","ROUTINE","PR08","infant feeding advice","IMCI: assess feeding / counselling",
  "advice on what to feed my young child","des conseils sur l'alimentation de mon jeune enfant"),
 ("preventive","ROUTINE","PR09","deworming for a child","IMCI: routine deworming",
  "deworming tablets for my child","un vermifuge pour mon enfant"),
 ("preventive","ROUTINE","PR10","advice on safe drinking water","not IMCI (health promotion)",
  "advice about making our drinking water safe","des conseils pour rendre l'eau de boisson potable"),
]
