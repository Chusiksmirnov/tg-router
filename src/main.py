import argparse
import asyncio
from dataclasses import replace
from pathlib import Path

from config import load_settings
from telegram import register_chat


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register a Telegram chat for message routing"
    )
    parser.add_argument("--register", required=True, help="registration name")
    parser.add_argument(
        "-r",
        "--registrations",
        default="./registrations.xml",
        help="path to the registrations XML file",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        settings = load_settings()
    except RuntimeError as error:
        raise SystemExit(str(error)) from error
    settings = replace(
        settings, registrations_path=Path(args.registrations).expanduser()
    )
    asyncio.run(
        register_chat(
            args.register, settings.token, settings.registrations_path
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
