import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATABASE_PATH = Path("./registrations.db")
DEFAULT_REGISTRATION_TTL_SECONDS = 600


@dataclass(frozen=True)
class Settings:
    token: str
    api_key: str
    database_path: Path = DEFAULT_DATABASE_PATH
    registration_ttl_seconds: int = DEFAULT_REGISTRATION_TTL_SECONDS


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    token = (env.get("TG_ROUTER_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("TG_ROUTER_BOT_TOKEN environment variable must be set")
    api_key = (env.get("TG_ROUTER_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("TG_ROUTER_API_KEY environment variable must be set")
    database_path = Path(
        env.get("TG_ROUTER_DATABASE") or DEFAULT_DATABASE_PATH
    ).expanduser()
    ttl_value = env.get("TG_ROUTER_REGISTRATION_TTL_SECONDS")
    try:
        registration_ttl_seconds = (
            int(ttl_value)
            if ttl_value is not None
            else DEFAULT_REGISTRATION_TTL_SECONDS
        )
    except ValueError as error:
        raise RuntimeError(
            "TG_ROUTER_REGISTRATION_TTL_SECONDS must be a positive integer"
        ) from error
    if registration_ttl_seconds <= 0:
        raise RuntimeError(
            "TG_ROUTER_REGISTRATION_TTL_SECONDS must be a positive integer"
        )
    return Settings(
        token=token,
        api_key=api_key,
        database_path=database_path,
        registration_ttl_seconds=registration_ttl_seconds,
    )
