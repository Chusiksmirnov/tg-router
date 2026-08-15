from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
)
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from config import Settings, load_settings
from storage import StorageError, get_registration, read_registrations


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    parse_mode: str | None = Field(
        default=None, pattern="^(HTML|MarkdownV2|Markdown)$"
    )


class SendMessageResponse(BaseModel):
    ok: bool = True


class BotInfo(BaseModel):
    name: str
    chat_id: int
    chat_type: str
    title: str | None
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_bot(request: Request) -> Bot:
    return request.app.state.bot


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if not hasattr(app.state, "settings"):
            app.state.settings = load_settings()
        if not hasattr(app.state, "bot"):
            app.state.bot = Bot(token=app.state.settings.token)
        yield
        await app.state.bot.session.close()

    app = FastAPI(title="tg-router", lifespan=lifespan)
    if settings is not None:
        app.state.settings = settings

    @app.post("/bots/{name}/messages", response_model=SendMessageResponse)
    async def post_message(
        name: str,
        body: SendMessageRequest,
        settings: Settings = Depends(get_settings),
        bot: Bot = Depends(get_bot),
    ) -> SendMessageResponse:
        try:
            registration = get_registration(settings.registrations_path, name)
        except StorageError as error:
            raise HTTPException(500, str(error)) from error
        if registration is None:
            raise HTTPException(404, f"Unknown bot '{name}'")
        try:
            await bot.send_message(
                chat_id=registration.chat_id,
                text=body.text,
                parse_mode=body.parse_mode,
            )
        except TelegramBadRequest as error:
            raise HTTPException(400, str(error)) from error
        except TelegramForbiddenError as error:
            raise HTTPException(403, str(error)) from error
        except TelegramNotFound as error:
            raise HTTPException(404, str(error)) from error
        except TelegramAPIError as error:
            raise HTTPException(502, str(error)) from error
        return SendMessageResponse()

    @app.get("/bots", response_model=list[BotInfo])
    async def list_bots(
        settings: Settings = Depends(get_settings),
    ) -> list[BotInfo]:
        try:
            registrations = read_registrations(settings.registrations_path)
        except StorageError as error:
            raise HTTPException(500, str(error)) from error
        return [
            BotInfo(
                name=registration.name,
                chat_id=registration.chat_id,
                chat_type=registration.chat_type,
                title=registration.title,
                username=registration.username,
                first_name=registration.first_name,
                last_name=registration.last_name,
                language_code=registration.language_code,
            )
            for registration in registrations
        ]

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    return app


app = create_app()
