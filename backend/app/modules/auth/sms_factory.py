from ...config import Settings
from .eskiz import EskizSmsSender
from .otp import NullSmsSender


def build_sms_sender(settings: Settings):
    """Sozlamaga qarab SMS yuboruvchini tanlaydi. `none` — yuboruvchi yo'q (productionda main.py rad etadi)."""
    if settings.sms_provider == "eskiz":
        return EskizSmsSender(settings.eskiz_email, settings.eskiz_password, settings.eskiz_from)
    return NullSmsSender()
