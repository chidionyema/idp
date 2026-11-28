"""Falsifier for bin/estate-founder-gate: known-bad must be refused, known-good admitted."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "estate-founder-gate"
_loader = importlib.machinery.SourceFileLoader("estate_founder_gate", str(SCRIPT))
_spec = importlib.util.spec_from_loader("estate_founder_gate", _loader)
g = importlib.util.module_from_spec(_spec)
_loader.exec_module(g)

GOOD_DONE = (
    "Friction producer merged\nProof: https://github.com/o/r/actions/runs/1 exit=0"
)
GOOD_ACTION = "Seal the delegate policy\nDo: approve the environment\nhttps://github.com/o/r/issues/8032"


def reasons(kind, text):
    return g.judge(kind, text)[1]


def test_known_good_messages_are_admitted():
    assert g.judge("DONE", GOOD_DONE) == ("ADMIT", [])
    assert g.judge("ACTION", GOOD_ACTION) == ("ADMIT", [])
    assert g.judge("FAILED", "Deploy failed\nProof: exit 1 at abcdef1") == ("ADMIT", [])


def test_empty_and_bad_kind_are_refused_never_admitted():
    assert g.judge("DONE", "") == ("REFUSE", ["EMPTY"])
    assert g.judge("DONE", "   \n ") == ("REFUSE", ["EMPTY"])
    assert g.judge("DONE", None) == ("REFUSE", ["EMPTY"])
    assert g.judge("CHAT", GOOD_DONE) == ("REFUSE", ["KIND"])


def test_done_without_proof_is_refused_and_one_change_fixes_it():
    assert "NO_PROOF" in reasons("DONE", "Merged\nit works now")
    assert "NO_PROOF" in reasons("DONE", "Merged\nProof: it works")
    assert reasons("DONE", "Merged\nProof: exit=0") == []


def test_action_needs_one_do_line_and_a_link():
    assert "NO_ACTION" in reasons("ACTION", "Seal it\nhttps://x.io/1")
    assert "NO_ACTION" in reasons("ACTION", "Seal it\nDo: approve")
    assert reasons("ACTION", GOOD_ACTION) == []


def test_secret_is_refused_not_redacted():
    leak = "Done\nProof: exit=0\nkey sk-abcdefghijklmnopqrstuv"
    assert "SECRET" in reasons("DONE", leak)
    assert "SECRET" in reasons("DONE", "Done\nProof: exit=0\nghp_" + "a" * 24)
    assert "SECRET" in reasons("DONE", "Done\nProof: exit=0\nbot1234567:" + "A" * 30)


def test_filler_apology_and_narration_are_refused():
    for phrase in (
        "I'll fix it",
        "Sorry about that",
        "Unfortunately it broke",
        "Let me know",
    ):
        assert "FILLER" in reasons("DONE", f"Merged\nProof: exit=0\n{phrase}")
    assert reasons("DONE", "Merged\nProof: exit=0\nrebuilt in 31 s") == []


def test_length_headline_and_fence_limits():
    assert "HEADLINE" in reasons("DONE", "x" * 101 + "\nProof: exit=0")
    assert "LENGTH" in reasons("DONE", "Merged\nProof: exit=0\n" + "y" * 900)
    assert "LENGTH" in reasons(
        "DONE", "Merged\nProof: exit=0\n" + "\n".join("z" for _ in range(12))
    )
    assert "FENCE" in reasons("DONE", "Merged\nProof: exit=0\n```x```")


def test_every_reason_is_reported_not_just_the_first():
    got = reasons("DONE", "I'll try\nsk-abcdefghijklmnopqrstuv")
    assert {"FILLER", "SECRET", "NO_PROOF"} <= set(got)


def test_payload_is_quiet_for_done_and_loud_for_failed_and_action():
    done = g.payload("DONE", GOOD_DONE, "k1")
    assert done["disable_notification"] is True and done["edit_key"] == "k1"
    assert "reply_markup" not in done
    failed = g.payload("FAILED", "Deploy failed\nProof: exit 1", None)
    assert failed["disable_notification"] is False
    act = g.payload("ACTION", GOOD_ACTION, None)
    assert act["disable_notification"] is False
    assert (
        act["reply_markup"]["inline_keyboard"][0][0]["url"]
        == "https://github.com/o/r/issues/8032"
    )
    assert "chat_id" not in done


def run(args, text):
    return subprocess.run(  # noqa: S603
        [sys.executable, "-I", str(SCRIPT), *args],
        input=text,
        capture_output=True,
        text=True,
    )


def test_cli_exit_codes_and_one_json_object():
    ok = run(["--kind", "DONE"], GOOD_DONE)
    assert ok.returncode == 0 and json.loads(ok.stdout)["verdict"] == "ADMIT"
    bad = run(["--kind", "DONE"], "it works")
    assert bad.returncode == 1 and json.loads(bad.stdout)["verdict"] == "REFUSE"
    assert run(["--kind", "DONE"], "").returncode == 1


def test_a_broken_rule_is_noticed():
    saved = g.PROOF
    try:
        g.PROOF = g.re.compile(
            r".*"
        )  # a proof rule that accepts anything must lose the bad case
        assert "NO_PROOF" not in reasons("DONE", "Merged\nit works now")
    finally:
        g.PROOF = saved
    assert "NO_PROOF" in reasons("DONE", "Merged\nit works now")


def test_selftest_reads_eight_and_a_broken_rule_reads_less(capsys):
    assert g.selftest() == 0
    assert capsys.readouterr().out == "optimus.founder_gate.falsifiers_passing=8\n"
    saved = g.PROOF
    try:
        g.PROOF = g.re.compile(r".*")
        g.selftest()
        assert capsys.readouterr().out != "optimus.founder_gate.falsifiers_passing=8\n"
    finally:
        g.PROOF = saved


def test_catalogue_registers_the_gate_metric_with_the_exact_argv():
    cat = json.loads((ROOT / "catalog" / "optimus-metrics.json").read_text())
    entry = {x["name"]: x for x in cat["metrics"]}["founder_gate.falsifiers_passing"]
    assert entry["measure"] == ["python3", "bin/estate-founder-gate", "--selftest"]
    assert entry["better"] == "higher" and entry["owner"] and entry["description"]
