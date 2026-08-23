import asyncio
import threading
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from aiogram.enums import ChatType
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramServerError,
    TelegramUnauthorizedError,
)
from aiogram.methods import SendMessage
from aiogram.types import Chat, User
from fastapi import HTTPException
from fastapi.testclient import TestClient

from config import Settings
from server import create_app, require_api_key
from storage import store_registration


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    database_path = tmp_path / "registrations.db"
    store_registration(
        database_path,
        "alerts",
        Chat(id=-456, type=ChatType.GROUP, title="Alerts"),
        User(
            id=42,
            is_bot=False,
            username="alerts-ops",
            first_name="Alert",
            last_name="Ops",
            language_code="en",
        ),
    )
    return Settings(
        token="env-token", database_path=database_path, api_key="test-api-key"
    )


@pytest.fixture
def bot() -> AsyncMock:
    bot = AsyncMock()
    bot.get_me.return_value = User(
        id=1, is_bot=True, first_name="Router", username="router_test_bot"
    )
    return bot


@pytest.fixture
def client(settings: Settings, bot: AsyncMock):
    app = create_app(settings, polling=False)
    app.state.bot = bot
    with TestClient(app) as test_client:
        yield test_client


def test_send_message_ok(client: TestClient, bot: AsyncMock):
    response = client.post("/bots/alerts/messages", json={"text": "hello"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    bot.send_message.assert_awaited_once_with(
        chat_id=-456, text="hello", parse_mode=None
    )


def test_send_message_parse_mode(client: TestClient, bot: AsyncMock):
    response = client.post(
        "/bots/alerts/messages",
        json={"text": "*hi*", "parse_mode": "MarkdownV2"},
    )

    assert response.status_code == 200
    bot.send_message.assert_awaited_once_with(
        chat_id=-456, text="*hi*", parse_mode="MarkdownV2"
    )


def test_invalid_parse_mode_rejected_422(client: TestClient, bot: AsyncMock):
    response = client.post(
        "/bots/alerts/messages", json={"text": "hi", "parse_mode": "Bogus"}
    )

    assert response.status_code == 422
    bot.send_message.assert_not_awaited()


def test_unknown_bot_returns_404(client: TestClient, bot: AsyncMock):
    response = client.post("/bots/unknown/messages", json={"text": "hello"})

    assert response.status_code == 404
    assert "Unknown bot 'unknown'" in response.text
    bot.send_message.assert_not_awaited()


def test_startup_fails_when_token_rejected(settings: Settings):
    bot = AsyncMock()
    bot.get_me.side_effect = TelegramUnauthorizedError(
        method=SendMessage(chat_id=1, text="x"), message="Unauthorized"
    )
    app = create_app(settings, polling=False)
    app.state.bot = bot
    with (
        pytest.raises(RuntimeError, match="Failed to validate TG_ROUTER_TOKEN"),
        TestClient(app),
    ):
        pass
    bot.session.close.assert_awaited_once()


def test_telegram_server_error_returns_502(client: TestClient, bot: AsyncMock):
    error = TelegramServerError(
        method=SendMessage(chat_id=1, text="x"), message="internal"
    )
    bot.send_message.side_effect = error

    response = client.post("/bots/alerts/messages", json={"text": "hello"})

    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to communicate with Telegram"


def test_telegram_bad_request_returns_400(client: TestClient, bot: AsyncMock):
    error = TelegramBadRequest(
        method=SendMessage(chat_id=1, text="x"), message="can't parse entities"
    )
    bot.send_message.side_effect = error

    response = client.post("/bots/alerts/messages", json={"text": "hello"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Telegram rejected the message"


def test_telegram_forbidden_returns_403(client: TestClient, bot: AsyncMock):
    error = TelegramForbiddenError(
        method=SendMessage(chat_id=1, text="x"), message="bot was kicked"
    )
    bot.send_message.side_effect = error

    response = client.post("/bots/alerts/messages", json={"text": "hello"})

    assert response.status_code == 403
    assert response.json()["detail"] == "The bot no longer has access to this chat"


def test_telegram_not_found_returns_404(client: TestClient, bot: AsyncMock):
    error = TelegramNotFound(
        method=SendMessage(chat_id=1, text="x"), message="chat not found"
    )
    bot.send_message.side_effect = error

    response = client.post("/bots/alerts/messages", json={"text": "hello"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Telegram could not find this chat"


def test_text_over_4096_rejected_422(client: TestClient, bot: AsyncMock):
    response = client.post("/bots/alerts/messages", json={"text": "a" * 4097})

    assert response.status_code == 422
    bot.send_message.assert_not_awaited()


def test_empty_text_rejected_422(client: TestClient, bot: AsyncMock):
    response = client.post("/bots/alerts/messages", json={"text": ""})

    assert response.status_code == 422
    bot.send_message.assert_not_awaited()


def test_list_bots(client: TestClient):
    response = client.get("/bots")

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "alerts",
            "chat_id": -456,
            "chat_type": "group",
            "title": "Alerts",
            "username": "alerts-ops",
            "first_name": "Alert",
            "last_name": "Ops",
            "language_code": "en",
        }
    ]


def test_corrupt_registrations_returns_500(
    client: TestClient, settings: Settings, bot: AsyncMock
):
    settings.database_path.write_text("not sqlite", encoding="utf-8")

    post = client.post("/bots/alerts/messages", json={"text": "hello"})
    get = client.get("/bots")

    assert post.status_code == 500
    assert post.json()["detail"] == "Registrations database is unavailable"
    assert get.status_code == 500
    assert get.json()["detail"] == "Registrations database is unavailable"
    bot.send_message.assert_not_awaited()


def test_health(client: TestClient):
    assert client.get("/health").json() == {"ok": True}


def test_create_registration_returns_expiring_deep_links(client: TestClient):
    response = client.post(
        "/bots/new-chat/registrations", headers={"X-API-Key": "test-api-key"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "new-chat"
    assert body["expires_at"]
    assert body["private_chat_url"].startswith("https://t.me/router_test_bot?start=")
    secret = body["private_chat_url"].split("=", 1)[1]
    assert body["group_chat_url"] == (
        f"https://t.me/router_test_bot?startgroup={secret}"
    )


def test_create_registration_rejects_invalid_name(client: TestClient):
    response = client.post(
        "/bots/bad%20name/registrations", headers={"X-API-Key": "test-api-key"}
    )

    assert response.status_code == 422


def test_create_registration_fails_without_bot_username(
    settings: Settings, bot: AsyncMock
):
    bot.get_me.return_value = User(id=1, is_bot=True, first_name="Router")
    app = create_app(settings, polling=False)
    app.state.bot = bot

    with pytest.raises(RuntimeError, match="username"), TestClient(app):
        pass


def test_create_registration_requires_api_key(client: TestClient):
    response = client.post("/bots/new-chat/registrations")

    assert response.status_code == 401


def test_create_registration_rejects_wrong_api_key(client: TestClient):
    response = client.post(
        "/bots/new-chat/registrations", headers={"X-API-Key": "wrong"}
    )

    assert response.status_code == 403


class BlockingDispatcher:
    async def start_polling(self, *args, **kwargs):
        await __import__("asyncio").Event().wait()


def test_polling_lifespan_shuts_down_cleanly(
    settings: Settings, bot: AsyncMock, monkeypatch
):
    monkeypatch.setattr(
        "server.create_dispatcher", lambda database_path: BlockingDispatcher()
    )
    app = create_app(settings, polling=True)
    app.state.bot = bot

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

    bot.session.close.assert_awaited_once()


class FailingDispatcher:
    async def start_polling(self, *args, **kwargs):
        raise RuntimeError("polling failed")


def test_health_reports_failed_polling(settings: Settings, bot: AsyncMock, monkeypatch):
    monkeypatch.setattr(
        "server.create_dispatcher", lambda database_path: FailingDispatcher()
    )
    app = create_app(settings, polling=True)
    app.state.bot = bot

    client = TestClient(app)
    client.__enter__()
    time.sleep(0.05)
    response = client.get("/health")
    with pytest.raises(RuntimeError, match="polling failed"):
        client.__exit__(None, None, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "Telegram polling is unavailable"
    bot.session.close.assert_awaited_once()


def test_run_storage_offloads_work_from_event_loop():
    from server import run_storage

    storage_threads = []

    def operation():
        storage_threads.append(threading.get_ident())
        return "ok"

    async def run():
        loop_thread = threading.get_ident()
        result = await run_storage(operation)
        return loop_thread, result

    loop_thread, result = asyncio.run(run())

    assert result == "ok"
    assert storage_threads[0] != loop_thread


def test_require_api_key_rejects_non_ascii_without_crashing(settings: Settings):
    with pytest.raises(HTTPException) as error:
        require_api_key(settings, "é")

    assert error.value.status_code == 403
