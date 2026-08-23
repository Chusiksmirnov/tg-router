import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aiogram.types import Chat, User

from model import PendingRegistration, Registration


class StorageError(Exception):
    pass


_SCHEMA = """
CREATE TABLE IF NOT EXISTS registrations (
    name TEXT PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    chat_type TEXT NOT NULL,
    title TEXT,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT
);
CREATE TABLE IF NOT EXISTS pending_registrations (
    secret TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    expires_at REAL NOT NULL
);
"""


def _connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.executescript(_SCHEMA)
    return connection


def _chat_type(chat: Chat) -> str:
    return getattr(chat.type, "value", chat.type)


def _registration_values(
    name: str, chat: Chat, user: User | None
) -> tuple[object, ...]:
    return (
        name,
        chat.id,
        _chat_type(chat),
        chat.title,
        getattr(user, "username", None),
        getattr(user, "first_name", None),
        getattr(user, "last_name", None),
        getattr(user, "language_code", None),
    )


def _upsert_registration(
    connection: sqlite3.Connection, name: str, chat: Chat, user: User | None
) -> None:
    connection.execute(
        """
        INSERT INTO registrations (
            name, chat_id, chat_type, title, username,
            first_name, last_name, language_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            chat_id = excluded.chat_id,
            chat_type = excluded.chat_type,
            title = excluded.title,
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            language_code = excluded.language_code
        """,
        _registration_values(name, chat, user),
    )


def _as_registration(row: sqlite3.Row) -> Registration:
    return Registration(
        name=row["name"],
        chat_id=row["chat_id"],
        chat_type=row["chat_type"],
        title=row["title"],
        username=row["username"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        language_code=row["language_code"],
    )


def read_registrations(database_path: Path) -> list[Registration]:
    try:
        with _connect(database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM registrations ORDER BY name"
            ).fetchall()
    except (sqlite3.Error, OSError) as error:
        raise StorageError(
            f"Cannot read registrations database {database_path}: {error}"
        ) from error
    return [_as_registration(row) for row in rows]


def get_registration(database_path: Path, name: str) -> Registration | None:
    try:
        with _connect(database_path) as connection:
            row = connection.execute(
                "SELECT * FROM registrations WHERE name = ?", (name,)
            ).fetchone()
    except (sqlite3.Error, OSError) as error:
        raise StorageError(
            f"Cannot read registrations database {database_path}: {error}"
        ) from error
    return _as_registration(row) if row is not None else None


def store_registration(
    database_path: Path,
    name: str,
    chat: Chat,
    user: User | None,
) -> Path:
    try:
        with _connect(database_path) as connection:
            _upsert_registration(connection, name, chat, user)
    except (sqlite3.Error, OSError) as error:
        raise StorageError(
            f"Cannot write registrations database {database_path}: {error}"
        ) from error
    return database_path


def create_pending_registration(
    database_path: Path,
    name: str,
    ttl_seconds: int,
    *,
    now: datetime | None = None,
) -> PendingRegistration:
    current = now or datetime.now(UTC)
    expires_at = current + timedelta(seconds=ttl_seconds)
    secret = secrets.token_urlsafe(24)
    try:
        with _connect(database_path) as connection:
            connection.execute(
                "DELETE FROM pending_registrations WHERE expires_at <= ? OR name = ?",
                (current.timestamp(), name),
            )
            connection.execute(
                "INSERT INTO pending_registrations (secret, name, expires_at) VALUES (?, ?, ?)",
                (secret, name, expires_at.timestamp()),
            )
    except (sqlite3.Error, OSError) as error:
        raise StorageError(
            f"Cannot write registrations database {database_path}: {error}"
        ) from error
    return PendingRegistration(name=name, secret=secret, expires_at=expires_at)


def consume_pending_registration(
    database_path: Path,
    secret: str,
    chat: Chat,
    user: User | None,
    *,
    now: datetime | None = None,
) -> str | None:
    current = now or datetime.now(UTC)
    try:
        with _connect(database_path) as connection:
            connection.execute(
                "DELETE FROM pending_registrations WHERE expires_at <= ?",
                (current.timestamp(),),
            )
            row = connection.execute(
                "SELECT name FROM pending_registrations WHERE secret = ?",
                (secret,),
            ).fetchone()
            if row is None:
                return None
            name = row["name"]
            _upsert_registration(connection, name, chat, user)
            connection.execute(
                "DELETE FROM pending_registrations WHERE secret = ?", (secret,)
            )
            return name
    except (sqlite3.Error, OSError) as error:
        raise StorageError(
            f"Cannot write registrations database {database_path}: {error}"
        ) from error
