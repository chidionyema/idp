"""The founder.decision intent carries `kind` and `proof` to bin/founder-decision.

Reuses the executor-faithful renderer of test_founder_decision_intent_ask_path: every argument
shell-quoted, an unset argument rendered as ''. Falsifiers: a default ask still says
`--kind decision` with an empty proof; an action carries `--kind action` and its proof as ONE
argument; the rendered step stays valid shell.
"""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "intent_ask_path", HERE / "test_founder_decision_intent_ask_path.py"
)
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

PROOF = "gh variable list shows GCP_SERVICE_ACCOUNT_EMAIL"


def _recorded(tmp_path, **overrides):
    args = base.defaults()
    args["question"] = "Share the Drive folder with the service account as Viewer"
    args.update(overrides)
    rc, out, recorded = base.run_rendered(base.step_cmd(), args, tmp_path)
    assert rc == 0, out
    return recorded


def test_default_ask_is_a_decision_with_no_proof(tmp_path):
    recorded = _recorded(tmp_path)
    assert recorded[recorded.index("--kind") + 1] == "decision"
    assert recorded[recorded.index("--proof") + 1] == ""


def test_action_carries_kind_and_proof_as_single_arguments(tmp_path):
    recorded = _recorded(tmp_path, kind="action", proof=PROOF)
    assert recorded[recorded.index("--kind") + 1] == "action"
    assert recorded[recorded.index("--proof") + 1] == PROOF


def test_kind_and_proof_follow_the_verb(tmp_path):
    recorded = _recorded(tmp_path, kind="action", proof=PROOF)
    assert recorded.index("ask") < recorded.index("--kind")


def test_rendered_action_step_parses_as_shell():
    args = {**base.defaults(), "question": "q", "kind": "action", "proof": PROOF}
    proc = subprocess.run(
        ["bash", "-n"],
        input=base.render(base.step_cmd(), args),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
