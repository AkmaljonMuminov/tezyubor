"""FastAPI qatlami: HTTP <-> WalletService. Barcha endpoint Bearer token talab qiladi. DIQQAT: bu muhitda fastapi yo'q —
HTTP testlari faqat CI'da ishlaydi."""
from fastapi import APIRouter, Header, Query
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

    def uid(authorization: str | None) -> str:
        return auth.authenticate(_bearer(authorization))

    @r.get("/cards")
    def list_cards(authorization: str | None = Header(default=None)):
        return {"cards": wallet.list_cards(uid(authorization)), "sandbox": True}

    @r.post("/cards", status_code=201)
    def add_card(body: CardIn, authorization: str | None = Header(default=None)):
        return wallet.add_card(uid(authorization), body.pan, body.exp_month, body.exp_year, body.holder_name)

    @r.delete("/cards/{card_id}", status_code=204)
    def delete_card(card_id: str, authorization: str | None = Header(default=None)):
        wallet.delete_card(uid(authorization), card_id)

    @r.post("/cards/{card_id}/default", status_code=204)
    def set_default(card_id: str, authorization: str | None = Header(default=None)):
        wallet.set_default(uid(authorization), card_id)

    @r.post("/receiver/lookup")
    def lookup(body: LookupIn, authorization: str | None = Header(default=None)):
        return wallet.lookup_receiver(uid(authorization), body.pan)

    @r.post("/transfers")
    def create_transfer(
        body: TransferIn,
        authorization: str | None = Header(default=None),
        idempotency_key: str | None = Header(default=None),
    ):
        return wallet.create_transfer(
            uid(authorization), idempotency_key, body.from_card_id, body.receiver_pan, body.amount_tiyin
        )

    @r.post("/transfers/{transfer_id}/confirm")
    def confirm(transfer_id: str, body: ConfirmIn, authorization: str | None = Header(default=None)):
        return wallet.confirm_transfer(uid(authorization), transfer_id, body.pin)

    @r.post("/transfers/{transfer_id}/cancel")
    def cancel(transfer_id: str, authorization: str | None = Header(default=None)):
        return wallet.cancel_transfer(uid(authorization), transfer_id)

    @r.get("/transactions")
    def history(
        authorization: str | None = Header(default=None),
        limit: int = Query(default=20),
        cursor: str | None = Query(default=None),
        status: str | None = Query(default=None),
        direction: str | None = Query(default=None),
    ):
        items, nxt = wallet.history(uid(authorization), limit, cursor, status, direction)
        return {"items": items, "next_cursor": nxt, "sandbox": True}

    @r.get("/transactions/{transfer_id}")
    def one(transfer_id: str, authorization: str | None = Header(default=None)):
        return wallet.get_transfer(uid(authorization), transfer_id)

    return r
