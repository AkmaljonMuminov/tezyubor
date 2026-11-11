import re

_PHONE_RE = re.compile(r"998[1-9][0-9]{8}")
_PIN_RE = re.compile(r"[0-9]{4}")


def normalize_phone(raw: str) -> str | None:
    """`998XXXXXXXXX` yoki None. Mobil ilovadagi qoida bilan bir xil (server qayta tekshiradi)."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:
        digits = "998" + digits
    return digits if _PHONE_RE.fullmatch(digits) else None


def mask_phone(phone: str) -> str:
    """Audit jurnali uchun: 998901234567 -> 998 90 *** ** 67."""
    return f"{phone[:3]} {phone[3:5]} *** ** {phone[-2:]}"


def is_pin_acceptable(pin: str) -> bool:
    if not _PIN_RE.fullmatch(pin or ""):
        return False
    d = [int(c) for c in pin]
    if len(set(d)) == 1:
        return False
    steps = {d[i + 1] - d[i] for i in range(3)}
    return steps not in ({1}, {-1})
