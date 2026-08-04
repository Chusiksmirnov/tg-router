from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage
from fastapi.testclient import TestClient

import server
from server import app


@pytest.fixture
def client(tmp_path: Path):
    original_path = server.REGISTRATIONS_PATH
    registrations_path = tmp_path / "registrations.xml"
    registrations_path.write_text(
        '<?xml version="1.0"?>\n'
        "<Registrations><Registration>"
        "<Name>alerts</Name><Token>123:abc</Token><ChatId>-456</ChatId>"
        "<ChatType>group</ChatType>"
        "</Registration></Registrations>",
        encoding="utf-8",
    )
    server.REGISTRATIONS_PATH = registrations_path
    try:
        yield TestClient(app)
    finally:
        server.REGISTRATIONS_PATH = original_path


@pytest.fixture
def mock_send_message():
    fake = AsyncMock()
    with patch.object(server, "send_message", fake):
        yield fake


def test_send_message_ok(client: TestClient, mock_send_message: AsyncMock):
    response = client.post("/bots/alerts/messages", json={"text": "hello"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_send_message.assert_awaited_once_with("123:abc", -456, "hello", None)


def test_send_message_parse_mode(client: TestClient, mock_send_message: AsyncMock):
    response = client.post(
        "/bots/alerts/messages",
        json={"text": "*hi*", "parse_mode": "MarkdownV2"},
    )

    assert response.status_code == 200
    mock_send_message.assert_awaited_once_with("123:abc", -456, "*hi*", "MarkdownV2")


def test_invalid_parse_mode_rejected_422(
    client: TestClient, mock_send_message: AsyncMock
):
    response = client.post(
        "/bots/alerts/messages", json={"text": "hi", "parse_mode": "Bogus"}
    )

    assert response.status_code == 422
    mock_send_message.assert_not_awaited()


def test_unknown_bot_returns_404(client: TestClient, mock_send_message: AsyncMock):
    response = client.post("/bots/unknown/messages", json={"text": "hello"})

    assert response.status_code == 404
    assert "Unknown bot 'unknown'" in response.text
    mock_send_message.assert_not_awaited()


def test_telegram_error_returns_502(client: TestClient, mock_send_message: AsyncMock):
    error = TelegramBadRequest(
        method=SendMessage(chat_id=1, text="x"), message="bad"
    )
    mock_send_message.side_effect = error

    response = client.post("/bots/alerts/messages", json={"text": "hello"})

    assert response.status_code == 502


def test_empty_text_rejected_422(client: TestClient, mock_send_message: AsyncMock):
    response = client.post("/bots/alerts/messages", json={"text": ""})

    assert response.status_code == 422
    mock_send_message.assert_not_awaited()


def test_list_bots_omits_tokens(client: TestClient):
    response = client.get("/bots")

    assert response.status_code == 200
    assert "alerts" in response.text
    assert "123:abc" not in response.text


def test_health(client: TestClient):
    assert client.get("/health").json() == {"ok": True}
