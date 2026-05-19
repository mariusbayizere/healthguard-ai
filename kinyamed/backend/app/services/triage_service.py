from sqlalchemy.orm import Session
from app.models.symptom_report import SymptomReport
from app.models.triage_result  import TriageResult, UrgencyLevel
from app.models.queue          import Queue, QueueStatus
from app.services.queue_service import get_next_queue_number, get_estimated_wait
from app.services.sms_service   import send_sms, build_triage_sms

def run_triage(db: Session, patient_id: int, patient_name: str, symptoms_input: str):

    # Step 1 — Save symptom report
    report = SymptomReport(
        patient_id         = patient_id,
        raw_input          = symptoms_input,
        language_detected  = detect_language(symptoms_input),
        symptoms_extracted = symptoms_input  # NLP model replaces this in Week 2
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Step 2 — Run AI classification (placeholder until NLP model in Week 2)
    urgency, conditions, confidence, response_rw = classify_symptoms(symptoms_input)

    # Step 3 — Save triage result
    result = TriageResult(
        symptom_report_id   = report.id,
        urgency_level       = urgency,
        possible_conditions = conditions,
        confidence_score    = confidence,
        ai_response_rw      = response_rw
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    # Step 4 — Add to queue
    queue_number   = get_next_queue_number(db)
    estimated_wait = get_estimated_wait(db, urgency)

    queue_entry = Queue(
        triage_result_id = result.id,
        queue_number     = queue_number,
        queue_position   = queue_number,
        status           = QueueStatus.WAITING,
        estimated_wait   = estimated_wait
    )
    db.add(queue_entry)
    db.commit()
    db.refresh(queue_entry)

    # Step 5 — Send SMS
    sms_message = build_triage_sms(patient_name, urgency.value, queue_number, estimated_wait)
    send_sms(db, patient_id, sms_message)

    return result, queue_entry

def detect_language(text: str) -> str:
    kinyarwanda_words = ["mfite", "urarya", "muraho", "ndwaye", "ubukene"]
    text_lower = text.lower()
    for word in kinyarwanda_words:
        if word in text_lower:
            return "mixed" if any(c.isascii() for c in text) else "kinyarwanda"
    return "english"

def classify_symptoms(text: str):
    # Placeholder logic — real NLP model replaces this in Week 2
    text_lower = text.lower()
    critical_keywords = ["chest pain", "breathing", "unconscious", "bleeding", "stroke"]
    urgent_keywords   = ["fever", "vomiting", "severe", "pain", "infection", "malaria"]

    if any(word in text_lower for word in critical_keywords):
        return (
            UrgencyLevel.CRITICAL,
            "Possible cardiac or respiratory emergency",
            0.91,
            "Ikibazo cyawe ni CRITICAL. Jya kwa muganga NONE NONE!"
        )
    elif any(word in text_lower for word in urgent_keywords):
        return (
            UrgencyLevel.URGENT,
            "Possible Malaria, Typhoid, or Infection",
            0.78,
            "Ikibazo cyawe ni URGENT. Genda kwa muganga uyu munsi."
        )
    return (
        UrgencyLevel.ROUTINE,
        "Routine consultation needed",
        0.65,
        "Ikibazo cyawe ni ROUTINE. Uzabona muganga vuba."
    )
