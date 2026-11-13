import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from app.config import Settings
from app.envfile import load_env_file, parse_env_file
from app.errors import ConfigError, OtpRateLimited, SmsDeliveryError
from app.tools import sms_check
from tests.helpers import RecordingSms, make_stack

# Foydalanuvchining haqiqiy .env shabloni (maxfiy qiymatlar bo'sh) — apostrof, '!' va bo'sh joylar bilan.
USER_ENV = """\
# Production sozlamalari
APP_ENV=production

# Xavfsizlik kalitlari
JWT_SECRET=
OTP_SECRET=

# SMS provayder
SMS_PROVIDER=eskiz

# Eskiz akkaunti
ESKIZ_EMAIL=owner@example.com
ESKIZ_PASSWORD=

# SMS jo'natuvchi
ESKIZ_FROM=4546

# SMS matni
SMS_TEMPLATE=Tezyubor tasdiqlash kodi: {code}. Ushbu kodni hech kimga bermang! Uni firibgarlar so'rashi mumkin.

# Kunlik SMS limiti
SMS_DAILY_CAP=9

# 8 soat ichida SMS limiti
SMS_8HOUR_CAP=3
"""
TEMPLATE = "Tezyubor tasdiqlash kodi: {code}. Ushbu kodni hech kimga bermang! Uni firibgarlar so'rashi mumkin."
H = 3600


class EnvFileTests(unittest.TestCase):
    def test_parses_template_with_spaces_apostrophe_and_bang(self):
        env = parse_env_file(USER_ENV)
        self.assertEqual(env["SMS_TEMPLATE"], TEMPLATE)
        self.assertEqual(env["SMS_DAILY_CAP"], "9")
        self.assertEqual(env["SMS_8HOUR_CAP"], "3")
        self.assertEqual(env["JWT_SECRET"], "")
        self.assertEqual(env["ESKIZ_FROM"], "4546")

    def test_quotes_export_and_comments(self):
        env = parse_env_file('export A="x y"\nB=\'q\'\n# C=1\n  D = z \nbad line\n')
        self.assertEqual(env, {"A": "x y", "B": "q", "D": "z"})

    def test_value_may_contain_equals_and_hash(self):
        self.assertEqual(parse_env_file("T=a=b #c")["T"], "a=b #c")

    def test_real_environment_wins_over_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8") as f:
            f.write("X=file\nY=file\n")
        try:
            environ = {"X": "real"}
            load_env_file(f.name, environ)
            self.assertEqual(environ, {"X": "real", "Y": "file"})
        finally:
            os.unlink(f.name)

    def test_user_env_builds_valid_settings(self):
        env = parse_env_file(USER_ENV)
        env.update(JWT_SECRET="a" * 40, OTP_SECRET="b" * 40, ESKIZ_PASSWORD="pw")
        s = Settings.from_env(env)
        self.assertEqual((s.sms_daily_cap, s.sms_8hour_cap), (9, 3))
        self.assertEqual(s.sms_template, TEMPLATE)
        self.assertFalse(s.test_mode)
        # Kod bilan bitta SMS (160 belgi) ichiga sig'adi: ortiqcha pul ketmaydi.
        self.assertLessEqual(len(s.sms_template.replace("{code}", "123456")), 160)

    def test_invalid_8hour_cap(self):
        base = {"JWT_SECRET": "a" * 40, "OTP_SECRET": "b" * 40}
        for v in ("-1", "x"):
            with self.subTest(v=v), self.assertRaises(ConfigError):
                Settings.from_env({**base, "SMS_8HOUR_CAP": v})
        self.assertEqual(Settings.from_env(base).sms_8hour_cap, 0)  # standart: o'chirilgan


