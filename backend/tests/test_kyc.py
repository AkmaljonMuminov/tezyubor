import base64
import logging
import os
import unittest

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401

    HAVE_CRYPTO = True
except ImportError:  # pragma: no cover
    HAVE_CRYPTO = False

try:
    from fastapi.testclient import TestClient

    from app.main import create_app

    HAVE_HTTP = True
except ImportError:  # pragma: no cover
    HAVE_HTTP = False

from app.config import Settings
from app.errors import (
    ConfigError,
    KycAlreadyVerified,
    KycConsentRequired,
    KycIdentityTaken,
    KycLocked,
    KycNotStarted,
    KycRejected,
    ValidationError,
)
from app.modules.auth.audit import AuditLog
from tests.helpers import SECRET_A, SECRET_B, FakeClock, make_settings

KEY = base64.b64encode(bytes(range(32))).decode()
KEY2 = base64.b64encode(bytes(range(1, 33))).decode()
NOW = 1_800_000_000.0  # 2027-01-15 atrofida
U1, U2 = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"
PASSPORT = "AB1234567"
BORN = "15.03.1990"


@unittest.skipUnless(HAVE_CRYPTO, "cryptography o'rnatilmagan")
class CipherTests(unittest.TestCase):
    def setUp(self):
        from app.security.pii import PiiCipher

        self.PiiCipher = PiiCipher
        self.c = PiiCipher(KEY)

    def test_roundtrip_and_nonce_is_random(self):
        a = self.c.encrypt(b"AB1234567", b"u1")
        b = self.c.encrypt(b"AB1234567", b"u1")
        self.assertNotEqual(a, b)
        self.assertNotIn(b"AB1234567", a)
        self.assertEqual(self.c.decrypt(a, b"u1"), b"AB1234567")

    def test_other_owner_cannot_decrypt(self):
        blob = self.c.encrypt(b"secret", b"user-1")
        with self.assertRaises(ValueError):
            self.c.decrypt(blob, b"user-2")

    def test_tampering_is_detected(self):
        blob = bytearray(self.c.encrypt(b"secret", b"u"))
        blob[-1] ^= 1
        with self.assertRaises(ValueError):
            self.c.decrypt(bytes(blob), b"u")

    def test_wrong_key_fails(self):
        blob = self.c.encrypt(b"secret", b"u")
        with self.assertRaises(ValueError):
            self.PiiCipher(KEY2).decrypt(blob, b"u")

    def test_blind_index_is_stable_keyed_and_not_the_value(self):
        a = self.c.blind_index("30101900000001")
        self.assertEqual(a, self.c.blind_index("30101900000001"))
        self.assertNotEqual(a, self.c.blind_index("30101900000002"))
        self.assertNotEqual(a, self.PiiCipher(KEY2).blind_index("30101900000001"))
        self.assertNotIn("30101900000001", a)

    def test_bad_keys_rejected(self):
        for bad in ("", "not base64!!", base64.b64encode(b"short").decode()):
            with self.assertRaises(ConfigError):
                self.PiiCipher(bad)


class ConfigRules(unittest.TestCase):
    def prod(self, **kw):
        return Settings(env="production", jwt_secret=SECRET_A, otp_secret=SECRET_B, sms_provider="none", **kw)

    def test_kyc_requires_pii_key(self):
        with self.assertRaises(ConfigError):
            make_settings("test", kyc_enabled=True).validate()

    def test_production_kyc_requires_database(self):
        with self.assertRaises(ConfigError):
            self.prod(kyc_enabled=True, pii_key=KEY, kyc_provider="myid").validate()

    def test_production_rejects_fake_provider(self):
        with self.assertRaises(ConfigError):
            self.prod(kyc_enabled=True, pii_key=KEY, database_url="postgresql://x/y").validate()

    def test_unknown_provider_and_bad_url_rejected(self):
        with self.assertRaises(ConfigError):
            make_settings("test", kyc_provider="other").validate()
        with self.assertRaises(ConfigError):
            make_settings("test", database_url="mysql://x/y").validate()

    def test_kyc_off_by_default_needs_nothing(self):
        make_settings("test").validate()

    def test_valid_production_kyc_config_passes(self):
        self.prod(kyc_enabled=True, pii_key=KEY, kyc_provider="myid", database_url="postgresql://x/y").validate()

    def test_bad_pii_key_fails_validation(self):
        with self.assertRaises(ConfigError):
            make_settings("test", kyc_enabled=True, pii_key="zzz").validate()

    def test_secrets_not_in_repr(self):
        s = make_settings("test", kyc_enabled=True, pii_key=KEY, database_url="postgresql://u:pw@h/d")
        self.assertNotIn(KEY, repr(s))
        self.assertNotIn("pw", repr(s))

    def test_myid_provider_not_wired_yet(self):
        from app.modules.kyc.provider import build_kyc_provider

        with self.assertRaises(ConfigError):
            build_kyc_provider(make_settings("test", kyc_provider="myid"))


