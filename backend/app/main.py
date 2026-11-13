from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import Settings
from .errors import AppError, ConfigError, SmsDeliveryError
from .modules.auth.audit import AuditLog
from .modules.auth.otp import OtpService
from .modules.auth.router import build_router
from .modules.auth.service import AuthService
from .modules.auth.sms_factory import build_sms_sender
from .modules.auth.stores import MemoryOtpStore, MemoryRefreshStore, MemoryUserStore
from .modules.auth.tokens import TokenService


def create_app(settings: Settings | None = None, sms=None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()
    sms = sms or build_sms_sender(settings)
    if not settings.test_mode and not getattr(sms, "is_real", False):
        raise ConfigError("Production uchun haqiqiy SMS provayder kerak (hozircha ulanmagan)")

    # 1-bosqich: xotirada saqlash (restartda yo'qoladi). Keyingi bosqich: Redis + PostgreSQL.
    svc = AuthService(
        settings,
        OtpService(settings, MemoryOtpStore(), sms),
        TokenService(settings, MemoryRefreshStore()),
        MemoryUserStore(),
        AuditLog(),
    )
    # Productionda API hujjati (/docs, /openapi.json) yopiq: tashqaridan tuzilma ko'rinmasin.
    docs = {} if settings.test_mode else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(title="Tezyubor API", version="0.1.0", **docs)
    app.include_router(build_router(svc, settings.otp_ttl))

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        message = exc.message
        if isinstance(exc, SmsDeliveryError):
            # Provayder xabarida ichki tafsilot bo'lishi mumkin — foydalanuvchiga faqat umumiy matn.
            message = "SMS yuborib bo'lmadi. Birozdan keyin qayta urinib ko'ring"
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": message, **exc.details}},
        )

    @app.exception_handler(RequestValidationError)
    async def _bad_request(_: Request, __: RequestValidationError):
        # FastAPI standart 422 javobi maydon tafsilotini qaytaradi; biz yagona formatda, tafsilotsiz qaytaramiz.
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Ma'lumot noto'g'ri"}},
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "test_mode": settings.test_mode}

    return app
