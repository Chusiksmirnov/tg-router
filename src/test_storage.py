import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from aiogram.enums import ChatType
from aiogram.types import Chat, User

from model import Registration
from storage import (
    get_registration,
    read_registrations,
    store_registration,
)


@pytest.fixture
def registrations_path(tmp_path: Path) -> Path:
    return tmp_path / "registrations.xml"


def test_store_creates_file_and_read_round_trips_all_fields(
    tmp_path: Path, registrations_path: Path
):
    chat = Chat(id=-456, type=ChatType.GROUP, title="Parents")
    user = User(
        id=42,
        is_bot=False,
        first_name="Example",
        username="example-user",
        last_name="User",
        language_code="en",
    )

    stored = store_registration(registrations_path, "alerts", chat, user)

    assert stored == registrations_path
    registrations = read_registrations(registrations_path)
    assert registrations == [
        Registration(
            name="alerts",
            chat_id=-456,
            chat_type="group",
            title="Parents",
            username="example-user",
            first_name="Example",
            last_name="User",
            language_code="en",
        )
    ]


def test_upsert_updates_fields_and_preserves_legacy_metadata(
    tmp_path: Path, registrations_path: Path
):
    registrations_path.write_text(
        '<?xml version="1.0"?>\n'
        "<Registrations><Registration><Name>alerts</Name>"
        "<Token>old-token</Token>"
        "<LegacyMetadata>keep-me</LegacyMetadata>"
        "</Registration></Registrations>",
        encoding="utf-8",
    )
    chat = Chat(id=-999, type=ChatType.GROUP, title="New Title")
    user = User(id=42, is_bot=False, first_name="Example")

    store_registration(registrations_path, "alerts", chat, user)

    root = ET.parse(registrations_path).getroot()
    assert len(root.findall("Registration")) == 1
    assert (
        root.findtext("./Registration[Name='alerts']/LegacyMetadata")
        == "keep-me"
    )
    assert root.findtext("./Registration[Name='alerts']/Token") is None
    assert root.findtext("./Registration[Name='alerts']/ChatId") == "-999"
    assert root.findtext("./Registration[Name='alerts']/Title") == "New Title"


def test_second_name_appends_and_get_registration_by_name(
    tmp_path: Path, registrations_path: Path
):
    first = Chat(id=1, type=ChatType.PRIVATE)
    second = Chat(id=2, type=ChatType.PRIVATE)

    store_registration(registrations_path, "alerts", first, None)
    store_registration(registrations_path, "other", second, None)

    root = ET.parse(registrations_path).getroot()
    assert len(root.findall("Registration")) == 2
    assert get_registration(registrations_path, "alerts").chat_id == 1
    assert get_registration(registrations_path, "other").chat_id == 2
    assert get_registration(registrations_path, "unknown") is None


def test_missing_file_reads_empty(tmp_path: Path, registrations_path: Path):
    assert read_registrations(registrations_path) == []
    assert get_registration(registrations_path, "alerts") is None
