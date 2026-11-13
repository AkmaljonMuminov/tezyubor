"""HTTP qatlami: haqiqiy FastAPI + TestClient. fastapi/httpx o'rnatilmagan muhitda o'tkazib yuboriladi
(CI'da o'rnatiladi, shuning uchun u yerda albatta ishlaydi)."""
import re
import unittest

try:
    from fastapi.testclient import TestClient

    from app.main import create_app

    HAVE_HTTP = True
except ImportError:  # pragma: no cover
    HAVE_HTTP = False

from tests.helpers import RecordingSms, make_settings

PHONE = "901234567"


@unittest.skipUnless(HAVE_HTTP, "fastapi/httpx o'rnatilmagan")
class TestModeHttp(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(make_settings("test", otp_cooldown=0, otp_max_per_hour=100)))

    def _login(self, phone=PHONE):
        r = self.client.post("/v1/auth/otp/request", json={"phone": phone})
        self.assertEqual(r.status_code, 200, r.text)
        cid = r.json()["challenge_id"]
        r = self.client.post("/v1/auth/otp/verify", json={"challenge_id": cid, "code": "123456"})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok", "test_mode": True})

    def test_otp_flow_returns_tokens_and_pin_not_set(self):
        body = self._login()
        self.assertEqual(body["token_type"], "bearer")
        self.assertFalse(body["pin_set"])
        self.assertTrue(body["access_token"] and body["refresh_token"])

    def test_request_returns_challenge_and_ttl(self):
        r = self.client.post("/v1/auth/otp/request", json={"phone": "+998 90 123 45 67"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["expires_in"], 120)
        self.assertTrue(r.json()["challenge_id"])

    def test_phone_formats_mobile_sends_are_accepted(self):
        # Mobil ilova `998XXXXXXXXX` yuboradi
        r = self.client.post("/v1/auth/otp/request", json={"phone": "998" + PHONE})
        self.assertEqual(r.status_code, 200, r.text)

    def test_bad_phone_gives_unified_422(self):
        r = self.client.post("/v1/auth/otp/request", json={"phone": "12345"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["error"]["code"], "VALIDATION_ERROR")

    def test_missing_body_field_gives_unified_422_without_details(self):
        r = self.client.post("/v1/auth/otp/request", json={})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json(), {"error": {"code": "VALIDATION_ERROR", "message": "Ma'lumot noto'g'ri"}})

    def test_wrong_code_gives_otp_invalid(self):
        cid = self.client.post("/v1/auth/otp/request", json={"phone": PHONE}).json()["challenge_id"]
        r = self.client.post("/v1/auth/otp/verify", json={"challenge_id": cid, "code": "000000"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"]["code"], "OTP_INVALID")

    def test_pin_set_requires_bearer(self):
        r = self.client.post("/v1/auth/pin/set", json={"pin": "2580"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["error"]["code"], "TOKEN_INVALID")

    def test_pin_set_204_then_pin_login_rotates_tokens(self):
        t = self._login()
        r = self.client.post(
            "/v1/auth/pin/set", json={"pin": "2580"}, headers={"Authorization": f"Bearer {t['access_token']}"}
        )
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.content, b"")

        r = self.client.post("/v1/auth/pin/login", json={"refresh_token": t["refresh_token"], "pin": "2580"})
        self.assertEqual(r.status_code, 200, r.text)
        new = r.json()
        self.assertNotEqual(new["refresh_token"], t["refresh_token"])

        # Eski refresh token qayta ishlatilsa — o'g'irlangan deb hisoblanadi
        r = self.client.post("/v1/auth/token/refresh", json={"refresh_token": t["refresh_token"]})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["error"]["code"], "TOKEN_REUSE_DETECTED")

    def test_second_login_after_pin_reports_pin_set(self):
        t = self._login()
        self.client.post(
            "/v1/auth/pin/set", json={"pin": "2580"}, headers={"Authorization": f"Bearer {t['access_token']}"}
        )
        self.assertTrue(self._login()["pin_set"])

    def test_wrong_pin_reports_attempts_left_and_lock_has_retry_after(self):
        t = self._login()
        self.client.post(
            "/v1/auth/pin/set", json={"pin": "2580"}, headers={"Authorization": f"Bearer {t['access_token']}"}
        )
        r = self.client.post("/v1/auth/pin/login", json={"refresh_token": t["refresh_token"], "pin": "1357"})
        self.assertEqual(r.status_code, 401)
        err = r.json()["error"]
        self.assertEqual(err["code"], "PIN_INVALID")
        self.assertEqual(err["attempts_left"], 4)
        for _ in range(4):
            r = self.client.post("/v1/auth/pin/login", json={"refresh_token": t["refresh_token"], "pin": "1357"})
        self.assertEqual(r.status_code, 423)
        err = r.json()["error"]
        self.assertEqual(err["code"], "PIN_LOCKED")
        self.assertIsInstance(err["retry_after"], int)  # mobil ilova shu maydonni o'qiydi

    def test_docs_available_in_test_mode(self):
        self.assertEqual(self.client.get("/docs").status_code, 200)


@unittest.skipUnless(HAVE_HTTP, "fastapi/httpx o'rnatilmagan")
class ProductionHttp(unittest.TestCase):
    def setUp(self):
        self.sms = RecordingSms()
        self.client = TestClient(create_app(make_settings("production", otp_cooldown=0), sms=self.sms))

    def test_real_sms_flow_end_to_end(self):
        r = self.client.post("/v1/auth/otp/request", json={"phone": PHONE})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len(self.sms.sent), 1)
        phone, text = self.sms.sent[0]
        self.assertEqual(phone, "998" + PHONE)
        code = re.search(r"\d{6}", text).group(0)
        self.assertNotEqual(code, "123456")

        cid = r.json()["challenge_id"]
        bad = self.client.post("/v1/auth/otp/verify", json={"challenge_id": cid, "code": "123456"})
        self.assertEqual(bad.status_code, 400)  # test kodi productionda ishlamaydi
        ok = self.client.post("/v1/auth/otp/verify", json={"challenge_id": cid, "code": code})
        self.assertEqual(ok.status_code, 200, ok.text)

    def test_health_hides_nothing_but_reports_production(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok", "test_mode": False})

    def test_docs_are_closed_in_production(self):
        for path in ("/docs", "/redoc", "/openapi.json"):
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_sms_failure_returns_502_without_leaking_details(self):
        from app.errors import SmsDeliveryError

        class Failing:
            is_real = True

            def send(self, phone, text):
                raise SmsDeliveryError("eskiz: token=SECRET-XYZ rad etdi")

        client = TestClient(create_app(make_settings("production"), sms=Failing()))
        r = client.post("/v1/auth/otp/request", json={"phone": PHONE})
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json()["error"]["code"], "SMS_DELIVERY_FAILED")
        self.assertNotIn("SECRET-XYZ", r.text)


if __name__ == "__main__":
    unittest.main()
