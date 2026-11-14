"""PostgreSQL saqlash testlari. TEST_DATABASE_URL (bo'sh baza) va psycopg bo'lmasa o'tkazib yuboriladi
(CI'da postgres xizmati bilan ishlaydi). Xotiradagi store'lar bilan BIR XIL shartnoma tekshiriladi."""
import os
import unittest

try:
    import psycopg  # noqa: F401
    import psycopg_pool  # noqa: F401
    from fastapi.testclient import TestClient

    from app.db import Database
    from app.main import create_app
    from app.modules.auth.pg_stores import PgAuditSink, PgOtpStore, PgRefreshStore, PgSessionStore, PgUserStore

    HAVE = True
except ImportError:  # pragma: no cover
    HAVE = False

from app.modules.auth.audit import AuditEvent
from app.modules.auth.stores import (
    MemoryOtpStore,
    MemoryRefreshStore,
    MemorySessionStore,
    MemoryUserStore,
    RefreshRecord,
    SessionRecord,
)
from tests.helpers import make_settings

URL = os.environ.get("TEST_DATABASE_URL", "")
PHONE = "998901234567"


class StoreContract:
    """Xotira va PostgreSQL uchun umumiy xulq-atvor."""

    def make(self):  # -> (users, refresh, otp, sessions)
        raise NotImplementedError

    def setUp(self):
        self.users, self.refresh, self.otp, self.sessions = self.make()

    def test_user_create_get_and_phone_lookup(self):
        u = self.users.create(PHONE)
        self.assertEqual(self.users.get(u.id).phone, PHONE)
        self.assertEqual(self.users.get_by_phone(PHONE).id, u.id)
        self.assertIsNone(self.users.get("not-a-uuid"))
        self.assertIsNone(self.users.get_by_phone("998000000000"))

    def test_create_twice_keeps_one_user(self):
        a = self.users.create(PHONE)
        b = self.users.create(PHONE)
        self.assertEqual(a.id, b.id)

    def test_user_save_persists_pin_state(self):
        u = self.users.create(PHONE)
        u.pin_hash, u.pin_failures, u.pin_locked_until = "hash", 3, 12345.5
        self.users.save(u)
        again = self.users.get(u.id)
        self.assertEqual((again.pin_hash, again.pin_failures, again.pin_locked_until), ("hash", 3, 12345.5))

    def test_refresh_put_get_mark_used_is_atomic(self):
        u = self.users.create(PHONE)
        self.refresh.put("h1", RefreshRecord(u.id, "fam", 999.0))
        rec = self.refresh.get("h1")
        self.assertEqual((rec.user_id, rec.family_id, rec.expires_at, rec.used), (u.id, "fam", 999.0, False))
        self.assertTrue(self.refresh.mark_used("h1"))
        self.assertFalse(self.refresh.mark_used("h1"))  # ikkinchi marta — rad
        self.assertTrue(self.refresh.get("h1").used)
        self.assertFalse(self.refresh.mark_used("yo'q"))

    def test_revoke_family_and_purge(self):
        u = self.users.create(PHONE)
        self.refresh.put("a", RefreshRecord(u.id, "fam", 10_000_000.0))
        self.refresh.put("b", RefreshRecord(u.id, "fam", 10_000_000.0))
        self.refresh.put("c", RefreshRecord(u.id, "other", 100.0))
        self.refresh.revoke_family("fam")
        self.assertIsNone(self.refresh.get("a"))
        self.assertIsNone(self.refresh.get("b"))
        self.assertIsNotNone(self.refresh.get("c"))
        self.refresh.purge_expired(100.0 + 86400 + 1)
        self.assertIsNone(self.refresh.get("c"))

    def test_sms_requests_add_list_discard(self):
        self.otp.add_request(PHONE, 100.0)
        self.otp.add_request(PHONE, 200.0)
        self.otp.add_request("*global*", 100.0)
        self.assertEqual(sorted(self.otp.request_times(PHONE)), [100.0, 200.0])
        self.otp.discard_request(PHONE, 100.0)
        self.assertEqual(self.otp.request_times(PHONE), [200.0])
        self.assertEqual(self.otp.request_times("*global*"), [100.0])
        self.otp.discard_request(PHONE, 999.0)  # yo'q yozuv xato bermaydi

    def test_old_sms_requests_are_pruned(self):
        self.otp.add_request(PHONE, 100.0)
        self.otp.add_request(PHONE, 100.0 + 3 * 86400)
        self.assertEqual(self.otp.request_times(PHONE), [100.0 + 3 * 86400])

    def test_challenge_roundtrip(self):
        from app.modules.auth.stores import OtpChallenge

        self.otp.put("c1", OtpChallenge(PHONE, "h", 50.0))
        self.assertEqual(self.otp.get("c1").phone, PHONE)
        self.otp.delete("c1")
        self.assertIsNone(self.otp.get("c1"))

    def test_challenge_attempts_and_one_time_consume(self):
        from app.modules.auth.stores import OtpChallenge

        self.otp.put("c2", OtpChallenge(PHONE, "h", 50.0))
        self.assertEqual(self.otp.bump_attempts("c2"), 1)
        self.assertEqual(self.otp.bump_attempts("c2"), 2)
        self.assertEqual(self.otp.get("c2").attempts, 2)
        self.assertIsNone(self.otp.bump_attempts("yo'q"))
        self.assertTrue(self.otp.consume("c2"))
        self.assertFalse(self.otp.consume("c2"))  # bir martalik
        self.assertIsNone(self.otp.get("c2"))

    def test_pin_attempt_counts_before_verify_and_escalates(self):
        u = self.users.create(PHONE)
        a = self.users.begin_pin_attempt(u.id, 1000.0, 3, 100, 1000)
        self.assertEqual((a.allowed, a.attempts_left, a.locked_now), (True, 2, False))
        self.users.begin_pin_attempt(u.id, 1000.0, 3, 100, 1000)
        a = self.users.begin_pin_attempt(u.id, 1000.0, 3, 100, 1000)
        self.assertEqual((a.allowed, a.locked_now, a.retry_after), (True, True, 100))
        a = self.users.begin_pin_attempt(u.id, 1050.0, 3, 100, 1000)
        self.assertEqual((a.allowed, a.retry_after), (False, 51))
        # blok tugagach: yangi sikl, ikkinchi blok 200 soniya
        for _ in range(2):
            self.users.begin_pin_attempt(u.id, 1101.0, 3, 100, 1000)
        a = self.users.begin_pin_attempt(u.id, 1101.0, 3, 100, 1000)
        self.assertEqual((a.locked_now, a.retry_after), (True, 200))
        self.users.reset_pin_state(u.id)
        again = self.users.get(u.id)
        self.assertEqual((again.pin_failures, again.pin_lock_level, again.pin_locked_until), (0, 0, 0.0))

    def test_set_pin_hash_only_if_unset(self):
        u = self.users.create(PHONE)
        self.assertTrue(self.users.set_pin_hash(u.id, "h1", only_if_unset=True))
        self.assertFalse(self.users.set_pin_hash(u.id, "h2", only_if_unset=True))
        self.assertEqual(self.users.get(u.id).pin_hash, "h1")
        self.assertTrue(self.users.set_pin_hash(u.id, "h3"))  # qayta xeshlash
        self.assertEqual(self.users.get(u.id).pin_hash, "h3")

    def test_sessions_lifecycle_and_ownership(self):
        a = self.users.create(PHONE)
        b = self.users.create("998907654321")
        self.sessions.create(SessionRecord("s1", a.id, "Telefon", 10.0, 10.0))
        self.sessions.create(SessionRecord("s2", a.id, "Planshet", 20.0, 20.0))
        self.sessions.create(SessionRecord("s3", b.id, "Boshqa", 30.0, 30.0))
        self.assertTrue(self.sessions.is_active("s1"))
        self.assertFalse(self.sessions.is_active("yo'q"))
        self.sessions.touch("s1", 99.0)
        self.assertEqual([r.id for r in self.sessions.list_active(a.id)], ["s1", "s2"])  # oxirgi ishlatilgani birinchi
        self.assertFalse(self.sessions.revoke("s3", a.id))  # begonaniki
        self.assertTrue(self.sessions.is_active("s3"))
        self.assertTrue(self.sessions.revoke("s1", a.id))
        self.assertFalse(self.sessions.revoke("s1", a.id))  # ikkinchi marta
        self.assertFalse(self.sessions.is_active("s1"))
        self.sessions.touch("s1", 123.0)  # bekor qilingan sessiya jonlanmaydi
        self.assertEqual([r.id for r in self.sessions.list_active(a.id)], ["s2"])


