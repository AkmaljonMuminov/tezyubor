import unittest

import jwt

from app.config import Settings
from app.errors import ConfigError, TokenInvalid, TokenReuseDetected
from tests.helpers import SECRET_A, SECRET_B, make_stack


class TokenTests(unittest.TestCase):
    def test_access_roundtrip(self):
        _, _o, tokens, *_ = make_stack()
        pair = tokens.issue_pair("u1")
        self.assertEqual(tokens.verify_access(pair.access_token), "u1")

    def test_access_expires(self):
        _, _o, tokens, _u, _a, clock, _s = make_stack()
        pair = tokens.issue_pair("u1")
        clock.advance(601)
        with self.assertRaises(TokenInvalid):
            tokens.verify_access(pair.access_token)

    def test_tampered_and_garbage_rejected(self):
        _, _o, tokens, *_ = make_stack()
        pair = tokens.issue_pair("u1")
        for bad in [pair.access_token[:-2] + "xx", "garbage", "", pair.refresh_token]:
            with self.assertRaises(TokenInvalid):
                tokens.verify_access(bad)

    def test_wrong_secret_and_alg_none_rejected(self):
        _, _o, tokens, *_ = make_stack()
        forged = jwt.encode(
            {"sub": "u1", "iat": 1_000_000, "exp": 2_000_000, "typ": "access"}, "z" * 40, "HS256"
        )
        with self.assertRaises(TokenInvalid):
            tokens.verify_access(forged)
        none_tok = jwt.encode({"sub": "u1", "iat": 1, "exp": 9**9, "typ": "access"}, None, "none")
        with self.assertRaises(TokenInvalid):
            tokens.verify_access(none_tok)

    def test_wrong_token_type_rejected(self):
        _, _o, tokens, *_ = make_stack()
        tok = jwt.encode(
            {"sub": "u1", "iat": 1_000_000, "exp": 2_000_000, "typ": "refresh"}, SECRET_A, "HS256"
        )
        with self.assertRaises(TokenInvalid):
            tokens.verify_access(tok)

    def test_refresh_rotation(self):
        _, _o, tokens, *_ = make_stack()
        p1 = tokens.issue_pair("u1")
        p2 = tokens.rotate(p1.refresh_token)
        self.assertNotEqual(p1.refresh_token, p2.refresh_token)
        self.assertEqual(tokens.verify_access(p2.access_token), "u1")

    def test_reuse_revokes_whole_family(self):
        _, _o, tokens, *_ = make_stack()
        p1 = tokens.issue_pair("u1")
        p2 = tokens.rotate(p1.refresh_token)
        with self.assertRaises(TokenReuseDetected):
            tokens.rotate(p1.refresh_token)  # eski token qayta ishlatildi
        with self.assertRaises(TokenInvalid):  # yangi token ham bekor qilingan
            tokens.rotate(p2.refresh_token)

    def test_refresh_expiry_and_unknown(self):
        _, _o, tokens, _u, _a, clock, _s = make_stack()
        p = tokens.issue_pair("u1")
        clock.advance(30 * 86400 + 1)
        with self.assertRaises(TokenInvalid):
            tokens.rotate(p.refresh_token)
        for bad in ["nope", "", None]:
            with self.assertRaises(TokenInvalid):
                tokens.rotate(bad)

    def test_refresh_stored_hashed(self):
        svc, _o, tokens, *_ = make_stack()
        p = tokens.issue_pair("u1")
        self.assertNotIn(p.refresh_token, str(vars(tokens._store)))


class ConfigTests(unittest.TestCase):
    def test_missing_secrets_fail(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({})
        with self.assertRaises(ConfigError):
            Settings.from_env({"JWT_SECRET": SECRET_A})

    def test_short_or_equal_secrets_fail(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"JWT_SECRET": "short", "OTP_SECRET": SECRET_B})
        with self.assertRaises(ConfigError):
            Settings.from_env({"JWT_SECRET": SECRET_A, "OTP_SECRET": SECRET_A})

    def test_bad_env_name_fails(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"APP_ENV": "prod", "JWT_SECRET": SECRET_A, "OTP_SECRET": SECRET_B})

    def test_test_mode_only_outside_production(self):
        ok = {"JWT_SECRET": SECRET_A, "OTP_SECRET": SECRET_B}
        self.assertTrue(Settings.from_env({**ok, "APP_ENV": "development"}).test_mode)
        self.assertFalse(Settings.from_env({**ok, "APP_ENV": "production"}).test_mode)


if __name__ == "__main__":
    unittest.main()
