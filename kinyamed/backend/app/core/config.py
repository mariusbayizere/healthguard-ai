"""Application configuration.

Settings are read once from the environment (and `.env`) at import time and are
immutable thereafter. Use `get_settings()` in dependency-injected code so tests
can override the cache; the module-level `settings` object is the convenience
handle for ordinary application code.
"""

from __future__ import annotations

import ipaddress
import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

Environment = Literal["development", "staging", "production"]

# Placeholder values that must never reach a deployed environment.


class Settings(BaseSettings):
    """Validated application settings.

    Every value that has no safe default is required, so a misconfigured
    deployment fails at start-up rather than at the first request that needs it.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Environment -----------------------------------------------------
    ENVIRONMENT: Environment = "development"

    # --- Database --------------------------------------------------------
    DATABASE_URL: PostgresDsn
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=5, ge=0, le=100)
    DB_POOL_RECYCLE_SECONDS: int = Field(default=1800, ge=60)
    DB_ECHO: bool = False

    # --- Redis -----------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379"
    # Logout withdraws an access token before it expires (FR-05-10). Redis is a
    # cache in front of a safety property, never a dependency of the request
    # path: if it is unreachable the service degrades to the pre-blocklist
    # behaviour rather than failing (ENGINEERING_SPEC §6.3).
    BLOCKLIST_ENABLED: bool = True
    # Short on purpose. This timeout sits on the request path, so a hung Redis
    # must cost milliseconds, not seconds.
    REDIS_TIMEOUT_SECONDS: float = Field(default=0.25, gt=0, le=5)

    # --- Security --------------------------------------------------------
    # SECRET_KEY was removed 2026-09-17. It signed tokens under HS256; once
    # tokens became RS256 nothing read it, and a required variable that nothing
    # reads is a trap: it gets rotated during an incident in the belief that
    # doing so invalidates sessions. A future CSRF token or signed URL should
    # introduce its own purpose-named secret rather than reviving this one.
    # Comma-separated list; use `cors_origins` for the parsed value.
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # --- SMS -------------------------------------------------------------
    SMS_API_KEY: SecretStr
    SMS_USERNAME: str = "sandbox"
    SMS_SENDER_ID: str = "KinyaMed"
    # When false the SMS provider is stubbed and messages are only logged.
    SMS_ENABLED: bool = False

    # --- Authentication ---
    # RS256, not HS256: under a symmetric algorithm anything able to verify a
    # token is also able to mint one. Changed 2026-09-17 as a clean break, with
    # no dual-verification path — a transition that still accepts HS256 is the
    # thing being removed. Every session issued before the cutover stops
    # validating, which is correct: there were none in production.
    JWT_ALGORITHM: Literal["RS256", "RS384", "RS512"] = "RS256"
    # PEM of the active signing key. Unset outside production means an
    # ephemeral pair is generated at start-up; production refuses to boot.
    JWT_PRIVATE_KEY: SecretStr | None = None
    # Zero or more public PEMs, concatenated. They verify and never sign, so a
    # rotation does not sign anyone out. See app/core/jwt_keys.py.
    JWT_RETIRED_PUBLIC_KEYS: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)
    # bcrypt's own minimum is 4. Production is held to 12 by the hardening
    # validator below; test suites lower it so that creating fixture users does
    # not cost 0.4s per hash.
    BCRYPT_ROUNDS: int = Field(default=12, ge=4, le=15)
    REFRESH_COOKIE_NAME: str = "kinyamed_refresh"
    # Cookies are sent over HTTPS only outside development.
    REFRESH_COOKIE_SECURE: bool = True
    REFRESH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # --- Rate limiting ---
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = Field(default=120, ge=1)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, ge=1)
    # Paths exempt from rate limiting (probes must never be throttled).
    RATE_LIMIT_EXEMPT_PATHS: str = "/health,/health/ready,/ready,/"
    # FR-05-09: credential-presenting endpoints get their own, far tighter
    # budget. Separate from the general one in both directions -- queue polling
    # must not consume the login allowance, and a clinician mistyping a
    # password must not lose access to the queue.
    AUTH_RATE_LIMIT_REQUESTS: int = Field(default=10, ge=1)
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=900, ge=1)
    # Refresh and logout are deliberately absent. Refresh runs on a timer, once
    # per access-token lifetime per session, so counting it would throttle a
    # clinician with several tabs open for doing nothing wrong.
    AUTH_RATE_LIMIT_PATHS: str = (
        "/api/v1/auth/login,/api/v1/auth/register,/api/v1/auth/change-password"
    )
    # Comma-separated IPs or CIDRs of reverse proxies whose X-Forwarded-For is
    # believed. EMPTY BY DEFAULT: with no proxy configured the header is ignored
    # and the limiter keys on the TCP peer, because any client can write it.
    TRUSTED_PROXIES: str = ""

    # --- Application -----------------------------------------------------
    APP_NAME: str = "KinyaMed"
    APP_VERSION: str = "1.0.0"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = Field(default=8000, ge=1, le=65535)
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api/v1"

    # --- Kafka -----------------------------------------------------------
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_PATIENTS: str = "kinyamed_patients"
    KAFKA_TOPIC_ALERTS: str = "kinyamed_alerts"

    # --- ML model --------------------------------------------------------
    MODEL_NAME: str = "Davlan/afro-xlmr-mini"
    # Unset: serve at the length the model records it was trained at
    # (<model dir>/kinyamed_training.json). Set to anything else: start-up refuses.
    MODEL_MAX_LENGTH: int | None = Field(default=None, ge=16, le=4096)
    MODEL_CONFIDENCE_THRESHOLD: float = Field(default=0.75, ge=0.0, le=1.0)

    # C1. Path to a fine-tuned classifier directory. UNSET BY DEFAULT: torch and
    # transformers are deliberately absent from the API image (see
    # requirements.txt). Without a loaded model the triage endpoint FAILS
    # CLOSED: it answers 503 and classifies nothing. There is no fallback.
    TRIAGE_MODEL_PATH: str = ""
    TRIAGE_MODEL_THREADS: int | None = None
    # Retry-After on that 503. The model is loaded only at start-up, so a retry
    # succeeds only after a restart; the header paces clients, the response
    # body tells staff to triage manually meanwhile.
    TRIAGE_UNAVAILABLE_RETRY_AFTER_SECONDS: int = Field(default=60, ge=1, le=3600)
    # Micro-batching (replaces a single inference lock). Requests arriving within
    # the wait window share one forward pass. A request with no result by the
    # timeout fails closed (503).
    TRIAGE_BATCH_MAX_SIZE: int = Field(default=16, ge=1, le=256)
    TRIAGE_BATCH_MAX_WAIT_MS: float = Field(default=5.0, ge=0.0, le=1000.0)
    TRIAGE_INFERENCE_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0.0, le=600.0)

    # --- Red-flag rules layer (docs/ENGINEERING_SPEC.md L2) --------------------------------
    # The §10.6 lexicon. It ships EMPTY (header only), so the layer is a no-op
    # until a clinical lead supplies validated terms. An invalid file stops start-up.
    RED_FLAG_LEXICON_PATH: str = str(
        Path(__file__).resolve().parents[3] / "data" / "lexicon" / "red_flags.csv"
    )

    # --- Triage / queue tuning -------------------------------------------
    # Average minutes a clinician spends per patient; drives wait estimates.
    MINUTES_PER_PATIENT: int = Field(default=10, ge=1, le=240)
    # Upper bound on the wait we will quote to an URGENT patient.
    URGENT_MAX_WAIT_MINUTES: int = Field(default=30, ge=0)
    # Longest symptom description we accept, in characters.
    MAX_SYMPTOM_LENGTH: int = Field(default=2000, ge=32)
    # Default and maximum page sizes for list endpoints.
    DEFAULT_PAGE_SIZE: int = Field(default=50, ge=1, le=500)
    MAX_PAGE_SIZE: int = Field(default=200, ge=1, le=1000)

    @field_validator("LOG_LEVEL")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in logging.getLevelNamesMapping():
            raise ValueError(f"LOG_LEVEL must be a valid logging level, got {value!r}")
        return level

    @field_validator("TRUSTED_PROXIES")
    @classmethod
    def _validate_trusted_proxies(cls, value: str) -> str:
        for entry in (part.strip() for part in value.split(",")):
            if not entry:
                continue
            try:
                ipaddress.ip_network(entry, strict=False)
            except ValueError as error:
                raise ValueError(
                    f"TRUSTED_PROXIES entry {entry!r} is not an IP address or CIDR"
                ) from error
        return value

    @model_validator(mode="after")
    def _enforce_production_hardening(self) -> Settings:
        """Refuse to boot a production process with development-grade secrets."""
        if self.ENVIRONMENT != "production":
            return self

        problems = self.hardening_problems()
        if problems:
            raise ValueError(
                "Insecure configuration for ENVIRONMENT=production: "
                + "; ".join(problems)
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        """CORS origins as a list, parsed from the comma-separated setting."""
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]

    @property
    def rate_limit_exempt_paths(self) -> frozenset[str]:
        """Paths that bypass rate limiting, parsed from the comma-separated setting."""
        return frozenset(
            path.strip()
            for path in self.RATE_LIMIT_EXEMPT_PATHS.split(",")
            if path.strip()
        )

    @property
    def auth_rate_limit_paths(self) -> frozenset[str]:
        """Paths counted against the authentication budget."""
        return frozenset(
            path.strip()
            for path in self.AUTH_RATE_LIMIT_PATHS.split(",")
            if path.strip()
        )

    @property
    def trusted_proxy_networks(
        self,
    ) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
        """TRUSTED_PROXIES parsed; validated at start-up, so this cannot raise."""
        return tuple(
            ipaddress.ip_network(entry.strip(), strict=False)
            for entry in self.TRUSTED_PROXIES.split(",")
            if entry.strip()
        )

    def hardening_problems(self) -> list[str]:
        """Every reason this configuration must not run in production.

        A method rather than inline validator code so a test can assert what
        production would refuse without having to construct a process that
        raises on import.
        """
        problems: list[str] = []
        if "*" in self.cors_origins:
            problems.append("CORS_ORIGINS must not be '*'")
        if self.DB_ECHO:
            problems.append("DB_ECHO must be off (it logs SQL containing patient data)")
        if self.BCRYPT_ROUNDS < 12:
            problems.append("BCRYPT_ROUNDS must be at least 12")
        if not self.REFRESH_COOKIE_SECURE:
            problems.append(
                "REFRESH_COOKIE_SECURE must be on (refresh tokens are bearer credentials)"
            )
        if self.JWT_PRIVATE_KEY is None:
            problems.append(
                "JWT_PRIVATE_KEY must be set (an ephemeral key would invalidate "
                "every session on restart and cannot be rotated)"
            )
        return problems

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def database_url(self) -> str:
        """The database URL as a plain string for SQLAlchemy."""
        return str(self.DATABASE_URL)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, constructed once.

    Tests override configuration with
    `app.dependency_overrides[get_settings] = ...` or by clearing the cache.
    """
    return Settings()  # type: ignore[call-arg]  # values come from the environment


settings = get_settings()
