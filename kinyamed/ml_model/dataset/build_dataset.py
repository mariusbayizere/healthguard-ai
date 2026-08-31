import csv
import random
import os

# ─── RAW SYMPTOM DATA ─────────────────────────────────────────────
# Each entry: (symptom_text, language, urgency_label)
# Languages: kinyarwanda, english, mixed

CRITICAL_SYMPTOMS = [
    # Kinyarwanda
    ("Ndumva agahinda mu gituza kenshi kandi sinshobora guhema neza", "kinyarwanda", "CRITICAL"),
    ("Umugabo wanjye arasinziriye ntashobora gusubuka", "kinyarwanda", "CRITICAL"),
    ("Mfite amaraso menshi avuye hanze ntashobora guhagarara", "kinyarwanda", "CRITICAL"),
    ("Umwana wanjye aragorwa no guhema, agira urusaku mu mazuru", "kinyarwanda", "CRITICAL"),
    ("Mfite ibibazo by'umutima, ndumva nk'aho umutima wahagarara", "kinyarwanda", "CRITICAL"),
    ("Sinshobora kuvuga neza, uruhande rumwe rw'umubiri rwanze gukora", "kinyarwanda", "CRITICAL"),
    ("Ndumva nk'aho mpfa, ubushyuhe bwanjye ni 40 degrees", "kinyarwanda", "CRITICAL"),
    ("Mfite ibizunguzungu byinshi kandi nasimbutse inshuro ebyiri", "kinyarwanda", "CRITICAL"),
    ("Umugore wanjye yaravuye amaraso menshi nyuma yo kubyara", "kinyarwanda", "CRITICAL"),
    ("Umwana arakorwa n'ibizunguzungu, amaso ye aragaragara hejuru", "kinyarwanda", "CRITICAL"),
    ("Ndumva umunwa wanjye wagoramye, sinshobora kureba neza", "kinyarwanda", "CRITICAL"),
    ("Mfite umurambo ukabije, sinshobora guhaguruka", "kinyarwanda", "CRITICAL"),
    # English
    ("I have severe chest pain and cannot breathe properly", "english", "CRITICAL"),
    ("Patient is unconscious and not responding to stimulation", "english", "CRITICAL"),
    ("Heavy bleeding that will not stop after 20 minutes", "english", "CRITICAL"),
    ("Child is having convulsions and high fever above 40 degrees", "english", "CRITICAL"),
    ("I think I am having a heart attack, left arm is numb", "english", "CRITICAL"),
    ("Stroke symptoms: face drooping, arm weakness, slurred speech", "english", "CRITICAL"),
    ("Severe allergic reaction, throat is closing up", "english", "CRITICAL"),
    ("Patient fell from height and cannot move legs", "english", "CRITICAL"),
    ("Severe head injury after accident, bleeding from ears", "english", "CRITICAL"),
    ("Difficulty breathing, lips turning blue, oxygen dropping", "english", "CRITICAL"),
    ("Pregnant woman with severe abdominal pain and bleeding", "english", "CRITICAL"),
    ("Child swallowed unknown substance, now vomiting blood", "english", "CRITICAL"),
    # Mixed Kinyarwanda-English
    ("Mfite chest pain ikabije, sinshobora guhema neza since this morning", "mixed", "CRITICAL"),
    ("My husband arasinziriye kandi ntashobora kuwubura, emergency", "mixed", "CRITICAL"),
    ("Ndumva heart yanjye itera cyane kandi mfite dizziness ikabije", "mixed", "CRITICAL"),
    ("Umwana wanjye aragorwa, temperature ye ni 41 degrees, help", "mixed", "CRITICAL"),
    ("Narasimbutse mu rugo, mfite bleeding itahagarara mu mutwe", "mixed", "CRITICAL"),
    ("I cannot breathe, ndumva throat yanjye ifunga slowly", "mixed", "CRITICAL"),
    ("Stroke symptoms, uruhande rumwe rwanjye rwahagaraye kugira action", "mixed", "CRITICAL"),
    ("Pregnant, mfite severe pain mu nda kandi ndavuye amaraso", "mixed", "CRITICAL"),
]

