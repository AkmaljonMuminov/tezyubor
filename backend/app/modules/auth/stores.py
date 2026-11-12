"""Saqlash qatlami. Hozir xotirada (test/dev). Keyingi bosqichda Redis (OTP, limitlar) va
PostgreSQL (foydalanuvchi, refresh) implementatsiyalari shu Protocol'larga mos yoziladi."""
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


class OtpStore(Protocol):
    def put(self, challenge_id: str, ch: OtpChallenge) -> None: ...
    def get(self, challenge_id: str) -> OtpChallenge | None: ...
    def delete(self, challenge_id: str) -> None: ...
    def request_times(self, phone: str) -> list[float]: ...
    def add_request(self, phone: str, ts: float) -> None: ...
    def discard_request(self, phone: str, ts: float) -> None: ...


class RefreshStore(Protocol):
    def put(self, token_hash: str, rec: RefreshRecord) -> None: ...
    def get(self, token_hash: str) -> RefreshRecord | None: ...
    def revoke_family(self, family_id: str) -> None: ...


class UserStore(Protocol):
    def get(self, user_id: str) -> User | None: ...
    def get_by_phone(self, phone: str) -> User | None: ...
    def create(self, phone: str) -> User: ...


class MemoryOtpStore:
    def __init__(self):
        self._challenges: dict[str, OtpChallenge] = {}
        self._requests: dict[str, list[float]] = {}

    def put(self, challenge_id, ch):
        self._challenges[challenge_id] = ch

    def get(self, challenge_id):
        return self._challenges.get(challenge_id)

    def delete(self, challenge_id):
        self._challenges.pop(challenge_id, None)

    def request_times(self, phone):
        return list(self._requests.get(phone, []))

    def add_request(self, phone, ts):
        self._requests.setdefault(phone, []).append(ts)

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

    def revoke_family(self, family_id):
        for h in [h for h, r in self._records.items() if r.family_id == family_id]:
            del self._records[h]


class MemoryUserStore:
    def __init__(self):
        self._users: dict[str, User] = {}
        self._by_phone: dict[str, str] = {}

    def get(self, user_id):
        return self._users.get(user_id)

    def get_by_phone(self, phone):
        uid = self._by_phone.get(phone)
        return self._users.get(uid) if uid else None

    def create(self, phone):
        import uuid

        user = User(id=str(uuid.uuid4()), phone=phone)
        self._users[user.id] = user
        self._by_phone[phone] = user.id
        return user
