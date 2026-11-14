import hashlib
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Callable

import jwt

from ...config import Settings
from ...errors import TokenInvalid, TokenReuseDetected
from .stores import MemorySessionStore, RefreshRecord, RefreshStore, SessionRecord, SessionStore


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


def _sha(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def clean_device_label(label: str | None) -> str:
    """Qurilma nomi foydalanuvchi ro'yxatida ko'rinadi: boshqaruv belgilarisiz, qisqa."""
    if not label:
        return ""
    return re.sub(r"[\x00-\x1f\x7f]", "", label).strip()[:60]


class TokenService:
    """Qisqa muddatli access JWT + aylantiriladigan (rotation) refresh token.
    Refresh token bazada faqat xeshi saqlanadi. Ishlatilgan token qayta kelsa — butun oila bekor qilinadi."""

    def __init__(
        self,
        settings: Settings,
        store: RefreshStore,
        clock: Callable[[], float] = time.time,
        sessions: SessionStore | None = None,
    ):
        self._s = settings
        self._store = store
        self._clock = clock
        self._sessions = sessions if sessions is not None else MemorySessionStore()

    def issue_pair(self, user_id: str, family_id: str | None = None, device_label: str = "") -> TokenPair:
        now = self._clock()
        if family_id is None:
            family_id = uuid.uuid4().hex
            self._sessions.create(
                SessionRecord(family_id, user_id, clean_device_label(device_label), now, now)
            )
        else:
            self._sessions.touch(family_id, now)
        access = jwt.encode(
            {
                "sub": user_id,
                "sid": family_id,
                "iat": int(now),
                "exp": int(now) + self._s.access_ttl,
                "typ": "access",
                "jti": uuid.uuid4().hex,
            },
            self._s.jwt_secret,
            algorithm="HS256",
        )
        refresh = secrets.token_urlsafe(32)
        if secrets.randbelow(50) == 0:  # eski yozuvlarni vaqti-vaqti bilan tozalash (arzon)
            self._store.purge_expired(now)
        self._store.put(
            _sha(refresh),
            RefreshRecord(user_id, family_id, now + self._s.refresh_ttl),
        )
        return TokenPair(access, refresh, self._s.access_ttl)

    def verify_access(self, token: str) -> str:
        return self.verify_access_session(token)[0]

    def verify_access_session(self, token: str) -> tuple[str, str]:
        """(user_id, session_id). Bekor qilingan sessiyaning access tokeni muddati tugamasa ham o'tmaydi."""
        try:
            payload = jwt.decode(
                token,
                self._s.jwt_secret,
                algorithms=["HS256"],  # 'none' va boshqa algoritmlar rad etiladi
                options={"verify_exp": False, "require": ["exp", "iat", "sub", "sid"]},
            )
        except jwt.PyJWTError:
            raise TokenInvalid("Token yaroqsiz") from None
        if payload.get("typ") != "access" or self._clock() >= payload["exp"]:
            raise TokenInvalid("Token yaroqsiz")
        sid = str(payload["sid"])
        if not self._sessions.is_active(sid):
            raise TokenInvalid("Token yaroqsiz")
        return str(payload["sub"]), sid

    def peek_user(self, refresh_token: str) -> str:
        """Tokenni sarflamasdan egasini aniqlaydi (PIN bilan kirish uchun)."""
        rec = self._store.get(_sha(refresh_token or ""))
        if rec is None or rec.used or self._clock() >= rec.expires_at or not self._sessions.is_active(rec.family_id):
            raise TokenInvalid("Token yaroqsiz")
        return rec.user_id

    def rotate(self, refresh_token: str) -> TokenPair:
        token_hash = _sha(refresh_token or "")
        rec = self._store.get(token_hash)
        if rec is None:
            raise TokenInvalid("Token yaroqsiz")
        if rec.used:
            self._kill(rec.family_id, rec.user_id)
            raise TokenReuseDetected("Token qayta ishlatildi, sessiya bekor qilindi")
        if self._clock() >= rec.expires_at or not self._sessions.is_active(rec.family_id):
            raise TokenInvalid("Token yaroqsiz")
        if not self._store.mark_used(token_hash):
            # Bir vaqtda ikkinchi so'rov tokenni oldin ishlatib bo'lgan
            self._kill(rec.family_id, rec.user_id)
            raise TokenReuseDetected("Token qayta ishlatildi, sessiya bekor qilindi")
        return self.issue_pair(rec.user_id, rec.family_id)

    def _kill(self, family_id: str, user_id: str) -> None:
        self._sessions.revoke(family_id, user_id)
        self._store.revoke_family(family_id)

    def logout(self, refresh_token: str) -> str | None:
        """Refresh token egasining shu qurilma sessiyasini bekor qiladi. Qaytaradi: user_id (yo'q/yaroqsiz bo'lsa None).
        Ishlatilgan eski token bilan ham ishlaydi (sessiya baribir yopiladi)."""
        rec = self._store.get(_sha(refresh_token or ""))
        if rec is None:
            return None
        self._kill(rec.family_id, rec.user_id)
        return rec.user_id

    def list_sessions(self, user_id: str) -> list[SessionRecord]:
        return self._sessions.list_active(user_id)

    def revoke_session(self, user_id: str, session_id: str) -> bool:
        """Faqat foydalanuvchining o'z sessiyasini bekor qiladi; boshqasiniki (yoki yo'q) bo'lsa False."""
        if not self._sessions.revoke(session_id, user_id):
            return False
        self._store.revoke_family(session_id)
        return True
