"""crew#66, 2026-08-28: asked to wire Tailscale, an agent proposed a manual setup step --
mint an OAuth client in a console and hand the value to the vault secret the PR names. The
founder caught it in the plan, not in CI, because the estate had a playbook against manual
toil and no guard (LAW 44). Founder, verbatim: "we must make it mathematically impossible for
an agent to merge one."

Rung 4, incident, both ways: the rejected sentence is denied, and the one human step the
estate does allow -- a LAW 47 `FOUNDER ACTION:` line naming a URL or a single word -- is
allowed, because a guard that refuses correct work is an outage (LAW 38).

On main policy/no-manual-steps.rego does not exist and every test here fails on that path.

No sockets: conftest runs against local files only, and the test skips when conftest is not
installed rather than reaching for it.
"""

import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "no-manual-steps.rego"
RUNNER = ROOT / "bin" / "idp-no-toil"

MESSAGE = (
    "Policy Violation: Instructions contain manual human toil steps. "
    "Automate the bootstrapping sequence."
)

# The sentence the founder rejected on crew#66 (comment 5451623095).
REJECTED = (
    "create one Tailscale OAuth client (scope auth_keys, tag tag:k8s) and paste it into "
    "the vault secret the PR names"
)

conftest_only = pytest.mark.skipif(
    shutil.which("conftest") is None,
    reason="conftest is not installed; CI installs the pinned v0.62.0 build",
)


def _run(payload, tmp_path, name="doc.json"):
    p = tmp_path / name
    p.write_text(json.dumps(payload))
    return subprocess.run(
        ["conftest", "test", "--parser", "json", "-p", str(POLICY), str(p)],
        capture_output=True,
        text=True,
    )


def _doc(*lines, path="docs/how-to/thing.md"):
    return {"file_path": path, "content": list(lines)}


def test_the_policy_exists_and_carries_the_founders_message_verbatim():
    assert POLICY.is_file(), f"missing {POLICY}"
    assert MESSAGE in POLICY.read_text()


@conftest_only
def test_the_rejected_sentence_is_denied(tmp_path):
    r = _run(_doc(REJECTED), tmp_path)
    assert r.returncode != 0, r.stdout
    assert MESSAGE in r.stdout


@conftest_only
@pytest.mark.parametrize(
    "line",
    [
        "You manually create the OAuth client in the admin console.",
        "Paste this value into the vault entry.",
        "Click here to generate an API key.",
        "Log into the web interface and add the tag.",
        "The founder must add the client secret before Flux reconciles.",
    ],
)
def test_every_toil_phrase_is_denied_case_insensitively(line, tmp_path):
    r = _run(_doc(line), tmp_path)
    assert r.returncode != 0, f"{line!r} was allowed:\n{r.stdout}"
    assert MESSAGE in r.stdout


@conftest_only
def test_a_founder_action_line_naming_a_url_is_allowed(tmp_path):
    r = _run(
        _doc(
            "The App is installed by CI. The one human step is a tap:",
            "FOUNDER ACTION: approve https://github.com/settings/apps/estate/installations",
        ),
        tmp_path,
    )
    assert r.returncode == 0, r.stdout


@conftest_only
def test_a_founder_action_line_naming_a_single_word_is_allowed(tmp_path):
    r = _run(_doc("FOUNDER ACTION: approve"), tmp_path)
    assert r.returncode == 0, r.stdout


@conftest_only
@pytest.mark.parametrize(
    "line",
    [
        "FOUNDER ACTION: paste the client secret at https://login.tailscale.com/admin/settings/oauth",
        "FOUNDER ACTION: copy the token from https://example.test/tokens",
        "FOUNDER ACTION: type the key into the vault",
    ],
)
def test_a_founder_action_whose_verb_is_a_hand_is_refused(line, tmp_path):
    """LAW 47 buys one tap, never a transcription."""
    r = _run(_doc(line), tmp_path)
    assert r.returncode != 0, f"{line!r} was allowed:\n{r.stdout}"
    assert MESSAGE in r.stdout


@conftest_only
def test_a_founder_action_naming_neither_a_url_nor_a_word_is_refused(tmp_path):
    r = _run(
        _doc("FOUNDER ACTION: sign in to the OCI console and add estate-tofu"), tmp_path
    )
    assert r.returncode != 0, r.stdout


@conftest_only
def test_the_pull_request_body_is_judged_by_the_same_rule(tmp_path):
    """bin/pr-report feeds reports/pr.json; the gate reads the body out of it, so the PR
    body needs no second job."""
    denied = _run({"pr": {"body": f"## What\n{REJECTED}\n"}}, tmp_path, "pr.json")
    assert denied.returncode != 0, denied.stdout
    assert MESSAGE in denied.stdout
    allowed = _run(
        {"pr": {"body": "## What\nCI mints the session from its OIDC token.\n"}},
        tmp_path,
        "pr-ok.json",
    )
    assert allowed.returncode == 0, allowed.stdout


@conftest_only
def test_a_file_outside_the_agreed_scope_is_not_judged(tmp_path):
    """The policy carries its own scope: README*.md, docs/**/*.md and platform/**. A caller
    cannot widen it by handing over a file the founder never agreed to gate -- the rego's own
    source, for one, has to be able to name the phrases it refuses."""
    r = _run(_doc(REJECTED, path="policy/no-manual-steps.rego"), tmp_path)
    assert r.returncode == 0, r.stdout


def test_the_runner_and_the_ci_job_exist():
    assert RUNNER.is_file() and RUNNER.stat().st_mode & 0o111, (
        f"missing or non-executable {RUNNER}"
    )
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "no-toil-gate:" in ci, "the gate has no job in ci.yml"
    assert "bin/idp-no-toil" in ci, "the ci.yml job does not run the gate"


def test_the_gate_is_scoped_to_the_changed_files_so_main_stays_green():
    """main carries pre-existing prose that trips the phrases (bin/idp-no-toil --sweep lists
    them). The job grades the pull request's own files, never the whole tree."""
    runs = [
        ln.strip()
        for ln in (ROOT / ".github" / "workflows" / "ci.yml").read_text().splitlines()
        if "bin/idp-no-toil" in ln and not ln.lstrip().startswith("#")
    ]
    assert runs, "ci.yml never runs bin/idp-no-toil"
    for ln in runs:
        assert "github.event.pull_request.number" in ln, ln
        assert "--sweep" not in ln, ln
