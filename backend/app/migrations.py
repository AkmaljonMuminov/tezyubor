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
    (
        2,
        "hamyon (sandbox): kartalar, o'tkazmalar, jurnal, karta qidiruv limiti",
        """
        CREATE TABLE IF NOT EXISTS cards (
            id          uuid PRIMARY KEY,
            user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            pan_index   text NOT NULL,                 -- HMAC(PAN). PAN va CVV bazada SAQLANMAYDI
            bin6        text NOT NULL,
            last4       text NOT NULL,
            brand       text NOT NULL,
            holder_name text NOT NULL,
            exp_month   smallint NOT NULL,
            exp_year    smallint NOT NULL,
            balance     bigint NOT NULL DEFAULT 0 CHECK (balance >= 0),   -- tiyin, SANDBOX
            is_default  boolean NOT NULL DEFAULT false,
            status      text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deleted')),
            created_at  double precision NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS cards_pan_index_uq ON cards (pan_index);
        CREATE INDEX IF NOT EXISTS cards_user_idx ON cards (user_id, status);

        CREATE TABLE IF NOT EXISTS transfers (
            id                   uuid PRIMARY KEY,
            user_id              uuid NOT NULL REFERENCES users(id),
            to_user_id           uuid NOT NULL REFERENCES users(id),
            from_card_id         uuid NOT NULL REFERENCES cards(id),
            to_card_id           uuid NOT NULL REFERENCES cards(id),
            amount               bigint NOT NULL CHECK (amount > 0),
            fee                  bigint NOT NULL CHECK (fee >= 0),
            status               text NOT NULL CHECK (status IN ('pending','completed','failed','expired','cancelled')),
            idempotency_key      text NOT NULL,
            request_hash         text NOT NULL,
            receiver_last4       text NOT NULL,
            receiver_name_masked text NOT NULL,
            created_at           double precision NOT NULL,
            expires_at           double precision NOT NULL,
            completed_at         double precision,
            receipt_no           text UNIQUE,
            failure_reason       text,
            UNIQUE (user_id, idempotency_key)
        );
        CREATE INDEX IF NOT EXISTS transfers_user_created_idx ON transfers (user_id, created_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS transfers_to_user_idx ON transfers (to_user_id, created_at DESC, id DESC);

        -- Faqat qo'shiladi. Har kartaning balansi = jurnal yig'indisi (tekshiruv: tests/test_wallet_store.py)
        CREATE TABLE IF NOT EXISTS ledger_entries (
            id          bigserial PRIMARY KEY,
            card_id     uuid NOT NULL REFERENCES cards(id),
            transfer_id uuid REFERENCES transfers(id),
            delta       bigint NOT NULL,
            kind        text NOT NULL,
            ts          double precision NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ledger_card_idx ON ledger_entries (card_id);

        CREATE TABLE IF NOT EXISTS card_lookups (
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            ts      double precision NOT NULL
        );
        CREATE INDEX IF NOT EXISTS card_lookups_user_idx ON card_lookups (user_id, ts);
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
