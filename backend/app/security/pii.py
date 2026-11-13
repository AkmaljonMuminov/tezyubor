"""Shaxsiy ma'lumotni (pasport, JShShIR) bazada shifrlab saqlash.

AES-256-GCM: shifrlangan matn butunligini ham tekshiradi. AAD sifatida egasining user_id'si beriladi — shuning uchun
bir foydalanuvchining shifrlangan yozuvini boshqasinikiga ko'chirib bo'lmaydi. Kalit faqat muhit o'zgaruvchisida
(PII_KEY), bazada va kodda YO'Q. Yangi kalit: python3 -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"
"""
import base64
import binascii
import hashlib
import hmac
import os

from ..errors import ConfigError

_NONCE = 12


def decode_key(key_b64: str) -> bytes:
    try:
        key = base64.b64decode(key_b64, validate=True)
    except (binascii.Error, ValueError):
        raise ConfigError("PII_KEY base64 formatida bo'lishi kerak") from None
    if len(key) != 32:
        raise ConfigError("PII_KEY aynan 32 bayt (base64) bo'lishi kerak")
    return key


class PiiCipher:
    def __init__(self, key_b64: str, key_id: str = "k1"):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = decode_key(key_b64)
        self.key_id = key_id
        self._aes = AESGCM(key)
        # Qidiruv indeksi uchun alohida kalit: shifrlash kalitidan olinadi, lekin undan farq qiladi
        self._index_key = hmac.new(key, b"tezyubor/blind-index/v1", hashlib.sha256).digest()

    def encrypt(self, plaintext: bytes, aad: bytes) -> bytes:
        nonce = os.urandom(_NONCE)
        return nonce + self._aes.encrypt(nonce, plaintext, aad)

    def decrypt(self, blob: bytes, aad: bytes) -> bytes:
        from cryptography.exceptions import InvalidTag

        try:
            return self._aes.decrypt(blob[:_NONCE], blob[_NONCE:], aad)
        except InvalidTag:
            raise ValueError("Shifrlangan ma'lumot buzilgan yoki kalit/egasi mos emas") from None

    def blind_index(self, value: str) -> str:
        """Qiymatni ochmasdan 'bir xil JShShIR boshqa hisobda ishlatilganmi' deb tekshirish uchun (HMAC-SHA256)."""
        return hmac.new(self._index_key, value.encode(), hashlib.sha256).hexdigest()
