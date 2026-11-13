"""Oddiy `.env` o'qigich (standart kutubxona). Faqat yordamchi vositalar uchun (masalan sms_check).
Bo'sh joy, apostrof va `!` bor qiymatlar ham to'g'ri o'qiladi — `export $(... | xargs)` bunda buziladi.
Server (uvicorn) uchun: `uvicorn app.main:create_app --factory --env-file ../.env`.
"""
import os


def parse_env_file(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key.startswith("export "):
            key = key[7:].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            out[key] = value
    return out


def load_env_file(path: str, environ=None) -> None:
    """Mavjud muhit o'zgaruvchilarini O'ZGARTIRMAYDI (haqiqiy muhit .env dan ustun)."""
    environ = os.environ if environ is None else environ
    with open(path, encoding="utf-8") as f:
        for k, v in parse_env_file(f.read()).items():
            environ.setdefault(k, v)
