import json
import unittest
import urllib.parse

from app.config import Settings
from app.errors import ConfigError, SmsDeliveryError
from app.modules.auth.eskiz import BASE_URL, EskizSmsSender
from app.modules.auth.otp import NullSmsSender
from app.modules.auth.sms_factory import build_sms_sender
from tests.helpers import SECRET_A, SECRET_B

PASSWORD = "very-secret-password"
EMAIL = "owner@example.com"


class FakeHttp:
    """Eskiz serverini taqlid qiladi. `script` — ketma-ket javoblar: (status, dict|bytes) yoki Exception."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append((method, url, dict(headers), urllib.parse.parse_qs(body.decode()) if body else {}))
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        status, payload = item
        return status, payload if isinstance(payload, bytes) else json.dumps(payload).encode()


LOGIN_OK = (200, {"message": "token_generated", "data": {"token": "TOK1"}, "token_type": "bearer"})
LOGIN_OK2 = (200, {"data": {"token": "TOK2"}})
SEND_OK = (200, {"id": "1", "status": "waiting", "message": "Waiting for SMS provider"})


def sender(http):
    return EskizSmsSender(EMAIL, PASSWORD, sender="4546", http=http)


class EskizTests(unittest.TestCase):
    def test_login_then_send_uses_expected_fields(self):
        http = FakeHttp([LOGIN_OK, SEND_OK])
        sender(http).send("998901234567", "Kod: 123456")

        (m1, u1, _, f1), (m2, u2, h2, f2) = http.calls
        self.assertEqual((m1, u1), ("POST", f"{BASE_URL}/auth/login"))
        self.assertEqual(f1, {"email": [EMAIL], "password": [PASSWORD]})
        self.assertEqual((m2, u2), ("POST", f"{BASE_URL}/message/sms/send"))
        self.assertEqual(h2["Authorization"], "Bearer TOK1")
        self.assertEqual(f2, {"mobile_phone": ["998901234567"], "message": ["Kod: 123456"], "from": ["4546"]})

    def test_token_is_reused_between_sends(self):
        http = FakeHttp([LOGIN_OK, SEND_OK, SEND_OK])
        s = sender(http)
        s.send("998901234567", "a")
        s.send("998901234567", "b")
        self.assertEqual(sum(1 for c in http.calls if c[1].endswith("/auth/login")), 1)

    def test_expired_token_relogin_and_retry_once(self):
        http = FakeHttp([LOGIN_OK, (401, {"message": "expired"}), LOGIN_OK2, SEND_OK])
        sender(http).send("998901234567", "a")
        self.assertEqual(http.calls[-1][2]["Authorization"], "Bearer TOK2")
        self.assertEqual(len(http.calls), 4)

    def test_second_401_is_failure_not_infinite_loop(self):
        http = FakeHttp([LOGIN_OK, (401, {}), LOGIN_OK2, (401, {})])
        with self.assertRaises(SmsDeliveryError):
            sender(http).send("998901234567", "a")
        self.assertEqual(len(http.calls), 4)

    def test_login_failure(self):
        for resp in [(401, {"message": "bad"}), (200, {"data": {}}), (200, b"not json"), (500, b"")]:
            with self.subTest(resp=resp), self.assertRaises(SmsDeliveryError):
                sender(FakeHttp([resp])).send("998901234567", "a")

    def test_send_rejected_by_provider(self):
        for status in (400, 402, 500):
            with self.subTest(status=status), self.assertRaises(SmsDeliveryError):
                sender(FakeHttp([LOGIN_OK, (status, {"message": "x"})])).send("998901234567", "a")

    def test_network_error_propagates_as_delivery_error(self):
        with self.assertRaises(SmsDeliveryError):
            sender(FakeHttp([SmsDeliveryError("SMS yuborib bo'lmadi")])).send("998901234567", "a")

    def test_no_secrets_in_repr_or_errors(self):
        s = sender(FakeHttp([LOGIN_OK, (400, {"message": f"{PASSWORD} 123456"})]))
        self.assertNotIn(PASSWORD, repr(s))
        self.assertNotIn("TOK1", repr(s))
        with self.assertRaises(SmsDeliveryError) as ctx:
            s.send("998901234567", "Kod: 123456")
        text = f"{ctx.exception} {ctx.exception.message} {ctx.exception.details}"
        for secret in (PASSWORD, "TOK1", "123456", "998901234567"):
            self.assertNotIn(secret, text)


class SettingsAndFactoryTests(unittest.TestCase):
    def env(self, **extra):
        return {"JWT_SECRET": SECRET_A, "OTP_SECRET": SECRET_B, **extra}

    def test_defaults_to_none_and_null_sender(self):
        s = Settings.from_env(self.env())
        self.assertEqual(s.sms_provider, "none")
        self.assertIsInstance(build_sms_sender(s), NullSmsSender)

    def test_eskiz_requires_credentials(self):
        with self.assertRaises(ConfigError):
            Settings.from_env(self.env(SMS_PROVIDER="eskiz"))
        with self.assertRaises(ConfigError):
            Settings.from_env(self.env(SMS_PROVIDER="eskiz", ESKIZ_EMAIL=EMAIL))

    def test_eskiz_configured(self):
        s = Settings.from_env(self.env(SMS_PROVIDER="eskiz", ESKIZ_EMAIL=EMAIL, ESKIZ_PASSWORD=PASSWORD))
        sender_ = build_sms_sender(s)
        self.assertIsInstance(sender_, EskizSmsSender)
        self.assertTrue(sender_.is_real)
        self.assertNotIn(PASSWORD, repr(s))  # Settings repr'da parol yo'q

    def test_invalid_values(self):
        for extra in (
            {"SMS_PROVIDER": "twilio"},
            {"SMS_TEMPLATE": "kod yo'q"},
            {"SMS_DAILY_CAP": "0"},
            {"SMS_DAILY_CAP": "abc"},
        ):
            with self.subTest(extra=extra), self.assertRaises(ConfigError):
                Settings.from_env(self.env(**extra))


if __name__ == "__main__":
    unittest.main()
