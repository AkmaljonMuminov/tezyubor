import unittest

from app.modules.auth.security import hash_pin, verify_pin
from app.modules.auth.validators import is_pin_acceptable, mask_phone, normalize_phone


class ValidatorTests(unittest.TestCase):
    def test_phone_variants(self):
        self.assertEqual(normalize_phone("90 123 45 67"), "998901234567")
        self.assertEqual(normalize_phone("+998 90 123-45-67"), "998901234567")
        self.assertEqual(normalize_phone("998901234567"), "998901234567")

    def test_phone_invalid(self):
        for bad in ["", "123", "012345678", "9989012345678", "+7 900 123 45 67", None]:
            self.assertIsNone(normalize_phone(bad), bad)

    def test_pin_weak(self):
        for p in ["1111", "0000", "1234", "4321", "3456", "12a4", "123", "12345", "", None]:
            self.assertFalse(is_pin_acceptable(p), p)

    def test_pin_ok(self):
        for p in ["1357", "2580", "7391", "1122"]:
            self.assertTrue(is_pin_acceptable(p), p)

    def test_mask_phone_hides_middle(self):
        m = mask_phone("998901234567")
        self.assertEqual(m, "998 90 *** ** 67")
        self.assertNotIn("1234", m)


class PinHashTests(unittest.TestCase):
    def test_roundtrip(self):
        h = hash_pin("7391")
        self.assertTrue(verify_pin("7391", h))
        self.assertFalse(verify_pin("7392", h))

    def test_salted_and_not_plaintext(self):
        a, b = hash_pin("7391"), hash_pin("7391")
        self.assertNotEqual(a, b)
        self.assertNotIn("7391", a)

    def test_malformed_hash_is_false_not_crash(self):
        for bad in ["", "x", "scrypt$1$2", "md5$1$2$3$4$5", "scrypt$a$b$c$d$e"]:
            self.assertFalse(verify_pin("7391", bad), bad)


if __name__ == "__main__":
    unittest.main()
