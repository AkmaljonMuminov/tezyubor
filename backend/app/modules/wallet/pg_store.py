"""PostgreSQL hamyon saqlash. Pul harakati bitta tranzaksiyada: avval foydalanuvchi qatori, keyin kartalar (id tartibida)
`FOR UPDATE` bilan qulflanadi — parallel tasdiqlashlar navbat bilan bajariladi va o'zaro qulflanib qolmaydi.
Holatni o'zgartirib xato ko'taradigan yo'llarda (`expired`, `failed`) avval tranzaksiya yopiladi (commit), keyin xato ko'tariladi,
aks holda rollback holat o'zgarishini ham bekor qilar edi."""
import uuid

from ...db import Database
from ...errors import (
    CardUnavailable,
    DailyLimitExceeded,
    InsufficientFunds,
    TransferExpired,
    TransferNotFound,
    TransferNotPending,
)
from .models import Card, Transfer
from .store import new_receipt_no

_U = uuid.UUID


def _card(r) -> Card:
    return Card(
        id=str(r["id"]), user_id=str(r["user_id"]), pan_index=r["pan_index"], bin6=r["bin6"], last4=r["last4"],
        brand=r["brand"], holder_name=r["holder_name"], exp_month=r["exp_month"], exp_year=r["exp_year"],
        balance=r["balance"], is_default=r["is_default"], status=r["status"], created_at=r["created_at"],
    )


def _transfer(r) -> Transfer:
    return Transfer(
        id=str(r["id"]), user_id=str(r["user_id"]), to_user_id=str(r["to_user_id"]),
        from_card_id=str(r["from_card_id"]), to_card_id=str(r["to_card_id"]), amount=r["amount"], fee=r["fee"],
        status=r["status"], idempotency_key=r["idempotency_key"], request_hash=r["request_hash"],
        receiver_last4=r["receiver_last4"], receiver_name_masked=r["receiver_name_masked"],
        created_at=r["created_at"], expires_at=r["expires_at"], completed_at=r["completed_at"],
        receipt_no=r["receipt_no"], failure_reason=r["failure_reason"],
    )


