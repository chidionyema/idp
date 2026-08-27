"""crew#535: a run whose jobs all have 0 steps never started; its annotation is named once, not re-diagnosed."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "idp-actions-refused"
BILLING = "The job was not started because recent account payments have failed or your spending limit needs to be increased."


def _load():
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("idp_actions_refused", loader=None))
    mod.__file__ = str(SCRIPT)
    exec(compile(SCRIPT.read_text(), str(SCRIPT), "exec"), mod.__dict__)
    return mod


def _wire(monkeypatch, mod, runs, jobs, notes):
    def gh_json(path):
        if "/actions/runs?" in path:
            return {"workflow_runs": runs}
        if path.endswith("/jobs"):
            return {"jobs": jobs}
        if "/annotations" in path:
            return notes
        raise AssertionError(path)
    monkeypatch.setattr(mod, "gh_json", gh_json)


def test_a_zero_step_failure_with_a_billing_annotation_is_one_founder_action(monkeypatch, capsys):
    mod = _load()
    _wire(monkeypatch, mod, [{"id": 33105070038, "conclusion": "failure"}],
          [{"id": 1, "steps": []}, {"id": 2, "steps": []}], [{"message": BILLING}])
    rc = mod.main(["--repo", "chidionyema/claude-estate"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "refused  chidionyema/claude-estate run 33105070038: The job was not started" in out
    assert out.count("FOUNDER ACTION:") == 1 and "github.com/settings/billing" in out


def test_a_failure_that_ran_steps_is_a_real_failure_not_a_refusal(monkeypatch, capsys):
    mod = _load()
    _wire(monkeypatch, mod, [{"id": 7, "conclusion": "failure"}],
          [{"id": 1, "steps": [{"name": "checkout"}]}, {"id": 2, "steps": []}], [{"message": BILLING}])
    rc = mod.main(["--repo", "chidionyema/idp"])
    out = capsys.readouterr().out
    assert rc == 0 and "refused" not in out and "FOUNDER ACTION" not in out


def test_a_zero_step_failure_without_an_annotation_is_named_but_is_not_billing(monkeypatch, capsys):
    mod = _load()
    _wire(monkeypatch, mod, [{"id": 9, "conclusion": "failure"}], [{"id": 1, "steps": []}], [])
    rc = mod.main(["--repo", "chidionyema/idp"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "run 9: refused before the first step, no annotation" in out
    assert "FOUNDER ACTION" not in out
