import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from aiogram.enums import ChatType
from aiogram.types import Chat, User

from model import Registration
from storage import (
    get_registration,
    read_registrations,
    store_registration,
)


class StorageTests(unittest.TestCase):
    def test_store_creates_file_and_read_round_trips_all_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registrations.xml"
            chat = Chat(id=-456, type=ChatType.GROUP, title="Parents")
            user = User(
                id=42,
                is_bot=False,
                first_name="Example",
                username="example-user",
                last_name="User",
                language_code="en",
            )

            stored = store_registration(path, "alerts", "123:abc", chat, user)

            self.assertEqual(path, stored)
            registrations = read_registrations(path)
            self.assertEqual(1, len(registrations))
            self.assertEqual(
                Registration(
                    name="alerts",
                    token="123:abc",
                    chat_id=-456,
                    chat_type="group",
                    title="Parents",
                    username="example-user",
                    first_name="Example",
                    last_name="User",
                    language_code="en",
                ),
                registrations[0],
            )

    def test_upsert_updates_fields_and_preserves_legacy_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registrations.xml"
            path.write_text(
                '<?xml version="1.0"?>\n'
                "<Registrations><Registration><Name>alerts</Name>"
                "<LegacyMetadata>keep-me</LegacyMetadata>"
                "</Registration></Registrations>",
                encoding="utf-8",
            )
            chat = Chat(id=-999, type=ChatType.GROUP, title="New Title")
            user = User(id=42, is_bot=False, first_name="Example")

            store_registration(path, "alerts", "456:def", chat, user)

            root = ET.parse(path).getroot()
            self.assertEqual(1, len(root.findall("Registration")))
            self.assertEqual(
                "keep-me",
                root.findtext("./Registration[Name='alerts']/LegacyMetadata"),
            )
            self.assertEqual(
                "456:def",
                root.findtext("./Registration[Name='alerts']/Token"),
            )
            self.assertEqual(
                "-999",
                root.findtext("./Registration[Name='alerts']/ChatId"),
            )
            self.assertEqual(
                "New Title",
                root.findtext("./Registration[Name='alerts']/Title"),
            )

    def test_second_name_appends_and_get_registration_by_name(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registrations.xml"
            first = Chat(id=1, type=ChatType.PRIVATE)
            second = Chat(id=2, type=ChatType.PRIVATE)

            store_registration(path, "alerts", "123:abc", first, None)
            store_registration(path, "other", "456:def", second, None)

            root = ET.parse(path).getroot()
            self.assertEqual(2, len(root.findall("Registration")))
            self.assertEqual(
                "123:abc",
                get_registration(path, "alerts").token,
            )
            self.assertEqual(
                "456:def",
                get_registration(path, "other").token,
            )
            self.assertIsNone(get_registration(path, "unknown"))

    def test_missing_file_reads_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registrations.xml"
            self.assertEqual([], read_registrations(path))
            self.assertIsNone(get_registration(path, "alerts"))


if __name__ == "__main__":
    unittest.main()
