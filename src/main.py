import argparse
import asyncio
from pathlib import Path

from telegram import register_chat


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register a Telegram bot and its chat for message routing"
    )
    parser.add_argument("--register", required=True, help="registration name")
    parser.add_argument("--token", required=True, help="bot token from BotFather")
    parser.add_argument(
        "-r",
        "--registrations",
        default="./registrations.xml",
        help="path to the registrations XML file",
    )
    args = parser.parse_args(argv)
    if not args.token.strip():
        parser.error("--token must not be empty")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    asyncio.run(
        register_chat(
            args.register,
            args.token.strip(),
            Path(args.registrations).expanduser(),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
