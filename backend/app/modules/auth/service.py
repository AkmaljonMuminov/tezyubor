import time
from typing import Callable

from ...config import Settings
from ...errors import (
    PinAlreadySet,
    PinInvalid,
    PinLocked,
    PinNotSet,
    SmsDeliveryError,
    TokenInvalid,
    TokenReuseDetected,
    ValidationError,
)
from .audit import AuditLog
from .otp import OtpService
from .security import hash_pin, verify_pin
from .stores import UserStore
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
        self.audit = audit
        self._clock = clock

    def request_otp(self, phone: str) -> str:
        try:
            challenge_id = self._otp.request(phone)
        except SmsDeliveryError:
            self._audit.record("otp_sms_failed")
            raise
        self._audit.record("otp_requested")
        return challenge_id

    def verify_otp(self, challenge_id: str, code: str) -> tuple[TokenPair, bool]:
        """(tokenlar, pin_o'rnatilganmi)"""
        try:
            phone = self._otp.verify(challenge_id, code)
        except Exception as e:
            self._audit.record("otp_failed", reason=getattr(e, "code", "UNKNOWN"))
            raise
        user = self._users.get_by_phone(phone) or self._users.create(phone)
        self._audit.record("login_otp_success", user_id=user.id, phone=mask_phone(phone))
        return self._tokens.issue_pair(user.id), user.pin_hash is not None

    def set_pin(self, user_id: str, pin: str) -> None:
        user = self._users.get(user_id)
        if user is None:
            raise TokenInvalid("Token yaroqsiz")
        if user.pin_hash is not None:
            raise PinAlreadySet("PIN allaqachon o'rnatilgan")
        if not is_pin_acceptable(pin):
            raise ValidationError("PIN juda oddiy yoki noto'g'ri formatda")
        user.pin_hash = hash_pin(pin)
        self._users.save(user)
        self._audit.record("pin_set", user_id=user.id)

    def login_with_pin(self, refresh_token: str, pin: str) -> TokenPair:
        user_id = self._tokens.peek_user(refresh_token)
        user = self._users.get(user_id)
        if user is None:
            raise TokenInvalid("Token yaroqsiz")
        if user.pin_hash is None:
            raise PinNotSet("PIN o'rnatilmagan")
        now = self._clock()
        if now < user.pin_locked_until:
            raise PinLocked("PIN vaqtincha bloklangan", retry_after=int(user.pin_locked_until - now) + 1)
        if not verify_pin(pin or "", user.pin_hash):
            user.pin_failures += 1
            self._audit.record("pin_failed", user_id=user.id, failures=user.pin_failures)
            if user.pin_failures >= self._s.pin_max_failures:
                user.pin_failures = 0
                user.pin_locked_until = now + self._s.pin_lock_seconds
                self._users.save(user)
                self._audit.record("pin_locked", user_id=user.id)
                raise PinLocked("PIN vaqtincha bloklangan", retry_after=self._s.pin_lock_seconds)
            self._users.save(user)
            raise PinInvalid("PIN noto'g'ri", attempts_left=self._s.pin_max_failures - user.pin_failures)
        if user.pin_failures:
            user.pin_failures = 0
            self._users.save(user)
        self._audit.record("login_pin_success", user_id=user.id)
        return self._tokens.rotate(refresh_token)

    def refresh(self, refresh_token: str) -> TokenPair:
        try:
            return self._tokens.rotate(refresh_token)
        except TokenReuseDetected:
            self._audit.record("refresh_reuse_detected")
            raise

    def authenticate(self, access_token: str) -> str:
        return self._tokens.verify_access(access_token)
