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
_INSECURE_SECRETS = {"", "changeme", "secret", "kinyamed_secret_key_2026"}


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

    # --- Security --------------------------------------------------------
    SECRET_KEY: SecretStr
    # Comma-separated list; use `cors_origins` for the parsed value.
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # --- SMS -------------------------------------------------------------
    SMS_API_KEY: SecretStr
    SMS_USERNAME: str = "sandbox"
    SMS_SENDER_ID: str = "KinyaMed"
    # When false the SMS provider is stubbed and messages are only logged.
    SMS_ENABLED: bool = False

    # --- Authentication ---
    JWT_ALGORITHM: str = "HS256"
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
    MODEL_MAX_LENGTH: int = Field(default=512, ge=16, le=4096)
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

    # --- Red-flag rules layer (CLAUDE.md L2) --------------------------------
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
            if self.SECRET_KEY.get_secret_value() in _INSECURE_SECRETS:
                logger.warning(
                    "SECRET_KEY is a known placeholder value. This is tolerated in "
                    "%s but will block start-up in production.",
                    self.ENVIRONMENT,
                )
            return self

        problems: list[str] = []
        secret = self.SECRET_KEY.get_secret_value()
        if secret in _INSECURE_SECRETS:
            problems.append("SECRET_KEY is a known placeholder value")
        if len(secret) < 32:
            problems.append("SECRET_KEY must be at least 32 characters")
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
    def trusted_proxy_networks(
        self,
    ) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
        """TRUSTED_PROXIES parsed; validated at start-up, so this cannot raise."""
        return tuple(
            ipaddress.ip_network(entry.strip(), strict=False)
            for entry in self.TRUSTED_PROXIES.split(",")
            if entry.strip()
        )

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
