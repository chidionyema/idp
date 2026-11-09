"""The Run Command queue guard, and the falsifiers it must reject.

Class: a guard that reports the SAFE state as BLIND. Measured 2026-11-09 on
idp#7334: `oci instance-agent command-execution list --lifecycle-state ACCEPTED`
answers a `--query data[].id` that selects nothing with NO output at all
(0 bytes, exit 0), while the unfiltered list of the same endpoint returned 8
commands. `json.loads('')` raised, so `require_idle_command_queue` reported
"BLIND unable to attest ACCEPTED OCI command queue ... Expecting value: line 1
column 1 (char 0)" and blocked every recovery run against a host whose command
queue was in fact empty.

An empty answer is an empty queue. It is not an outage, and it is not blindness.
A non-empty answer that is not JSON is still BLIND, because that is a real fault.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_MODULE = Path(__file__).resolve().parents[1] / "platform/oci/recovery/run-command.py"


def _load():
    spec = importlib.util.spec_from_file_location("recovery_run_command", _MODULE)
    assert spec and spec.loader, f"cannot load {_MODULE}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rc = _load()


# --- the known-good the guard must ACCEPT -----------------------------------


@pytest.mark.parametrize("raw", ["", "   ", "\n", None])
def test_empty_answer_is_an_empty_queue(raw):
    """The exact production shape: no output means no command in flight."""
    assert rc._parse_command_ids(raw) == []


def test_a_real_command_list_round_trips():
    ids = ["ocid1.instanceagentcommandexecution.oc1..aaa", "ocid1...bbb"]
    assert rc._parse_command_ids(json.dumps(ids)) == ids


# --- the known-bad the guard must REJECT (the falsifier) --------------------


@pytest.mark.parametrize(
    "raw", ["not json", "Query returned empty result", "{", "<html>500</html>"]
)
def test_non_empty_garbage_is_still_blind(raw):
    """A real fault must never be swallowed into "queue is empty".

    `Query returned empty result, no output to show.` is literal CLI prose that
    reached this parser on a failed `--query` (measured same session); treating
    it as an empty queue would hide a broken query behind a green guard.
    """
    with pytest.raises(json.JSONDecodeError):
        rc._parse_command_ids(raw)


def test_the_guard_still_blocks_on_a_real_in_flight_command(monkeypatch):
    """The whole point of the guard: an occupied queue refuses new work."""

    class TransportError(RuntimeError):
        pass

    monkeypatch.setattr(
        rc,
        "_oci",
        lambda *a, **k: json.dumps(["ocid1.instanceagentcommandexecution.oc1..held"]),
    )
    monkeypatch.setattr(rc, "TransportError", TransportError)
    monkeypatch.setattr(rc, "say", lambda *a, **k: None)
    with pytest.raises(TransportError, match="BLOCKED OCI Run Command"):
        rc.require_idle_command_queue(
            "ocid1.compartment.oc1..x", "ocid1.instance.oc1..y"
        )


def test_the_guard_passes_on_the_empty_answer_that_was_breaking_it(monkeypatch):
    """The regression itself: this exact input used to raise BLIND."""
    monkeypatch.setattr(rc, "_oci", lambda *a, **k: "")
    monkeypatch.setattr(rc, "say", lambda *a, **k: None)
    rc.require_idle_command_queue("ocid1.compartment.oc1..x", "ocid1.instance.oc1..y")
