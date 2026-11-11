from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import Settings
from .errors import AppError, ConfigError
from .modules.auth.audit import AuditLog
from .modules.auth.otp import NullSmsSender, OtpService
from .modules.auth.router import build_router
from .modules.auth.service import AuthService
from .modules.auth.stores import MemoryOtpStore, MemoryRefreshStore, MemoryUserStore
from .modules.auth.tokens import TokenService


def create_app(settings: Settings | None = None, sms=None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()
    sms = sms or NullSmsSender()
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
    app = FastAPI(title="Tezyubor API", version="0.1.0")
    app.include_router(build_router(svc, settings.otp_ttl))

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": exc.message, **exc.details}},
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "test_mode": settings.test_mode}

    return app
