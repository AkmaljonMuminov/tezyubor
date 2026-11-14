"""HTTP qatlami (FastAPI) — faqat fastapi o'rnatilgan muhitda (CI) ishlaydi."""
import unittest

try:
    from fastapi.testclient import TestClient

    from app.main import create_app

    HAVE = True
except ImportError:  # pragma: no cover
    HAVE = False

from tests.helpers import make_settings
from tests.wallet_helpers import KEY, PAN_A, PAN_B, PIN


@unittest.skipUnless(HAVE, "fastapi kerak")
class WalletHttpTests(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(
            create_app(
                make_settings("test", wallet_enabled=True, card_index_key=KEY, otp_cooldown=0, otp_max_per_hour=100,
                              transfer_fee_bps=100)
            )
        )
        self.a = self.login("901111111")
        self.b = self.login("902222222")

    def login(self, phone):
        cid = self.c.post("/v1/auth/otp/request", json={"phone": phone}).json()["challenge_id"]
        t = self.c.post("/v1/auth/otp/verify", json={"challenge_id": cid, "code": "123456", "device_label": "Test"}).json()
        h = {"Authorization": f"Bearer {t['access_token']}"}
        self.assertEqual(self.c.post("/v1/auth/pin/set", json={"pin": PIN}, headers=h).status_code, 204)
        return {"h": h, "refresh": t["refresh_token"]}

    def add(self, who, pan):
        r = self.c.post("/v1/wallet/cards", json={"pan": pan, "exp_month": 12, "exp_year": 2099, "holder_name": "Ali Vali"}, headers=who["h"])
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def test_requires_auth_everywhere(self):
        for method, path in [("get", "/v1/wallet/cards"), ("post", "/v1/wallet/cards"), ("post", "/v1/wallet/transfers"),
                             ("get", "/v1/wallet/transactions"), ("post", "/v1/wallet/receiver/lookup")]:
            r = getattr(self.c, method)(path, **({} if method == "get" else {"json": {}}))
            self.assertEqual(r.status_code, 401, (method, path, r.text))
            self.assertEqual(r.json()["error"]["code"], "TOKEN_INVALID")
        r = self.c.get("/v1/wallet/cards", headers={"Authorization": "Bearer garbage"})
        self.assertEqual(r.status_code, 401)

    def test_full_flow_over_http(self):
        ca, cb = self.add(self.a, PAN_A), self.add(self.b, PAN_B)
        self.assertTrue(ca["sandbox"])
        self.assertNotIn(PAN_A, str(ca))
        self.assertEqual(self.c.get("/v1/wallet/cards", headers=self.a["h"]).json()["cards"][0]["id"], ca["id"])

        lk = self.c.post("/v1/wallet/receiver/lookup", json={"pan": PAN_B}, headers=self.a["h"]).json()
        self.assertEqual(lk["name_masked"], "A* V*")

        hdr = {**self.a["h"], "Idempotency-Key": "http-key-0001"}
        body = {"from_card_id": ca["id"], "receiver_pan": PAN_B, "amount_tiyin": 1_000_000}
        q = self.c.post("/v1/wallet/transfers", json=body, headers=hdr).json()
        self.assertEqual((q["status"], q["fee_tiyin"], q["total_tiyin"]), ("pending", 10_000, 1_010_000))
        self.assertEqual(self.c.post("/v1/wallet/transfers", json=body, headers=hdr).json()["id"], q["id"])  # idempotent

        r = self.c.post("/v1/wallet/transfers", json={**body, "amount_tiyin": 2_000_000}, headers=hdr)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "IDEMPOTENCY_CONFLICT"))

        bad = self.c.post(f"/v1/wallet/transfers/{q['id']}/confirm", json={"pin": "9999"}, headers=self.a["h"])
        self.assertEqual((bad.status_code, bad.json()["error"]["code"]), (401, "PIN_INVALID"))
        done = self.c.post(f"/v1/wallet/transfers/{q['id']}/confirm", json={"pin": PIN}, headers=self.a["h"]).json()
        self.assertEqual(done["status"], "completed")
        self.assertTrue(done["receipt"]["number"].startswith("TZ-"))

        cards_a = self.c.get("/v1/wallet/cards", headers=self.a["h"]).json()["cards"]
        cards_b = self.c.get("/v1/wallet/cards", headers=self.b["h"]).json()["cards"]
        self.assertEqual(cards_a[0]["balance_tiyin"], 100_000_000 - 1_010_000)
        self.assertEqual(cards_b[0]["balance_tiyin"], 100_000_000 + 1_000_000)

        hist = self.c.get("/v1/wallet/transactions?limit=1", headers=self.b["h"]).json()
        self.assertEqual((hist["items"][0]["direction"], hist["next_cursor"]), ("received", None))
        one = self.c.get(f"/v1/wallet/transactions/{q['id']}", headers=self.a["h"])
        self.assertEqual(one.json()["receipt"]["number"], done["receipt"]["number"])

    def test_missing_idempotency_key_and_bad_body(self):
        ca = self.add(self.a, PAN_A)
        self.add(self.b, PAN_B)
        body = {"from_card_id": ca["id"], "receiver_pan": PAN_B, "amount_tiyin": 1_000_000}
        r = self.c.post("/v1/wallet/transfers", json=body, headers=self.a["h"])
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "IDEMPOTENCY_KEY_INVALID"))
        hdr = {**self.a["h"], "Idempotency-Key": "http-key-0002"}
        for bad in ({**body, "amount_tiyin": 10.5}, {**body, "amount_tiyin": "1000000"}, {**body, "amount_tiyin": True}, {"from_card_id": ca["id"]}):
            r = self.c.post("/v1/wallet/transfers", json=bad, headers=hdr)
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "VALIDATION_ERROR"), bad)

    def test_cannot_touch_foreign_card_or_transfer(self):
        ca, cb = self.add(self.a, PAN_A), self.add(self.b, PAN_B)
        self.assertEqual(self.c.delete(f"/v1/wallet/cards/{ca['id']}", headers=self.b["h"]).status_code, 404)
        hdr = {**self.b["h"], "Idempotency-Key": "http-key-0003"}
        r = self.c.post("/v1/wallet/transfers", json={"from_card_id": ca["id"], "receiver_pan": PAN_B, "amount_tiyin": 1_000_000}, headers=hdr)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (404, "CARD_NOT_FOUND"))
        q = self.c.post("/v1/wallet/transfers", json={"from_card_id": ca["id"], "receiver_pan": PAN_B, "amount_tiyin": 1_000_000},
                        headers={**self.a["h"], "Idempotency-Key": "http-key-0004"}).json()
        r = self.c.post(f"/v1/wallet/transfers/{q['id']}/confirm", json={"pin": PIN}, headers=self.b["h"])
        self.assertEqual(r.status_code, 404)

    def test_revoked_session_loses_wallet_access(self):
        self.add(self.a, PAN_A)
        self.assertEqual(self.c.post("/v1/auth/logout", json={"refresh_token": self.a["refresh"]}).status_code, 204)
        r = self.c.get("/v1/wallet/cards", headers=self.a["h"])
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (401, "TOKEN_INVALID"))

    def test_disabled_by_default(self):
        c = TestClient(create_app(make_settings("test")))
        self.assertEqual(c.get("/v1/wallet/cards").status_code, 404)


