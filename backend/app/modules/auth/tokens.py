import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Callable

import jwt

from ...config import Settings
from ...errors import TokenInvalid, TokenReuseDetected
from .stores import RefreshRecord, RefreshStore


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


def _sha(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class TokenService:
    """Qisqa muddatli access JWT + aylantiriladigan (rotation) refresh token.
    Refresh token bazada faqat xeshi saqlanadi. Ishlatilgan token qayta kelsa — butun oila bekor qilinadi."""

    def __init__(self, settings: Settings, store: RefreshStore, clock: Callable[[], float] = time.time):
        self._s = settings
        self._store = store
        self._clock = clock

    def issue_pair(self, user_id: str, family_id: str | None = None) -> TokenPair:
        now = self._clock()
        access = jwt.encode(
            {
                "sub": user_id,
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
            RefreshRecord(user_id, family_id or uuid.uuid4().hex, now + self._s.refresh_ttl),
        )
        return TokenPair(access, refresh, self._s.access_ttl)

    def verify_access(self, token: str) -> str:
        try:
            payload = jwt.decode(
                token,
                self._s.jwt_secret,
                algorithms=["HS256"],  # 'none' va boshqa algoritmlar rad etiladi
                options={"verify_exp": False, "require": ["exp", "iat", "sub"]},
            )
        except jwt.PyJWTError:
            raise TokenInvalid("Token yaroqsiz") from None
        if payload.get("typ") != "access" or self._clock() >= payload["exp"]:
            raise TokenInvalid("Token yaroqsiz")
        return str(payload["sub"])

    def peek_user(self, refresh_token: str) -> str:
        """Tokenni sarflamasdan egasini aniqlaydi (PIN bilan kirish uchun)."""
        rec = self._store.get(_sha(refresh_token or ""))
        if rec is None or rec.used or self._clock() >= rec.expires_at:
            raise TokenInvalid("Token yaroqsiz")
        return rec.user_id

    def rotate(self, refresh_token: str) -> TokenPair:
        token_hash = _sha(refresh_token or "")
        rec = self._store.get(token_hash)
        if rec is None:
            raise TokenInvalid("Token yaroqsiz")
        if rec.used:
            self._store.revoke_family(rec.family_id)
            raise TokenReuseDetected("Token qayta ishlatildi, sessiya bekor qilindi")
        if self._clock() >= rec.expires_at:
            raise TokenInvalid("Token yaroqsiz")
        if not self._store.mark_used(token_hash):
            # Bir vaqtda ikkinchi so'rov tokenni oldin ishlatib bo'lgan
            self._store.revoke_family(rec.family_id)
            raise TokenReuseDetected("Token qayta ishlatildi, sessiya bekor qilindi")
        return self.issue_pair(rec.user_id, rec.family_id)
