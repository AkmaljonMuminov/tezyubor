"""Eskiz ulanishini BITTA haqiqiy SMS bilan tekshirish (o'zingizning raqamingizga).

Ishlatish (kalitlar .env dan, chatga yozilmaydi):
    export $(grep -v '^#' ../.env | xargs)
    python3 -m app.tools.sms_check 901234567

Eslatma: bu haqiqiy SMS yuboradi va hisobingizdan pul yechiladi. Kod tasodifiy; SMS ni telefoningizda ko'rasiz.
"""
import secrets
import sys

from ..config import Settings
from ..errors import SmsDeliveryError
from ..modules.auth.sms_factory import build_sms_sender
from ..modules.auth.validators import normalize_phone


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Ishlatish: python3 -m app.tools.sms_check <telefon, masalan 901234567>")
        return 2
    phone = normalize_phone(argv[1])
    if phone is None:
        print("Telefon raqami noto'g'ri")
        return 2
    settings = Settings.from_env()
    if settings.sms_provider == "none":
        print("SMS_PROVIDER=none. .env da SMS_PROVIDER=eskiz va ESKIZ_* ni to'ldiring")
        return 2
    code = f"{secrets.randbelow(10**6):06d}"
    try:
        build_sms_sender(settings).send(phone, settings.sms_template.replace("{code}", code))
    except SmsDeliveryError as e:
        print(f"XATO: {e.message}. Login/parol, hisob puli, jo'natuvchi nomi va shablonni tekshiring")
        return 1
    print("Yuborildi (provayder so'rovni qabul qildi). Telefoningizda SMS kelishini tekshiring")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
