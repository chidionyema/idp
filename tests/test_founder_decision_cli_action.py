"""`bin/founder-decision ask --kind action --proof ...`: the CLI half of the founder-action door.

The Door is stubbed, so nothing is sent. Falsifiers: an action without proof is refused before
any message; an unknown kind is refused by argparse; a good action reaches the Door with its
kind and proof intact; a plain ask still asks a decision.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "founder-decision"


def _cli():
    loader = importlib.machinery.SourceFileLoader("founder_decision_cli", str(SCRIPT))
    spec = importlib.util.spec_from_loader("founder_decision_cli", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class _Door:
    seen: list = []

    def __init__(self, **_kw):
        pass

    def ask(self, request, take_webhook=False):
        _Door.seen.append(request)
        return {"ok": True, "decision_id": request.decision_id, "state": "asked"}


@pytest.fixture
def cli(monkeypatch):
    module = _cli()
    real_load = module._load

    def load():
        lib = real_load()
        lib.Door = _Door
        return lib

    monkeypatch.setattr(module, "_load", load)
    _Door.seen = []
    return module


def test_action_without_proof_is_refused_and_nothing_is_asked(cli, capsys, tmp_path):
    code = cli.main(
        [
            "--state",
            str(tmp_path / "s.json"),
            "ask",
            "--kind",
            "action",
            "--question",
            "Share the folder",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 1 and out["ok"] is False and "proof" in out["error"]
    assert _Door.seen == []


def test_unknown_kind_is_refused_by_argparse(cli, tmp_path):
    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "--state",
                str(tmp_path / "s.json"),
                "ask",
                "--kind",
                "chat",
                "--question",
                "x",
            ]
        )
    assert exc.value.code == 2


def test_action_with_proof_reaches_the_door_with_default_buttons(cli, capsys, tmp_path):
    code = cli.main(
        [
            "--state",
            str(tmp_path / "s.json"),
            "ask",
            "--kind",
            "action",
            "--proof",
            "gh variable list shows GCP_SERVICE_ACCOUNT_EMAIL",
            "--question",
            "Share the Drive folder with the service account as Viewer",
        ]
    )
    assert code == 0 and json.loads(capsys.readouterr().out)["ok"] is True
    (request,) = _Door.seen
    assert request.kind == "action"
    assert request.proof == "gh variable list shows GCP_SERVICE_ACCOUNT_EMAIL"
    assert [o.key if hasattr(o, "key") else o["key"] for o in request.options] == [
        "done",
        "cannot",
    ]


def test_plain_ask_is_still_a_decision(cli, capsys, tmp_path):
    code = cli.main(
        [
            "--state",
            str(tmp_path / "s.json"),
            "ask",
            "--question",
            "Ship it?",
            "--options",
            "ship: yes, hold: no",
        ]
    )
    assert code == 0
    capsys.readouterr()
    (request,) = _Door.seen
    assert request.kind == "decision" and request.proof == ""
