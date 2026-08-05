import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REGISTRATIONS_PATH = Path("./registrations.xml")


@dataclass(frozen=True)
class Settings:
    token: str
    registrations_path: Path = DEFAULT_REGISTRATIONS_PATH


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    token = (env.get("TG_ROUTER_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("TG_ROUTER_TOKEN environment variable must be set")
    path = Path(
        env.get("TG_ROUTER_REGISTRATIONS") or DEFAULT_REGISTRATIONS_PATH
    ).expanduser()
    return Settings(token=token, registrations_path=path)
