from dataclasses import dataclass


@dataclass
class Card:
    id: str
    user_id: str
    pan_index: str          # HMAC(PAN) — PAN o'zi saqlanmaydi
    bin6: str
    last4: str
    brand: str
    holder_name: str
    exp_month: int
    exp_year: int
    balance: int            # tiyin (1 so'm = 100 tiyin). SANDBOX qiymat
    is_default: bool
    status: str             # active | deleted
    created_at: float


@dataclass
class Transfer:
    id: str
    user_id: str            # jo'natuvchi
    to_user_id: str
    from_card_id: str
    to_card_id: str
    amount: int
    fee: int
    status: str             # pending | completed | failed | expired | cancelled
    idempotency_key: str
    request_hash: str
    receiver_last4: str
    receiver_name_masked: str
    created_at: float
    expires_at: float
    completed_at: float | None = None
    receipt_no: str | None = None
    failure_reason: str | None = None
