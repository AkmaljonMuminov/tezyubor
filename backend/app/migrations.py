"""Versiyalangan migratsiyalar. Har biri bir marta, tartib bo'yicha, bitta tranzaksiyada qo'llanadi va
`schema_migrations` jadvaliga yoziladi. Eski yozuvlar o'zgartirilmaydi — yangi o'zgarish uchun yangi versiya qo'shiladi.
Asosiy jadvallar (users, refresh_tokens, sms_requests) `db.SCHEMA` da; undan keyingi hamma narsa shu yerda."""

MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "sessiyalar, PIN blok darajasi, OTP challenge va audit jadvallari",
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            id            text PRIMARY KEY,              -- refresh token oilasi (family_id)
            user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            device_label  text NOT NULL DEFAULT '',
            created_at    double precision NOT NULL,
            last_used_at  double precision NOT NULL,
            revoked_at    double precision
        );
        CREATE INDEX IF NOT EXISTS auth_sessions_user_idx ON auth_sessions (user_id);

        -- Eski (migratsiyadan oldin chiqarilgan) refresh oilalari uchun sessiya yozuvi
        INSERT INTO auth_sessions (id, user_id, created_at, last_used_at)
        SELECT DISTINCT ON (family_id) family_id, user_id,
               extract(epoch from now()), extract(epoch from now())
        FROM refresh_tokens
        ON CONFLICT (id) DO NOTHING;

        ALTER TABLE users ADD COLUMN IF NOT EXISTS pin_lock_level integer NOT NULL DEFAULT 0;

        CREATE TABLE IF NOT EXISTS otp_challenges (
            challenge_id  text PRIMARY KEY,
            phone         text NOT NULL,
            code_hash     text NOT NULL,
            expires_at    double precision NOT NULL,
            attempts      integer NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS otp_challenges_expires_idx ON otp_challenges (expires_at);

        CREATE TABLE IF NOT EXISTS audit_log (
            id       bigserial PRIMARY KEY,
            ts       double precision NOT NULL,
            event    text NOT NULL,
            user_id  text,
            fields   jsonb NOT NULL DEFAULT '{}'::jsonb
        );
        CREATE INDEX IF NOT EXISTS audit_log_ts_idx ON audit_log (ts);
        CREATE INDEX IF NOT EXISTS audit_log_user_idx ON audit_log (user_id, ts);
        """,
    ),
]

TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     integer PRIMARY KEY,
    description text NOT NULL,
    applied_at  timestamptz NOT NULL DEFAULT now()
);
"""


def apply_all(conn, extra: list[tuple[int, str, str]] | None = None) -> list[int]:
    """Kutilayotgan migratsiyalarni qo'llaydi; qo'llangan versiyalar ro'yxatini qaytaradi."""
    items = sorted(MIGRATIONS + (extra or []), key=lambda m: m[0])
    if len({m[0] for m in items}) != len(items):
        raise ValueError("migratsiya versiyalari takrorlanmasligi kerak")
    conn.execute(TRACKING_TABLE)
    done = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    applied = []
    for version, description, sql in items:
        if version in done:
            continue
        conn.execute(sql)
        conn.execute("INSERT INTO schema_migrations (version, description) VALUES (%s, %s)", (version, description))
        applied.append(version)
    return applied
