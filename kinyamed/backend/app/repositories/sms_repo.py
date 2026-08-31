"""SMS log data access."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.sms_log import SMSLog, SMSStatus
from app.repositories.base import BaseRepository


class SMSLogRepository(BaseRepository[SMSLog]):
    def __init__(self) -> None:
        super().__init__(SMSLog)

    def status_counts(self, db: Session) -> dict[str, int]:
        """Return every delivery-status count in one pass over the table."""
        row = db.execute(
            select(
                func.count().filter(SMSLog.status == SMSStatus.SENT).label("sent"),
                func.count().filter(SMSLog.status == SMSStatus.FAILED).label("failed"),
                func.count().filter(SMSLog.status == SMSStatus.PENDING).label("pending"),
                func.count().filter(SMSLog.status == SMSStatus.SKIPPED).label("skipped"),
            ).select_from(SMSLog)
        ).one()
        return {
            "sent": row.sent,
            "failed": row.failed,
            "pending": row.pending,
            "skipped": row.skipped,
        }


sms_log_repository = SMSLogRepository()
