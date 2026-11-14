"""FastAPI qatlami: HTTP <-> WalletService. Barcha endpoint Bearer token talab qiladi. DIQQAT: bu muhitda fastapi yo'q —
HTTP testlari faqat CI'da ishlaydi."""
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, StrictInt

from ..auth.router import _bearer
from ..auth.service import AuthService
from .service import WalletService


class CardIn(BaseModel):
    pan: str
    exp_month: StrictInt
    exp_year: StrictInt
    holder_name: str


class LookupIn(BaseModel):
    pan: str


class TransferIn(BaseModel):
    from_card_id: str
    receiver_pan: str
    amount_tiyin: StrictInt


class ConfirmIn(BaseModel):
    pin: str


def build_router(wallet: WalletService, auth: AuthService) -> APIRouter:
    r = APIRouter(prefix="/v1/wallet", tags=["wallet (sandbox)"])

    def current_user(authorization: str | None = Header(default=None)) -> str:
        # Depends sifatida: ruxsatsiz so'rov tana tekshiruvidan (422) OLDIN 401 oladi
        return auth.authenticate(_bearer(authorization))

    @r.get("/cards")
    def list_cards(user_id: str = Depends(current_user)):
        return {"cards": wallet.list_cards(user_id), "sandbox": True}

    @r.post("/cards", status_code=201)
    def add_card(body: CardIn, user_id: str = Depends(current_user)):
        return wallet.add_card(user_id, body.pan, body.exp_month, body.exp_year, body.holder_name)

    @r.delete("/cards/{card_id}", status_code=204)
    def delete_card(card_id: str, user_id: str = Depends(current_user)):
        wallet.delete_card(user_id, card_id)

    @r.post("/cards/{card_id}/default", status_code=204)
    def set_default(card_id: str, user_id: str = Depends(current_user)):
        wallet.set_default(user_id, card_id)

    @r.post("/receiver/lookup")
    def lookup(body: LookupIn, user_id: str = Depends(current_user)):
        return wallet.lookup_receiver(user_id, body.pan)

    @r.post("/transfers")
    def create_transfer(
        body: TransferIn,
        user_id: str = Depends(current_user),
        idempotency_key: str | None = Header(default=None),
    ):
        return wallet.create_transfer(
            user_id, idempotency_key, body.from_card_id, body.receiver_pan, body.amount_tiyin
        )

    @r.post("/transfers/{transfer_id}/confirm")
    def confirm(transfer_id: str, body: ConfirmIn, user_id: str = Depends(current_user)):
        return wallet.confirm_transfer(user_id, transfer_id, body.pin)

    @r.post("/transfers/{transfer_id}/cancel")
    def cancel(transfer_id: str, user_id: str = Depends(current_user)):
        return wallet.cancel_transfer(user_id, transfer_id)

    @r.get("/transactions")
    def history(
        user_id: str = Depends(current_user),
        limit: int = Query(default=20),
        cursor: str | None = Query(default=None),
        status: str | None = Query(default=None),
        direction: str | None = Query(default=None),
    ):
        items, nxt = wallet.history(user_id, limit, cursor, status, direction)
        return {"items": items, "next_cursor": nxt, "sandbox": True}

    @r.get("/transactions/{transfer_id}")
    def one(transfer_id: str, user_id: str = Depends(current_user)):
        return wallet.get_transfer(user_id, transfer_id)

    return r
