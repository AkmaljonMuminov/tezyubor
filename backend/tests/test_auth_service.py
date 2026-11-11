import unittest

from app.errors import (
    PinAlreadySet,
    PinInvalid,
    PinLocked,
    PinNotSet,
    TokenInvalid,
    TokenReuseDetected,
    ValidationError,
)
from app.modules.auth.otp import TEST_CODE
from tests.helpers import make_stack

PHONE = "901234567"


def login(svc):
    cid = svc.request_otp(PHONE)
    return svc.verify_otp(cid, TEST_CODE)


class AuthServiceTests(unittest.TestCase):
    def test_new_user_flow_and_same_user_on_relogin(self):
        svc, _o, tokens, users, _a, clock, _s = make_stack()
        pair, pin_set = login(svc)
        self.assertFalse(pin_set)
        uid = svc.authenticate(pair.access_token)
        clock.advance(61)
        pair2, _ = login(svc)
        self.assertEqual(svc.authenticate(pair2.access_token), uid)

    def test_set_pin_rules(self):
        svc, *_ = make_stack()
        pair, _ = login(svc)
        uid = svc.authenticate(pair.access_token)
        for weak in ["1111", "1234", "12", "abcd"]:
            with self.assertRaises(ValidationError):
                svc.set_pin(uid, weak)
        svc.set_pin(uid, "7391")
        with self.assertRaises(PinAlreadySet):
            svc.set_pin(uid, "2580")

    def test_pin_login_rotates_token(self):
        svc, *_ = make_stack()
        pair, _ = login(svc)
        svc.set_pin(svc.authenticate(pair.access_token), "7391")
        new = svc.login_with_pin(pair.refresh_token, "7391")
        self.assertNotEqual(new.refresh_token, pair.refresh_token)
        # eski refresh token endi ishlatilgan: qayta urinish oilani bekor qiladi
        with self.assertRaises(TokenInvalid):
            svc.login_with_pin(pair.refresh_token, "7391")

    def test_pin_login_without_pin_set(self):
        svc, *_ = make_stack()
        pair, _ = login(svc)
        with self.assertRaises(PinNotSet):
            svc.login_with_pin(pair.refresh_token, "7391")

    def test_wrong_pin_does_not_consume_refresh_token(self):
        svc, *_ = make_stack()
        pair, _ = login(svc)
        svc.set_pin(svc.authenticate(pair.access_token), "7391")
        with self.assertRaises(PinInvalid) as ctx:
            svc.login_with_pin(pair.refresh_token, "7392")
        self.assertEqual(ctx.exception.details["attempts_left"], 4)
        svc.login_with_pin(pair.refresh_token, "7391")  # hali ishlaydi

    def test_pin_lockout_and_unlock(self):
        svc, _o, _t, _u, audit, clock, _s = make_stack()
        pair, _ = login(svc)
        svc.set_pin(svc.authenticate(pair.access_token), "7391")
        for _ in range(4):
            with self.assertRaises(PinInvalid):
                svc.login_with_pin(pair.refresh_token, "0000")
        with self.assertRaises(PinLocked):
            svc.login_with_pin(pair.refresh_token, "0000")
        with self.assertRaises(PinLocked):  # bloklanganda to'g'ri PIN ham o'tmaydi
            svc.login_with_pin(pair.refresh_token, "7391")
        clock.advance(901)
        svc.login_with_pin(pair.refresh_token, "7391")
        self.assertIn("pin_locked", [e.event for e in audit.events])

    def test_refresh_reuse_is_audited(self):
        svc, _o, _t, _u, audit, *_ = make_stack()
        pair, _ = login(svc)
        svc.refresh(pair.refresh_token)
        with self.assertRaises(TokenReuseDetected):
            svc.refresh(pair.refresh_token)
        self.assertIn("refresh_reuse_detected", [e.event for e in audit.events])

    def test_audit_has_no_secrets(self):
        svc, _o, _t, _u, audit, *_ = make_stack()
        pair, _ = login(svc)
        svc.set_pin(svc.authenticate(pair.access_token), "7391")
        with self.assertRaises(PinInvalid):
            svc.login_with_pin(pair.refresh_token, "7392")
        dump = str([vars(e) for e in audit.events])
        for secret in [TEST_CODE, "7391", "7392", pair.refresh_token, pair.access_token, "998" + PHONE]:
            self.assertNotIn(secret, dump)

    def test_failed_otp_is_audited(self):
        svc, _o, _t, _u, audit, *_ = make_stack()
        cid = svc.request_otp(PHONE)
        from app.errors import OtpInvalid

        with self.assertRaises(OtpInvalid):
            svc.verify_otp(cid, "000000")
        self.assertIn("otp_failed", [e.event for e in audit.events])


if __name__ == "__main__":
    unittest.main()
