"""Hamyon biznes mantiqi (SANDBOX). Qoidalar:
- barcha pul hisob-kitobi serverda: klient faqat summani yuboradi, komissiya va jami serverda hisoblanadi;
- PAN saqlanmaydi (faqat BIN6 + last4 + HMAC indeks), CVV umuman olinmaydi, log/audit'ga karta raqami yozilmaydi;
- o'tkazma ikki bosqichli: yaratish (taklif/quote) -> PIN bilan tasdiqlash (PIN serverda tekshiriladi, blok qoidalari bilan);
- takroriy so'rov (Idempotency-Key) ikki marta yechmaydi;
- chek faqat serverda tasdiqlangan (completed) o'tkazma uchun beriladi."""
import base64
import hashlib
import hmac
import time
import uuid
from typing import Callable

from ...config import Settings
from ...errors import (
    AmountOutOfRange,
    CardInvalid,
    CardLimitReached,
    CardNotFound,
    IdempotencyConflict,
    IdempotencyKeyInvalid,
    InsufficientFunds,
    ReceiverNotFound,
    SameCard,
    TransferNotFound,
    ValidationError,
    WalletRateLimited,
)
from ..auth.audit import AuditLog
from .models import Card, Transfer
from .store import WalletStore
from .validators import (
    card_brand,
    clean_holder_name,
    mask_name,
    mask_pan,
    normalize_pan,
    normalize_year,
    valid_expiry,
    valid_idempotency_key,
)

MAX_CARDS = 5
LOOKUP_WINDOW = 60
LOOKUP_MAX = 10
MAX_PAGE = 50
_STATUSES = ("pending", "completed", "failed", "expired", "cancelled")

PinCheck = Callable[[str, str, str], None]


