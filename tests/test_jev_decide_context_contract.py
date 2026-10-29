"""The `jev.decide` context contract, made safe for the next caller.

THE TRAP THIS FILE EXISTS FOR (measured 2026-10-27). A caller passed a context whose root
object was closed before its last member. The JSON parse died deep inside the call, and the
caller could not tell a bad argument from a broken decision layer.

Two things were true at once, and neither was obvious:

1. **The context was never a quoting problem.** The executor shell-quotes every `{{arg}}`
   (`platform/estate/bin/estate-execute`, `interpolate()`), and the intent's step passes it as
   `"${args[@]}"`. Whitespace and braces inside a JSON context arrive as ONE argument. The
   quoting is proved below against the executor's own function, not assumed.
2. **An unavailable layer is not an answer.** ADR 0030's fallback is a null answer with
   `escalated=true`: the layer was consulted and could not answer. A caller that reads
   `answer=None` as a decision has turned an escalation into a verdict. The printed line now
   carries `route=human_review` so that cannot be read silently.

Every test here can fail, and each one fails on a real defect.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "platform" / "estate" / "libexec" / "jev-decide.py"
INTENT = REPO / "platform" / "estate" / "intents" / "jev.decide.yaml"
EXECUTOR = REPO / "platform" / "estate" / "bin" / "estate-execute"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"{path} must be importable"
    module = importlib.util.module_from_spec(spec)
    # Registered before it runs: a dataclass looks its own module up in sys.modules while the
    # class body is created (measured 2026-10-27, python 3.9).
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


jev_decide = _load(SCRIPT, "estate_jev_decide")


def _executor_interpolate():
    """The executor's own interpolation, imported from the file that runs every intent."""
    source = EXECUTOR.read_text()
    match = re.search(r"^def interpolate\(cmd, args\):.*?(?=^\S)", source, re.S | re.M)
    assert match, "estate-execute must define interpolate()"
    namespace: dict = {"shlex": __import__("shlex")}
    exec(match.group(0), namespace)  # noqa: S102 - the estate's own function, read from source
    return namespace["interpolate"]


# --- the context is validated before the layer is consulted -----------------------


def test_a_malformed_context_is_refused_before_the_layer_is_loaded(monkeypatch, capsys):
    """A bad argument must not cost a call, a vendor round trip, or a row in jev_decisions."""
    loaded = []

    def _never(repo):
        loaded.append(repo)
        raise AssertionError("the layer must not be loaded for a malformed context")

    monkeypatch.setattr(jev_decide, "_load_layer", _never)

    code = jev_decide.main(["--question", "q", "--id", "d", "--context", '{"a": 1,}'])
    assert code == 2
    err = capsys.readouterr().err
    assert "not JSON" in err
    assert loaded == []

    code = jev_decide.main(["--question", "q", "--id", "d", "--context", "[1, 2]"])
    assert code == 2
    assert "must be a JSON object" in capsys.readouterr().err
    assert loaded == []


def test_a_context_error_never_echoes_the_context(monkeypatch, capsys):
    """The context is evidence, and evidence can be sensitive."""
    # Not named "secret": ruff's S105 reads a variable called secret as a hardcoded password,
    # and py-strict (E9,F,B,S over the push diff) refuses the file for it.
    canary = "s3cr3t-value-inside-the-context"
    monkeypatch.setattr(
        jev_decide, "_load_layer", lambda repo: pytest.fail("must not be called")
    )
    jev_decide.main(["--question", "q", "--id", "d", "--context", '{"a": ' + canary])
    assert canary not in capsys.readouterr().err


# --- an unavailable layer is an escalation, not an answer -------------------------


class _FakeLayer:
    """A layer that was consulted and could not answer (ADR 0030's fallback shape)."""

    def __init__(self, result):
        self.result = result

    def jev_noul(self, **kwargs):
        return self.result

    def jev_choice(self, **kwargs):
        return self.result

    def jev_score(self, **kwargs):
        return self.result

    DEFAULT_FLOOR = 0.7


def test_an_unavailable_layer_is_marked_for_review_not_read_as_an_answer(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        jev_decide,
        "_load_layer",
        lambda repo: _FakeLayer(
            {
                "decision": None,
                "confidence": None,
                "escalated": True,
                "_fallback": "jev_unavailable",
            }
        ),
    )
    code = jev_decide.main(["--question", "q", "--id", "d", "--context", "{}"])
    out = capsys.readouterr().out
    assert code == 0, "a decision is not a failure; an escalation is not an error"
    assert "escalated=True" in out
    assert "_fallback=jev_unavailable" in out
    assert "route=human_review" in out, "an escalation must say where it goes"


def test_a_real_decision_is_not_marked_for_review(monkeypatch, capsys):
    monkeypatch.setattr(
        jev_decide,
        "_load_layer",
        lambda repo: _FakeLayer(
            {"decision": True, "confidence": 0.83, "escalated": False}
        ),
    )
    code = jev_decide.main(["--question", "q", "--id", "d", "--context", "{}"])
    out = capsys.readouterr().out
    assert code == 0
    assert "answer=True" in out
    assert "confidence=0.83" in out
    assert "route=human_review" not in out


# --- the quoting, proved against the executor's own function ----------------------


def test_a_json_context_survives_the_executor_as_one_argument():
    """Whitespace inside a JSON context is NOT the trap. Prove it with the real function."""
    interpolate = _executor_interpolate()
    context = '{"chokepoints": ["a", "b"], "note": "two words"}'
    step = (
        "args=(--question {{question}} --id {{id}} --context {{context}}); "
        'printf "%s\\n" "${#args[@]}"; '
        'for a in "${args[@]}"; do printf "[%s]\\n" "$a"; done'
    )
    command = interpolate(step, {"question": "q", "id": "d", "context": context})
    result = subprocess.run(
        ["bash", "-c", command], capture_output=True, text=True, check=True
    )
    lines = result.stdout.split("\n")
    elements = [line for line in lines[1:] if line]
    # Three flags and three values. If the JSON had been split, the count would be larger.
    assert lines[0] == "6", f"the context must arrive as ONE argument, got {lines[0]!r}"
    assert len(elements) == 6
    assert elements[-1] == f"[{context}]", "the context must arrive byte-for-byte"


def test_the_intent_passes_the_context_unquoted_for_the_executor_to_quote():
    """The intent must not add its own quotes: the executor already quotes every {{arg}}."""
    text = INTENT.read_text()
    step = re.search(r"cmd: \|\n(.*)", text, re.S)
    assert step, "the intent must have a command"
    assert "--context {{context}}" in step.group(1)
    assert "'{{context}}'" not in step.group(1), (
        "double quoting breaks on a quote in the context"
    )


# --- the contract is documented where the caller reads it -------------------------


def test_the_intent_documents_the_context_contract():
    text = INTENT.read_text()
    context_line = next(
        line for line in text.splitlines() if line.strip().startswith("context:")
    )
    assert "string" in context_line.lower()
    assert "exit 2" in context_line or "refused" in context_line.lower()


def test_the_intent_says_an_escalation_is_not_a_no():
    text = INTENT.read_text().lower()
    assert "escalation is not a no" in text
    assert "human review" in text
