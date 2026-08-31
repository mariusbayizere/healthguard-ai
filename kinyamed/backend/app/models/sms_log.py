"""Delivery log for patient SMS notifications."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.patient import Patient


class SMSStatus(enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"  # provider disabled (e.g. local development)


class SMSLog(TimestampedModel):
    __tablename__ = "sms_logs"

    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SMSStatus] = mapped_column(
        SAEnum(SMSStatus, name="smsstatus", validate_strings=True),
        nullable=False,
        default=SMSStatus.PENDING,
        server_default=SMSStatus.PENDING.value,
        index=True,
    )
    # Set only when the provider actually accepted the message, so "sent"
    # counts in analytics mean what they say.
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_message_id: Mapped[str | None] = mapped_column(String(128))
    error_detail: Mapped[str | None] = mapped_column(Text)

    patient: Mapped["Patient"] = relationship(back_populates="sms_logs")

    def __repr__(self) -> str:
        return f"<SMSLog id={self.id} patient_id={self.patient_id} status={self.status.value}>"