URGENT_SYMPTOMS = [
    # Kinyarwanda
    ("Mfite umuriro ukabije kuva ejo, ubushyuhe ni 39 degrees", "kinyarwanda", "URGENT"),
    ("Ndumva ububabare bukabije mu nda kuva ijoro", "kinyarwanda", "URGENT"),
    ("Mfite inkorora ikabije kandi ndavoma amaraso make", "kinyarwanda", "URGENT"),
    ("Ubushyuhe bwanjye ni 38.5, mfite inkorora n'umunaniro", "kinyarwanda", "URGENT"),
    ("Mfite ibara ry'umuhondo mu maso no mu maso, sinyoye neza", "kinyarwanda", "URGENT"),
    ("Umwana wanjye ariyisanga ararira, mfite ubwoba bw'malaria", "kinyarwanda", "URGENT"),
    ("Ndumva ububabare bukabije mu gituza iyo ndema", "kinyarwanda", "URGENT"),
    ("Mfite diarrhea kuva hashize iminsi 3, ndangirika", "kinyarwanda", "URGENT"),
    ("Umurambo wanjye urababara cyane nyuma yo kugwa", "kinyarwanda", "URGENT"),
    ("Mfite inkorora n'umuriro kuva hashize iminsi 4", "kinyarwanda", "URGENT"),
    ("Ndumva amarira make avuye mu maso, ubushyuhe ni 38 degrees", "kinyarwanda", "URGENT"),
    ("Mfite ibibazo byo kurara, ndababara cyane mu gituza", "kinyarwanda", "URGENT"),
    ("Umwana mfite ubushyuhe bwinshi no gutera imitsi", "kinyarwanda", "URGENT"),
    ("Ndavoma kenshi kandi sinariye uyu munsi wose", "kinyarwanda", "URGENT"),
    ("Mfite uburibwe bwinshi mu mutwe no mu maso", "kinyarwanda", "URGENT"),
    # English
    ("High fever of 38.5 degrees for the past 3 days", "english", "URGENT"),
    ("Severe abdominal pain that started last night", "english", "URGENT"),
    ("Vomiting blood mixed with food, happened twice today", "english", "URGENT"),
    ("Suspected malaria symptoms: fever, chills, body aches", "english", "URGENT"),
    ("Child with fever and rash spreading across the body", "english", "URGENT"),
    ("Severe diarrhea for 3 days, signs of dehydration", "english", "URGENT"),
    ("Head injury from fall, mild confusion but conscious", "english", "URGENT"),
    ("Severe toothache with facial swelling for 2 days", "english", "URGENT"),
    ("Urinary tract infection with high fever and back pain", "english", "URGENT"),
    ("Wound showing signs of infection: red, swollen, pus", "english", "URGENT"),
    ("Asthma attack, inhaler not working as well as usual", "english", "URGENT"),
    ("Diabetic patient with very high blood sugar levels", "english", "URGENT"),
    ("Severe allergic reaction, hives spreading on body", "english", "URGENT"),
    ("Hypertension patient with very high blood pressure reading", "english", "URGENT"),
    ("Severe ear pain with discharge, cannot hear well", "english", "URGENT"),
    # Mixed
    ("Mfite fever ikabije, 38.5 degrees kuva hashize 3 days", "mixed", "URGENT"),
    ("Ndumva severe pain mu nda, started ijoro ryashize", "mixed", "URGENT"),
    ("Umwana wanjye mfite malaria symptoms, fever na chills", "mixed", "URGENT"),
    ("I have been vomiting kuva this morning, sinariye anything", "mixed", "URGENT"),
    ("Mfite diarrhea for 3 days, ndumva dehydrated cyane", "mixed", "URGENT"),
    ("Wound yanjye iranga infection, itukura kandi yivuye pus", "mixed", "URGENT"),
    ("Mfite high blood pressure today, ndumva dizzy kandi nababara umutwe", "mixed", "URGENT"),
    ("Umwana mfite fever na rash, spreading across the body", "mixed", "URGENT"),
    ("Ndumva severe toothache, face yanjye yivuye kuva yesterday", "mixed", "URGENT"),
    ("I have UTI symptoms, mfite fever na back pain ikabije", "mixed", "URGENT"),
]