class MemoryContract(StoreContract, unittest.TestCase):
    def make(self):
        return MemoryUserStore(), MemoryRefreshStore(), MemoryOtpStore(), MemorySessionStore()


@unittest.skipUnless(URL and HAVE, "TEST_DATABASE_URL va psycopg kerak")
class PostgresContract(StoreContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database(URL)
        cls.db.migrate()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def make(self):
        with self.db.connection() as c:
            c.execute("TRUNCATE users, refresh_tokens, sms_requests, otp_challenges, audit_log RESTART IDENTITY CASCADE")
        return PgUserStore(self.db), PgRefreshStore(self.db), PgOtpStore(self.db), PgSessionStore(self.db)

    def test_migrate_is_idempotent_and_versioned(self):
        self.db.migrate()
        self.db.migrate()
        with self.db.connection() as c:
            rows = c.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        self.assertEqual([r["version"] for r in rows], [1, 2])

    def test_audit_sink_appends_json_without_pii(self):
        sink = PgAuditSink(self.db)
        sink.write(AuditEvent(5.0, "pin_failed", {"user_id": "abc", "attempts_left": 2}))
        sink.write(AuditEvent(6.0, "otp_requested", {}))
        with self.db.connection() as c:
            rows = c.execute("SELECT ts, event, user_id, fields FROM audit_log ORDER BY id").fetchall()
        self.assertEqual([r["event"] for r in rows], ["pin_failed", "otp_requested"])
        self.assertEqual(rows[0]["user_id"], "abc")
        self.assertEqual(rows[0]["fields"]["attempts_left"], 2)
        self.assertIsNone(rows[1]["user_id"])

    def test_legacy_refresh_family_gets_session_on_migrate(self):
        """Migratsiyadan oldin chiqarilgan refresh oilasi sessiyasiz qolib, foydalanuvchini tashqariga chiqarib yubormasin."""
        u = self.users.create(PHONE)
        self.refresh.put("legacy", RefreshRecord(u.id, "oldfam", 9e12))
        with self.db.connection() as c:
            c.execute("DELETE FROM schema_migrations")
            c.execute("DELETE FROM auth_sessions")
        self.db.migrate()
        self.assertTrue(self.sessions.is_active("oldfam"))


@unittest.skipUnless(URL and HAVE, "TEST_DATABASE_URL va psycopg kerak")
class SurvivesRestart(unittest.TestCase):
    """Asosiy maqsad: server qayta ishga tushsa foydalanuvchi, PIN va sessiya saqlanadi."""

    def setUp(self):
        db = Database(URL)
        db.migrate()
        with db.connection() as c:
            c.execute("TRUNCATE users, refresh_tokens, sms_requests, otp_challenges, audit_log RESTART IDENTITY CASCADE")
        db.close()
        self.apps = []

    def tearDown(self):
        for app in self.apps:
            app.state.db.close()

    def boot(self):
        app = create_app(make_settings("test", database_url=URL, otp_cooldown=0, otp_max_per_hour=100))
        self.apps.append(app)
        return TestClient(app)

    def test_pin_login_works_after_restart(self):
        c1 = self.boot()
        cid = c1.post("/v1/auth/otp/request", json={"phone": "901234567"}).json()["challenge_id"]
        t = c1.post("/v1/auth/otp/verify", json={"challenge_id": cid, "code": "123456"}).json()
        r = c1.post("/v1/auth/pin/set", json={"pin": "2580"}, headers={"Authorization": f"Bearer {t['access_token']}"})
        self.assertEqual(r.status_code, 204)

        c2 = self.boot()  # "restart": yangi ilova nusxasi, bir xil baza
        r = c2.post("/v1/auth/pin/login", json={"refresh_token": t["refresh_token"], "pin": "2580"})
        self.assertEqual(r.status_code, 200, r.text)
        # Xuddi shu telefon — xuddi shu foydalanuvchi, PIN o'rnatilgan
        cid = c2.post("/v1/auth/otp/request", json={"phone": "901234567"}).json()["challenge_id"]
        again = c2.post("/v1/auth/otp/verify", json={"challenge_id": cid, "code": "123456"}).json()
        self.assertTrue(again["pin_set"])

    def test_refresh_reuse_detected_across_restart(self):
        c1 = self.boot()
        cid = c1.post("/v1/auth/otp/request", json={"phone": "901234567"}).json()["challenge_id"]
        t = c1.post("/v1/auth/otp/verify", json={"challenge_id": cid, "code": "123456"}).json()
        self.assertEqual(c1.post("/v1/auth/token/refresh", json={"refresh_token": t["refresh_token"]}).status_code, 200)
        c2 = self.boot()
        r = c2.post("/v1/auth/token/refresh", json={"refresh_token": t["refresh_token"]})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["error"]["code"], "TOKEN_REUSE_DETECTED")

    def test_pin_lock_persists_across_restart(self):
        c1 = self.boot()
        cid = c1.post("/v1/auth/otp/request", json={"phone": "901234567"}).json()["challenge_id"]
        t = c1.post("/v1/auth/otp/verify", json={"challenge_id": cid, "code": "123456"}).json()
        c1.post("/v1/auth/pin/set", json={"pin": "2580"}, headers={"Authorization": f"Bearer {t['access_token']}"})
        for _ in range(5):
            c1.post("/v1/auth/pin/login", json={"refresh_token": t["refresh_token"], "pin": "1357"})
        c2 = self.boot()
        r = c2.post("/v1/auth/pin/login", json={"refresh_token": t["refresh_token"], "pin": "2580"})
        self.assertEqual(r.status_code, 423)  # restart bilan PIN blokini aylanib o'tib bo'lmaydi


if __name__ == "__main__":
    unittest.main()