class EightHourCapTests(unittest.TestCase):
    def stack(self, **kw):
        sms = RecordingSms()
        kw = {"sms_daily_cap": 9, "sms_8hour_cap": 3, "otp_cooldown": 0, "otp_max_per_hour": 100, **kw}
        _, otp, _, _, _, clock, _ = make_stack("production", sms=sms, **kw)
        return sms, otp, clock

    def test_blocks_fourth_within_8h_with_correct_retry_after(self):
        sms, otp, clock = self.stack()
        for i in range(3):
            otp.request(f"90123450{i}")
        with self.assertRaises(OtpRateLimited) as ctx:
            otp.request("901234599")
        self.assertEqual(len(sms.sent), 3)
        self.assertTrue(8 * H <= ctx.exception.details["retry_after"] <= 8 * H + 2)
        clock.advance(8 * H + 1)
        otp.request("901234599")
        self.assertEqual(len(sms.sent), 4)

    def test_daily_cap_applies_even_when_8h_window_is_free(self):
        # Sutkalik limit 4, 8 soatlik 3: ikkinchi oyna bo'sh bo'lsa ham sutkalik limit to'xtatadi.
        sms, otp, clock = self.stack(sms_daily_cap=4)
        for i in range(3):
            otp.request(f"90123450{i}")
        clock.advance(8 * H + 1)  # 8 soatlik oyna bo'shadi
        otp.request("901234510")  # 4-chisi (sutkada)
        with self.assertRaises(OtpRateLimited) as ctx:
            otp.request("901234599")
        self.assertEqual(len(sms.sent), 4)
        # Birinchi SMS dan 24 soat o'tishi kerak: ~16 soat qolgan
        self.assertTrue(15 * H <= ctx.exception.details["retry_after"] <= 16 * H + 2)
        clock.advance(16 * H + 1)
        otp.request("901234599")
        self.assertEqual(len(sms.sent), 5)

    def test_8h_cap_alone_already_implies_9_per_day(self):
        # 9 / 3 sozlamasida sutkalik limit 8 soatlik limitni takrorlaydi (3 oyna * 3 SMS)
        sms, otp, clock = self.stack()
        n = 0
        for batch in range(3):
            for _ in range(3):
                otp.request(f"9012345{n:02d}")
                n += 1
            if batch < 2:
                clock.advance(8 * H + 1)
        self.assertEqual(len(sms.sent), 9)
        with self.assertRaises(OtpRateLimited):
            otp.request("901239999")

    def test_disabled_when_zero(self):
        sms, otp, _ = self.stack(sms_8hour_cap=0, sms_daily_cap=50)
        for i in range(10):
            otp.request(f"9012340{i:02d}")
        self.assertEqual(len(sms.sent), 10)

    def test_failed_send_frees_the_window(self):
        class Flaky(RecordingSms):
            fail = True

            def send(self, phone, text):
                if Flaky.fail:
                    Flaky.fail = False
                    raise SmsDeliveryError("x")
                super().send(phone, text)

        sms = Flaky()
        _, otp, *_ = make_stack(
            "production", sms=sms, sms_daily_cap=9, sms_8hour_cap=1, otp_cooldown=0, otp_max_per_hour=100
        )
        with self.assertRaises(SmsDeliveryError):
            otp.request("901234501")
        otp.request("901234502")  # yuborilmagan SMS oynani band qilmagan
        self.assertEqual(len(sms.sent), 1)


class SmsCheckToolTests(unittest.TestCase):
    def run_tool(self, argv, env_text=None, sender=None):
        path = None
        if env_text is not None:
            with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8") as f:
                f.write(env_text)
            path = f.name
            argv = [*argv, "--env-file", path]
        out = io.StringIO()
        try:
            with mock.patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(out):
                if sender is not None:
                    with mock.patch.object(sms_check, "build_sms_sender", return_value=sender):
                        code = sms_check.main(["sms_check", *argv])
                else:
                    code = sms_check.main(["sms_check", *argv])
        finally:
            if path:
                os.unlink(path)
        return code, out.getvalue()

    FULL = USER_ENV.replace("JWT_SECRET=\n", "JWT_SECRET=" + "a" * 40 + "\n").replace(
        "OTP_SECRET=\n", "OTP_SECRET=" + "b" * 40 + "\n"
    ).replace("ESKIZ_PASSWORD=\n", "ESKIZ_PASSWORD=topsecret\n")

    def test_sends_rendered_template_to_normalized_phone(self):
        sms = RecordingSms()
        code, out = self.run_tool(["90 123 45 67"], self.FULL, sms)
        self.assertEqual(code, 0)
        (phone, text), = sms.sent
        self.assertEqual(phone, "998901234567")
        self.assertRegex(text, r"^Tezyubor tasdiqlash kodi: \d{6}\. Ushbu kodni hech kimga bermang!")
        self.assertNotIn(text.split(": ")[1][:6], out)  # kod ekranga chiqmaydi
        self.assertNotIn("topsecret", out)

    def test_delivery_failure_exit_code_and_no_secrets(self):
        class Fail:
            def send(self, phone, text):
                raise SmsDeliveryError("SMS yuborib bo'lmadi")

        code, out = self.run_tool(["901234567"], self.FULL, Fail())
        self.assertEqual(code, 1)
        self.assertNotIn("topsecret", out)

    def test_config_errors_are_reported_not_crashed(self):
        code, out = self.run_tool(["901234567"], USER_ENV)  # JWT/OTP/parol bo'sh
        self.assertEqual(code, 2)
        self.assertIn("Sozlama xatosi", out)
        code, _ = self.run_tool(["123"], self.FULL)
        self.assertEqual(code, 2)
        code, _ = self.run_tool(["901234567", "--env-file", "/yo'q/fayl.env"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
