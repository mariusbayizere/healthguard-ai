from sqlalchemy.orm import Session
from app.models.queue import Queue, QueueStatus
from app.models.triage_result import UrgencyLevel

URGENCY_PRIORITY = {
    UrgencyLevel.CRITICAL: 1,
    UrgencyLevel.URGENT:   2,
    UrgencyLevel.ROUTINE:  3,
}

def get_next_queue_number(db: Session) -> int:
    count = db.query(Queue).count()
    return count + 1

def get_estimated_wait(db: Session, urgency: UrgencyLevel) -> int:
    waiting = db.query(Queue).filter(
        Queue.status == QueueStatus.WAITING
    ).count()
    base_time = 10  # minutes per patient
    if urgency == UrgencyLevel.CRITICAL:
        return 0
    elif urgency == UrgencyLevel.URGENT:
        return min(waiting * base_time, 30)
    return waiting * base_time

def get_full_queue(db: Session):
    return db.query(Queue).filter(
        Queue.status != QueueStatus.DONE
    ).order_by(Queue.queue_position).all()
