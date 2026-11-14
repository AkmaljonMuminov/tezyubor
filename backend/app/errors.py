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


class SmsDeliveryError(AppError):
    """SMS provayder xatosi (ulanish, avtorizatsiya, hisob bo'sh va h.k.). Tafsilot foydalanuvchiga ko'rsatilmaydi."""

    http_status = 502
    code = "SMS_DELIVERY_FAILED"


class SessionNotFound(AppError):
    http_status = 404
    code = "SESSION_NOT_FOUND"


# --- Hamyon (sandbox) ---
class CardInvalid(AppError):
    http_status = 422
    code = "CARD_INVALID"


class CardNotFound(AppError):
    http_status = 404
    code = "CARD_NOT_FOUND"


class CardUnavailable(AppError):
    """Karta qo'shib bo'lmaydi (band yoki boshqa sabab). Sababi ataylab aytilmaydi: karta raqamlarini taxmin qilishga yo'l bermaslik."""

    http_status = 409
    code = "CARD_UNAVAILABLE"


class CardLimitReached(AppError):
    http_status = 409
    code = "CARD_LIMIT_REACHED"


class ReceiverNotFound(AppError):
    http_status = 404
    code = "RECEIVER_NOT_FOUND"


class SameCard(AppError):
    http_status = 422
    code = "SAME_CARD"


class AmountOutOfRange(AppError):
    http_status = 422
    code = "AMOUNT_OUT_OF_RANGE"


class InsufficientFunds(AppError):
    http_status = 409
    code = "INSUFFICIENT_FUNDS"


class DailyLimitExceeded(AppError):
    http_status = 409
    code = "DAILY_LIMIT_EXCEEDED"


class TransferNotFound(AppError):
    http_status = 404
    code = "TRANSFER_NOT_FOUND"


class TransferNotPending(AppError):
    http_status = 409
    code = "TRANSFER_NOT_PENDING"


class TransferExpired(AppError):
    http_status = 409
    code = "TRANSFER_EXPIRED"


class IdempotencyKeyInvalid(AppError):
    http_status = 422
    code = "IDEMPOTENCY_KEY_INVALID"


class IdempotencyConflict(AppError):
    http_status = 409
    code = "IDEMPOTENCY_CONFLICT"


class WalletRateLimited(AppError):
    http_status = 429
    code = "WALLET_RATE_LIMITED"
