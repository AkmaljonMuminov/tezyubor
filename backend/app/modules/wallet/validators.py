"""Karta ma'lumotlarini tekshirish va maskalash. PAN va CVV hech qachon log'ga yozilmaydi; CVV umuman olinmaydi."""
import re

_PAN_RE = re.compile(r"^[0-9]{16}$")
_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,38}[A-Za-z.]$")


def normalize_pan(raw: str | None) -> str | None:
    """Bo'shliq/chiziqchalarni olib tashlaydi. 16 raqam va Luhn bo'lmasa — None."""
    if not isinstance(raw, str):
        return None
    pan = re.sub(r"[ -]", "", raw)
    if not _PAN_RE.fullmatch(pan) or not luhn_ok(pan):
        return None
    return pan


def luhn_ok(pan: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(pan)):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def card_brand(pan: str) -> str:
    if pan.startswith("8600"):
        return "uzcard"
    if pan.startswith("9860"):
        return "humo"
    if pan.startswith("4"):
        return "visa"
    if re.match(r"^(5[1-5]|2[2-7])", pan):
        return "mastercard"
    return "other"


def valid_expiry(month: int, year: int, now_epoch: float) -> bool:
    """Muddat oy oxirigacha amal qiladi. `year` — 4 xonali (2026) yoki 2 xonali (26)."""
    import datetime as _dt

    if not isinstance(month, int) or not isinstance(year, int) or isinstance(month, bool) or isinstance(year, bool):
        return False
    if year < 100:
        year += 2000
    if not 1 <= month <= 12 or not 2000 <= year <= 2100:
        return False
    today = _dt.datetime.fromtimestamp(now_epoch, tz=_dt.timezone.utc)
    return (year, month) >= (today.year, today.month)


def normalize_year(year: int) -> int:
    return year + 2000 if year < 100 else year


def clean_holder_name(raw: str | None) -> str | None:
    if not isinstance(raw, str):
        return None
    name = re.sub(r"\s+", " ", raw).strip()
    if not _NAME_RE.fullmatch(name):
        return None
    return name.upper()


def valid_idempotency_key(key: str | None) -> bool:
    return isinstance(key, str) and _KEY_RE.fullmatch(key) is not None


def mask_pan(bin6: str, last4: str) -> str:
    return f"{bin6[:4]} {bin6[4:6]}** **** {last4}"


def mask_name(name: str) -> str:
    """'ALISHER KARIMOV' -> 'A****** K******'. Qabul qiluvchi shaxsini tasdiqlash uchun yetarli, to'liq oshkor qilmaydi."""
    parts = []
    for word in name.split():
        parts.append(word[0] + "*" * min(len(word) - 1, 6))
    return " ".join(parts)
