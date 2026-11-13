import json
import time
import uuid
from datetime import date
from typing import Callable

from ...config import Settings
from ...errors import (
    KycAlreadyVerified,
    KycConsentRequired,
    KycIdentityTaken,
    KycLocked,
    KycNotReady,
    KycNotStarted,
    KycRejected,
    ValidationError,
)
from ...security.pii import PiiCipher
from ..auth.audit import AuditLog
from . import models as m
from .provider import KycProvider
from .store import KycStore
from .validators import age_on, is_pinfl, mask_passport, normalize_passport, parse_birth_date

MAX_FAILED = 5
LOCK_SECONDS = 3600


class KycService:
    """Identifikatsiya. Qoidalar: rozilik bo'lmasa boshlanmaydi; kiritilgan pasport saqlanmaydi (faqat provayderga
    uzatiladi); tasdiqlangan ma'lumot shifrlab saqlanadi; audit va loglarga shaxsiy ma'lumot yozilmaydi."""

    def __init__(
        self,
        settings: Settings,
        store: KycStore,
        provider: KycProvider,
        cipher: PiiCipher,
        audit: AuditLog,
        clock: Callable[[], float] = time.time,
    ):
        self._s = settings
        self._store = store
        self._provider = provider
        self._cipher = cipher
        self._audit = audit
        self._clock = clock

    def _rec(self, user_id: str) -> m.KycRecord:
        return self._store.get(user_id) or m.KycRecord(user_id=user_id, provider=self._provider.name)

    def _save(self, rec: m.KycRecord) -> None:
        rec.updated_at = self._clock()
        self._store.save(rec)

    def status(self, user_id: str) -> dict:
        rec = self._rec(user_id)
        now = self._clock()
        out: dict = {
            "status": rec.status,
            "consent_given": rec.consent_version == m.CONSENT_VERSION,
            "consent_version": m.CONSENT_VERSION,
            "is_test": not self._provider.is_real,
        }
        if rec.locked_until > now:
            out["retry_after"] = int(rec.locked_until - now) + 1
        if rec.status == m.VERIFIED and rec.payload:
            ident = json.loads(self._cipher.decrypt(rec.payload, user_id.encode()))
            out["identity"] = {"full_name": ident["full_name"], "passport": mask_passport(ident["passport"])}
        return out

    def give_consent(self, user_id: str, version: str) -> None:
        if version != m.CONSENT_VERSION:
            raise ValidationError("Rozilik matni yangilangan, qayta ko'rib chiqing")
        rec = self._rec(user_id)
        rec.consent_version = m.CONSENT_VERSION
        rec.consent_at = self._clock()
        self._save(rec)
        self._audit.record("kyc_consent", user_id=user_id, version=m.CONSENT_VERSION)

    def start(self, user_id: str, passport_raw: str, birth_date_raw: str) -> dict:
        rec = self._rec(user_id)
        if rec.consent_version != m.CONSENT_VERSION:
            raise KycConsentRequired("Avval rozilik berishingiz kerak")
        if rec.status == m.VERIFIED:
            raise KycAlreadyVerified("Siz allaqachon identifikatsiyadan o'tgansiz")
        self._check_lock(rec)

        passport = normalize_passport(passport_raw)
        if passport is None:
            raise ValidationError("Pasport seriyasi va raqami noto'g'ri")
        born = parse_birth_date(birth_date_raw)
        today = date.fromtimestamp(self._clock())
        if born is None or born > today:
            raise ValidationError("Tug'ilgan sana noto'g'ri (kk.oo.yyyy)")
        if age_on(born, today) < m.MIN_AGE:
            raise ValidationError(f"Identifikatsiya {m.MIN_AGE} yoshdan boshlab mumkin")

        external_id = str(uuid.uuid4())
        # Provayder xatosi (KycProviderError) shu yerdan chiqadi; holat o'zgarmaydi, pasport saqlanmaydi.
        res = self._provider.start(external_id=external_id, passport=passport, birth_date=born.strftime("%d.%m.%Y"))
        rec.status = m.PENDING
        rec.provider = self._provider.name
        rec.external_id = external_id
        rec.session_id = res.session_id
        self._save(rec)
        self._audit.record("kyc_started", user_id=user_id, provider=self._provider.name)
        return {"session_id": res.session_id, "sdk": res.sdk}

    def complete(self, user_id: str) -> dict:
        rec = self._rec(user_id)
        if rec.status == m.VERIFIED:
            raise KycAlreadyVerified("Siz allaqachon identifikatsiyadan o'tgansiz")
        if rec.status != m.PENDING or not rec.session_id:
            raise KycNotStarted("Identifikatsiya boshlanmagan")
        self._check_lock(rec)

        try:
            ident = self._provider.complete(session_id=rec.session_id)
        except KycNotReady:
            raise  # hali tayyor emas: holat o'zgarmaydi, qayta so'rash mumkin
        except KycRejected:
            self._register_failure(rec, "provider_rejected")
            raise

        if not is_pinfl(ident.pinfl) or normalize_passport(ident.passport) is None:
            self._register_failure(rec, "bad_provider_data")
            raise KycRejected("Hujjat tasdiqlanmadi")

        index = self._cipher.blind_index(ident.pinfl)
        owner = self._store.find_by_pinfl_index(index)
        if owner is not None and owner != user_id:
            self._audit.record("kyc_identity_conflict", user_id=user_id)
            self._register_failure(rec, "identity_taken")
            raise KycIdentityTaken("Bu hujjat boshqa hisobga bog'langan")

        payload = json.dumps(
            {
                "full_name": ident.full_name,
                "pinfl": ident.pinfl,
                "passport": ident.passport,
                "birth_date": ident.birth_date,
            },
            ensure_ascii=False,
        ).encode()
        rec.payload = self._cipher.encrypt(payload, user_id.encode())
        rec.key_id = self._cipher.key_id
        rec.pinfl_index = index
        rec.status = m.VERIFIED
        rec.verified_at = self._clock()
        rec.failed_attempts = 0
        rec.locked_until = 0.0
        self._save(rec)
        self._audit.record("kyc_verified", user_id=user_id, provider=self._provider.name)
        return self.status(user_id)

    # --- ichki ---

    def _check_lock(self, rec: m.KycRecord) -> None:
        now = self._clock()
        if rec.locked_until > now:
            raise KycLocked("Juda ko'p urinish. Keyinroq qayta urinib ko'ring", retry_after=int(rec.locked_until - now) + 1)

    def _register_failure(self, rec: m.KycRecord, reason: str) -> None:
        rec.failed_attempts += 1
        rec.status = m.REJECTED
        rec.session_id = None
        if rec.failed_attempts >= MAX_FAILED:
            rec.failed_attempts = 0
            rec.locked_until = self._clock() + LOCK_SECONDS
            self._audit.record("kyc_locked", user_id=rec.user_id)
        self._save(rec)
        self._audit.record("kyc_rejected", user_id=rec.user_id, reason=reason)
