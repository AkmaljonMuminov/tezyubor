import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

_log = logging.getLogger("tezyubor.audit")


@dataclass
class AuditEvent:
    ts: float
    event: str
    fields: dict = field(default_factory=dict)


class AuditSink(Protocol):
    def write(self, ev: AuditEvent) -> None: ...


class AuditLog:
    """Xavfsizlik hodisalari. Hech qachon OTP kodi, PIN, token yoki karta raqami yozilmaydi; telefon maskalanadi.
    Xotirada faqat oxirgi `max_memory` ta hodisa (cheksiz o'smaydi); `sink` berilsa (PostgreSQL) har hodisa doimiy saqlanadi.
    Sink xatosi so'rovni buzmaydi — faqat log'ga yoziladi."""

    def __init__(self, clock: Callable[[], float] = time.time, sink: AuditSink | None = None, max_memory: int = 5000):
        self._clock = clock
        self._sink = sink
        self._max = max_memory
        self.events: list[AuditEvent] = []

    def record(self, event: str, **fields) -> None:
        ev = AuditEvent(self._clock(), event, fields)
        self.events.append(ev)
        if len(self.events) > self._max:
            del self.events[: len(self.events) - self._max]
        if self._sink is not None:
            try:
                self._sink.write(ev)
            except Exception:  # noqa: BLE001 - audit yozuvi xatosi foydalanuvchi so'rovini to'xtatmasin
                _log.exception("audit yozilmadi: %s", event)
