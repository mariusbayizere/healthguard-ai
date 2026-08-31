"""Authentication principals and refresh-token records.

A `User` is who is calling; `Patient` and `Doctor` remain the clinical records.
The two are linked rather than merged, so a receptionist can register a walk-in
patient who has no login, and a clinician's account can be disabled without
touching their consultation history.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.doctor import Doctor
    from app.models.patient import Patient


class UserRole(enum.Enum):
    """Who the caller is, and therefore what they may do."""

    PATIENT = "PATIENT"
    DOCTOR = "DOCTOR"
    ADMIN = "ADMIN"


class User(TimestampedModel):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("position('@' in email) > 1", name="ck_users_email_shape"),
        # A patient account must point at a patient record and nothing else;
        # a doctor account at a doctor record. Enforced in the database so no
        # code path can create a doctor account linked to a patient chart.
        CheckConstraint(
            "(role = 'PATIENT' AND doctor_id IS NULL) OR "
            "(role = 'DOCTOR' AND patient_id IS NULL) OR "
            "(role = 'ADMIN' AND patient_id IS NULL AND doctor_id IS NULL)",
            name="ck_users_role_link_consistency",
        ),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # bcrypt digest; the plaintext password never leaves the request that set it.
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole", validate_strings=True),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    patient_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    doctor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True, index=True
    )

    patient: Mapped["Patient | None"] = relationship(lazy="joined")
    doctor: Mapped["Doctor | None"] = relationship(lazy="joined")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"


class RefreshToken(TimestampedModel):
    """A issued refresh token, tracked so it can be revoked.

    Refresh tokens are long-lived bearer credentials. Recording each one by its
    `jti` is what makes logout, rotation and reuse-detection possible: a
    stateless refresh token cannot be withdrawn before it expires.
    """

    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Coarse client fingerprint, for showing a user their active sessions.
    user_agent: Mapped[str | None] = mapped_column(String(255))

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def __repr__(self) -> str:
        return f"<RefreshToken jti={self.jti} user_id={self.user_id} revoked={self.is_revoked}>"
