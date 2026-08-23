import asyncio
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

from aiogram.enums import ChatType
from aiogram.types import Chat, User

from storage import create_pending_registration, get_registration
from telegram import complete_registration


def test_complete_registration_consumes_link_and_confirms(tmp_path: Path):
    database_path = tmp_path / "router.db"
    now = datetime(2026, 1, 1, tzinfo=UTC)
    pending = create_pending_registration(
        database_path, "alerts", ttl_seconds=60, now=now
    )
    message = AsyncMock()
    message.chat = Chat(id=-456, type=ChatType.GROUP, title="Alerts")
    message.from_user = User(id=42, is_bot=False, first_name="Example")

    name = asyncio.run(
        complete_registration(database_path, pending.secret, message, now=now)
    )

    assert name == "alerts"
    message.answer.assert_awaited_once_with(
        "Messages can now be routed to this chat as 'alerts'."
    )
    assert get_registration(database_path, "alerts").chat_id == -456


def test_complete_registration_rejects_expired_link(tmp_path: Path):
    database_path = tmp_path / "router.db"
    now = datetime(2026, 1, 1, tzinfo=UTC)
    pending = create_pending_registration(
        database_path, "alerts", ttl_seconds=60, now=now
    )
    message = AsyncMock()
    message.chat = Chat(id=1, type=ChatType.PRIVATE)
    message.from_user = None

    name = asyncio.run(
        complete_registration(
            database_path,
            pending.secret,
            message,
            now=now + timedelta(seconds=61),
        )
    )

    assert name is None
    message.answer.assert_awaited_once_with(
        "This registration link is invalid or has expired."
    )


def test_complete_registration_runs_sqlite_off_event_loop(monkeypatch, tmp_path: Path):
    storage_threads = []

    def fake_consume(*args, **kwargs):
        storage_threads.append(threading.get_ident())

    monkeypatch.setattr("telegram.consume_pending_registration", fake_consume)
    message = AsyncMock()
    message.chat = Chat(id=1, type=ChatType.PRIVATE)
    message.from_user = None

    async def run():
        loop_thread = threading.get_ident()
        await complete_registration(tmp_path / "router.db", "secret", message)
        return loop_thread

    loop_thread = asyncio.run(run())

    assert storage_threads
    assert storage_threads[0] != loop_thread
