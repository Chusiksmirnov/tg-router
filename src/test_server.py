import tempfile
import unittest
from pathlib import Path

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

import server
from server import app


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.addCleanup(self._restore_path)
        self._original_path = server.REGISTRATIONS_PATH
        server.REGISTRATIONS_PATH = Path(self.tempdir.name) / "registrations.xml"
        server.REGISTRATIONS_PATH.write_text(
            '<?xml version="1.0"?>\n'
            "<Registrations><Registration>"
            "<Name>alerts</Name><Token>123:abc</Token><ChatId>-456</ChatId>"
            "<ChatType>group</ChatType>"
            "</Registration></Registrations>",
            encoding="utf-8",
        )
        self.client = TestClient(app)

    def _restore_path(self):
        server.REGISTRATIONS_PATH = self._original_path

    def _patch_send(self, fake):
        self.patcher = unittest.mock.patch.object(
            server, "send_message", fake
        )
        self.mock = self.patcher.start()
        self.addCleanup(self.patcher.stop)
        return self.mock

    def test_send_message_ok(self):
        fake = AsyncMock()
        self._patch_send(fake)

        response = self.client.post(
            "/bots/alerts/messages", json={"text": "hello"}
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual({"ok": True}, response.json())
        fake.assert_awaited_once_with("123:abc", -456, "hello", None)

    def test_send_message_parse_mode(self):
        fake = AsyncMock()
        self._patch_send(fake)

        response = self.client.post(
            "/bots/alerts/messages",
            json={"text": "*hi*", "parse_mode": "MarkdownV2"},
        )

        self.assertEqual(200, response.status_code)
        fake.assert_awaited_once_with("123:abc", -456, "*hi*", "MarkdownV2")

    def test_invalid_parse_mode_rejected_422(self):
        fake = AsyncMock()
        self._patch_send(fake)

        response = self.client.post(
            "/bots/alerts/messages", json={"text": "hi", "parse_mode": "Bogus"}
        )

        self.assertEqual(422, response.status_code)
        fake.assert_not_awaited()

    def test_unknown_bot_returns_404(self):
        fake = AsyncMock()
        self._patch_send(fake)

        response = self.client.post(
            "/bots/unknown/messages", json={"text": "hello"}
        )

        self.assertEqual(404, response.status_code)
        self.assertIn("Unknown bot 'unknown'", response.text)
        fake.assert_not_awaited()

    def test_telegram_error_returns_502(self):
        error = TelegramBadRequest(
            method=SendMessage(chat_id=1, text="x"), message="bad"
        )
        fake = AsyncMock(side_effect=error)
        self._patch_send(fake)

        response = self.client.post(
            "/bots/alerts/messages", json={"text": "hello"}
        )

        self.assertEqual(502, response.status_code)

    def test_empty_text_rejected_422(self):
        fake = AsyncMock()
        self._patch_send(fake)

        response = self.client.post("/bots/alerts/messages", json={"text": ""})

        self.assertEqual(422, response.status_code)
        fake.assert_not_awaited()

    def test_list_bots_omits_tokens(self):
        response = self.client.get("/bots")

        self.assertEqual(200, response.status_code)
        body = response.text
        self.assertIn("alerts", body)
        self.assertNotIn("123:abc", body)

    def test_health(self):
        self.assertEqual({"ok": True}, self.client.get("/health").json())


if __name__ == "__main__":
    unittest.main()
