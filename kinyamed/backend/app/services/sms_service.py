from sqlalchemy.orm import Session
from app.models.sms_log import SMSLog, SMSStatus
from app.core.config import settings

def send_sms(db: Session, patient_id: int, message: str):
    sms = SMSLog(
        patient_id=patient_id,
        message=message,
        status=SMSStatus.PENDING
    )
    db.add(sms)
    db.commit()

    # TODO: Connect Africa's Talking API here in Week 3
    # For now we simulate sending
    print(f"[SMS] To patient {patient_id}: {message}")

    sms.status = SMSStatus.SENT
    db.commit()
    return sms

def build_triage_sms(name: str, urgency: str, queue_number: int, wait: int) -> str:
    if urgency == "CRITICAL":
        return f"Muraho {name}, ikibazo cyawe ni CRITICAL. Jya kwa muganga NONE NONE. Numero yawe: {queue_number}."
    elif urgency == "URGENT":
        return f"Muraho {name}, ikibazo cyawe ni URGENT. Genda kwa muganga uyu munsi. Numero: {queue_number}. Itegereze: ~{wait} min."
    return f"Muraho {name}, ikibazo cyawe ni ROUTINE. Numero yawe ni {queue_number}. Itegereze: ~{wait} min."
