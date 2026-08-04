import os
from pathlib import Path

from aiogram.exceptions import TelegramAPIError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from storage import get_registration, read_registrations
from telegram import send_message

REGISTRATIONS_PATH = Path(
    os.environ.get("TG_ROUTER_REGISTRATIONS", "./registrations.xml")
)

app = FastAPI(title="tg-router")


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1)


class SendMessageResponse(BaseModel):
    ok: bool = True


class BotInfo(BaseModel):
    name: str
    chat_id: int
    chat_type: str
    title: str | None
    username: str | None


@app.post("/bots/{name}/messages", response_model=SendMessageResponse)
async def post_message(name: str, body: SendMessageRequest) -> SendMessageResponse:
    registration = get_registration(REGISTRATIONS_PATH, name)
    if registration is None:
        raise HTTPException(404, f"Unknown bot '{name}'")
    try:
        await send_message(registration.token, registration.chat_id, body.text)
    except TelegramAPIError as error:
        raise HTTPException(502, str(error)) from error
    return SendMessageResponse()


@app.get("/bots", response_model=list[BotInfo])
async def list_bots() -> list[BotInfo]:
    return [
        BotInfo(
            name=registration.name,
            chat_id=registration.chat_id,
            chat_type=registration.chat_type,
            title=registration.title,
            username=registration.username,
        )
        for registration in read_registrations(REGISTRATIONS_PATH)
    ]


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
