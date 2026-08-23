from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from aiogram.enums import ChatType
from aiogram.types import Chat, User

from model import Registration
from storage import (
    StorageError,
    consume_pending_registration,
    create_pending_registration,
    get_registration,
    read_registrations,
    store_registration,
)


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "registrations.db"


def test_store_creates_sqlite_database_and_round_trips_all_fields(
    database_path: Path,
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

    stored = store_registration(database_path, "alerts", chat, user)

    assert stored == database_path
    assert database_path.read_bytes().startswith(b"SQLite format 3\x00")
    assert read_registrations(database_path) == [
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


def test_store_upserts_existing_name(database_path: Path):
    store_registration(
        database_path,
        "alerts",
        Chat(id=1, type=ChatType.PRIVATE),
        None,
    )

    store_registration(
        database_path,
        "alerts",
        Chat(id=-999, type=ChatType.GROUP, title="New Title"),
        User(id=42, is_bot=False, first_name="Example"),
    )

    registrations = read_registrations(database_path)
    assert len(registrations) == 1
    assert registrations[0].chat_id == -999
    assert registrations[0].title == "New Title"


def test_missing_database_reads_empty(database_path: Path):
    assert read_registrations(database_path) == []
    assert get_registration(database_path, "alerts") is None


def test_corrupt_database_raises_storage_error(database_path: Path):
    database_path.write_text("not sqlite", encoding="utf-8")

    with pytest.raises(StorageError, match="database"):
        read_registrations(database_path)


def test_pending_registration_has_ttl(database_path: Path):
    now = datetime(2026, 1, 1, tzinfo=UTC)

    pending = create_pending_registration(
        database_path, "alerts", ttl_seconds=60, now=now
    )

    assert pending.name == "alerts"
    assert pending.secret
    assert pending.expires_at == now + timedelta(seconds=60)


def test_valid_pending_registration_is_consumed_once(database_path: Path):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    pending = create_pending_registration(
        database_path, "alerts", ttl_seconds=60, now=now
    )
    chat = Chat(id=-456, type=ChatType.GROUP, title="Alerts")

    name = consume_pending_registration(
        database_path, pending.secret, chat, None, now=now
    )
    second = consume_pending_registration(
        database_path, pending.secret, chat, None, now=now
    )

    assert name == "alerts"
    assert second is None
    assert get_registration(database_path, "alerts").chat_id == -456


def test_expired_pending_registration_cannot_be_consumed(database_path: Path):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    pending = create_pending_registration(
        database_path, "alerts", ttl_seconds=60, now=now
    )

    name = consume_pending_registration(
        database_path,
        pending.secret,
        Chat(id=1, type=ChatType.PRIVATE),
        None,
        now=now + timedelta(seconds=61),
    )

    assert name is None
    assert get_registration(database_path, "alerts") is None


def test_new_pending_registration_replaces_previous_link(database_path: Path):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = create_pending_registration(
        database_path, "alerts", ttl_seconds=60, now=now
    )
    second = create_pending_registration(
        database_path, "alerts", ttl_seconds=60, now=now
    )
    chat = Chat(id=1, type=ChatType.PRIVATE)

    assert first.secret != second.secret
    assert (
        consume_pending_registration(database_path, first.secret, chat, None, now=now)
        is None
    )
    assert (
        consume_pending_registration(database_path, second.secret, chat, None, now=now)
        == "alerts"
    )
