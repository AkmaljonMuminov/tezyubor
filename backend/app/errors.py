"""Yagona xatolik modeli: har xato barqaror `code` va HTTP status'ga ega."""


class AppError(Exception):
    http_status = 400
    code = "APP_ERROR"

    def __init__(self, message: str | None = None, **details):
        self.message = message or self.code
        self.details = details
        super().__init__(self.message)


class ConfigError(Exception):
    """Noto'g'ri sozlama — ilova ishga tushmasligi kerak."""


class ValidationError(AppError):
    http_status = 422
    code = "VALIDATION_ERROR"


class OtpRateLimited(AppError):
    http_status = 429
    code = "OTP_RATE_LIMITED"


class OtpInvalid(AppError):
    http_status = 400
    code = "OTP_INVALID"


class OtpExpired(AppError):
    http_status = 400
    code = "OTP_EXPIRED"


class OtpLocked(AppError):
    http_status = 429
    code = "OTP_LOCKED"


class PinLocked(AppError):
    http_status = 423
    code = "PIN_LOCKED"


class PinInvalid(AppError):
    http_status = 401
    code = "PIN_INVALID"


class PinAlreadySet(AppError):
    http_status = 409
    code = "PIN_ALREADY_SET"


class PinNotSet(AppError):
    http_status = 409
    code = "PIN_NOT_SET"


class TokenInvalid(AppError):
    http_status = 401
    code = "TOKEN_INVALID"


class TokenReuseDetected(AppError):
    http_status = 401
    code = "TOKEN_REUSE_DETECTED"
