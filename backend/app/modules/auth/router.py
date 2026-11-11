"""FastAPI qatlami — faqat HTTP <-> AuthService o'tkazgichi. Biznes mantiq service.py da.
DIQQAT: bu fayl 1-bosqichda yozilgan, lekin fastapi o'rnatilmagan muhitda ISHGA TUSHIRIB TEKSHIRILMAGAN."""
from fastapi import APIRouter, Header
from pydantic import BaseModel

from ...errors import TokenInvalid
from .service import AuthService


class OtpRequestIn(BaseModel):
    phone: str


class OtpVerifyIn(BaseModel):
    challenge_id: str
    code: str


class PinIn(BaseModel):
    pin: str


class PinLoginIn(BaseModel):
    refresh_token: str
    pin: str


class RefreshIn(BaseModel):
    refresh_token: str


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise TokenInvalid("Token yaroqsiz")
    return authorization[7:]


def _pair(pair) -> dict:
    return {
        "access_token": pair.access_token,
        "refresh_token": pair.refresh_token,
        "token_type": "bearer",
        "expires_in": pair.expires_in,
    }


def build_router(svc: AuthService, otp_ttl: int) -> APIRouter:
    r = APIRouter(prefix="/v1/auth", tags=["auth"])

    @r.post("/otp/request")
    def otp_request(body: OtpRequestIn):
        return {"challenge_id": svc.request_otp(body.phone), "expires_in": otp_ttl}

    @r.post("/otp/verify")
    def otp_verify(body: OtpVerifyIn):
        pair, pin_set = svc.verify_otp(body.challenge_id, body.code)
        return {**_pair(pair), "pin_set": pin_set}

    @r.post("/pin/set", status_code=204)
    def pin_set(body: PinIn, authorization: str | None = Header(default=None)):
        svc.set_pin(svc.authenticate(_bearer(authorization)), body.pin)

    @r.post("/pin/login")
    def pin_login(body: PinLoginIn):
        return _pair(svc.login_with_pin(body.refresh_token, body.pin))

    @r.post("/token/refresh")
    def token_refresh(body: RefreshIn):
        return _pair(svc.refresh(body.refresh_token))

    return r
