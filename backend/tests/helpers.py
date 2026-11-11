from app.config import Settings
from app.modules.auth.audit import AuditLog
from app.modules.auth.otp import NullSmsSender, OtpService
from app.modules.auth.service import AuthService
from app.modules.auth.stores import MemoryOtpStore, MemoryRefreshStore, MemoryUserStore
from app.modules.auth.tokens import TokenService

SECRET_A = "a" * 40
SECRET_B = "b" * 40


class FakeClock:
    def __init__(self, t: float = 1_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


class RecordingSms:
    is_real = True

    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    def send(self, phone, text):
        self.sent.append((phone, text))


def make_settings(env: str = "test", **kw) -> Settings:
    return Settings(env=env, jwt_secret=SECRET_A, otp_secret=SECRET_B, **kw)


def make_stack(env: str = "test", clock: FakeClock | None = None, sms=None, **kw):
    clock = clock or FakeClock()
    s = make_settings(env, **kw)
    otp_store = MemoryOtpStore()
    otp = OtpService(s, otp_store, sms or NullSmsSender(), clock)
    tokens = TokenService(s, MemoryRefreshStore(), clock)
    users = MemoryUserStore()
    audit = AuditLog(clock)
    svc = AuthService(s, otp, tokens, users, audit, clock)
    return svc, otp, tokens, users, audit, clock, otp_store
