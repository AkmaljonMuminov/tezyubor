"""Sozlamalar faqat muhit o'zgaruvchilaridan (.env) olinadi. Kod ichida maxfiy qiymat YO'Q."""
import os
from dataclasses import dataclass, field

from .errors import ConfigError

_ENVS = ("development", "test", "production")


@dataclass(frozen=True)
class Settings:
    env: str
    jwt_secret: str
    otp_secret: str
    access_ttl: int = 600            # 10 daqiqa
    refresh_ttl: int = 30 * 86400    # 30 kun
    otp_ttl: int = 120
    otp_max_attempts: int = 5
    otp_cooldown: int = 60
    otp_max_per_hour: int = 5
    pin_max_failures: int = 5
    pin_lock_seconds: int = 900
    # SMS. Productionda `none` bo'lsa ilova ishga tushmaydi. Parol repr/log'ga tushmasin (repr=False).
    sms_provider: str = "none"                       # none | eskiz
    sms_template: str = "Tezyubor tasdiqlash kodi: {code}"
    sms_daily_cap: int = 500                         # bir sutkada jami yuboriladigan SMS (pul yo'qotishdan himoya)
    sms_8hour_cap: int = 0                           # 8 soat ichida jami SMS; 0 — o'chirilgan
    eskiz_email: str = field(default="", repr=False)
    eskiz_password: str = field(default="", repr=False)
    eskiz_from: str = "4546"
    # Bo'sh bo'lsa ma'lumot xotirada (restartda yo'qoladi). Parol URL ichida bo'lgani uchun repr/log'ga tushmaydi.
    database_url: str = field(default="", repr=False)

    @property
    def test_mode(self) -> bool:
        """Test rejimida OTP doim 123456 va SMS yuborilmaydi. Productionda HECH QACHON."""
        return self.env != "production"

    def validate(self) -> None:
        if self.env not in _ENVS:
            raise ConfigError(f"APP_ENV noto'g'ri: {self.env!r}")
        for name in ("jwt_secret", "otp_secret"):
            if len(getattr(self, name)) < 32:
                raise ConfigError(f"{name.upper()} kamida 32 belgi bo'lishi kerak")
        if self.jwt_secret == self.otp_secret:
            raise ConfigError("JWT_SECRET va OTP_SECRET har xil bo'lishi kerak")
        if self.sms_provider not in ("none", "eskiz"):
            raise ConfigError(f"SMS_PROVIDER noto'g'ri: {self.sms_provider!r}")
        if self.sms_provider == "eskiz" and not (self.eskiz_email and self.eskiz_password):
            raise ConfigError("SMS_PROVIDER=eskiz uchun ESKIZ_EMAIL va ESKIZ_PASSWORD kerak")
        if "{code}" not in self.sms_template:
            raise ConfigError("SMS_TEMPLATE ichida {code} bo'lishi kerak")
        if self.database_url and not self.database_url.startswith(("postgres://", "postgresql://")):
            raise ConfigError("DATABASE_URL postgres:// yoki postgresql:// bilan boshlanishi kerak")
        if self.sms_daily_cap < 1:
            raise ConfigError("SMS_DAILY_CAP kamida 1 bo'lishi kerak")
        if self.sms_8hour_cap < 0:
            raise ConfigError("SMS_8HOUR_CAP manfiy bo'lishi mumkin emas (0 — o'chirilgan)")

    @staticmethod
    def from_env(environ=None) -> "Settings":
        environ = os.environ if environ is None else environ
        try:
            s = Settings(
                env=environ.get("APP_ENV", "development"),
                jwt_secret=environ["JWT_SECRET"],
                otp_secret=environ["OTP_SECRET"],
                sms_provider=environ.get("SMS_PROVIDER", "none"),
                sms_template=environ.get("SMS_TEMPLATE", "Tezyubor tasdiqlash kodi: {code}"),
                sms_daily_cap=int(environ.get("SMS_DAILY_CAP", "500")),
                sms_8hour_cap=int(environ.get("SMS_8HOUR_CAP", "0")),
                eskiz_email=environ.get("ESKIZ_EMAIL", ""),
                eskiz_password=environ.get("ESKIZ_PASSWORD", ""),
                eskiz_from=environ.get("ESKIZ_FROM", "4546"),
                database_url=environ.get("DATABASE_URL", ""),
            )
        except KeyError as e:
            raise ConfigError(f"Muhit o'zgaruvchisi yo'q: {e.args[0]}") from None
        except ValueError:
            raise ConfigError("SMS_DAILY_CAP va SMS_8HOUR_CAP butun son bo'lishi kerak") from None
        s.validate()
        return s
