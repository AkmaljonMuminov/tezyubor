"""PostgreSQL saqlash (stores.py dagi Protocol'larga mos). SQL faqat parametrli so'rovlar bilan — qiymatlar
hech qachon satrga qo'shilmaydi."""
import uuid

from ...db import Database
from .stores import OtpChallenge, PinAttempt, RefreshRecord, SessionRecord, User, lock_duration

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
            pin_lock_level=r["pin_lock_level"],
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
                "UPDATE users SET pin_hash = %s, pin_failures = %s, pin_locked_until = %s, pin_lock_level = %s "
                "WHERE id = %s",
                (user.pin_hash, user.pin_failures, user.pin_locked_until, user.pin_lock_level, uuid.UUID(user.id)),
            )

    def begin_pin_attempt(self, user_id, now, max_failures, base_lock, max_lock):
        """Atomik: qator `FOR UPDATE` bilan qulflanadi, shuning uchun parallel so'rovlar navbat bilan sanaladi."""
        with self._db.connection() as c:
            r = c.execute(
                "SELECT pin_failures, pin_locked_until, pin_lock_level FROM users WHERE id = %s FOR UPDATE",
                (uuid.UUID(user_id),),
            ).fetchone()
            if r is None:
                return PinAttempt(False)
            if now < r["pin_locked_until"]:
                return PinAttempt(False, retry_after=int(r["pin_locked_until"] - now) + 1)
            failures = r["pin_failures"] + 1
            if failures >= max_failures:
                dur = lock_duration(r["pin_lock_level"], base_lock, max_lock)
                c.execute(
                    "UPDATE users SET pin_failures = 0, pin_lock_level = pin_lock_level + 1, pin_locked_until = %s "
                    "WHERE id = %s",
                    (now + dur, uuid.UUID(user_id)),
                )
                return PinAttempt(True, attempts_left=0, locked_now=True, retry_after=dur)
            c.execute("UPDATE users SET pin_failures = %s WHERE id = %s", (failures, uuid.UUID(user_id)))
            return PinAttempt(True, attempts_left=max_failures - failures)

    def reset_pin_state(self, user_id):
        with self._db.connection() as c:
            c.execute(
                "UPDATE users SET pin_failures = 0, pin_lock_level = 0, pin_locked_until = 0 WHERE id = %s",
                (uuid.UUID(user_id),),
            )

    def set_pin_hash(self, user_id, pin_hash, only_if_unset=False):
        with self._db.connection() as c:
            cond = " AND pin_hash IS NULL" if only_if_unset else ""
            cur = c.execute(
                "UPDATE users SET pin_hash = %s WHERE id = %s" + cond, (pin_hash, uuid.UUID(user_id))
            )
            return cur.rowcount == 1


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
    """OTP challenge'lar va SMS so'rovlari soni bazada: restart yoki bir necha server nusxasi bo'lsa ham
    kod ishlaydi, urinish va SMS limitlari nolga tushib ketmaydi."""

    def __init__(self, db: Database):
        self._db = db

    def put(self, challenge_id, ch):
        with self._db.connection() as c:
            c.execute(
                "INSERT INTO otp_challenges (challenge_id, phone, code_hash, expires_at, attempts) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (challenge_id) DO UPDATE SET phone = EXCLUDED.phone, code_hash = EXCLUDED.code_hash, "
                "expires_at = EXCLUDED.expires_at, attempts = EXCLUDED.attempts",
                (challenge_id, ch.phone, ch.code_hash, ch.expires_at, ch.attempts),
            )
            # Muddati o'tganiga 1 kun bo'lganlarni tozalash (jadval o'smasin)
            c.execute("DELETE FROM otp_challenges WHERE expires_at < %s", (ch.expires_at - _DAY,))

    def get(self, challenge_id):
        with self._db.connection() as c:
            r = c.execute("SELECT * FROM otp_challenges WHERE challenge_id = %s", (challenge_id,)).fetchone()
        if r is None:
            return None
        return OtpChallenge(r["phone"], r["code_hash"], r["expires_at"], r["attempts"])

    def delete(self, challenge_id):
        with self._db.connection() as c:
            c.execute("DELETE FROM otp_challenges WHERE challenge_id = %s", (challenge_id,))

    def bump_attempts(self, challenge_id):
        with self._db.connection() as c:
            r = c.execute(
                "UPDATE otp_challenges SET attempts = attempts + 1 WHERE challenge_id = %s RETURNING attempts",
                (challenge_id,),
            ).fetchone()
        return None if r is None else r["attempts"]

    def consume(self, challenge_id):
        with self._db.connection() as c:
            return c.execute("DELETE FROM otp_challenges WHERE challenge_id = %s", (challenge_id,)).rowcount == 1

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


class PgSessionStore:
    def __init__(self, db: Database):
        self._db = db

    @staticmethod
    def _rec(r) -> SessionRecord:
        return SessionRecord(
            id=r["id"],
            user_id=str(r["user_id"]),
            device_label=r["device_label"],
            created_at=r["created_at"],
            last_used_at=r["last_used_at"],
            revoked=r["revoked_at"] is not None,
        )

    def create(self, rec):
        with self._db.connection() as c:
            c.execute(
                "INSERT INTO auth_sessions (id, user_id, device_label, created_at, last_used_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (rec.id, uuid.UUID(rec.user_id), rec.device_label, rec.created_at, rec.last_used_at),
            )

    def touch(self, session_id, now):
        with self._db.connection() as c:
            c.execute(
                "UPDATE auth_sessions SET last_used_at = %s WHERE id = %s AND revoked_at IS NULL", (now, session_id)
            )

    def is_active(self, session_id):
        with self._db.connection() as c:
            r = c.execute("SELECT 1 AS ok FROM auth_sessions WHERE id = %s AND revoked_at IS NULL", (session_id,)).fetchone()
        return r is not None

    def list_active(self, user_id):
        with self._db.connection() as c:
            rows = c.execute(
                "SELECT * FROM auth_sessions WHERE user_id = %s AND revoked_at IS NULL ORDER BY last_used_at DESC",
                (uuid.UUID(user_id),),
            ).fetchall()
        return [self._rec(r) for r in rows]

    def revoke(self, session_id, user_id):
        with self._db.connection() as c:
            cur = c.execute(
                "UPDATE auth_sessions SET revoked_at = extract(epoch from now()) "
                "WHERE id = %s AND user_id = %s AND revoked_at IS NULL",
                (session_id, uuid.UUID(user_id)),
            )
            return cur.rowcount == 1


class PgAuditSink:
    """audit_log jadvaliga faqat qo'shiladi (o'chirish/o'zgartirish kodda yo'q)."""

    def __init__(self, db: Database):
        self._db = db

    def write(self, ev):
        from psycopg.types.json import Jsonb

        user_id = ev.fields.get("user_id")
        with self._db.connection() as c:
            c.execute(
                "INSERT INTO audit_log (ts, event, user_id, fields) VALUES (%s, %s, %s, %s)",
                (ev.ts, ev.event, None if user_id is None else str(user_id), Jsonb(ev.fields)),
            )
