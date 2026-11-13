import re
from datetime import date, datetime

_PASSPORT_RE = re.compile(r"[A-Z]{2}[0-9]{7}")
_PINFL_RE = re.compile(r"[0-9]{14}")


def normalize_passport(raw: str) -> str | None:
    """`AA 1234567` -> `AA1234567` (pasport yoki ID-karta: 2 harf + 7 raqam). Noto'g'ri bo'lsa None."""
    s = re.sub(r"[\s\-]", "", raw or "").upper()
    return s if _PASSPORT_RE.fullmatch(s) else None


def parse_birth_date(raw: str) -> date | None:
    """`dd.MM.yyyy` (MyID SDK formati). Noto'g'ri sana yoki format bo'lsa None."""
    try:
        return datetime.strptime((raw or "").strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


def age_on(born: date, today: date) -> int:
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def is_pinfl(value: str) -> bool:
    return bool(_PINFL_RE.fullmatch(value or ""))


def mask_passport(passport: str) -> str:
    """`AA1234567` -> `AA ***4567`"""
    return f"{passport[:2]} ***{passport[-4:]}"
