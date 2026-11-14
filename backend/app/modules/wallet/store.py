"""Hamyon saqlash qatlami. Pul harakati (`execute_transfer`) BITTA atomik amal: qulflash, tekshirish, yechish, qo'shish,
jurnal yozuvi va holat o'zgarishi birga bajariladi yoki umuman bajarilmaydi. Xotira va PostgreSQL implementatsiyalari
bir xil shartnomadan o'tadi (tests/test_wallet_store.py)."""
import secrets
import threading
from dataclasses import replace
from typing import Protocol

from ...errors import (
    CardUnavailable,
    DailyLimitExceeded,
    InsufficientFunds,
    TransferExpired,
    TransferNotFound,
    TransferNotPending,
)
from .models import Card, Transfer


def new_receipt_no() -> str:
    return "TZ-" + secrets.token_hex(5).upper()


class WalletStore(Protocol):
    def add_card(self, card: Card, bonus: int, now: float) -> Card: ...          # CardUnavailable
    def get_card(self, card_id: str) -> Card | None: ...
    def list_cards(self, user_id: str) -> list[Card]: ...
    def find_active_by_index(self, pan_index: str) -> Card | None: ...
    def soft_delete_card(self, card_id: str, user_id: str) -> bool: ...
    def set_default(self, card_id: str, user_id: str) -> bool: ...
    def allow_lookup(self, user_id: str, now: float, window: int, max_count: int) -> bool: ...
    def create_transfer(self, t: Transfer) -> Transfer: ...                        # (user_id, key) bo'yicha idempotent
    def get_transfer(self, transfer_id: str) -> Transfer | None: ...
    def get_transfer_by_key(self, user_id: str, key: str) -> Transfer | None: ...
    def execute_transfer(
        self, transfer_id: str, user_id: str, now: float, day_start: float, daily_limit: int
    ) -> Transfer: ...
    def cancel_transfer(self, transfer_id: str, user_id: str) -> Transfer: ...
    def list_history(
        self, user_id: str, limit: int, before: tuple[float, str] | None, status: str | None, direction: str | None
    ) -> list[Transfer]: ...
    def ledger_sum(self, card_id: str) -> int: ...


class MemoryWalletStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._cards: dict[str, Card] = {}
        self._transfers: dict[str, Transfer] = {}
        self._keys: dict[tuple[str, str], str] = {}
        self._ledger: list[tuple[str, int]] = []
        self._lookups: dict[str, list[float]] = {}

    # --- kartalar ---
    def add_card(self, card, bonus, now):
        with self._lock:
            existing = next((c for c in self._cards.values() if c.pan_index == card.pan_index), None)
            if existing is not None:
                # Faol karta yoki boshqa odamning (o'chirilgan) kartasi — qo'shib bo'lmaydi. O'zining o'chirilganini qayta yoqish
                # mumkin, lekin yangi sovg'a balans BERILMAYDI (cheksiz test pul olishning oldini oladi).
                if existing.status == "active" or existing.user_id != card.user_id:
                    raise CardUnavailable("Bu kartani qo'shib bo'lmaydi")
                has_default = any(
                    c.is_default and c.status == "active" and c.user_id == card.user_id for c in self._cards.values()
                )
                existing.holder_name, existing.exp_month, existing.exp_year = (
                    card.holder_name,
                    card.exp_month,
                    card.exp_year,
                )
                existing.status, existing.is_default = "active", not has_default
                return replace(existing)
            has_default = any(c.is_default and c.status == "active" and c.user_id == card.user_id for c in self._cards.values())
            card = replace(card, balance=bonus, is_default=not has_default)
            self._cards[card.id] = card
            if bonus:
                self._ledger.append((card.id, bonus))
            return replace(card)

    def get_card(self, card_id):
        c = self._cards.get(card_id)
        return replace(c) if c else None

    def list_cards(self, user_id):
        rows = [c for c in self._cards.values() if c.user_id == user_id and c.status == "active"]
        rows.sort(key=lambda c: (not c.is_default, c.created_at, c.id))
        return [replace(c) for c in rows]

    def find_active_by_index(self, pan_index):
        c = next((c for c in self._cards.values() if c.pan_index == pan_index and c.status == "active"), None)
        return replace(c) if c else None

    def soft_delete_card(self, card_id, user_id):
        with self._lock:
            c = self._cards.get(card_id)
            if c is None or c.user_id != user_id or c.status != "active":
                return False
            c.status, was_default, c.is_default = "deleted", c.is_default, False
            if was_default:
                nxt = sorted(
                    (x for x in self._cards.values() if x.user_id == user_id and x.status == "active"),
                    key=lambda x: (x.created_at, x.id),
                )
                if nxt:
                    nxt[0].is_default = True
            return True

    def set_default(self, card_id, user_id):
        with self._lock:
            c = self._cards.get(card_id)
            if c is None or c.user_id != user_id or c.status != "active":
                return False
            for x in self._cards.values():
                if x.user_id == user_id:
                    x.is_default = x.id == card_id
            return True

    def allow_lookup(self, user_id, now, window, max_count):
        with self._lock:
            times = [t for t in self._lookups.get(user_id, []) if now - t < window]
            if len(times) >= max_count:
                self._lookups[user_id] = times
                return False
            times.append(now)
            self._lookups[user_id] = times
            return True

    # --- o'tkazmalar ---
    def create_transfer(self, t):
        with self._lock:
            existing_id = self._keys.get((t.user_id, t.idempotency_key))
            if existing_id is not None:
                return replace(self._transfers[existing_id])
            self._transfers[t.id] = replace(t)
            self._keys[(t.user_id, t.idempotency_key)] = t.id
            return replace(t)

    def get_transfer(self, transfer_id):
        t = self._transfers.get(transfer_id)
        return replace(t) if t else None

    def get_transfer_by_key(self, user_id, key):
        tid = self._keys.get((user_id, key))
        return replace(self._transfers[tid]) if tid else None

    def execute_transfer(self, transfer_id, user_id, now, day_start, daily_limit):
        with self._lock:
            t = self._transfers.get(transfer_id)
            if t is None or t.user_id != user_id:
                raise TransferNotFound("O'tkazma topilmadi")
            if t.status == "completed":
                return replace(t)
            if t.status != "pending":
                raise TransferNotPending("O'tkazma tasdiqlash holatida emas")
            if now >= t.expires_at:
                t.status = "expired"
                raise TransferExpired("O'tkazma tasdiqlash muddati tugagan")
            src, dst = self._cards.get(t.from_card_id), self._cards.get(t.to_card_id)
            if src is None or dst is None or src.status != "active" or dst.status != "active":
                t.status, t.failure_reason = "failed", "card_unavailable"
                raise CardUnavailable("Karta mavjud emas")
            total = t.amount + t.fee
            sent = sum(
                x.amount
                for x in self._transfers.values()
                if x.user_id == user_id and x.status == "completed" and (x.completed_at or 0) >= day_start
            )
            if sent + t.amount > daily_limit:
                raise DailyLimitExceeded("Kunlik limit oshib ketadi")
            if src.balance < total:
                t.status, t.failure_reason = "failed", "insufficient_funds"
                raise InsufficientFunds("Mablag' yetarli emas")
            src.balance -= total
            dst.balance += t.amount
            self._ledger += [(src.id, -t.amount), (dst.id, t.amount)]
            if t.fee:
                self._ledger.append((src.id, -t.fee))
            t.status, t.completed_at, t.receipt_no = "completed", now, new_receipt_no()
            return replace(t)

    def cancel_transfer(self, transfer_id, user_id):
        with self._lock:
            t = self._transfers.get(transfer_id)
            if t is None or t.user_id != user_id:
                raise TransferNotFound("O'tkazma topilmadi")
            if t.status == "cancelled":
                return replace(t)
            if t.status != "pending":
                raise TransferNotPending("O'tkazma tasdiqlash holatida emas")
            t.status = "cancelled"
            return replace(t)

    def list_history(self, user_id, limit, before, status, direction):
        rows = []
        for t in self._transfers.values():
            sent = t.user_id == user_id
            received = t.to_user_id == user_id and t.status == "completed"
            if not (sent or received):
                continue
            if direction == "sent" and not sent:
                continue
            if direction == "received" and not (received and not sent):
                continue
            if status and t.status != status:
                continue
            if before is not None and (t.created_at, t.id) >= before:
                continue
            rows.append(t)
        rows.sort(key=lambda t: (t.created_at, t.id), reverse=True)
        return [replace(t) for t in rows[:limit]]

    def ledger_sum(self, card_id):
        return sum(d for cid, d in self._ledger if cid == card_id)