@unittest.skipUnless(HAVE, "fastapi kerak")
class SessionHttpTests(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(create_app(make_settings("test", otp_cooldown=0, otp_max_per_hour=100)))

    def login(self, label):
        cid = self.c.post("/v1/auth/otp/request", json={"phone": "901111111"}).json()["challenge_id"]
        return self.c.post("/v1/auth/otp/verify", json={"challenge_id": cid, "code": "123456", "device_label": label}).json()

    def test_logout_and_sessions(self):
        a, b = self.login("Telefon"), self.login("Planshet")
        ha = {"Authorization": f"Bearer {a['access_token']}"}
        rows = self.c.get("/v1/auth/sessions", headers=ha).json()["sessions"]
        self.assertEqual({r["device_label"] for r in rows}, {"Telefon", "Planshet"})
        self.assertEqual([r["device_label"] for r in rows if r["current"]], ["Telefon"])
        other = next(r for r in rows if not r["current"])
        self.assertEqual(self.c.delete(f"/v1/auth/sessions/{other['id']}", headers=ha).status_code, 204)
        self.assertEqual(self.c.post("/v1/auth/token/refresh", json={"refresh_token": b["refresh_token"]}).status_code, 401)
        r = self.c.delete("/v1/auth/sessions/yoq", headers=ha)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (404, "SESSION_NOT_FOUND"))
        self.assertEqual(self.c.post("/v1/auth/logout", json={"refresh_token": a["refresh_token"]}).status_code, 204)
        self.assertEqual(self.c.get("/v1/auth/sessions", headers=ha).status_code, 401)
        self.assertEqual(self.c.post("/v1/auth/logout", json={"refresh_token": "x"}).status_code, 204)  # noma'lum token ham 204


if __name__ == "__main__":
    unittest.main()
