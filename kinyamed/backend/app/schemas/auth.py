"""Authentication request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models.user import UserRole
from app.schemas.common import ORMModel


def _normalised_phone(value: str) -> str:
    """E.164 or a validation error, raised where Pydantic can render it."""
    from app.schemas.patient import normalise_phone

    return normalise_phone(value)


PersonName = Annotated[
    str, Field(min_length=2, max_length=50), AfterValidator(str.strip)
]
E164Phone = Annotated[
    str,
    Field(max_length=24, examples=["0788123456"]),
    AfterValidator(_normalised_phone),
]


# FR-05-11. The rule set is deliberately small: four character classes and a
# length floor, checked together so one attempt reports every failure rather
# than making the user discover them one at a time.
#
# The floor stays at 12 although FR-05-11 says 8. A specification minimum is a
# floor, not a target, and lowering a limit that already holds to match a
# document would weaken a live gate for nothing.
SPECIAL_CHARACTERS = "!@#$%^&*()-_=+[]{};:,.<>?/\\|`~\"'"

_PASSWORD_RULES: tuple[tuple[str, str], ...] = (
    ("an uppercase letter", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    ("a lowercase letter", "abcdefghijklmnopqrstuvwxyz"),
    ("a digit", "0123456789"),
    (f"a special character ({SPECIAL_CHARACTERS[:8]}...)", SPECIAL_CHARACTERS),
)


def enforce_password_composition(value: str) -> str:
    """Require all four character classes, naming every class that is missing.

    Raises ValueError, which Pydantic renders into the standard validation
    envelope, so the client sees which rules failed rather than a bare refusal.
    """
    missing = [
        name for name, alphabet in _PASSWORD_RULES if not set(value) & set(alphabet)
    ]
    if missing:
        raise ValueError("Password must contain " + ", ".join(missing))
    return value


# Long enough to resist offline guessing, short enough to stay within bcrypt's
# 72-byte input limit.
PasswordStr = Annotated[
    str,
    Field(min_length=12, max_length=72),
    AfterValidator(enforce_password_composition),
]


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=72)]

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class RegisterRequest(BaseModel):
    """Self-service patient registration.

    Creates the login and the patient chart together; staff accounts are
    created by an administrator, never by this endpoint.
    """

    email: EmailStr
    password: PasswordStr
    # A typing check, not a field. It is compared and discarded; nothing
    # downstream ever sees it.
    confirm_password: Annotated[str, Field(min_length=1, max_length=72)]
    first_name: PersonName
    last_name: PersonName
    # Validated HERE, in the schema, so a mistyped number is a 422 naming the
    # field. It used to be normalised in the service, where the bare ValueError
    # had no handler and the caller got a 500: not a validation message, but a
    # page for somebody and no information for the user.
    phone: E164Phone
    age: Annotated[int | None, Field(default=None, ge=0, le=130)] = None
    gender: str | None = None
    location: Annotated[str | None, Field(default=None, max_length=100)] = None

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def _passwords_match(self) -> RegisterRequest:
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password must match")
        return self


class UserCreate(BaseModel):
    """Administrator-created account, for staff."""

    email: EmailStr
    password: PasswordStr
    first_name: PersonName
    last_name: PersonName
    # Optional for staff: an administrator may not have it to hand. Without one
    # a password-reset code cannot reach this account, which the reset flow
    # logs rather than failing silently.
    phone: E164Phone | None = None
    role: UserRole
    doctor_id: Annotated[int | None, Field(default=None, gt=0)] = None
    patient_id: Annotated[int | None, Field(default=None, gt=0)] = None

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class PasswordChangeRequest(BaseModel):
    current_password: Annotated[str, Field(min_length=1, max_length=72)]
    new_password: PasswordStr


class UserResponse(ORMModel):
    id: int
    email: str
    first_name: str
    last_name: str | None
    role: UserRole
    is_active: bool
    patient_id: int | None
    doctor_id: int | None
    last_login_at: datetime | None
    created_at: datetime


class TokenResponse(BaseModel):
    """Issued access token.

    The refresh token is intentionally absent: it is set as an httpOnly cookie
    so that JavaScript on the page cannot read it.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access-token lifetime in seconds.")
    user: UserResponse


class SessionResponse(ORMModel):
    """An active refresh-token session."""

    jti: str
    created_at: datetime
    expires_at: datetime
    user_agent: str | None


class PasswordResetRequest(BaseModel):
    """Ask for a reset code. Answered identically whether or not the account exists."""

    email: EmailStr

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class PasswordResetConfirm(BaseModel):
    """Spend a code and set a new password."""

    email: EmailStr
    # Not PasswordStr: this is a six-digit code, not a password.
    code: Annotated[str, Field(min_length=6, max_length=6, pattern=r"^\d{6}$")]
    new_password: PasswordStr

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class GoogleSignIn(BaseModel):
    """The ID token the browser received from Google.

    Nothing else is accepted from the client: the email, the name and the
    picture all come from inside the verified token. Taking any of them as a
    request field would mean trusting the caller for the thing being proved.
    """

    id_token: Annotated[str, Field(min_length=1, max_length=8192)]
