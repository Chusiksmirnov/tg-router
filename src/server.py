import asyncio
import logging
import secrets
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from typing import Annotated

from aiogram import Bot, Dispatcher
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
)
from aiogram.types import User
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Request, status
from fastapi.responses import HTMLResponse

from config import Settings, load_settings
from schemas import BotInfo, RegistrationLinks, SendMessageRequest, SendMessageResponse
from storage import (
    StorageError,
    create_pending_registration,
    get_registration,
    read_registrations,
)
from telegram import create_dispatcher
from web import web_ui

logger = logging.getLogger("tg-router")
NAME_PATTERN = r"^[A-Za-z0-9_-]+$"


async def run_storage[StorageResult](
    function: Callable[..., StorageResult], *args: object
) -> StorageResult:
    return await asyncio.to_thread(function, *args)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_bot(request: Request) -> Bot:
    return request.app.state.bot


def get_bot_user(request: Request) -> User:
    return request.app.state.bot_user


def require_api_key(
    settings: Annotated[Settings, Depends(get_settings)],
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    if api_key is None:
        raise HTTPException(401, "X-API-Key header is required")
    if not secrets.compare_digest(api_key.encode(), settings.api_key.encode()):
        raise HTTPException(403, "Invalid API key")


def create_app(settings: Settings | None = None, *, polling: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if not hasattr(app.state, "settings"):
            app.state.settings = load_settings()
        if not hasattr(app.state, "bot"):
            app.state.bot = Bot(token=app.state.settings.token)
        dispatcher: Dispatcher | None = None
        polling_task: asyncio.Task[None] | None = None
        try:
            app.state.bot_user = await app.state.bot.get_me()
            if not app.state.bot_user.username:
                raise RuntimeError("Telegram bot must have a username")
            if polling:
                dispatcher = create_dispatcher(app.state.settings.database_path)
                polling_task = asyncio.create_task(
                    dispatcher.start_polling(
                        app.state.bot,
                        handle_signals=False,
                        close_bot_session=False,
                    )
                )
                app.state.polling_task = polling_task
            yield
        except TelegramAPIError as error:
            raise RuntimeError(
                f"Failed to validate TG_ROUTER_BOT_TOKEN: {error}"
            ) from error
        finally:
            try:
                if polling_task is not None:
                    polling_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await polling_task
            finally:
                await app.state.bot.session.close()

    app = FastAPI(title="tg-router", lifespan=lifespan)
    if settings is not None:
        app.state.settings = settings

    @app.get("/", include_in_schema=False)
    async def root() -> HTMLResponse:
        return web_ui()

    @app.post(
        "/bots/{name}",
        response_model=RegistrationLinks,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_registration(
        name: Annotated[str, Path(pattern=NAME_PATTERN)],
        settings: Annotated[Settings, Depends(get_settings)],
        bot_user: Annotated[User, Depends(get_bot_user)],
        _: Annotated[None, Depends(require_api_key)],
    ) -> RegistrationLinks:
        try:
            pending = await run_storage(
                create_pending_registration,
                settings.database_path,
                name,
                settings.registration_ttl_seconds,
            )
        except StorageError as error:
            logger.error(
                "cannot create registration in %s: %s",
                settings.database_path,
                error,
            )
            raise HTTPException(500, "Registrations database is unavailable") from error
        base = f"https://t.me/{bot_user.username}"
        return RegistrationLinks(
            name=name,
            expires_at=pending.expires_at,
            private_chat_url=f"{base}?start={pending.secret}",
            group_chat_url=f"{base}?startgroup={pending.secret}",
        )

    @app.post("/bots/{name}/messages", response_model=SendMessageResponse)
    async def post_message(
        name: str,
        body: SendMessageRequest,
        settings: Annotated[Settings, Depends(get_settings)],
        bot: Annotated[Bot, Depends(get_bot)],
    ) -> SendMessageResponse:
        try:
            registration = await run_storage(
                get_registration, settings.database_path, name
            )
        except StorageError as error:
            logger.error(
                "cannot read registrations from %s: %s",
                settings.database_path,
                error,
            )
            raise HTTPException(500, "Registrations database is unavailable") from error
        if registration is None:
            raise HTTPException(404, f"Unknown bot '{name}'")
        try:
            await bot.send_message(
                chat_id=registration.chat_id,
                text=body.text,
                parse_mode=body.parse_mode,
            )
        except TelegramBadRequest as error:
            logger.warning(
                "send_message rejected for registration %r (chat %s): %s",
                name,
                registration.chat_id,
                error,
            )
            raise HTTPException(400, "Telegram rejected the message") from error
        except TelegramForbiddenError as error:
            logger.warning(
                "send_message rejected for registration %r (chat %s): %s",
                name,
                registration.chat_id,
                error,
            )
            raise HTTPException(
                403, "The bot no longer has access to this chat"
            ) from error
        except TelegramNotFound as error:
            logger.warning(
                "send_message rejected for registration %r (chat %s): %s",
                name,
                registration.chat_id,
                error,
            )
            raise HTTPException(404, "Telegram could not find this chat") from error
        except TelegramAPIError as error:
            logger.error(
                "send_message failed for registration %r (chat %s): %s",
                name,
                registration.chat_id,
                error,
            )
            raise HTTPException(502, "Failed to communicate with Telegram") from error
        return SendMessageResponse()

    @app.get("/bots", response_model=list[BotInfo])
    async def list_bots(
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> list[BotInfo]:
        try:
            registrations = await run_storage(
                read_registrations, settings.database_path
            )
        except StorageError as error:
            logger.error(
                "cannot read registrations from %s: %s",
                settings.database_path,
                error,
            )
            raise HTTPException(500, "Registrations database is unavailable") from error
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
    async def health(request: Request) -> dict[str, bool]:
        polling_task = getattr(request.app.state, "polling_task", None)
        if polling_task is not None and polling_task.done():
            if not polling_task.cancelled() and polling_task.exception() is not None:
                logger.error("Telegram polling stopped: %s", polling_task.exception())
            raise HTTPException(503, "Telegram polling is unavailable")
        return {"ok": True}

    return app


app = create_app()
