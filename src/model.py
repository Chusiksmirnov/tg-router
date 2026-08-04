from dataclasses import dataclass


@dataclass(frozen=True)
class Registration:
    name: str
    token: str
    chat_id: int
    chat_type: str
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None
