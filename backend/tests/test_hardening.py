"""Auth qotirish: sessiyalar, serverda logout, atomik PIN hisoblagich + eskalatsiya, pepper, OTP bir martalik, audit chegarasi."""
import threading
import unittest

from app.errors import (
    OtpInvalid,
    PinAlreadySet,
    PinInvalid,
    PinLocked,
    SessionNotFound,
    TokenInvalid,
)
from app.modules.auth.audit import AuditLog
from app.modules.auth.security import hash_pin, needs_rehash, verify_pin
from app.modules.auth.stores import lock_duration
from tests.helpers import make_stack

PHONE = "901234567"
PEPPER = "p" * 40


def login(svc, otp_store=None, label=""):
    cid = svc.request_otp(PHONE)
    pair, _ = svc.verify_otp(cid, "123456", label)
    return pair


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.svc, self.otp, self.tokens, self.users, self.audit, self.clock, _ = make_stack(otp_cooldown=0)

    def test_logout_revokes_refresh_and_access(self):
        pair = login(self.svc)
        self.svc.logout(pair.refresh_token)
        with self.assertRaises(TokenInvalid):
            self.svc.refresh(pair.refresh_token)
        with self.assertRaises(TokenInvalid):
            self.svc.authenticate(pair.access_token)  # muddati tugamagan bo'lsa ham o'tmaydi
        self.assertEqual(self.audit.events[-1].event, "logout")

    def test_logout_with_unknown_token_is_silent(self):
        self.svc.logout("yo'q-token")  # xato bermaydi, tokenni taxmin qilishga imkon yo'q
        self.svc.logout("")

    def test_logout_with_already_used_token_still_closes_session(self):
        pair = login(self.svc)
        new = self.svc.refresh(pair.refresh_token)
        self.svc.logout(pair.refresh_token)  # eski token
        with self.assertRaises(TokenInvalid):
            self.svc.authenticate(new.access_token)

    def test_rotation_keeps_same_session(self):
        pair = login(self.svc, label="Pixel 7")
        new = self.svc.refresh(pair.refresh_token)
        rows = self.svc.list_sessions(new.access_token)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0][1])
        self.assertEqual(rows[0][0].device_label, "Pixel 7")

    def test_two_devices_listed_and_current_marked(self):
        a = login(self.svc, label="Telefon")
        b = login(self.svc, label="Planshet")
        rows = self.svc.list_sessions(a.access_token)
        self.assertEqual({r.device_label for r, _ in rows}, {"Telefon", "Planshet"})
        self.assertEqual([r.device_label for r, cur in rows if cur], ["Telefon"])
        self.assertEqual(len(self.svc.list_sessions(b.access_token)), 2)

    def test_revoke_other_session_only(self):
        a = login(self.svc, label="A")
        b = login(self.svc, label="B")
        other = next(r for r, cur in self.svc.list_sessions(a.access_token) if not cur)
        self.svc.revoke_session(a.access_token, other.id)
        with self.assertRaises(TokenInvalid):
            self.svc.authenticate(b.access_token)
        with self.assertRaises(TokenInvalid):
            self.svc.refresh(b.refresh_token)
        self.assertEqual(self.svc.authenticate(a.access_token), self.users.get_by_phone("998901234567").id)

    def test_cannot_revoke_foreign_or_missing_session(self):
        a = login(self.svc)
        with self.assertRaises(SessionNotFound):
            self.svc.revoke_session(a.access_token, "yo'q")
        # Boshqa foydalanuvchining sessiyasi
        cid = self.svc.request_otp("907654321")
        b, _ = self.svc.verify_otp(cid, "123456")
        b_sid = self.svc.list_sessions(b.access_token)[0][0].id
        with self.assertRaises(SessionNotFound):
            self.svc.revoke_session(a.access_token, b_sid)
        self.assertEqual(len(self.svc.list_sessions(b.access_token)), 1)  # begonaniki saqlandi

    def test_reuse_detection_closes_session(self):
        pair = login(self.svc)
        new = self.svc.refresh(pair.refresh_token)
        with self.assertRaises(Exception):
            self.svc.refresh(pair.refresh_token)  # qayta ishlatish
        with self.assertRaises(TokenInvalid):
            self.svc.authenticate(new.access_token)
        self.assertEqual(self.tokens.list_sessions(self.users.get_by_phone("998901234567").id), [])

    def test_access_without_sid_is_rejected(self):
        import jwt

        old = jwt.encode(
            {"sub": "u1", "iat": 1_000_000, "exp": 2_000_000, "typ": "access"}, "a" * 40, "HS256"
        )
        with self.assertRaises(TokenInvalid):
            self.tokens.verify_access(old)

    def test_device_label_is_sanitized(self):
        pair = login(self.svc, label="Pixel\n7\x00" + "x" * 200)
        label = self.svc.list_sessions(pair.access_token)[0][0].device_label
        self.assertNotIn("\n", label)
        self.assertNotIn("\x00", label)
        self.assertLessEqual(len(label), 60)


