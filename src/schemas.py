from datetime import datetime

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    parse_mode: str | None = Field(default=None, pattern="^(HTML|MarkdownV2|Markdown)$")


class SendMessageResponse(BaseModel):
    ok: bool = True


class RegistrationLinks(BaseModel):
    name: str
    expires_at: datetime
    private_chat_url: str
    group_chat_url: str


class BotInfo(BaseModel):
    name: str
    chat_id: int
    chat_type: str
    title: str | None
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None
