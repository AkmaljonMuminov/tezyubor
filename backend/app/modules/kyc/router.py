from typing import Callable

from fastapi import APIRouter, Header
from pydantic import BaseModel

from ...errors import TokenInvalid
from .service import KycService


class ConsentIn(BaseModel):
    version: str


class StartIn(BaseModel):
    passport: str
    birth_date: str  # dd.MM.yyyy


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise TokenInvalid("Token yaroqsiz")
    return authorization[7:]


def build_kyc_router(svc: KycService, authenticate: Callable[[str], str]) -> APIRouter:
    r = APIRouter(prefix="/v1/kyc", tags=["kyc"])

    @r.get("/status")
    def status(authorization: str | None = Header(default=None)):
        return svc.status(authenticate(_bearer(authorization)))

    @r.post("/consent", status_code=204)
    def consent(body: ConsentIn, authorization: str | None = Header(default=None)):
        svc.give_consent(authenticate(_bearer(authorization)), body.version)

    @r.post("/start")
    def start(body: StartIn, authorization: str | None = Header(default=None)):
        return svc.start(authenticate(_bearer(authorization)), body.passport, body.birth_date)

    @r.post("/complete")
    def complete(authorization: str | None = Header(default=None)):
        return svc.complete(authenticate(_bearer(authorization)))

    return r
