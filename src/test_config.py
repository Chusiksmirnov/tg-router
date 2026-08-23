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
        load_settings(
            {"TG_ROUTER_TOKEN": "  abc:def ", "TG_ROUTER_API_KEY": "key"}
        ).token
        == "abc:def"
    )


def test_env_database_path_override():
    settings = load_settings(
        {
            "TG_ROUTER_TOKEN": "t",
            "TG_ROUTER_API_KEY": "key",
            "TG_ROUTER_DATABASE": "/tmp/router.db",
        }
    )
    assert settings.database_path == Path("/tmp/router.db")


def test_default_database_path():
    settings = load_settings({"TG_ROUTER_TOKEN": "t", "TG_ROUTER_API_KEY": "key"})
    assert settings.database_path == Path("./registrations.db")


def test_registration_ttl_defaults_to_ten_minutes():
    settings = load_settings({"TG_ROUTER_TOKEN": "t", "TG_ROUTER_API_KEY": "key"})
    assert settings.registration_ttl_seconds == 600


def test_registration_ttl_can_be_configured():
    settings = load_settings(
        {
            "TG_ROUTER_TOKEN": "t",
            "TG_ROUTER_API_KEY": "key",
            "TG_ROUTER_REGISTRATION_TTL_SECONDS": "30",
        }
    )
    assert settings.registration_ttl_seconds == 30


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_registration_ttl_must_be_a_positive_integer(value: str):
    with pytest.raises(RuntimeError, match="TG_ROUTER_REGISTRATION_TTL_SECONDS"):
        load_settings(
            {
                "TG_ROUTER_TOKEN": "t",
                "TG_ROUTER_API_KEY": "key",
                "TG_ROUTER_REGISTRATION_TTL_SECONDS": value,
            }
        )


def test_missing_api_key_raises():
    with pytest.raises(RuntimeError, match="TG_ROUTER_API_KEY"):
        load_settings({"TG_ROUTER_TOKEN": "t"})


def test_strips_api_key():
    settings = load_settings(
        {"TG_ROUTER_TOKEN": "t", "TG_ROUTER_API_KEY": "  secret-key  "}
    )
    assert settings.api_key == "secret-key"
