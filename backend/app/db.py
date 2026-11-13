"""PostgreSQL ulanishi (psycopg 3 + connection pool) va sxema. psycopg faqat DATABASE_URL berilganda import qilinadi,
shuning uchun bazasiz ishlatishda (test/dev) o'rnatilgan bo'lishi shart emas."""
from .errors import ConfigError

# Sxema idempotent (IF NOT EXISTS): har ishga tushishda xavfsiz ishlaydi. Vaqtlar — epoch soniya (float),
# kodning qolgan qismidagi `clock()` bilan bir xil.
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id                uuid PRIMARY KEY,
    phone             text NOT NULL UNIQUE,
    pin_hash          text,
    pin_failures      integer NOT NULL DEFAULT 0,
    pin_locked_until  double precision NOT NULL DEFAULT 0,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_hash  text PRIMARY KEY,
    user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    family_id   text NOT NULL,
    expires_at  double precision NOT NULL,
    used        boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS refresh_tokens_family_idx ON refresh_tokens (family_id);
CREATE INDEX IF NOT EXISTS refresh_tokens_expires_idx ON refresh_tokens (expires_at);

CREATE TABLE IF NOT EXISTS sms_requests (
    id     bigserial PRIMARY KEY,
    phone  text NOT NULL,
    ts     double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS sms_requests_phone_ts_idx ON sms_requests (phone, ts);
"""

_MIGRATION_LOCK = 727001  # bir nechta nusxa bir vaqtda ishga tushsa, sxema navbat bilan yaratiladi


class Database:
    def __init__(self, url: str, max_size: int = 5):
        if not url.startswith(("postgres://", "postgresql://")):
            raise ConfigError("DATABASE_URL postgres:// yoki postgresql:// bilan boshlanishi kerak")
        try:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool
        except ImportError:
            raise ConfigError("DATABASE_URL uchun 'psycopg[binary,pool]' o'rnatilishi kerak") from None
        self._pool = ConnectionPool(
            url, min_size=1, max_size=max_size, timeout=10, open=True, kwargs={"row_factory": dict_row}
        )

    def connection(self):
        """`with db.connection() as conn:` — blok tugaganda commit, xatoda rollback."""
        return self._pool.connection()

    def migrate(self) -> None:
        with self._pool.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK,))
            conn.execute(SCHEMA)

    def close(self) -> None:
        self._pool.close()
