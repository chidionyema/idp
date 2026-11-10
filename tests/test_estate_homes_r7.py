"""R7 regression tests: a blind probe must never stall an executor."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path

IDP = Path(__file__).resolve().parent.parent
DOOR = IDP / "bin/idp-estate-homes"


def _load():
    loader = importlib.machinery.SourceFileLoader("estate_homes_r7", str(DOOR))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


door = _load()


def test_service_filter_precedes_vault_resolution(monkeypatch):
    seen = []
    monkeypatch.setattr(
        door, "resolve_secret", lambda name, env: seen.append(name) or ""
    )
    key_a = "_".join(("ONLY", "THIS", "SECRET"))
    key_b = "_".join(("UNRELATED", "SECRET"))
    config = {
        "services": [
            {"service": "one", "legs": [{"name": "a", "url": "", "secret": key_a}]},
            {"service": "two", "legs": [{"name": "b", "url": "", "secret": key_b}]},
        ]
    }
    rows = door.grade(config, {}, only="one")
    assert len(rows) == 1
    assert rows[0]["service"] == "one"
    assert seen == [key_a]


def test_vault_command_has_a_short_hard_timeout(monkeypatch):
    def fake_run(args, **kwargs):
        assert args[:2] == [str(IDP / "bin/idp-cloud"), "secret"]
        assert kwargs["timeout"] <= 6.0
        return type("Result", (), {"stdout": "", "returncode": 1})()

    monkeypatch.setattr(door.subprocess, "run", fake_run)
    assert door.vault_get("unavailable") == ""


def test_offline_mode_does_not_use_network_vault_or_github(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline must not call live dependencies")

    monkeypatch.setattr(door, "probe", forbidden)
    monkeypatch.setattr(door, "vault_get", forbidden)
    monkeypatch.setattr(door, "_gh", forbidden)
    monkeypatch.setenv("GROQ_API_KEY", "canary-secret-not-for-output")

    assert door.main(["--service", "llm-router", "--offline", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["mode"] == "offline"
    assert data["availability"] == "NOT_MEASURED"
    assert data["inventory"][0]["service"] == "llm-router"
    assert "canary-secret-not-for-output" not in json.dumps(data)
    assert any(
        leg["secret_in_environment"]
        for leg in data["inventory"][0]["legs"]
        if leg["provider"] == "groq"
    )


def test_offline_gate_cannot_certify_a_live_service(capsys):
    code = door.main(["--service", "llm-router", "--offline", "--gate"])
    assert code == 1  # the documented host:laptop selector is a single point
    assert "NOT_MEASURED" in capsys.readouterr().out


def test_missing_secret_explains_cause_without_filing(monkeypatch, tmp_path, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("--remedy must not file issues")

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(door, "resolve_secret", lambda name, env: "")
    monkeypatch.setattr(door, "_gh", forbidden)

    secret_name = "_".join(("GROQ", "API", "KEY"))
    leg = {
        "name": "groq free tier",
        "provider": "groq",
        "role": "floor",
        "url": "https://api.groq.com/openai/v1/models",
        "secret": secret_name,
        "headers": {"Authorization": "Bearer ${GROQ_API_KEY}"},
    }
    path = tmp_path / "single.json"
    path.write_text(
        json.dumps({"services": [{"service": "llm-router", "legs": [leg]}]})
    )

    args = ["--config", str(path), "--service", "llm-router", "--why", "--remedy"]
    assert door.main(args) == 0
    output = capsys.readouterr().out
    assert "GROQ_API_KEY" in output
    assert "provider not queried" in output
    assert "REMEDY:" in output and "WHY:" in output


def test_unknown_service_is_not_an_all_clear(capsys):
    assert door.main(["--service", "not-a-service", "--offline"]) == 2
    assert "unknown service" in capsys.readouterr().err


def test_workflow_references_secret_names_not_values():
    workflow = (IDP / ".github/workflows/estate-homes-drill.yml").read_text()
    assert "GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}" in workflow
    assert "LIFEBOAT_KEY: ${{ secrets.LIFEBOAT_KEY }}" in workflow