class WalletService:
    def __init__(
        self,
        settings: Settings,
        store: WalletStore,
        pin_check: PinCheck,
        audit: AuditLog,
        clock: Callable[[], float] = time.time,
    ):
        self._s = settings
        self._store = store
        self._pin_check = pin_check
        self._audit = audit
        self._clock = clock

    # --- yordamchilar ---
    def _index(self, pan: str) -> str:
        return hmac.new(self._s.card_index_key.encode(), pan.encode(), hashlib.sha256).hexdigest()

    def _throttle(self, user_id: str) -> None:
        """Karta raqamlarini ketma-ket sinab ko'rishga (enumeration) qarshi: qidiruv/qo'shish/o'tkazma uchun umumiy limit."""
        if not self._store.allow_lookup(user_id, self._clock(), LOOKUP_WINDOW, LOOKUP_MAX):
            self._audit.record("wallet_throttled", user_id=user_id)
            raise WalletRateLimited("Juda ko'p urinish. Birozdan keyin qayta urinib ko'ring", retry_after=LOOKUP_WINDOW)

    def compute_fee(self, amount: int) -> int:
        bps, min_fee = self._s.transfer_fee_bps, self._s.transfer_fee_min_tiyin
        if not bps and not min_fee:
            return 0
        return max(-(-amount * bps // 10000), min_fee)

    @staticmethod
    def card_view(c: Card) -> dict:
        return {
            "id": c.id,
            "masked_pan": mask_pan(c.bin6, c.last4),
            "last4": c.last4,
            "brand": c.brand,
            "holder_name": c.holder_name,
            "exp_month": c.exp_month,
            "exp_year": c.exp_year,
            "balance_tiyin": c.balance,
            "is_default": c.is_default,
            "sandbox": True,
        }

    def _own_active_card(self, user_id: str, card_id: str) -> Card:
        c = self._store.get_card(card_id)
        # Begona yoki o'chirilgan karta uchun bir xil javob: boshqaning kartasi bor-yo'qligi ma'lum bo'lmasin
        if c is None or c.user_id != user_id or c.status != "active":
            raise CardNotFound("Karta topilmadi")
        return c

    # --- kartalar ---
    def add_card(self, user_id: str, pan: str, exp_month: int, exp_year: int, holder_name: str) -> dict:
        self._throttle(user_id)
        norm = normalize_pan(pan)
        name = clean_holder_name(holder_name)
        now = self._clock()
        if norm is None or name is None or not valid_expiry(exp_month, exp_year, now):
            raise CardInvalid("Karta ma'lumotlari noto'g'ri")
        if len(self._store.list_cards(user_id)) >= MAX_CARDS:
            raise CardLimitReached("Kartalar soni chegaraga yetdi")
        card = Card(
            id=str(uuid.uuid4()), user_id=user_id, pan_index=self._index(norm), bin6=norm[:6], last4=norm[-4:],
            brand=card_brand(norm), holder_name=name, exp_month=exp_month, exp_year=normalize_year(exp_year),
            balance=0, is_default=False, status="active", created_at=now,
        )
        saved = self._store.add_card(card, self._s.sandbox_start_balance_tiyin, now)
        self._audit.record("card_added", user_id=user_id, card_id=saved.id)
        return self.card_view(saved)

    def list_cards(self, user_id: str) -> list[dict]:
        return [self.card_view(c) for c in self._store.list_cards(user_id)]

    def delete_card(self, user_id: str, card_id: str) -> None:
        if not self._store.soft_delete_card(card_id, user_id):
            raise CardNotFound("Karta topilmadi")
        self._audit.record("card_deleted", user_id=user_id, card_id=card_id)

    def set_default(self, user_id: str, card_id: str) -> None:
        if not self._store.set_default(card_id, user_id):
            raise CardNotFound("Karta topilmadi")

    # --- qabul qiluvchi ---
    def _resolve_receiver(self, user_id: str, pan: str) -> tuple[Card, str]:
        self._throttle(user_id)
        norm = normalize_pan(pan)
        if norm is None:
            raise CardInvalid("Karta raqami noto'g'ri")
        idx = self._index(norm)
        card = self._store.find_active_by_index(idx)
        if card is None:
            raise ReceiverNotFound("Qabul qiluvchi kartasi topilmadi")
        return card, idx

    def lookup_receiver(self, user_id: str, pan: str) -> dict:
        card, _ = self._resolve_receiver(user_id, pan)
        return {
            "masked_pan": mask_pan(card.bin6, card.last4),
            "brand": card.brand,
            "name_masked": mask_name(card.holder_name),
            "sandbox": True,
        }

    # --- o'tkazma ---
    def create_transfer(self, user_id: str, key: str | None, from_card_id: str, receiver_pan: str, amount) -> dict:
        if not valid_idempotency_key(key):
            raise IdempotencyKeyInvalid("Idempotency-Key sarlavhasi kerak (8-64 belgi: harf, raqam, _ yoki -)")
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise ValidationError("Summa butun son (tiyin) bo'lishi kerak")
        if not self._s.transfer_min_tiyin <= amount <= self._s.transfer_max_tiyin:
            raise AmountOutOfRange(
                "Summa ruxsat etilgan oraliqdan tashqarida",
                min_tiyin=self._s.transfer_min_tiyin,
                max_tiyin=self._s.transfer_max_tiyin,
            )
        norm = normalize_pan(receiver_pan)
        if norm is None:
            raise CardInvalid("Karta raqami noto'g'ri")
        req_hash = hashlib.sha256(f"{from_card_id}|{self._index(norm)}|{amount}".encode()).hexdigest()

        existing = self._store.get_transfer_by_key(user_id, key)
        if existing is not None:
            return self._replay(existing, req_hash, user_id)

        src = self._own_active_card(user_id, from_card_id)
        if not valid_expiry(src.exp_month, src.exp_year, self._clock()):
            raise CardInvalid("Karta muddati tugagan")
        dst, _ = self._resolve_receiver(user_id, receiver_pan)
        if dst.id == src.id:
            raise SameCard("Bir xil kartaga o'tkazib bo'lmaydi")
        fee = self.compute_fee(amount)
        if src.balance < amount + fee:
            raise InsufficientFunds("Mablag' yetarli emas")  # dastlabki tekshiruv; yakuniysi tasdiqlashda
        now = self._clock()
        t = Transfer(
            id=str(uuid.uuid4()), user_id=user_id, to_user_id=dst.user_id, from_card_id=src.id, to_card_id=dst.id,
            amount=amount, fee=fee, status="pending", idempotency_key=key, request_hash=req_hash,
            receiver_last4=dst.last4, receiver_name_masked=mask_name(dst.holder_name), created_at=now,
            expires_at=now + self._s.transfer_confirm_ttl,
        )
        saved = self._store.create_transfer(t)
        if saved.id != t.id:  # bir vaqtda ikkinchi so'rov oldin yaratgan
            return self._replay(saved, req_hash, user_id)
        self._audit.record("transfer_created", user_id=user_id, transfer_id=saved.id, amount=amount, fee=fee)
        return self.transfer_view(saved, user_id)

    def _replay(self, existing: Transfer, req_hash: str, user_id: str) -> dict:
        if existing.request_hash != req_hash:
            raise IdempotencyConflict("Bu Idempotency-Key boshqa so'rov bilan ishlatilgan")
        return self.transfer_view(existing, user_id)

    def confirm_transfer(self, user_id: str, transfer_id: str, pin) -> dict:
        t = self._store.get_transfer(transfer_id)
        if t is None or t.user_id != user_id:
            raise TransferNotFound("O'tkazma topilmadi")
        if t.status == "completed":  # takroriy tasdiqlash: qayta yechilmaydi, PIN ham so'ralmaydi
            return self.transfer_view(t, user_id)
        if not isinstance(pin, str) or not pin:
            raise ValidationError("PIN kerak")
        self._pin_check(user_id, pin, "transfer")
        now = self._clock()
        try:
            done = self._store.execute_transfer(
                transfer_id, user_id, now, now - 86400, self._s.transfer_daily_limit_tiyin
            )
        except Exception as e:
            self._audit.record("transfer_not_completed", user_id=user_id, transfer_id=transfer_id, reason=getattr(e, "code", "ERROR"))
            raise
        self._audit.record("transfer_completed", user_id=user_id, transfer_id=done.id, amount=done.amount, fee=done.fee)
        return self.transfer_view(done, user_id)

    def cancel_transfer(self, user_id: str, transfer_id: str) -> dict:
        t = self._store.cancel_transfer(transfer_id, user_id)
        self._audit.record("transfer_cancelled", user_id=user_id, transfer_id=t.id)
        return self.transfer_view(t, user_id)

    def get_transfer(self, user_id: str, transfer_id: str) -> dict:
        t = self._store.get_transfer(transfer_id)
        visible = t is not None and (t.user_id == user_id or (t.to_user_id == user_id and t.status == "completed"))
        if not visible:
            raise TransferNotFound("O'tkazma topilmadi")
        return self.transfer_view(t, user_id)

    # --- tarix ---
    def history(self, user_id: str, limit: int = 20, cursor: str | None = None, status: str | None = None, direction: str | None = None):
        if not isinstance(limit, int) or not 1 <= limit <= MAX_PAGE:
            raise ValidationError(f"limit 1..{MAX_PAGE} oralig'ida bo'lishi kerak")
        if status is not None and status not in _STATUSES:
            raise ValidationError("status noto'g'ri")
        if direction is not None and direction not in ("sent", "received"):
            raise ValidationError("direction noto'g'ri")
        before = self._decode_cursor(cursor) if cursor else None
        rows = self._store.list_history(user_id, limit + 1, before, status, direction)
        page = rows[:limit]
        nxt = self._encode_cursor(page[-1]) if len(rows) > limit else None
        return [self.transfer_view(t, user_id) for t in page], nxt

    @staticmethod
    def _encode_cursor(t: Transfer) -> str:
        return base64.urlsafe_b64encode(f"{t.created_at!r}|{t.id}".encode()).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cur: str) -> tuple[float, str]:
        try:
            raw = base64.urlsafe_b64decode(cur + "=" * (-len(cur) % 4)).decode()
            ts, tid = raw.split("|", 1)
            uuid.UUID(tid)
            return float(ts), tid
        except (ValueError, UnicodeDecodeError):
            raise ValidationError("cursor noto'g'ri") from None

    # --- ko'rinish ---
    def transfer_view(self, t: Transfer, viewer_id: str) -> dict:
        sent = t.user_id == viewer_id
        src = self._store.get_card(t.from_card_id)
        view = {
            "id": t.id,
            "status": t.status,
            "direction": "sent" if sent else "received",
            "amount_tiyin": t.amount,
            "fee_tiyin": t.fee if sent else 0,
            "total_tiyin": t.amount + t.fee if sent else t.amount,
            "counterparty": (
                {"name_masked": t.receiver_name_masked, "last4": t.receiver_last4}
                if sent
                else {"name_masked": mask_name(src.holder_name) if src else "", "last4": src.last4 if src else ""}
            ),
            "created_at": int(t.created_at),
            "expires_at": int(t.expires_at) if t.status == "pending" else None,
            "completed_at": int(t.completed_at) if t.completed_at else None,
            "failure_reason": t.failure_reason if sent else None,
            # Chek faqat serverda tasdiqlangan o'tkazma uchun
            "receipt": {"number": t.receipt_no, "completed_at": int(t.completed_at)}
            if t.status == "completed" and t.receipt_no and t.completed_at
            else None,
            "sandbox": True,
        }
        if sent:
            view["from_card_id"] = t.from_card_id
            view["from_last4"] = src.last4 if src else ""
        return view
