from pathlib import Path

import pytest

from config import load_settings


def test_missing_token_raises():
    with pytest.raises(RuntimeError, match="TG_ROUTER_TOKEN"):
        load_settings({})


def test_whitespace_only_token_raises():
    with pytest.raises(RuntimeError, match="TG_ROUTER_TOKEN"):
        load_settings({"TG_ROUTER_TOKEN": "   "})


def test_strips_token():
    assert (
        load_settings({"TG_ROUTER_TOKEN": "  abc:def "}).token == "abc:def"
    )


def test_env_path_override():
    settings = load_settings(
        {"TG_ROUTER_TOKEN": "t", "TG_ROUTER_REGISTRATIONS": "/tmp/x.xml"}
    )
    assert settings.registrations_path == Path("/tmp/x.xml")


def test_default_path():
    settings = load_settings({"TG_ROUTER_TOKEN": "t"})
    assert settings.registrations_path == Path("./registrations.xml")
