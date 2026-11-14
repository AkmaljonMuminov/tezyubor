import time
from typing import Callable

from ...config import Settings
from ...errors import (
    PinAlreadySet,
    PinInvalid,
    PinLocked,
    PinNotSet,
    SessionNotFound,
    SmsDeliveryError,
    TokenInvalid,
    TokenReuseDetected,
    ValidationError,
)
from .audit import AuditLog
from .otp import OtpService
from .security import hash_pin, needs_rehash, verify_pin
from .stores import SessionRecord, UserStore
from .tokens import TokenPair, TokenService
from .validators import is_pin_acceptable, mask_phone


class AuthService:
    def __init__(
        self,
        settings: Settings,
        otp: OtpService,
        tokens: TokenService,
        users: UserStore,
        audit: AuditLog,
        clock: Callable[[], float] = time.time,
    ):
        self._s = settings
        self._otp = otp
        self._tokens = tokens
        self._users = users
        self._audit = audit
        self._clock = clock

    def request_otp(self, phone: str) -> str:
        try:
            challenge_id = self._otp.request(phone)
        except SmsDeliveryError:
            self._audit.record("otp_sms_failed")
            raise
        self._audit.record("otp_requested")
        return challenge_id

    def verify_otp(self, challenge_id: str, code: str, device_label: str = "") -> tuple[TokenPair, bool]:
        """(tokenlar, pin_o'rnatilganmi). Har muvaffaqiyatli OTP — yangi qurilma sessiyasi."""
        try:
            phone = self._otp.verify(challenge_id, code)
        except Exception as e:
            self._audit.record("otp_failed", reason=getattr(e, "code", "UNKNOWN"))
            raise
        user = self._users.get_by_phone(phone) or self._users.create(phone)
        self._audit.record("login_otp_success", user_id=user.id, phone=mask_phone(phone))
        return self._tokens.issue_pair(user.id, device_label=device_label), user.pin_hash is not None

    def set_pin(self, user_id: str, pin: str) -> None:
        user = self._users.get(user_id)
        if user is None:
            raise TokenInvalid("Token yaroqsiz")
        if user.pin_hash is not None:
            raise PinAlreadySet("PIN allaqachon o'rnatilgan")
        if not is_pin_acceptable(pin):
            raise ValidationError("PIN juda oddiy yoki noto'g'ri formatda")
        # Atomik: ikki parallel so'rovdan faqat bittasi PIN'ni o'rnata oladi
        if not self._users.set_pin_hash(user.id, hash_pin(pin, self._s.pin_pepper), only_if_unset=True):
            raise PinAlreadySet("PIN allaqachon o'rnatilgan")
        self._audit.record("pin_set", user_id=user.id)

    def check_pin(self, user_id: str, pin: str, purpose: str = "login") -> None:
        """PIN'ni tekshiradi (xato/blok bo'lsa AppError). Hisoblagich AVVAL atomik oshiriladi, shuning uchun
        parallel so'rovlar bilan ham limitdan ortiq taxmin qilib bo'lmaydi. Pul harakati ham shu yo'ldan o'tadi."""
        user = self._users.get(user_id)
        if user is None:
            raise TokenInvalid("Token yaroqsiz")
        if user.pin_hash is None:
            raise PinNotSet("PIN o'rnatilmagan")
        att = self._users.begin_pin_attempt(
            user.id, self._clock(), self._s.pin_max_failures, self._s.pin_lock_seconds, self._s.pin_lock_max_seconds
        )
        if not att.allowed:
            raise PinLocked("PIN vaqtincha bloklangan", retry_after=att.retry_after)
        if not verify_pin(pin or "", user.pin_hash, self._s.pin_pepper):
            self._audit.record("pin_failed", user_id=user.id, purpose=purpose, attempts_left=att.attempts_left)
            if att.locked_now:
                self._audit.record("pin_locked", user_id=user.id, seconds=att.retry_after)
                raise PinLocked("PIN vaqtincha bloklangan", retry_after=att.retry_after)
            raise PinInvalid("PIN noto'g'ri", attempts_left=att.attempts_left)
        self._users.reset_pin_state(user.id)
        if needs_rehash(user.pin_hash, self._s.pin_pepper):
            self._users.set_pin_hash(user.id, hash_pin(pin, self._s.pin_pepper))

    def login_with_pin(self, refresh_token: str, pin: str) -> TokenPair:
        user_id = self._tokens.peek_user(refresh_token)
        self.check_pin(user_id, pin)
        self._audit.record("login_pin_success", user_id=user_id)
        return self._tokens.rotate(refresh_token)

    def refresh(self, refresh_token: str) -> TokenPair:
        try:
            return self._tokens.rotate(refresh_token)
        except TokenReuseDetected:
            self._audit.record("refresh_reuse_detected")
            raise

    def authenticate(self, access_token: str) -> str:
        return self._tokens.verify_access(access_token)

    def logout(self, refresh_token: str) -> None:
        """Serverda sessiyani bekor qiladi. Token yo'q/yaroqsiz bo'lsa ham xato bermaydi (tokenni taxmin qilishga yo'l yo'q)."""
        user_id = self._tokens.logout(refresh_token)
        if user_id is not None:
            self._audit.record("logout", user_id=user_id)

    def list_sessions(self, access_token: str) -> list[tuple[SessionRecord, bool]]:
        user_id, sid = self._tokens.verify_access_session(access_token)
        return [(r, r.id == sid) for r in self._tokens.list_sessions(user_id)]

    def revoke_session(self, access_token: str, session_id: str) -> None:
        user_id, _ = self._tokens.verify_access_session(access_token)
        if not self._tokens.revoke_session(user_id, session_id):
            raise SessionNotFound("Sessiya topilmadi")
        self._audit.record("session_revoked", user_id=user_id)
