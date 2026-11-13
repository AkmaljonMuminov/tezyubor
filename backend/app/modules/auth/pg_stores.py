"""PostgreSQL saqlash (stores.py dagi Protocol'larga mos). SQL faqat parametrli so'rovlar bilan — qiymatlar
hech qachon satrga qo'shilmaydi."""
import uuid

from ...db import Database
from .stores import OtpChallenge, RefreshRecord, User

_DAY = 86400


class PgUserStore:
    def __init__(self, db: Database):
        self._db = db

    @staticmethod
    def _row(r) -> User | None:
        if r is None:
            return None
        return User(
            id=str(r["id"]),
            phone=r["phone"],
            pin_hash=r["pin_hash"],
            pin_failures=r["pin_failures"],
            pin_locked_until=r["pin_locked_until"],
        )

    def get(self, user_id: str) -> User | None:
        try:
            uid = uuid.UUID(user_id)
        except (ValueError, AttributeError, TypeError):
            return None
        with self._db.connection() as c:
            return self._row(c.execute("SELECT * FROM users WHERE id = %s", (uid,)).fetchone())

    def get_by_phone(self, phone: str) -> User | None:
        with self._db.connection() as c:
            return self._row(c.execute("SELECT * FROM users WHERE phone = %s", (phone,)).fetchone())

    def create(self, phone: str) -> User:
        with self._db.connection() as c:
            # Bir vaqtda ikki so'rov kelsa ham bitta foydalanuvchi qoladi
            c.execute(
                "INSERT INTO users (id, phone) VALUES (%s, %s) ON CONFLICT (phone) DO NOTHING",
                (uuid.uuid4(), phone),
            )
            return self._row(c.execute("SELECT * FROM users WHERE phone = %s", (phone,)).fetchone())

    def save(self, user: User) -> None:
        with self._db.connection() as c:
            c.execute(
                "UPDATE users SET pin_hash = %s, pin_failures = %s, pin_locked_until = %s WHERE id = %s",
                (user.pin_hash, user.pin_failures, user.pin_locked_until, uuid.UUID(user.id)),
            )


class PgRefreshStore:
    def __init__(self, db: Database):
        self._db = db

    def put(self, token_hash: str, rec: RefreshRecord) -> None:
        with self._db.connection() as c:
            c.execute(
                "INSERT INTO refresh_tokens (token_hash, user_id, family_id, expires_at, used) "
                "VALUES (%s, %s, %s, %s, %s)",
                (token_hash, uuid.UUID(rec.user_id), rec.family_id, rec.expires_at, rec.used),
            )

    def get(self, token_hash: str) -> RefreshRecord | None:
        with self._db.connection() as c:
            r = c.execute("SELECT * FROM refresh_tokens WHERE token_hash = %s", (token_hash,)).fetchone()
        if r is None:
            return None
        return RefreshRecord(str(r["user_id"]), r["family_id"], r["expires_at"], r["used"])

    def mark_used(self, token_hash: str) -> bool:
        """Atomik: faqat bitta so'rov tokenni 'ishlatilgan' qila oladi (poyga holatida ikkinchisi False oladi)."""
        with self._db.connection() as c:
            cur = c.execute(
                "UPDATE refresh_tokens SET used = true WHERE token_hash = %s AND used = false", (token_hash,)
            )
            return cur.rowcount == 1

    def revoke_family(self, family_id: str) -> None:
        with self._db.connection() as c:
            c.execute("DELETE FROM refresh_tokens WHERE family_id = %s", (family_id,))

    def purge_expired(self, now: float) -> None:
        """Muddati o'tganiga 1 kun bo'lgan yozuvlarni o'chiradi (ishlatilgan token qayta kelishini aniqlash uchun saqlanadi)."""
        with self._db.connection() as c:
            c.execute("DELETE FROM refresh_tokens WHERE expires_at < %s", (now - _DAY,))


class PgOtpStore:
    """OTP urinishlari xotirada (2 daqiqalik, restartda yo'qolsa foydalanuvchi qayta so'raydi).
    SMS so'rovlari soni (telefon va umumiy limit) bazada: restart limitni nolga tushirib yubormasin."""

    def __init__(self, db: Database):
        self._db = db
        self._challenges: dict[str, OtpChallenge] = {}

    def put(self, challenge_id, ch):
        self._challenges[challenge_id] = ch

    def get(self, challenge_id):
        return self._challenges.get(challenge_id)

    def delete(self, challenge_id):
        self._challenges.pop(challenge_id, None)

    def request_times(self, phone):
        with self._db.connection() as c:
            rows = c.execute("SELECT ts FROM sms_requests WHERE phone = %s ORDER BY ts", (phone,)).fetchall()
        return [r["ts"] for r in rows]

    def add_request(self, phone, ts):
        with self._db.connection() as c:
            c.execute("INSERT INTO sms_requests (phone, ts) VALUES (%s, %s)", (phone, ts))
            # Eng uzun oyna 24 soat; undan eskilari kerak emas
            c.execute("DELETE FROM sms_requests WHERE ts < %s", (ts - 2 * _DAY,))

    def discard_request(self, phone, ts):
        with self._db.connection() as c:
            c.execute(
                "DELETE FROM sms_requests WHERE id = "
                "(SELECT id FROM sms_requests WHERE phone = %s AND ts = %s LIMIT 1)",
                (phone, ts),
            )
