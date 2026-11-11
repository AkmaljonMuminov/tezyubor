import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class AuditEvent:
    ts: float
    event: str
    fields: dict = field(default_factory=dict)


class AuditLog:
    """Xavfsizlik hodisalari. Hech qachon OTP kodi, PIN yoki token yozilmaydi; telefon maskalanadi.
    Keyingi bosqich: o'zgartirib bo'lmaydigan jadval (PostgreSQL, append-only)."""

    def __init__(self, clock: Callable[[], float] = time.time):
        self._clock = clock
        self.events: list[AuditEvent] = []

    def record(self, event: str, **fields) -> None:
        self.events.append(AuditEvent(self._clock(), event, fields))
