"""bin/fleetview-launchd: the launchd job gets the router key from the vault's one egress, by name."""

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(monkeypatch, secret_load: Path):
    monkeypatch.setenv("ESTATE_SECRET_LOAD", str(secret_load))
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    loader = importlib.machinery.SourceFileLoader(
        "fleetview_launchd", str(ROOT / "bin/fleetview-launchd")
    )
    spec = importlib.util.spec_from_loader("fleetview_launchd", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_key_comes_from_secret_load_with_the_laptop_key_name(tmp_path, monkeypatch):
    fake = tmp_path / "secret-load"
    fake.write_text(
        '[ "$*" = "dev LITELLM_LAPTOP_KEY LITELLM_API_KEY" ] && printf sk-fake\n'
    )
    assert load(monkeypatch, fake).load_key() == "sk-fake"


def test_a_vault_that_cannot_answer_starts_the_board_without_voice(
    tmp_path, monkeypatch, capsys
):
    fake = tmp_path / "secret-load"
    fake.write_text("echo 'sops: cannot decrypt' >&2; exit 1\n")
    assert load(monkeypatch, fake).load_key() == ""
    assert "exit 1" in capsys.readouterr().err


def test_intent_key_prefers_the_dedicated_vault_entry(tmp_path, monkeypatch):
    fake = tmp_path / "secret-load"
    fake.write_text(
        '[ "$2" = "ESTATE_AGENT_KEY" ] && printf sk-agent\n[ "$2" = "LITELLM_LAPTOP_KEY" ] && printf sk-router\nexit 0\n'
    )
    monkeypatch.delenv("ESTATE_AGENT_KEY", raising=False)
    mod = load(monkeypatch, fake)
    assert mod.agent_key("sk-router") == ("sk-agent", "dedicated vault entry")


def test_intent_key_falls_back_to_the_router_key_silently(
    tmp_path, monkeypatch, capsys
):
    fake = tmp_path / "secret-load"
    fake.write_text("echo 'no such entry' >&2; exit 1\n")
    monkeypatch.delenv("ESTATE_AGENT_KEY", raising=False)
    mod = load(monkeypatch, fake)
    key, why = mod.agent_key("sk-router")
    assert key == "sk-router" and "router key" in why
    assert (
        "not loaded" not in capsys.readouterr().err
    )  # an absent entry is expected, not an error


def test_the_server_runs_the_tree_it_was_installed_from(tmp_path, monkeypatch):
    # Measured 2026-10-23: the editable install pointed at ~/Documents/code/idp, a checkout stuck in
    # October, so a restart staged main's intents and came back with last month's code -- production
    # `pr-list` with args was confirmed without them and ran on defaults.
    mod = load(monkeypatch, tmp_path / "secret-load")
    src = mod.runtime_src()
    assert src == (ROOT / "backstage" / "plugins" / "fleetview-backend" / "src")
    assert (src / "fleetview_backend" / "serve.py").is_file()


def test_the_tree_goes_on_pythonpath_ahead_of_the_install(tmp_path, monkeypatch):
    (tmp_path / "secret-load").write_text("exit 1\n")
    monkeypatch.setenv("PYTHONPATH", "/somewhere/else")
    mod = load(monkeypatch, tmp_path / "secret-load")
    monkeypatch.setattr(mod.os, "execv", lambda *_a: None)
    monkeypatch.setattr(mod, "load_key", lambda *_a, **_k: "")
    mod.main()
    parts = mod.os.environ["PYTHONPATH"].split(mod.os.pathsep)
    assert parts[0] == str(mod.runtime_src())
    assert "/somewhere/else" in parts


def test_a_tree_without_the_server_refuses_instead_of_borrowing_one(
    tmp_path, monkeypatch, capsys
):
    (tmp_path / "secret-load").write_text("exit 1\n")
    mod = load(monkeypatch, tmp_path / "secret-load")
    monkeypatch.setattr(mod, "runtime_src", lambda: tmp_path / "gone")
    with pytest.raises(SystemExit) as done:
        mod.main()
    assert done.value.code == 78
    assert "refusing to start" in capsys.readouterr().err


def test_intent_key_missing_says_so(tmp_path, monkeypatch):
    fake = tmp_path / "secret-load"
    fake.write_text("exit 1\n")
    monkeypatch.delenv("ESTATE_AGENT_KEY", raising=False)
    key, why = load(monkeypatch, fake).agent_key("")
    assert key == "" and "MISSING" in why
