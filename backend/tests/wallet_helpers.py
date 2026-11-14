from app.modules.wallet.service import WalletService
from app.modules.wallet.store import MemoryWalletStore
from tests.helpers import make_stack

KEY = "k" * 40
PIN = "2580"


def make_pan(prefix: str, body: str) -> str:
    """Luhn bo'yicha to'g'ri 16 xonali raqam (testlar uchun)."""
    base = prefix + body
    base = base[:15]
    total = 0
    for i, ch in enumerate(reversed(base)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return base + str((10 - total % 10) % 10)


PAN_A = make_pan("8600", "12345678901")
PAN_B = make_pan("9860", "98765432101")
PAN_C = make_pan("4111", "11111111111")


class Env:
    """Ikki foydalanuvchi (A, B), ularning PIN'i o'rnatilgan, xotira hamyon store'i."""

    def __init__(self, **kw):
        kw.setdefault("otp_cooldown", 0)
        kw.setdefault("otp_max_per_hour", 100)
        self.auth, _otp, self.tokens, self.users, self.audit, self.clock, _ = make_stack(
            wallet_enabled=True, card_index_key=KEY, **kw
        )
        self.settings = self.auth._s
        self.store = MemoryWalletStore()
        self.wallet = WalletService(self.settings, self.store, self.auth.check_pin, self.audit, self.clock)
        self.a = self._user("901111111")
        self.b = self._user("902222222")

    def _user(self, phone: str) -> str:
        pair, _ = self.auth.verify_otp(self.auth.request_otp(phone), "123456")
        uid = self.auth.authenticate(pair.access_token)
        self.auth.set_pin(uid, PIN)
        return uid

    def card(self, uid: str, pan: str, name: str = "ALISHER KARIMOV") -> dict:
        return self.wallet.add_card(uid, pan, 12, 2099, name)
