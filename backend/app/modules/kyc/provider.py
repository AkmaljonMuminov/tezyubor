"""Identifikatsiya provayderi interfeysi.

Oqim (MyID "yangi" backend-sessiya oqimiga mos): backend `start` bilan sessiya yaratadi (pasport va tug'ilgan sana
FAQAT shu so'rovda provayderga uzatiladi, bizda saqlanmaydi) -> ilova SDK bilan yuzni tekshiradi -> backend `complete`
bilan tasdiqlangan ma'lumotni oladi. Yuz tasviri hech qachon bizning serverga kelmaydi."""
import hashlib
from dataclasses import dataclass, field
from typing import Protocol

from ...config import Settings
from ...errors import ConfigError, KycRejected
from .models import Identity


@dataclass(frozen=True)
class StartResult:
    session_id: str
    sdk: dict = field(default_factory=dict)  # ilovaning SDK'si uchun (masalan, clientHash) — maxfiy kalit emas


class KycProvider(Protocol):
    name: str
    is_real: bool

    def start(self, *, external_id: str, passport: str, birth_date: str) -> StartResult: ...

    def complete(self, *, session_id: str) -> Identity:
        """Tasdiqlangan shaxs. Rad etilsa KycRejected, natija hali tayyor bo'lmasa KycNotReady,
        provayder xatosida KycProviderError."""
        ...


class FakeKycProvider:
    """FAQAT test rejimi. Hech kimni haqiqatda tekshirmaydi: har qanday format-to'g'ri hujjatni 'tasdiqlaydi'.
    Ismi doim 'TEST FOYDALANUVCHI'. `*0000` bilan tugagan pasport raqami rad etiladi (rad etish oqimini sinash uchun)."""

    name = "fake"
    is_real = False

    def __init__(self):
        self._sessions: dict[str, tuple[str, str]] = {}

    def start(self, *, external_id, passport, birth_date):
        session_id = f"fake-{external_id}"
        self._sessions[session_id] = (passport, birth_date)
        return StartResult(session_id=session_id, sdk={"provider": "fake"})

    def complete(self, *, session_id):
        data = self._sessions.get(session_id)
        if data is None:
            raise KycRejected("Sessiya topilmadi")
        passport, birth_date = data
        if passport.endswith("0000"):
            raise KycRejected("Hujjat tasdiqlanmadi")
        digest = hashlib.sha256(f"{passport}|{birth_date}".encode()).hexdigest()
        pinfl = "9" + str(int(digest[:16], 16))[:13].rjust(13, "0")  # '9' bilan boshlanadi: haqiqiy JShShIR bo'lmaydi
        return Identity(full_name="TEST FOYDALANUVCHI", pinfl=pinfl, passport=passport, birth_date=birth_date)


def build_kyc_provider(settings: Settings) -> KycProvider:
    if settings.kyc_provider == "fake":
        if not settings.test_mode:
            raise ConfigError("Productionda soxta KYC provayder ishlatib bo'lmaydi")
        return FakeKycProvider()
    # MyID adapteri MyID'ning backend API hujjati olingach yoziladi (sessiya yaratish va natijani olish so'rovlari).
    raise ConfigError("KYC_PROVIDER=myid hali ulanmagan: MyID backend API hujjati kerak")
