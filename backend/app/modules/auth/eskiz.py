"""Eskiz.uz SMS-shlyuzi orqali SMS yuborish. Faqat standart kutubxona (qo'shimcha paket yo'q).

DIQQAT: endpoint nomlari va maydonlar Eskiz hujjati asosida yozilgan, lekin REAL HISOB BILAN HALI SINALMAGAN
(muhitda tashqi tarmoq yo'q edi). Birinchi ishga tushirishdan oldin `python -m app.tools.sms_check` bilan
bitta SMS yuborib tekshiring. Eskiz API o'zgargan bo'lsa, faqat shu fayl va uning testlarini yangilash kifoya.

Xavfsizlik: parol, token va SMS matni (ichida kod bor) hech qachon log'ga yoki xato matniga yozilmaydi.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

from ...errors import SmsDeliveryError

BASE_URL = "https://notify.eskiz.uz/api"

# (method, url, headers, body, timeout) -> (status, response_body)
HttpFn = Callable[[str, str, dict, bytes | None, float], tuple[int, bytes]]


def _urllib_http(method: str, url: str, headers: dict, body: bytes | None, timeout: float) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (url konstantadan olinadi)
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        raise SmsDeliveryError("SMS yuborib bo'lmadi") from None


class EskizSmsSender:
    is_real = True

    def __init__(
        self,
        email: str,
        password: str,
        sender: str = "4546",
        base_url: str = BASE_URL,
        http: HttpFn | None = None,
        timeout: float = 10.0,
    ):
        self._email = email
        self._password = password
        self._sender = sender
        self._base = base_url.rstrip("/")
        self._http = http or _urllib_http
        self._timeout = timeout
        self._token: str | None = None

    def __repr__(self) -> str:  # parol/token tasodifan chiqib ketmasin
        return f"EskizSmsSender(sender={self._sender!r})"

    def send(self, phone: str, text: str) -> None:
        """[phone] — `998XXXXXXXXX`. Xatoda [SmsDeliveryError] (ichida maxfiy ma'lumot yo'q)."""
        if self._token is None:
            self._login()
        status = self._send_once(phone, text)
        if status == 401:  # token muddati tugagan: bir marta qayta kirib, yana urinamiz
            self._login()
            status = self._send_once(phone, text)
        if not 200 <= status < 300:
            raise SmsDeliveryError("SMS yuborib bo'lmadi")

    # --- ichki ---

    def _form(self, fields: dict) -> tuple[bytes, dict]:
        return (
            urllib.parse.urlencode(fields).encode(),
            {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )

    def _login(self) -> None:
        body, headers = self._form({"email": self._email, "password": self._password})
        status, raw = self._http("POST", f"{self._base}/auth/login", headers, body, self._timeout)
        token = None
        if 200 <= status < 300:
            try:
                token = json.loads(raw).get("data", {}).get("token")
            except (ValueError, AttributeError):
                token = None
        if not isinstance(token, str) or not token:
            self._token = None
            raise SmsDeliveryError("SMS provayderga kirib bo'lmadi")
        self._token = token

    def _send_once(self, phone: str, text: str) -> int:
        body, headers = self._form({"mobile_phone": phone, "message": text, "from": self._sender})
        headers["Authorization"] = f"Bearer {self._token}"
        status, _ = self._http("POST", f"{self._base}/message/sms/send", headers, body, self._timeout)
        return status
