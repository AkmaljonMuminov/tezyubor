import unittest

from app.errors import (
    OtpExpired,
    OtpInvalid,
    OtpLocked,
    OtpRateLimited,
    ValidationError,
)
from app.modules.auth.otp import TEST_CODE
from tests.helpers import RecordingSms, make_stack

PHONE = "901234567"


class OtpTests(unittest.TestCase):
    def test_success_returns_phone_and_is_single_use(self):
        _, otp, *_ = make_stack()
        cid = otp.request(PHONE)
        self.assertEqual(otp.verify(cid, TEST_CODE), "998" + PHONE)
        with self.assertRaises(OtpInvalid):
            otp.verify(cid, TEST_CODE)

    def test_invalid_phone(self):
        _, otp, *_ = make_stack()
        with self.assertRaises(ValidationError):
            otp.request("123")

    def test_wrong_code_counts_attempts_then_locks(self):
        _, otp, *_ = make_stack()
        cid = otp.request(PHONE)
        for left in (4, 3, 2, 1):
            with self.assertRaises(OtpInvalid) as ctx:
                otp.verify(cid, "000000")
            self.assertEqual(ctx.exception.details["attempts_left"], left)
        with self.assertRaises(OtpLocked):
            otp.verify(cid, "000000")
        # bloklangach to'g'ri kod ham ishlamaydi
        with self.assertRaises(OtpInvalid):
            otp.verify(cid, TEST_CODE)

    def test_non_numeric_code_is_rejected(self):
        # Har bir noto'g'ri format alohida urinish hisoblanadi (limit 5), shuning uchun 4 tadan.
        for group in (["", "abc", "12345", "1234567"], [None]):
            _, otp, *_ = make_stack()
            cid = otp.request(PHONE)
            for bad in group:
                with self.assertRaises(OtpInvalid):
                    otp.verify(cid, bad)

    def test_expiry(self):
        _, otp, _t, _u, _a, clock, _s = make_stack()
        cid = otp.request(PHONE)
        clock.advance(121)
        with self.assertRaises(OtpExpired):
            otp.verify(cid, TEST_CODE)

    def test_cooldown_between_requests(self):
        _, otp, _t, _u, _a, clock, _s = make_stack()
        otp.request(PHONE)
        with self.assertRaises(OtpRateLimited) as ctx:
            otp.request(PHONE)
        self.assertGreater(ctx.exception.details["retry_after"], 0)
        clock.advance(61)
        otp.request(PHONE)

    def test_hourly_limit(self):
        _, otp, _t, _u, _a, clock, _s = make_stack()
        for _ in range(5):
            otp.request(PHONE)
            clock.advance(61)
        with self.assertRaises(OtpRateLimited):
            otp.request(PHONE)
        clock.advance(3600)
        otp.request(PHONE)

    def test_limits_are_per_phone(self):
        _, otp, *_ = make_stack()
        otp.request("901234567")
        otp.request("931234567")

    def test_code_not_stored_in_plaintext(self):
        _, otp, *rest = make_stack()
        store = rest[-1]
        cid = otp.request(PHONE)
        self.assertNotIn(TEST_CODE, store.get(cid).code_hash)

    def test_production_sends_random_code_via_sms_and_never_test_code(self):
        sms = RecordingSms()
        _, otp, *_ = make_stack(env="production", sms=sms)
        cid = otp.request(PHONE)
        self.assertEqual(len(sms.sent), 1)
        code = sms.sent[0][1].split()[-1]
        self.assertRegex(code, r"^[0-9]{6}$")
        if code != TEST_CODE:  # 1/10^6 ehtimol bilan teng bo'lishi mumkin
            with self.assertRaises(OtpInvalid):
                otp.verify(cid, TEST_CODE)
        self.assertEqual(otp.verify(cid, code), "998" + PHONE)

    def test_test_mode_sends_no_sms(self):
        sms = RecordingSms()
        _, otp, *_ = make_stack(env="test", sms=sms)
        otp.request(PHONE)
        self.assertEqual(sms.sent, [])


if __name__ == "__main__":
    unittest.main()