class PgWalletStore:
    def __init__(self, db: Database):
        self._db = db

    # --- kartalar ---
    def add_card(self, card, bonus, now):
        with self._db.connection() as c:
            c.execute("SELECT 1 FROM users WHERE id = %s FOR UPDATE", (_U(card.user_id),))  # foydalanuvchi bo'yicha navbat
            ex = c.execute("SELECT * FROM cards WHERE pan_index = %s FOR UPDATE", (card.pan_index,)).fetchone()
            has_default = c.execute(
                "SELECT 1 AS ok FROM cards WHERE user_id = %s AND status = 'active' AND is_default",
                (_U(card.user_id),),
            ).fetchone() is not None
            if ex is not None:
                if ex["status"] == "active" or str(ex["user_id"]) != card.user_id:
                    raise CardUnavailable("Bu kartani qo'shib bo'lmaydi")
                r = c.execute(
                    "UPDATE cards SET status = 'active', is_default = %s, holder_name = %s, exp_month = %s, exp_year = %s "
                    "WHERE id = %s RETURNING *",
                    (not has_default, card.holder_name, card.exp_month, card.exp_year, ex["id"]),
                ).fetchone()
                return _card(r)
            r = c.execute(
                "INSERT INTO cards (id, user_id, pan_index, bin6, last4, brand, holder_name, exp_month, exp_year, "
                "balance, is_default, status, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',%s) RETURNING *",
                (_U(card.id), _U(card.user_id), card.pan_index, card.bin6, card.last4, card.brand, card.holder_name,
                 card.exp_month, card.exp_year, bonus, not has_default, card.created_at),
            ).fetchone()
            if bonus:
                c.execute(
                    "INSERT INTO ledger_entries (card_id, delta, kind, ts) VALUES (%s, %s, 'sandbox_topup', %s)",
                    (_U(card.id), bonus, now),
                )
            return _card(r)

    def get_card(self, card_id):
        try:
            cid = _U(card_id)
        except (ValueError, AttributeError, TypeError):
            return None
        with self._db.connection() as c:
            r = c.execute("SELECT * FROM cards WHERE id = %s", (cid,)).fetchone()
        return _card(r) if r else None

    def list_cards(self, user_id):
        with self._db.connection() as c:
            rows = c.execute(
                "SELECT * FROM cards WHERE user_id = %s AND status = 'active' ORDER BY (NOT is_default), created_at, id",
                (_U(user_id),),
            ).fetchall()
        return [_card(r) for r in rows]

    def find_active_by_index(self, pan_index):
        with self._db.connection() as c:
            r = c.execute("SELECT * FROM cards WHERE pan_index = %s AND status = 'active'", (pan_index,)).fetchone()
        return _card(r) if r else None

    def soft_delete_card(self, card_id, user_id):
        try:
            cid = _U(card_id)
        except (ValueError, AttributeError, TypeError):
            return False
        with self._db.connection() as c:
            r = c.execute(
                "SELECT is_default FROM cards WHERE id = %s AND user_id = %s AND status = 'active' FOR UPDATE",
                (cid, _U(user_id)),
            ).fetchone()
            if r is None:
                return False
            c.execute("UPDATE cards SET status = 'deleted', is_default = false WHERE id = %s", (cid,))
            if r["is_default"]:
                c.execute(
                    "UPDATE cards SET is_default = true WHERE id = (SELECT id FROM cards WHERE user_id = %s "
                    "AND status = 'active' ORDER BY created_at, id LIMIT 1)",
                    (_U(user_id),),
                )
            return True

    def set_default(self, card_id, user_id):
        try:
            cid = _U(card_id)
        except (ValueError, AttributeError, TypeError):
            return False
        with self._db.connection() as c:
            ok = c.execute(
                "SELECT 1 AS ok FROM cards WHERE id = %s AND user_id = %s AND status = 'active' FOR UPDATE",
                (cid, _U(user_id)),
            ).fetchone()
            if ok is None:
                return False
            c.execute("UPDATE cards SET is_default = (id = %s) WHERE user_id = %s AND status = 'active'", (cid, _U(user_id)))
            return True

    def allow_lookup(self, user_id, now, window, max_count):
        with self._db.connection() as c:
            c.execute("SELECT 1 FROM users WHERE id = %s FOR UPDATE", (_U(user_id),))
            n = c.execute(
                "SELECT count(*) AS n FROM card_lookups WHERE user_id = %s AND ts > %s", (_U(user_id), now - window)
            ).fetchone()["n"]
            if n >= max_count:
                return False
            c.execute("INSERT INTO card_lookups (user_id, ts) VALUES (%s, %s)", (_U(user_id), now))
            c.execute("DELETE FROM card_lookups WHERE user_id = %s AND ts <= %s", (_U(user_id), now - window))
            return True

    # --- o'tkazmalar ---
    def create_transfer(self, t):
        with self._db.connection() as c:
            r = c.execute(
                "INSERT INTO transfers (id, user_id, to_user_id, from_card_id, to_card_id, amount, fee, status, "
                "idempotency_key, request_hash, receiver_last4, receiver_name_masked, created_at, expires_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (user_id, idempotency_key) DO NOTHING RETURNING *",
                (_U(t.id), _U(t.user_id), _U(t.to_user_id), _U(t.from_card_id), _U(t.to_card_id), t.amount, t.fee,
                 t.status, t.idempotency_key, t.request_hash, t.receiver_last4, t.receiver_name_masked, t.created_at,
                 t.expires_at),
            ).fetchone()
            if r is None:  # bir vaqtda ikkinchi so'rov allaqachon yaratgan
                r = c.execute(
                    "SELECT * FROM transfers WHERE user_id = %s AND idempotency_key = %s",
                    (_U(t.user_id), t.idempotency_key),
                ).fetchone()
            return _transfer(r)

    def get_transfer(self, transfer_id):
        try:
            tid = _U(transfer_id)
        except (ValueError, AttributeError, TypeError):
            return None
        with self._db.connection() as c:
            r = c.execute("SELECT * FROM transfers WHERE id = %s", (tid,)).fetchone()
        return _transfer(r) if r else None

    def get_transfer_by_key(self, user_id, key):
        with self._db.connection() as c:
            r = c.execute(
                "SELECT * FROM transfers WHERE user_id = %s AND idempotency_key = %s", (_U(user_id), key)
            ).fetchone()
        return _transfer(r) if r else None

    def execute_transfer(self, transfer_id, user_id, now, day_start, daily_limit):
        try:
            tid = _U(transfer_id)
        except (ValueError, AttributeError, TypeError):
            raise TransferNotFound("O'tkazma topilmadi") from None
        outcome, result = None, None
        with self._db.connection() as c:
            # 1) foydalanuvchi qatori: shu foydalanuvchining tasdiqlashlari (va kunlik limit hisobi) navbat bilan
            c.execute("SELECT 1 FROM users WHERE id = %s FOR UPDATE", (_U(user_id),))
            r = c.execute("SELECT * FROM transfers WHERE id = %s AND user_id = %s FOR UPDATE", (tid, _U(user_id))).fetchone()
            if r is None:
                raise TransferNotFound("O'tkazma topilmadi")
            t = _transfer(r)
            if t.status == "completed":
                return t
            if t.status != "pending":
                raise TransferNotPending("O'tkazma tasdiqlash holatida emas")
            if now >= t.expires_at:
                c.execute("UPDATE transfers SET status = 'expired' WHERE id = %s", (tid,))
                outcome = "expired"
            else:
                # 2) kartalar id tartibida qulflanadi (deadlock'siz)
                ids = sorted({_U(t.from_card_id), _U(t.to_card_id)}, key=str)
                rows = {
                    str(x["id"]): x
                    for x in c.execute("SELECT * FROM cards WHERE id = ANY(%s) ORDER BY id FOR UPDATE", (ids,)).fetchall()
                }
                src, dst = rows.get(t.from_card_id), rows.get(t.to_card_id)
                total = t.amount + t.fee
                if src is None or dst is None or src["status"] != "active" or dst["status"] != "active":
                    c.execute("UPDATE transfers SET status='failed', failure_reason='card_unavailable' WHERE id = %s", (tid,))
                    outcome = "card"
                else:
                    sent = c.execute(
                        "SELECT COALESCE(SUM(amount), 0) AS s FROM transfers "
                        "WHERE user_id = %s AND status = 'completed' AND completed_at >= %s",
                        (_U(user_id), day_start),
                    ).fetchone()["s"]
                    if sent + t.amount > daily_limit:
                        outcome = "limit"
                    elif src["balance"] < total:
                        c.execute("UPDATE transfers SET status='failed', failure_reason='insufficient_funds' WHERE id = %s", (tid,))
                        outcome = "funds"
                    else:
                        c.execute("UPDATE cards SET balance = balance - %s WHERE id = %s", (total, src["id"]))
                        c.execute("UPDATE cards SET balance = balance + %s WHERE id = %s", (t.amount, dst["id"]))
                        c.execute(
                            "INSERT INTO ledger_entries (card_id, transfer_id, delta, kind, ts) VALUES "
                            "(%s,%s,%s,'transfer_out',%s), (%s,%s,%s,'transfer_in',%s)",
                            (src["id"], tid, -t.amount, now, dst["id"], tid, t.amount, now),
                        )
                        if t.fee:
                            c.execute(
                                "INSERT INTO ledger_entries (card_id, transfer_id, delta, kind, ts) VALUES (%s,%s,%s,'fee',%s)",
                                (src["id"], tid, -t.fee, now),
                            )
                        r2 = c.execute(
                            "UPDATE transfers SET status='completed', completed_at=%s, receipt_no=%s WHERE id=%s RETURNING *",
                            (now, new_receipt_no(), tid),
                        ).fetchone()
                        outcome, result = "ok", _transfer(r2)
        # Tranzaksiya yopildi (holat yozildi) — endi xato ko'tarish xavfsiz
        if outcome == "ok":
            return result
        raise {
            "expired": TransferExpired("O'tkazma tasdiqlash muddati tugagan"),
            "card": CardUnavailable("Karta mavjud emas"),
            "limit": DailyLimitExceeded("Kunlik limit oshib ketadi"),
            "funds": InsufficientFunds("Mablag' yetarli emas"),
        }[outcome]

    def cancel_transfer(self, transfer_id, user_id):
        try:
            tid = _U(transfer_id)
        except (ValueError, AttributeError, TypeError):
            raise TransferNotFound("O'tkazma topilmadi") from None
        with self._db.connection() as c:
            r = c.execute("SELECT * FROM transfers WHERE id = %s AND user_id = %s FOR UPDATE", (tid, _U(user_id))).fetchone()
            if r is None:
                raise TransferNotFound("O'tkazma topilmadi")
            if r["status"] == "cancelled":
                return _transfer(r)
            if r["status"] != "pending":
                raise TransferNotPending("O'tkazma tasdiqlash holatida emas")
            return _transfer(c.execute("UPDATE transfers SET status='cancelled' WHERE id = %s RETURNING *", (tid,)).fetchone())

    def list_history(self, user_id, limit, before, status, direction):
        uid = _U(user_id)
        where = ["((user_id = %(u)s) OR (to_user_id = %(u)s AND status = 'completed'))"]
        params: dict = {"u": uid, "lim": limit}
        if direction == "sent":
            where.append("user_id = %(u)s")
        elif direction == "received":
            where.append("to_user_id = %(u)s AND user_id <> %(u)s")
        if status:
            where.append("status = %(st)s")
            params["st"] = status
        if before is not None:
            where.append("(created_at, id) < (%(ca)s, %(bid)s)")
            params["ca"], params["bid"] = before[0], _U(before[1])
        sql = "SELECT * FROM transfers WHERE " + " AND ".join(where) + " ORDER BY created_at DESC, id DESC LIMIT %(lim)s"
        with self._db.connection() as c:
            return [_transfer(r) for r in c.execute(sql, params).fetchall()]

    def ledger_sum(self, card_id):
        with self._db.connection() as c:
            return int(c.execute("SELECT COALESCE(SUM(delta), 0) AS s FROM ledger_entries WHERE card_id = %s", (_U(card_id),)).fetchone()["s"])
