"""Saqlash qatlami. Hozir xotirada (test/dev). Keyingi bosqichda Redis (OTP, limitlar) va
PostgreSQL (foydalanuvchi, refresh) implementatsiyalari shu Protocol'larga mos yoziladi."""
import threading
import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass
class OtpChallenge:
    phone: str
    code_hash: str
    expires_at: float
    attempts: int = 0


@dataclass
class RefreshRecord:
    user_id: str
    family_id: str
    expires_at: float
    used: bool = False


@dataclass
class User:
    id: str
    phone: str
    pin_hash: str | None = None
    pin_failures: int = 0
    pin_locked_until: float = 0.0
    pin_lock_level: int = 0   # ketma-ket nechta blok bo'lgan (har blokda muddat ikki baravar uzayadi)


@dataclass
class SessionRecord:
    """Bitta qurilma sessiyasi = bitta refresh token oilasi (family_id)."""

    id: str
    user_id: str
    device_label: str
    created_at: float
    last_used_at: float
    revoked: bool = False


@dataclass(frozen=True)
class PinAttempt:
    allowed: bool          # False — hozir bloklangan, PIN tekshirilmaydi
    retry_after: int = 0   # allowed=False bo'lsa: necha soniyadan keyin
    attempts_left: int = 0
    locked_now: bool = False  # bu urinish blokni yoqdi (xato bo'lsa — PinLocked)


def lock_duration(level: int, base: int, max_seconds: int) -> int:
    """1-blok `base`, keyingilari ikki baravardan (yuqori chegara bilan)."""
    return min(base * (2 ** max(level, 0)), max_seconds)


class OtpStore(Protocol):
    def put(self, challenge_id: str, ch: OtpChallenge) -> None: ...
    def get(self, challenge_id: str) -> OtpChallenge | None: ...
    def delete(self, challenge_id: str) -> None: ...
    def bump_attempts(self, challenge_id: str) -> int | None: ...   # atomik; yo'q bo'lsa None
    def consume(self, challenge_id: str) -> bool: ...               # atomik o'chirish; kod bir martalik
    def request_times(self, phone: str) -> list[float]: ...
    def add_request(self, phone: str, ts: float) -> None: ...
    def discard_request(self, phone: str, ts: float) -> None: ...


class RefreshStore(Protocol):
    def put(self, token_hash: str, rec: RefreshRecord) -> None: ...
    def get(self, token_hash: str) -> RefreshRecord | None: ...
    def mark_used(self, token_hash: str) -> bool: ...
    def revoke_family(self, family_id: str) -> None: ...
    def purge_expired(self, now: float) -> None: ...


class UserStore(Protocol):
    def get(self, user_id: str) -> User | None: ...
    def get_by_phone(self, phone: str) -> User | None: ...
    def create(self, phone: str) -> User: ...
    def save(self, user: User) -> None: ...
    def begin_pin_attempt(
        self, user_id: str, now: float, max_failures: int, base_lock: int, max_lock: int
    ) -> PinAttempt: ...
    def reset_pin_state(self, user_id: str) -> None: ...
    def set_pin_hash(self, user_id: str, pin_hash: str, only_if_unset: bool = False) -> bool: ...


class SessionStore(Protocol):
    def create(self, rec: SessionRecord) -> None: ...
    def touch(self, session_id: str, now: float) -> None: ...
    def is_active(self, session_id: str) -> bool: ...
    def list_active(self, user_id: str) -> list[SessionRecord]: ...
    def revoke(self, session_id: str, user_id: str) -> bool: ...   # faqat egasiniki; faol bo'lgan bo'lsa True


class MemoryOtpStore:
    def __init__(self):
        self._challenges: dict[str, OtpChallenge] = {}
        self._requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def put(self, challenge_id, ch):
        self._challenges[challenge_id] = ch

    def get(self, challenge_id):
        return self._challenges.get(challenge_id)

    def delete(self, challenge_id):
        self._challenges.pop(challenge_id, None)

    def bump_attempts(self, challenge_id):
        with self._lock:
            ch = self._challenges.get(challenge_id)
            if ch is None:
                return None
            ch.attempts += 1
            return ch.attempts

    def consume(self, challenge_id):
        with self._lock:
            return self._challenges.pop(challenge_id, None) is not None

    def request_times(self, phone):
        return list(self._requests.get(phone, []))

    def add_request(self, phone, ts):
        times = self._requests.setdefault(phone, [])
        times.append(ts)
        # Eng uzun oyna 24 soat; undan eskilari kerak emas (xotira o'smasin)
        times[:] = [t for t in times if t >= ts - 2 * 86400]

    def discard_request(self, phone, ts):
        """SMS yuborilmay qolsa, foydalanuvchi limiti behuda sarflanmasin."""
        times = self._requests.get(phone, [])
        if ts in times:
            times.remove(ts)


