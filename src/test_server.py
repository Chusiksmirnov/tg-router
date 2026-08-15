from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramServerError,
)
from aiogram.methods import SendMessage
from fastapi.testclient import TestClient

from config import Settings
from server import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    registrations_path = tmp_path / "registrations.xml"
    registrations_path.write_text(
        '<?xml version="1.0"?>\n'
        "<Registrations><Registration>"
        "<Name>alerts</Name><ChatId>-456</ChatId>"
        "<ChatType>group</ChatType>"
        "<Title>Alerts</Title><Username>alerts-ops</Username>"
        "<FirstName>Alert</FirstName><LastName>Ops</LastName>"
        "<LanguageCode>en</LanguageCode>"
        "</Registration></Registrations>",
        encoding="utf-8",
    )
    return Settings(token="env-token", registrations_path=registrations_path)


@pytest.fixture
def bot() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(settings: Settings, bot: AsyncMock):
    app = create_app(settings)
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


def test_telegram_server_error_returns_502(client: TestClient, bot: AsyncMock):
    error = TelegramServerError(
        method=SendMessage(chat_id=1, text="x"), message="internal"
    )
    bot.send_message.side_effect = error

    response = client.post("/bots/alerts/messages", json={"text": "hello"})

    assert response.status_code == 502


def test_telegram_bad_request_returns_400(client: TestClient, bot: AsyncMock):
    error = TelegramBadRequest(
        method=SendMessage(chat_id=1, text="x"), message="can't parse entities"
    )
    bot.send_message.side_effect = error

    response = client.post("/bots/alerts/messages", json={"text": "hello"})

    assert response.status_code == 400
    assert "can't parse entities" in response.text


def test_telegram_forbidden_returns_403(client: TestClient, bot: AsyncMock):
    error = TelegramForbiddenError(
        method=SendMessage(chat_id=1, text="x"), message="bot was kicked"
    )
    bot.send_message.side_effect = error

    response = client.post("/bots/alerts/messages", json={"text": "hello"})

    assert response.status_code == 403


def test_telegram_not_found_returns_404(client: TestClient, bot: AsyncMock):
    error = TelegramNotFound(
        method=SendMessage(chat_id=1, text="x"), message="chat not found"
    )
    bot.send_message.side_effect = error

    response = client.post("/bots/alerts/messages", json={"text": "hello"})

    assert response.status_code == 404


def test_text_over_4096_rejected_422(client: TestClient, bot: AsyncMock):
    response = client.post(
        "/bots/alerts/messages", json={"text": "a" * 4097}
    )

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
    settings.registrations_path.write_text("not xml", encoding="utf-8")

    post = client.post("/bots/alerts/messages", json={"text": "hello"})
    get = client.get("/bots")

    assert post.status_code == 500
    assert get.status_code == 500
    bot.send_message.assert_not_awaited()


def test_health(client: TestClient):
    assert client.get("/health").json() == {"ok": True}