class PinHardeningTests(unittest.TestCase):
    def setUp(self):
        self.svc, self.otp, self.tokens, self.users, self.audit, self.clock, _ = make_stack(otp_cooldown=0)
        self.pair = login(self.svc)
        self.uid = self.svc.authenticate(self.pair.access_token)
        self.svc.set_pin(self.uid, "2580")

    def fail(self, n):
        last = None
        for _ in range(n):
            try:
                self.svc.check_pin(self.uid, "1357")
            except (PinInvalid, PinLocked) as e:
                last = e
        return last

    def test_lock_durations_escalate_and_are_capped(self):
        self.assertEqual([lock_duration(i, 900, 86400) for i in range(8)], [900, 1800, 3600, 7200, 14400, 28800, 57600, 86400])
        self.assertEqual(lock_duration(50, 900, 86400), 86400)

    def test_second_lock_is_twice_as_long_and_success_resets(self):
        e = self.fail(5)
        self.assertIsInstance(e, PinLocked)
        self.assertEqual(e.details["retry_after"], 900)
        self.clock.advance(901)
        e = self.fail(5)
        self.assertEqual(e.details["retry_after"], 1800)
        self.clock.advance(1801)
        self.svc.check_pin(self.uid, "2580")  # to'g'ri PIN darajani nolga qaytaradi
        e = self.fail(5)
        self.assertEqual(e.details["retry_after"], 900)

    def test_correct_pin_while_locked_is_rejected_without_verifying(self):
        self.fail(5)
        with self.assertRaises(PinLocked):
            self.svc.check_pin(self.uid, "2580")

    def test_fifth_attempt_correct_does_not_leave_lock(self):
        self.fail(4)
        self.svc.check_pin(self.uid, "2580")
        self.svc.check_pin(self.uid, "2580")  # bloklanmagan

    def test_parallel_guesses_cannot_exceed_limit(self):
        """30 ta parallel noto'g'ri urinishdan faqat 5 tasi tekshirilishi mumkin (qolgani blokga uriladi)."""
        results = []
        lock = threading.Lock()

        def worker():
            try:
                self.svc.check_pin(self.uid, "1357")
                r = "ok"
            except PinInvalid:
                r = "invalid"
            except PinLocked:
                r = "locked"
            with lock:
                results.append(r)

        ts = [threading.Thread(target=worker) for _ in range(30)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(results.count("ok"), 0)
        self.assertLessEqual(results.count("invalid"), 4)  # 5-urinish PinLocked bo'lib qaytadi
        self.assertGreaterEqual(results.count("locked"), 26)

    def test_pin_set_only_once_atomically(self):
        with self.assertRaises(PinAlreadySet):
            self.svc.set_pin(self.uid, "1470")

    def test_pin_never_in_audit(self):
        self.fail(5)
        blob = repr([(e.event, e.fields) for e in self.audit.events])
        for secret in ("1357", "2580"):
            self.assertNotIn(secret, blob)


class PepperTests(unittest.TestCase):
    def test_pepper_hash_roundtrip_and_scheme(self):
        h = hash_pin("2580", PEPPER)
        self.assertTrue(h.startswith("scrypt2$"))
        self.assertTrue(verify_pin("2580", h, PEPPER))
        self.assertFalse(verify_pin("2581", h, PEPPER))
        self.assertFalse(verify_pin("2580", h, "q" * 40))  # boshqa pepper
        self.assertFalse(verify_pin("2580", h, ""))        # pepper yo'q — rad

    def test_legacy_hash_still_verifies_and_is_upgraded(self):
        legacy = hash_pin("2580")
        self.assertTrue(legacy.startswith("scrypt$"))
        self.assertTrue(verify_pin("2580", legacy, PEPPER))
        self.assertTrue(needs_rehash(legacy, PEPPER))
        self.assertFalse(needs_rehash(legacy, ""))
        self.assertFalse(needs_rehash(hash_pin("2580", PEPPER), PEPPER))

    def test_service_upgrades_legacy_hash_on_login(self):
        svc, _o, _t, users, _a, _c, _s = make_stack(otp_cooldown=0, pin_pepper=PEPPER)
        pair = login(svc)
        uid = svc.authenticate(pair.access_token)
        users.set_pin_hash(uid, hash_pin("2580"))  # eski sxemada yozuv
        svc.check_pin(uid, "2580")
        self.assertTrue(users.get(uid).pin_hash.startswith("scrypt2$"))
        svc.check_pin(uid, "2580")  # yangi xesh bilan ham ishlaydi

    def test_short_pepper_rejected_by_config(self):
        from app.errors import ConfigError

        with self.assertRaises(ConfigError):
            make_stack(pin_pepper="short")[0]._s.validate()


class OtpOneTimeTests(unittest.TestCase):
    def test_code_cannot_be_used_twice_even_in_parallel(self):
        svc, otp, _t, _u, _a, _c, store = make_stack(otp_cooldown=0)
        cid = svc.request_otp(PHONE)
        out = []
        lock = threading.Lock()

        def worker():
            try:
                otp.verify(cid, "123456")
                r = "ok"
            except OtpInvalid:
                r = "invalid"
            with lock:
                out.append(r)

        ts = [threading.Thread(target=worker) for _ in range(10)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(out.count("ok"), 1)

    def test_attempts_counted_atomically(self):
        _svc, otp, *_rest = make_stack(otp_cooldown=0)
        cid = otp.request(PHONE)
        self.assertEqual(_rest[-1].bump_attempts(cid), 1)
        self.assertIsNone(_rest[-1].bump_attempts("yo'q"))


class AuditBoundTests(unittest.TestCase):
    def test_memory_is_bounded_and_sink_failure_is_swallowed(self):
        calls = []

        class Boom:
            def write(self, ev):
                calls.append(ev.event)
                raise RuntimeError("db o'chiq")

        log = AuditLog(sink=Boom(), max_memory=3)
        with self.assertLogs("tezyubor.audit", level="ERROR"):
            for i in range(10):
                log.record(f"e{i}")  # sink xatosi so'rovni buzmaydi
        self.assertEqual([e.event for e in log.events], ["e7", "e8", "e9"])
        self.assertEqual(len(calls), 10)


if __name__ == "__main__":
    unittest.main()
