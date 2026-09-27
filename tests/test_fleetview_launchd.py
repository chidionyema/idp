"""bin/fleetview-launchd: the launchd job gets the router key from the vault's one egress, by name."""

import importlib.machinery
import importlib.util
from pathlib import Path

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