ROUTINE_SYMPTOMS = [
    # Kinyarwanda
    ("Mfite inkorora yoroheje kuva hashize iminsi 2", "kinyarwanda", "ROUTINE"),
    ("Ndumva umutwe urarya gato ntabwo ari ikabije", "kinyarwanda", "ROUTINE"),
    ("Ndashaka gupimwa ingano n'ubuzima rusange", "kinyarwanda", "ROUTINE"),
    ("Mfite uburibwe bworoheje mu mugongo kuva ejo", "kinyarwanda", "ROUTINE"),
    ("Ndashaka gusuzumwa demoyen'amajyambere ya mwana wanjye", "kinyarwanda", "ROUTINE"),
    ("Mfite amazuru yoroheje, sinjya gusinda neza", "kinyarwanda", "ROUTINE"),
    ("Ndashaka gutunga imiti yo kurwanya malaria nk'igihe cyose", "kinyarwanda", "ROUTINE"),
    ("Mfite inkorora yoroheje na amazuru, ndi nzima ariko", "kinyarwanda", "ROUTINE"),
    ("Ndashaka gupima amaraso kugirango menye ubuzima bwanjye", "kinyarwanda", "ROUTINE"),
    ("Umunaniro woroheje w'imibiri, sinzi impamvu", "kinyarwanda", "ROUTINE"),
    ("Mfite uburibwe bworoheje mu nkokora kuva hashize iminsi", "kinyarwanda", "ROUTINE"),
    ("Ndashaka gutunga imiti yo gutuza umugongo", "kinyarwanda", "ROUTINE"),
    ("Umwana wanjye afite inkorora yoroheje, ntabwo ari umuriro", "kinyarwanda", "ROUTINE"),
    ("Ndashaka kujya na muganga kubera isuzuma rusange", "kinyarwanda", "ROUTINE"),
    ("Mfite ibibazo byo kurarira neza gusa, ariko ndi nzima", "kinyarwanda", "ROUTINE"),
    # English
    ("Mild headache that comes and goes, not severe", "english", "ROUTINE"),
    ("Routine checkup needed, no specific complaints", "english", "ROUTINE"),
    ("Mild cough and runny nose for 2 days, no fever", "english", "ROUTINE"),
    ("Need prescription refill for chronic medication", "english", "ROUTINE"),
    ("Child vaccination appointment needed", "english", "ROUTINE"),
    ("Minor back pain after sitting at desk all day", "english", "ROUTINE"),
    ("Mild fatigue, sleeping well but feel tired during day", "english", "ROUTINE"),
    ("Skin rash that is not spreading, mild itching only", "english", "ROUTINE"),
    ("Annual blood test and general health screening", "english", "ROUTINE"),
    ("Mild sore throat, no fever, eating and drinking normally", "english", "ROUTINE"),
    ("Minor cut that needs cleaning and dressing", "english", "ROUTINE"),
    ("Follow up appointment after previous treatment", "english", "ROUTINE"),
    ("Mild stomach discomfort after eating, no vomiting", "english", "ROUTINE"),
    ("Need advice on nutrition and healthy diet", "english", "ROUTINE"),
    ("Minor eye irritation, no pain, just redness", "english", "ROUTINE"),
    # Mixed
    ("Mfite mild headache gato, ntabwo ari serious", "mixed", "ROUTINE"),
    ("Ndashaka routine checkup, no specific complaints mfite", "mixed", "ROUTINE"),
    ("I have inkorora yoroheje na runny nose, no fever", "mixed", "ROUTINE"),
    ("Ndashaka prescription refill for imiti yanjye ya chronic", "mixed", "ROUTINE"),
    ("Umwana wanjye needs vaccination, appointment ndashaka", "mixed", "ROUTINE"),
    ("Mfite mild back pain after sitting all day ku murimo", "mixed", "ROUTINE"),
    ("Ndumva fatigue gato but sleeping well, no other symptoms", "mixed", "ROUTINE"),
    ("I have skin rash yoroheje, itching gato, not spreading", "mixed", "ROUTINE"),
    ("Ndashaka annual blood test na general checkup", "mixed", "ROUTINE"),
    ("Mfite sore throat yoroheje, ndi nzima ariko, no fever", "mixed", "ROUTINE"),
]

def build_dataset(output_path: str, augment: bool = True):
    all_data = CRITICAL_SYMPTOMS + URGENT_SYMPTOMS + ROUTINE_SYMPTOMS

    # Augmentation — slightly vary sentences to increase dataset size
    augmented = []
    if augment:
        prefixes_rw = ["Muganga, ", "Muraho, ", "Mfasha, ", "Ndakeneye ubufasha, "]
        prefixes_en = ["Doctor, ", "Please help, ", "I need help, ", "Good morning, "]
        prefixes_mx = ["Muganga please, ", "Help, ", "Ndakeneye help, "]

        for text, lang, label in all_data:
            augmented.append((text, lang, label))
            if lang == "kinyarwanda":
                prefix = random.choice(prefixes_rw)
            elif lang == "english":
                prefix = random.choice(prefixes_en)
            else:
                prefix = random.choice(prefixes_mx)
            augmented.append((prefix + text.lower(), lang, label))

    final_data = augmented if augment else all_data
    random.shuffle(final_data)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "language", "label"])
        for text, lang, label in final_data:
            writer.writerow([text, lang, label])

    # Count per label
    counts = {"CRITICAL": 0, "URGENT": 0, "ROUTINE": 0}
    for _, _, label in final_data:
        counts[label] += 1

    print(f"Dataset built successfully!")
    print(f"Total examples : {len(final_data)}")
    print(f"CRITICAL       : {counts['CRITICAL']}")
    print(f"URGENT         : {counts['URGENT']}")
    print(f"ROUTINE        : {counts['ROUTINE']}")
    print(f"Saved to       : {output_path}")

if __name__ == "__main__":
    build_dataset("dataset/raw/symptoms_raw.csv")
