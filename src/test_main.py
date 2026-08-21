import pytest

from main import main


def test_invalid_name_rejected():
    with pytest.raises(SystemExit, match="Invalid registration name"):
        main(["--register", "bad name!"])


def test_empty_name_rejected():
    with pytest.raises(SystemExit, match="Invalid registration name"):
        main(["--register", ""])


def test_valid_name_registers(monkeypatch, tmp_path):
    monkeypatch.setenv("TG_ROUTER_TOKEN", "token")
    calls = []

    async def fake_register_chat(name, token, registrations_path):
        calls.append((name, token, registrations_path))

    monkeypatch.setattr("main.register_chat", fake_register_chat)
    path = tmp_path / "regs.xml"

    assert main(["--register", "alerts", "-r", str(path)]) == 0

    assert calls == [("alerts", "token", path)]


def test_env_registrations_path_used_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("TG_ROUTER_TOKEN", "token")
    env_path = tmp_path / "env-regs.xml"
    monkeypatch.setenv("TG_ROUTER_REGISTRATIONS", str(env_path))
    calls = []

    async def fake_register_chat(name, token, registrations_path):
        calls.append((name, token, registrations_path))

    monkeypatch.setattr("main.register_chat", fake_register_chat)

    assert main(["--register", "alerts"]) == 0

    assert calls == [("alerts", "token", env_path)]
