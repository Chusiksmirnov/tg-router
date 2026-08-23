from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Registration:
    name: str
    chat_id: int
    chat_type: str
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None


@dataclass(frozen=True)
class PendingRegistration:
    name: str
    secret: str
    expires_at: datetime