@unittest.skipUnless(HAVE_CRYPTO, "cryptography o'rnatilmagan")
class KycServiceTests(unittest.TestCase):
    def setUp(self):
        from app.modules.kyc.models import CONSENT_VERSION
        from app.modules.kyc.provider import FakeKycProvider
        from app.modules.kyc.service import KycService
        from app.modules.kyc.store import MemoryKycStore
        from app.security.pii import PiiCipher

        self.version = CONSENT_VERSION
        self.clock = FakeClock(NOW)
        self.audit = AuditLog(self.clock)
        self.store = MemoryKycStore()
        self.cipher = PiiCipher(KEY)
        self.svc = KycService(
            make_settings("test", kyc_enabled=True, pii_key=KEY),
            self.store, FakeKycProvider(), self.cipher, self.audit, self.clock,
        )

    def consent(self, uid=U1):
        self.svc.give_consent(uid, self.version)

    def verify(self, uid=U1, passport=PASSPORT, born=BORN):
        self.consent(uid)
        self.svc.start(uid, passport, born)
        return self.svc.complete(uid)

    def test_initial_status(self):
        st = self.svc.status(U1)
        self.assertEqual(st["status"], "not_started")
        self.assertFalse(st["consent_given"])
        self.assertTrue(st["is_test"])
        self.assertNotIn("identity", st)

    def test_start_requires_consent(self):
        with self.assertRaises(KycConsentRequired):
            self.svc.start(U1, PASSPORT, BORN)

    def test_old_consent_version_rejected(self):
        with self.assertRaises(ValidationError):
            self.svc.give_consent(U1, "eski-versiya")

    def test_full_flow_verified_with_masked_identity(self):
        st = self.verify()
        self.assertEqual(st["status"], "verified")
        self.assertEqual(st["identity"], {"full_name": "TEST FOYDALANUVCHI", "passport": "AB ***4567"})
        self.assertNotIn("pinfl", st["identity"])

    def test_payload_is_encrypted_and_bound_to_owner(self):
        self.verify()
        rec = self.store.get(U1)
        self.assertNotIn(PASSPORT.encode(), rec.payload)
        self.assertNotIn(b"TEST FOYDALANUVCHI", rec.payload)
        self.assertEqual(rec.key_id, "k1")
        with self.assertRaises(ValueError):
            self.cipher.decrypt(rec.payload, U2.encode())  # boshqa egasi uchun ochilmaydi

    def test_entered_passport_is_not_stored_before_verification(self):
        self.consent()
        self.svc.start(U1, PASSPORT, BORN)
        rec = self.store.get(U1)
        self.assertEqual(rec.status, "pending")
        self.assertIsNone(rec.payload)
        self.assertNotIn(PASSPORT, repr(rec))

    def test_passport_input_is_normalized(self):
        self.consent()
        self.svc.start(U1, " ab 1234567 ", BORN)
        self.assertEqual(self.svc.complete(U1)["identity"]["passport"], "AB ***4567")

    def test_invalid_passport_and_dates(self):
        self.consent()
        for passport in ("", "A1234567", "ABC123456", "AB123456", "1234567AB"):
            with self.assertRaises(ValidationError, msg=passport):
                self.svc.start(U1, passport, BORN)
        for born in ("", "1990-03-15", "31.02.1990", "15.03.2999"):
            with self.assertRaises(ValidationError, msg=born):
                self.svc.start(U1, PASSPORT, born)

    def test_minor_rejected_adult_boundary(self):
        self.consent()
        with self.assertRaises(ValidationError):
            self.svc.start(U1, PASSPORT, "20.01.2010")  # 2027-01 da 16 yosh
        # 18 yoshga to'lgan kun
        self.svc.start(U1, PASSPORT, "15.01.2009")

    def test_complete_without_start(self):
        self.consent()
        with self.assertRaises(KycNotStarted):
            self.svc.complete(U1)

    def test_already_verified_cannot_restart(self):
        self.verify()
        with self.assertRaises(KycAlreadyVerified):
            self.svc.start(U1, PASSPORT, BORN)
        with self.assertRaises(KycAlreadyVerified):
            self.svc.complete(U1)

    def test_same_document_cannot_verify_two_accounts(self):
        self.verify(U1)
        self.consent(U2)
        self.svc.start(U2, PASSPORT, BORN)
        with self.assertRaises(KycIdentityTaken):
            self.svc.complete(U2)
        self.assertEqual(self.svc.status(U2)["status"], "rejected")
        self.assertIn("kyc_identity_conflict", [e.event for e in self.audit.events])

    def test_rejection_then_lock_after_five_failures(self):
        self.consent()
        bad = "AB1230000"  # fake provider rad etadi
        for i in range(5):
            self.svc.start(U1, bad, BORN)
            with self.assertRaises(KycRejected):
                self.svc.complete(U1)
        self.assertEqual(self.svc.status(U1)["status"], "rejected")
        with self.assertRaises(KycLocked) as ctx:
            self.svc.start(U1, PASSPORT, BORN)
        self.assertGreater(ctx.exception.details["retry_after"], 3000)
        self.assertIn("retry_after", self.svc.status(U1))
        self.clock.advance(3601)
        self.svc.start(U1, PASSPORT, BORN)  # blok tugadi
        self.assertEqual(self.svc.complete(U1)["status"], "verified")

    def test_audit_has_no_personal_data(self):
        self.verify()
        text = repr([(e.event, e.fields) for e in self.audit.events])
        for secret in (PASSPORT, BORN, "TEST FOYDALANUVCHI", "1234567"):
            self.assertNotIn(secret, text)
        self.assertIn("kyc_verified", text)

    def test_no_personal_data_in_logs(self):
        records = []

        class Grab(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        h = Grab(level=logging.DEBUG)
        root = logging.getLogger()
        old = root.level
        root.addHandler(h)
        root.setLevel(logging.DEBUG)
        try:
            self.verify()
        finally:
            root.removeHandler(h)
            root.setLevel(old)
        self.assertNotIn(PASSPORT, " ".join(records))

    def test_blind_index_stored_not_pinfl(self):
        self.verify()
        rec = self.store.get(U1)
        self.assertEqual(len(rec.pinfl_index), 64)
        self.assertTrue(rec.pinfl_index.isalnum())


@unittest.skipUnless(HAVE_HTTP and HAVE_CRYPTO, "fastapi/httpx/cryptography kerak")
class KycHttp(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(
            create_app(make_settings("test", kyc_enabled=True, pii_key=KEY, otp_cooldown=0, otp_max_per_hour=100))
        )
        cid = self.client.post("/v1/auth/otp/request", json={"phone": "901234567"}).json()["challenge_id"]
        t = self.client.post("/v1/auth/otp/verify", json={"challenge_id": cid, "code": "123456"}).json()
        self.h = {"Authorization": f"Bearer {t['access_token']}"}

    def test_requires_auth(self):
        for method, path in (("get", "/v1/kyc/status"), ("post", "/v1/kyc/start"), ("post", "/v1/kyc/complete")):
            r = getattr(self.client, method)(path)
            self.assertIn(r.status_code, (401, 422), path)
        r = self.client.get("/v1/kyc/status")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["error"]["code"], "TOKEN_INVALID")

    def test_full_flow_over_http(self):
        st = self.client.get("/v1/kyc/status", headers=self.h).json()
        self.assertEqual(st["status"], "not_started")
        r = self.client.post("/v1/kyc/start", headers=self.h, json={"passport": PASSPORT, "birth_date": BORN})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["error"]["code"], "KYC_CONSENT_REQUIRED")
        ok = self.client.post("/v1/kyc/consent", headers=self.h, json={"version": st["consent_version"]})
        self.assertEqual(ok.status_code, 204)
        r = self.client.post("/v1/kyc/start", headers=self.h, json={"passport": PASSPORT, "birth_date": BORN})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["session_id"])
        r = self.client.post("/v1/kyc/complete", headers=self.h)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "verified")
        self.assertNotIn(PASSPORT, r.text)

    def test_validation_error_does_not_echo_passport(self):
        self.client.post("/v1/kyc/consent", headers=self.h, json={"version": self.client.get("/v1/kyc/status", headers=self.h).json()["consent_version"]})
        r = self.client.post("/v1/kyc/start", headers=self.h, json={"passport": "XX-bad-9999999", "birth_date": BORN})
        self.assertEqual(r.status_code, 422)
        self.assertNotIn("9999999", r.text)
        r = self.client.post("/v1/kyc/start", headers=self.h, json={"passport": PASSPORT})  # birth_date yo'q
        self.assertEqual(r.status_code, 422)
        self.assertNotIn(PASSPORT, r.text)

    def test_kyc_routes_absent_when_disabled(self):
        c = TestClient(create_app(make_settings("test")))
        self.assertEqual(c.get("/v1/kyc/status").status_code, 404)


if __name__ == "__main__":
    unittest.main()
