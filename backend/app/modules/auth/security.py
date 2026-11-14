"""PIN xeshlash (scrypt, stdlib). Eslatma: 4 xonali PIN offline buzishga qarshi kuchsiz (10 000 variant) —
asosiy himoya serverdagi urinishlar limiti va bloklash (AuthService). Qo'shimcha qatlam: server "pepper"
(PIN_PEPPER, faqat muhit o'zgaruvchisida): u bo'lmasa, faqat bazaning o'zi sizib chiqsa ham PIN'ni taxmin qilib bo'lmaydi.

Sxemalar: "scrypt"  — pepper'siz (eski yozuvlar), "scrypt2" — HMAC-SHA256(pepper, pin) ustidan scrypt."""
import base64
import hashlib
import hmac
import os

_N, _R, _P = 2**14, 8, 1


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _material(pin: str, pepper: str) -> bytes:
    if pepper:
        return hmac.new(pepper.encode(), pin.encode(), hashlib.sha256).digest()
    return pin.encode()


def hash_pin(pin: str, pepper: str = "") -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(_material(pin, pepper), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    scheme = "scrypt2" if pepper else "scrypt"
    return f"{scheme}${_N}${_R}${_P}${_b64(salt)}${_b64(dk)}"


def verify_pin(pin: str, stored: str, pepper: str = "") -> bool:
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme == "scrypt":
            material = pin.encode()
        elif scheme == "scrypt2":
            if not pepper:
                return False  # pepper sozlanmagan: bu yozuvni tekshirib bo'lmaydi (xavfsiz tomonga — rad)
            material = _material(pin, pepper)
        else:
            return False
        dk = hashlib.scrypt(
            material, salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32
        )
        return hmac.compare_digest(dk, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


def needs_rehash(stored: str, pepper: str) -> bool:
    """Pepper yoqilgan, lekin yozuv eski sxemada — to'g'ri PIN kiritilganda yangilanadi."""
    return bool(pepper) and stored.startswith("scrypt$")
