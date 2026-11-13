"""Eskiz ulanishini BITTA haqiqiy SMS bilan tekshirish (o'zingizning raqamingizga).

Ishlatish (kalitlar .env dan, chatga yozilmaydi):
    python3 -m app.tools.sms_check 901234567 --env-file ../.env

Eslatma: bu haqiqiy SMS yuboradi va hisobingizdan pul yechiladi. Kod tasodifiy; SMS ni telefoningizda ko'rasiz.
"""
import secrets
import sys

from ..config import Settings
from ..envfile import load_env_file
from ..errors import ConfigError, SmsDeliveryError
from ..modules.auth.sms_factory import build_sms_sender
from ..modules.auth.validators import normalize_phone


def main(argv: list[str]) -> int:
    args = argv[1:]
    env_file = None
    if "--env-file" in args:
        i = args.index("--env-file")
        if i + 1 >= len(args):
            print("--env-file dan keyin fayl yo'li kerak")
            return 2
        env_file = args[i + 1]
        del args[i : i + 2]
    if len(args) != 1:
        print("Ishlatish: python3 -m app.tools.sms_check <telefon, masalan 901234567> [--env-file ../.env]")
        return 2
    phone = normalize_phone(args[0])
    if phone is None:
        print("Telefon raqami noto'g'ri")
        return 2
    if env_file:
        try:
            load_env_file(env_file)
        except OSError:
            print(f".env faylini o'qib bo'lmadi: {env_file}")
            return 2
    try:
        settings = Settings.from_env()
    except ConfigError as e:
        print(f"Sozlama xatosi: {e}")
        return 2
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
