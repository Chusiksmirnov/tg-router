import argparse
import asyncio
import os
from pathlib import Path

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
    token = os.environ.get("TG_ROUTER_TOKEN")
    if not token:
        raise SystemExit("TG_ROUTER_TOKEN environment variable must be set")
    asyncio.run(
        register_chat(
            args.register,
            token.strip(),
            Path(args.registrations).expanduser(),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
