"""KYC yozuvlari saqlash. Xotira — faqat test/dev; productionda PostgreSQL (config buni majbur qiladi)."""
from typing import Protocol

from ...db import Database
from ...errors import KycIdentityTaken
from .models import KycRecord


class KycStore(Protocol):
    def get(self, user_id: str) -> KycRecord | None: ...
    def save(self, rec: KycRecord) -> None: ...
    def find_by_pinfl_index(self, index: str) -> str | None: ...


class MemoryKycStore:
    def __init__(self):
        self._by_user: dict[str, KycRecord] = {}

    def get(self, user_id):
        return self._by_user.get(user_id)

    def save(self, rec):
        if rec.pinfl_index:
            owner = self.find_by_pinfl_index(rec.pinfl_index)
            if owner is not None and owner != rec.user_id:
                raise KycIdentityTaken("Bu hujjat boshqa hisobga bog'langan")
        self._by_user[rec.user_id] = rec

    def find_by_pinfl_index(self, index):
        for uid, r in self._by_user.items():
            if r.pinfl_index == index:
                return uid
        return None


_COLUMNS = (
    "user_id, status, provider, external_id, session_id, consent_version, consent_at, payload, key_id, "
    "pinfl_index, failed_attempts, locked_until, verified_at, updated_at"
)


class PgKycStore:
    def __init__(self, db: Database):
        self._db = db

    @staticmethod
    def _row(r) -> KycRecord | None:
        if r is None:
            return None
        return KycRecord(
            user_id=str(r["user_id"]),
            status=r["status"],
            provider=r["provider"],
            external_id=r["external_id"],
            session_id=r["session_id"],
            consent_version=r["consent_version"],
            consent_at=r["consent_at"],
            payload=bytes(r["payload"]) if r["payload"] is not None else None,
            key_id=r["key_id"],
            pinfl_index=r["pinfl_index"],
            failed_attempts=r["failed_attempts"],
            locked_until=r["locked_until"],
            verified_at=r["verified_at"],
            updated_at=r["updated_at"],
        )

    def get(self, user_id):
        import uuid

        try:
            uid = uuid.UUID(user_id)
        except (ValueError, AttributeError, TypeError):
            return None
        with self._db.connection() as c:
            return self._row(c.execute(f"SELECT {_COLUMNS} FROM kyc_profiles WHERE user_id = %s", (uid,)).fetchone())

    def save(self, rec):
        import uuid

        import psycopg

        values = (
            uuid.UUID(rec.user_id), rec.status, rec.provider, rec.external_id, rec.session_id, rec.consent_version,
            rec.consent_at, rec.payload, rec.key_id, rec.pinfl_index, rec.failed_attempts, rec.locked_until,
            rec.verified_at, rec.updated_at,
        )
        try:
            with self._db.connection() as c:
                c.execute(
                    f"INSERT INTO kyc_profiles ({_COLUMNS}) VALUES ({', '.join(['%s'] * 14)}) "
                    "ON CONFLICT (user_id) DO UPDATE SET status = EXCLUDED.status, provider = EXCLUDED.provider, "
                    "external_id = EXCLUDED.external_id, session_id = EXCLUDED.session_id, "
                    "consent_version = EXCLUDED.consent_version, consent_at = EXCLUDED.consent_at, "
                    "payload = EXCLUDED.payload, key_id = EXCLUDED.key_id, pinfl_index = EXCLUDED.pinfl_index, "
                    "failed_attempts = EXCLUDED.failed_attempts, locked_until = EXCLUDED.locked_until, "
                    "verified_at = EXCLUDED.verified_at, updated_at = EXCLUDED.updated_at",
                    values,
                )
        except psycopg.errors.UniqueViolation:
            raise KycIdentityTaken("Bu hujjat boshqa hisobga bog'langan") from None

    def find_by_pinfl_index(self, index):
        with self._db.connection() as c:
            r = c.execute("SELECT user_id FROM kyc_profiles WHERE pinfl_index = %s", (index,)).fetchone()
        return str(r["user_id"]) if r else None
