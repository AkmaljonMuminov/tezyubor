import re
import unittest

from app.errors import OtpRateLimited, SmsDeliveryError
from tests.helpers import RecordingSms, make_stack

PHONE = "901234567"


class FailingSms:
    is_real = True

    def __init__(self, exc=None):
        self.exc = exc or SmsDeliveryError("SMS yuborib bo'lmadi")
        self.calls = 0

    def send(self, phone, text):
        self.calls += 1
        raise self.exc


class FlakySms(RecordingSms):
    """Birinchi chaqiriqda xato, keyin ishlaydi."""

    def __init__(self):
        super().__init__()
        self.fail_next = True

    def send(self, phone, text):
        if self.fail_next:
            self.fail_next = False
            raise SmsDeliveryError("SMS yuborib bo'lmadi")
        super().send(phone, text)


class SmsOtpTests(unittest.TestCase):
    def test_production_sends_template_with_random_code_that_verifies(self):
        sms = RecordingSms()
        _, otp, *_ = make_stack("production", sms=sms, sms_template="Tezyubor: kod {code}. Hech kimga bermang")
        cid = otp.request(PHONE)
        phone, text = sms.sent[0]
        self.assertEqual(phone, "998" + PHONE)
        code = re.search(r"kod (\d{6})\.", text).group(1)
        self.assertNotEqual(code, "123456")
        self.assertEqual(otp.verify(cid, code), "998" + PHONE)

    def test_test_mode_sends_nothing_and_ignores_global_cap(self):
        sms = RecordingSms()
        clock_stack = make_stack("test", sms=sms, sms_daily_cap=1, otp_max_per_hour=100, otp_cooldown=0)
        _, otp, *_ = clock_stack
        for i in range(5):
            otp.request(f"90123456{i}")
        self.assertEqual(sms.sent, [])

    def test_sms_failure_rolls_back_challenge_and_quota(self):
        sms = FlakySms()
        _, otp, _, _, _, _, store = make_stack("production", sms=sms)
        with self.assertRaises(SmsDeliveryError):
            otp.request(PHONE)
        # Limit sarflanmadi: darhol qayta urinsa bo'ladi (cooldown 60 s ga tushmaydi)
        self.assertEqual(store.request_times("998" + PHONE), [])
        self.assertEqual(store.request_times("*global*"), [])
        cid = otp.request(PHONE)
        self.assertEqual(len(sms.sent), 1)
        self.assertTrue(cid)

    def test_failed_challenge_cannot_be_verified(self):
        _, otp, _, _, _, _, store = make_stack("production", sms=FailingSms())
        with self.assertRaises(SmsDeliveryError):
            otp.request(PHONE)
        self.assertEqual(store._challenges, {})

    def test_unexpected_sender_error_becomes_delivery_error_without_leaking(self):
        sms = FailingSms(RuntimeError("password=hunter2 token=ABC"))
        _, otp, *_ = make_stack("production", sms=sms)
        with self.assertRaises(SmsDeliveryError) as ctx:
            otp.request(PHONE)
        self.assertNotIn("hunter2", f"{ctx.exception} {ctx.exception.details}")

    def test_global_daily_cap_blocks_then_expires(self):
        sms = RecordingSms()
        svc, otp, _, _, _, clock, _ = make_stack(
            "production", sms=sms, sms_daily_cap=3, otp_cooldown=0, otp_max_per_hour=100
        )
        for i in range(3):
            otp.request(f"90123450{i}")
        with self.assertRaises(OtpRateLimited) as ctx:
            otp.request("901234599")
        self.assertGreater(ctx.exception.details["retry_after"], 0)
        self.assertEqual(len(sms.sent), 3)  # to'rtinchisi yuborilmadi
        clock.advance(86400 + 1)
        otp.request("901234599")
        self.assertEqual(len(sms.sent), 4)

    def test_auth_service_audits_sms_failure(self):
        svc, _, _, _, audit, *_ = make_stack("production", sms=FailingSms())
        with self.assertRaises(SmsDeliveryError):
            svc.request_otp(PHONE)
        events = [getattr(e, "event", None) or (e.get("event") if isinstance(e, dict) else None) for e in audit.events]
        self.assertIn("otp_sms_failed", events)


if __name__ == "__main__":
    unittest.main()
