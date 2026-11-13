from dataclasses import dataclass, field

# Foydalanuvchi ko'rgan rozilik matnining versiyasi. Matn o'zgarsa versiya yangilanadi va rozilik qayta olinadi.
CONSENT_VERSION = "2026-11-v1"
MIN_AGE = 18

NOT_STARTED = "not_started"
PENDING = "pending"
VERIFIED = "verified"
REJECTED = "rejected"


@dataclass(frozen=True)
class Identity:
    """Provayder tasdiqlagan shaxs ma'lumoti. Faqat xotirada; bazaga shifrlangan holda yoziladi. repr yashirin."""

    full_name: str = field(repr=False)
    pinfl: str = field(repr=False)
    passport: str = field(repr=False)
    birth_date: str = field(repr=False)  # dd.MM.yyyy


@dataclass
class KycRecord:
    user_id: str
    status: str = NOT_STARTED
    provider: str = ""
    external_id: str | None = None
    session_id: str | None = None
    consent_version: str | None = None
    consent_at: float | None = None
    payload: bytes | None = field(default=None, repr=False)
    key_id: str | None = None
    pinfl_index: str | None = field(default=None, repr=False)
    failed_attempts: int = 0
    locked_until: float = 0.0
    verified_at: float | None = None
    updated_at: float = 0.0
