import asyncio
import logging
from datetime import datetime
from pathlib import Path

from aiogram import Dispatcher, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from storage import StorageError, consume_pending_registration

logger = logging.getLogger("tg-router")


async def complete_registration(
    database_path: Path,
    secret: str,
    message: Message,
    *,
    now: datetime | None = None,
) -> str | None:
    name = await asyncio.to_thread(
        consume_pending_registration,
        database_path,
        secret,
        message.chat,
        message.from_user,
        now=now,
    )
    if name is None:
        await message.answer("This registration link is invalid or has expired.")
        return None
    await message.answer(f"Messages can now be routed to this chat as '{name}'.")
    return name


def create_dispatcher(database_path: Path) -> Dispatcher:
    dispatcher = Dispatcher()
    router = Router()

    @router.message(CommandStart(deep_link=True))
    async def register(message: Message, command: CommandObject) -> None:
        if not command.args:
            return
        try:
            await complete_registration(database_path, command.args, message)
        except StorageError as error:
            logger.error("cannot complete chat registration: %s", error)
            await message.answer("Registration failed due to a storage error.")

    dispatcher.include_router(router)
    return dispatcher
