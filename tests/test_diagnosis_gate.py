"""bin/diagnosis-gate: a router config/code change must carry a Bayesian diagnosis record.

crew#654, founder 2026-09-29: "no theories without bayesian reasoning and evidence gathering",
"why is this not enforced". These cases exercise the gate's pure decision logic (no git, no real
repository) against every branch the docstring promises: no record -> refused; a record whose
winning hypothesis falls short of 0.95 -> refused; a record that clears it -> passes; the
docs/tests-only exemption; a change that never touches the router at all.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
from pathlib import Path

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(ROOT, "bin", "diagnosis-gate")


def _load():
    loader = importlib.machinery.SourceFileLoader("diagnosis_gate", MODULE_PATH)
    spec = importlib.util.spec_from_file_location(
        "diagnosis_gate", MODULE_PATH, loader=loader
    )
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load()


DIAGNOSIS_MSG = (
    "fix: tighten the auth header check\n\nDiagnosis: docs/diagnoses/example.yaml\n"
)


def _good_diagnose(_path):
    return 0, "ok"


def _bad_diagnose(_path):
    return (
        3,
        "FAIL  estate-diagnose  winning hypothesis 'H1' posterior 0.910000 < required 0.95",
    )


def test_no_router_paths_touched_is_skipped(mod, tmp_path: Path):
    rc, msg = mod.evaluate(["docs/runbooks/foo.md", "bin/idp-ci"], [], tmp_path)
    assert rc == 0
    assert "skip" in msg


def test_router_change_with_no_diagnosis_reference_is_refused(mod, tmp_path: Path):
    rc, msg = mod.evaluate(["llm/config.yaml"], ["fix: bump timeout\n"], tmp_path)
    assert rc == 1
    assert "no `Diagnosis:" in msg


def test_router_change_referencing_a_missing_record_is_refused(mod, tmp_path: Path):
    rc, msg = mod.evaluate(["bin/litellm-local"], [DIAGNOSIS_MSG], tmp_path)
    assert rc == 1
    assert "does not exist" in msg


def test_router_change_with_sub_threshold_record_is_refused(mod, tmp_path: Path):
    (tmp_path / "docs" / "diagnoses").mkdir(parents=True)
    record = tmp_path / "docs" / "diagnoses" / "example.yaml"
    record.write_text("hypotheses: []\n")
    rc, msg = mod.evaluate(
        ["platform/llm/router.py"],
        [DIAGNOSIS_MSG],
        tmp_path,
        run_diagnose=_bad_diagnose,
    )
    assert rc == 1
    assert "did not clear posterior" in msg


def test_router_change_with_good_record_passes(mod, tmp_path: Path):
    (tmp_path / "docs" / "diagnoses").mkdir(parents=True)
    record = tmp_path / "docs" / "diagnoses" / "example.yaml"
    record.write_text("hypotheses: []\n")
    rc, msg = mod.evaluate(
        ["platform/llm/config.yaml"],
        [DIAGNOSIS_MSG],
        tmp_path,
        run_diagnose=_good_diagnose,
    )
    assert rc == 0
    assert "ok" in msg


def test_docs_and_tests_only_change_is_exempt_even_touching_docs_diagnoses(
    mod, tmp_path: Path
):
    rc, msg = mod.evaluate(
        ["docs/diagnoses/example.yaml", "tests/test_something.py"], [], tmp_path
    )
    assert rc == 0
    assert "skip" in msg


def test_diagnosis_reference_found_across_multiple_commit_messages(mod, tmp_path: Path):
    (tmp_path / "docs" / "diagnoses").mkdir(parents=True)
    record = tmp_path / "docs" / "diagnoses" / "example.yaml"
    record.write_text("hypotheses: []\n")
    rc, msg = mod.evaluate(
        ["llm/config.yaml"],
        ["unrelated commit\n", "chore: wip\n", DIAGNOSIS_MSG],
        tmp_path,
        run_diagnose=_good_diagnose,
    )
    assert rc == 0


def test_find_diagnosis_ref_parses_the_exact_commit_message_line(mod):
    assert mod.find_diagnosis_ref([DIAGNOSIS_MSG]) == "docs/diagnoses/example.yaml"
    assert mod.find_diagnosis_ref(["no reference here\n"]) is None


def test_touches_router_matches_every_named_path(mod):
    assert mod.touches_router(["llm/config.yaml"])
    assert mod.touches_router(["platform/llm/config.yaml"])
    assert mod.touches_router(["platform/llm/anthropic_beta_passthrough.py"])
    assert mod.touches_router(["bin/litellm-local"])
    assert not mod.touches_router(["bin/litellm-local.md"])
    assert not mod.touches_router(["platform/llm/README.md"])


def test_a_refusal_names_the_router_files_it_rejected(mod, tmp_path: Path):
    """The hole this closes: the FAIL printed no file, so nobody could tell which of a large
    diff tripped the gate -- and the base it judged had already moved, so the verdict could not
    be replayed either. A refusal must carry its own evidence."""
    rc, msg = mod.evaluate(
        ["README.md", "platform/llm/config.yaml", "bin/litellm-local"], [], tmp_path
    )
    assert rc == 1
    assert "Router file(s) judged:" in msg
    assert "platform/llm/config.yaml" in msg
    assert "bin/litellm-local" in msg
    # The non-router file must NOT be blamed: naming an innocent file sends the reader to the
    # wrong place, which is worse than naming nothing.
    assert "README.md" not in msg


def test_a_long_refusal_is_capped_and_counts_the_rest(mod, tmp_path: Path):
    """A refusal must not flood a log, but it must not silently truncate either."""
    files = [f"platform/llm/lane_{i}.py" for i in range(mod.MAX_NAMED_FILES + 5)]
    rc, msg = mod.evaluate(files, [], tmp_path)
    assert rc == 1
    assert "(+5 more)" in msg
    assert msg.count("platform/llm/lane_") == mod.MAX_NAMED_FILES


def test_router_hits_is_stable_and_deduplicated(mod):
    """A verdict is evidence: the same input must print the same line every time."""
    hits = mod.router_hits(
        ["platform/llm/b.py", "platform/llm/a.py", "platform/llm/b.py", "README.md"]
    )
    assert hits == ["platform/llm/a.py", "platform/llm/b.py"]


def test_an_unresolvable_base_is_blind_and_exits_nonzero(mod, tmp_path: Path, capsys):
    """GOV-016: a check whose non-execution is indistinguishable from its success is not a
    check. Before this, a bogus base raised CalledProcessError out of main() -- a traceback, not
    a verdict. It still exited non-zero, so nothing was wrongly certified, but the line never
    said what could not be judged. BLIND must be said in the gate's own voice."""
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-q", "--allow-empty", "-m", "init"],
        check=True,
    )
    rc = mod.main(["--base", "0" * 40, "--repo-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 2, "an unjudged gate must not exit 0"
    assert out.startswith("BLIND diagnosis-gate"), out
    assert "nothing was judged" in out
    assert "Traceback" not in out


def test_every_verdict_carries_the_base_it_judged(mod, tmp_path: Path, capsys):
    """A verdict that does not say which base it judged cannot be replayed once origin/main
    moves -- which is exactly why a FAIL seen at push time could not be reproduced after the
    fact. The base must ride on the skip line too, not only on a refusal."""
    import subprocess

    def git(*a: str) -> str:
        return subprocess.run(
            ["git", "-C", str(tmp_path), *a], capture_output=True, text=True, check=True
        ).stdout.strip()

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    git("commit", "-q", "--allow-empty", "-m", "init")
    base = git("rev-parse", "HEAD")
    (tmp_path / "README.md").write_text("x\n")
    git("add", "README.md")
    git("commit", "-q", "-m", "docs: readme")

    rc = mod.main(["--base", base, "--repo-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert f"base {base[:12]}" in out
    assert "1 file(s) judged" in out


def test_end_to_end_against_the_real_committed_record(mod):
    """Runs the real bin/estate-diagnose subprocess against the real crew#654 record via the
    gate's default run_diagnose -- the same path bin/idp-ci's fast gate takes in CI."""
    repo_root = Path(ROOT)
    rc, msg = mod.evaluate(
        ["llm/config.yaml"],
        [
            "fix: router\n\nDiagnosis: docs/diagnoses/2026-09-29-laptop-router-auth-errors.yaml\n"
        ],
        repo_root,
    )
    assert rc == 0
    assert "ok" in msg
