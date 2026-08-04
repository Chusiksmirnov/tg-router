import secrets
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from storage import store_registration


async def send_message(token: str, chat_id: int, text: str) -> None:
    async with Bot(token=token) as bot:
        await bot.send_message(chat_id=chat_id, text=text)


async def register_chat(name: str, token: str, registrations_path: Path) -> None:
    secret = secrets.token_urlsafe(24)
    dispatcher = Dispatcher()

    async with Bot(token=token) as bot:
        bot_user = await bot.get_me()
        if not bot_user.username:
            raise RuntimeError("Telegram bot has no username")

        print(f"https://t.me/{bot_user.username}?start={secret}", flush=True)
        print("Waiting for the Telegram chat to follow the link...", flush=True)

        @dispatcher.message(CommandStart(deep_link=True))
        async def register(message: Message, command: CommandObject) -> None:
            if command.args != secret:
                return
            path = store_registration(
                registrations_path, name, token, message.chat, message.from_user
            )
            await message.answer(
                f"Messages can now be routed to this chat as '{name}'."
            )
            print(
                f"Registration '{name}' saved to {path} (chat {message.chat.id})",
                flush=True,
            )
            await dispatcher.stop_polling()

        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
            close_bot_session=False,
        )