class MemoryRefreshStore:
    def __init__(self):
        self._records: dict[str, RefreshRecord] = {}

    def put(self, token_hash, rec):
        self._records[token_hash] = rec

    def get(self, token_hash):
        return self._records.get(token_hash)

    def mark_used(self, token_hash):
        rec = self._records.get(token_hash)
        if rec is None or rec.used:
            return False
        rec.used = True
        return True

    def revoke_family(self, family_id):
        for h in [h for h, r in self._records.items() if r.family_id == family_id]:
            del self._records[h]

    def purge_expired(self, now):
        for h in [h for h, r in self._records.items() if r.expires_at < now - 86400]:
            del self._records[h]


class MemoryUserStore:
    def __init__(self):
        self._users: dict[str, User] = {}
        self._by_phone: dict[str, str] = {}
        self._lock = threading.Lock()

    def get(self, user_id):
        return self._users.get(user_id)

    def get_by_phone(self, phone):
        uid = self._by_phone.get(phone)
        return self._users.get(uid) if uid else None

    def create(self, phone):
        existing = self.get_by_phone(phone)
        if existing is not None:
            return existing
        user = User(id=str(uuid.uuid4()), phone=phone)
        self._users[user.id] = user
        self._by_phone[phone] = user.id
        return user

    def save(self, user):
        """Xotirada obyektning o'zi saqlanadi; bu usul bazali implementatsiya bilan bir xil interfeys uchun."""
        self._users[user.id] = user

    def begin_pin_attempt(self, user_id, now, max_failures, base_lock, max_lock):
        """Atomik: urinish AVVAL sanaladi, keyin tekshiriladi — parallel so'rovlar bilan limitni aylanib bo'lmaydi."""
        with self._lock:
            u = self._users[user_id]
            if now < u.pin_locked_until:
                return PinAttempt(False, retry_after=int(u.pin_locked_until - now) + 1)
            u.pin_failures += 1
            if u.pin_failures >= max_failures:
                dur = lock_duration(u.pin_lock_level, base_lock, max_lock)
                u.pin_failures = 0
                u.pin_lock_level += 1
                u.pin_locked_until = now + dur
                return PinAttempt(True, attempts_left=0, locked_now=True, retry_after=dur)
            return PinAttempt(True, attempts_left=max_failures - u.pin_failures)

    def reset_pin_state(self, user_id):
        with self._lock:
            u = self._users[user_id]
            u.pin_failures, u.pin_lock_level, u.pin_locked_until = 0, 0, 0.0

    def set_pin_hash(self, user_id, pin_hash, only_if_unset=False):
        with self._lock:
            u = self._users[user_id]
            if only_if_unset and u.pin_hash is not None:
                return False
            u.pin_hash = pin_hash
            return True


class MemorySessionStore:
    def __init__(self):
        self._items: dict[str, SessionRecord] = {}
        self._lock = threading.Lock()

    def create(self, rec):
        with self._lock:
            self._items[rec.id] = rec

    def touch(self, session_id, now):
        with self._lock:
            rec = self._items.get(session_id)
            if rec is not None and not rec.revoked:
                rec.last_used_at = now

    def is_active(self, session_id):
        rec = self._items.get(session_id)
        return rec is not None and not rec.revoked

    def list_active(self, user_id):
        rows = [r for r in self._items.values() if r.user_id == user_id and not r.revoked]
        return sorted(rows, key=lambda r: r.last_used_at, reverse=True)

    def revoke(self, session_id, user_id):
        with self._lock:
            rec = self._items.get(session_id)
            if rec is None or rec.user_id != user_id or rec.revoked:
                return False
            rec.revoked = True
            return True
