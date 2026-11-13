import hashlib
import hmac
import re
import secrets
import time
from typing import Callable, Protocol

from ...config import Settings
from ...errors import (
    OtpExpired,
    OtpInvalid,
    OtpLocked,
    OtpRateLimited,
    SmsDeliveryError,
    ValidationError,
)
from .stores import OtpChallenge, OtpStore
from .validators import normalize_phone

TEST_CODE = "123456"

# Hamma foydalanuvchilar uchun umumiy hisoblagich kaliti. Telefon raqami faqat raqamlardan iborat, shuning uchun to'qnashmaydi.
_GLOBAL_KEY = "*global*"
_DAY = 86400
_8H = 8 * 3600


class SmsSender(Protocol):
    is_real: bool

    def send(self, phone: str, text: str) -> None: ...


class NullSmsSender:
    """SMS yuboruvchi YO'Q (haqiqiy provayder ulanmagan). Productionda ishlatib bo'lmaydi."""

    is_real = False

    def send(self, phone: str, text: str) -> None:  # pragma: no cover - ataylab hech narsa qilmaydi
        return None


class OtpService:
    def __init__(
        self,
        settings: Settings,
        store: OtpStore,
        sms: SmsSender,
        clock: Callable[[], float] = time.time,
    ):
        self._s = settings
        self._store = store
        self._sms = sms
        self._clock = clock

    def _hash(self, challenge_id: str, code: str) -> str:
        return hmac.new(
            self._s.otp_secret.encode(), f"{challenge_id}:{code}".encode(), hashlib.sha256
        ).hexdigest()

    def request(self, phone_raw: str) -> str:
        phone = normalize_phone(phone_raw)
        if phone is None:
            raise ValidationError("Telefon raqami noto'g'ri")
        now = self._clock()
        recent = sorted(t for t in self._store.request_times(phone) if now - t < 3600)
        if recent and now - recent[-1] < self._s.otp_cooldown:
            raise OtpRateLimited(retry_after=int(self._s.otp_cooldown - (now - recent[-1])) + 1)
        if len(recent) >= self._s.otp_max_per_hour:
            raise OtpRateLimited(retry_after=int(3600 - (now - recent[0])) + 1)
        send_sms = not self._s.test_mode
        if send_sms:
            # Pul yo'qotishdan himoya: bir sutkadagi jami SMS soni cheklanadi (SMS-bombing, tasodifiy raqamlar).
            day = sorted(t for t in self._store.request_times(_GLOBAL_KEY) if now - t < _DAY)
            waits = []
            if len(day) >= self._s.sms_daily_cap:
                # Joy bo'shashi uchun eng eski kerakli yozuv muddati tugashi kerak
                waits.append(_DAY - (now - day[len(day) - self._s.sms_daily_cap]))
            cap8 = self._s.sms_8hour_cap
            if cap8 > 0:
                w8 = [t for t in day if now - t < _8H]
                if len(w8) >= cap8:
                    waits.append(_8H - (now - w8[len(w8) - cap8]))
            if waits:
                raise OtpRateLimited(retry_after=int(max(waits)) + 1)
        self._store.add_request(phone, now)
        if send_sms:
            self._store.add_request(_GLOBAL_KEY, now)

        challenge_id = secrets.token_urlsafe(16)
        code = TEST_CODE if self._s.test_mode else f"{secrets.randbelow(10**6):06d}"
        self._store.put(
            challenge_id,
            OtpChallenge(phone, self._hash(challenge_id, code), now + self._s.otp_ttl),
        )
        if send_sms:
            try:
                self._sms.send(phone, self._s.sms_template.replace("{code}", code))
            except Exception as e:
                # Yuborilmadi: kod ham, limit ham behuda sarflanmasin (provayder uzilishida foydalanuvchi bloklanib qolmasin).
                self._store.delete(challenge_id)
                self._store.discard_request(phone, now)
                self._store.discard_request(_GLOBAL_KEY, now)
                if isinstance(e, SmsDeliveryError):
                    raise
                raise SmsDeliveryError("SMS yuborib bo'lmadi") from None
        return challenge_id

    def verify(self, challenge_id: str, code: str) -> str:
        """To'g'ri bo'lsa telefonni qaytaradi. Kod bir martalik."""
        ch = self._store.get(challenge_id)
        if ch is None:
            raise OtpInvalid("Kod noto'g'ri")
        if self._clock() >= ch.expires_at:
            self._store.delete(challenge_id)
            raise OtpExpired("Kod muddati tugagan")
        ch.attempts += 1
        candidate = code if re.fullmatch(r"[0-9]{6}", code or "") else ""
        if not hmac.compare_digest(ch.code_hash, self._hash(challenge_id, candidate)):
            if ch.attempts >= self._s.otp_max_attempts:
                self._store.delete(challenge_id)
                raise OtpLocked("Urinishlar tugadi, yangi kod so'rang")
            raise OtpInvalid("Kod noto'g'ri", attempts_left=self._s.otp_max_attempts - ch.attempts)
        self._store.delete(challenge_id)
        return ch.phone
