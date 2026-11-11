"""Sozlamalar faqat muhit o'zgaruvchilaridan (.env) olinadi. Kod ichida maxfiy qiymat YO'Q."""
import os
from dataclasses import dataclass

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

    @staticmethod
    def from_env(environ=None) -> "Settings":
        environ = os.environ if environ is None else environ
        try:
            s = Settings(
                env=environ.get("APP_ENV", "development"),
                jwt_secret=environ["JWT_SECRET"],
                otp_secret=environ["OTP_SECRET"],
            )
        except KeyError as e:
            raise ConfigError(f"Muhit o'zgaruvchisi yo'q: {e.args[0]}") from None
        s.validate()
        return s
