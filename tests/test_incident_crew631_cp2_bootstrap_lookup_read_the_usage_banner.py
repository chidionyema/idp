"""crew#631 CP2, 2026-08-31: the founder's bootstrap looked identity-domain objects up with
`oci identity-domains <resource> list`, a command the CLI it runs from (3.90.3) does not have. The
CLI printed its usage banner on stdout, the lookup swallowed stderr and took the banner as the id,
the trust PATCH went to /IdentityPropagationTrusts/Usage:%20oci... and every bootstrap since
2026-08-26 printed "trust github-actions-estate rule PATCH refused: " with no detail. The same run
also read ./verdict.json in the backstage prover (nothing writes it) behind `|| true`, and graded a
refused UPDATE as ACCEPTED. Three silent greens, one class: an answer nobody checked the shape of.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "bin" / "idp-oci-bootstrap"
VERDICT = ROOT / "bin" / "idp-verdict"
WORKFLOWS = ROOT / ".github" / "workflows"


def test_bootstrap_lookup_is_a_scim_get_never_the_cli_list_command():
    src = BOOTSTRAP.read_text()
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    assert "oci identity-domains" not in code, (
        "the CLI list command prints a usage banner, not an id"
    )
    body = re.search(r"^scim_find\(\) \{\n(.*?)^\}", src, re.S | re.M)
    assert body, "scim_find is a multi-line function"
    assert "raw-request" in body.group(1) and "?filter=" in body.group(1)


def test_prover_workflows_store_the_file_the_prover_wrote_and_a_store_failure_is_red():
    for wf in ("verdict-backstage.yml", "verdict-langfuse.yml"):
        lines = [
            ln
            for ln in (WORKFLOWS / wf).read_text().splitlines()
            if "idp-verdict store" in ln
        ]
        assert lines, f"{wf}: no store step"
        for ln in lines:
            assert '"$RUNNER_TEMP/verdict.json"' in ln, f"{wf}: {ln.strip()}"
            code = ln.split("#", 1)[0]
            assert "|| true" not in code, f"{wf}: a store Traceback must not read green"


# --- the refusal side of the wall (founder, 2026-08-31: "what do you mean by live") -------------
# Prover-side live was measured (a signed row stored); the refusal side was UNKNOWN because no run
# had ever tried the key as a non-prover. bin/idp-verdict key-wall grades the ExternalSecret
# backstage/verdict-key-wall (platform/verification, its own Flux row): refused is ok, synced is
# FAIL, absent is BLIND. The prover workflow calls it on every run, with no `|| true`.


def _grade_key_wall():
    import importlib.machinery
    import importlib.util

    loader = importlib.machinery.SourceFileLoader(
        "idp_verdict", str(ROOT / "bin" / "idp-verdict")
    )
    spec = importlib.util.spec_from_loader("idp_verdict", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod.grade_key_wall


def _es(status, message, synced=None):
    obj = {
        "metadata": {"name": "verdict-key-wall", "namespace": "backstage"},
        "status": {},
    }
    if status is not None:
        obj["status"]["conditions"] = [
            {
                "type": "Ready",
                "status": status,
                "reason": "SecretSyncedError" if status == "False" else "SecretSynced",
                "message": message,
            }
        ]
    if synced:
        obj["status"]["syncedResourceVersion"] = synced
    return obj


def test_key_wall_refused_by_the_vault_is_the_wall_standing(capsys):
    grade = _grade_key_wall()
    assert (
        grade(
            _es(
                "False",
                "could not get secret data from provider: NotAuthorizedOrNotFound (404)",
            )
        )
        == 0
    )
    assert capsys.readouterr().out.startswith("ok ")


def test_key_wall_synced_means_a_pod_read_the_signing_key(capsys):
    grade = _grade_key_wall()
    assert grade(_es("True", "secret synced", synced="1-abc")) == 1
    assert capsys.readouterr().out.startswith("FAIL")
    # a synced version with a stale False condition is still a breach, never a green
    assert grade(_es("False", "NotAuthorizedOrNotFound", synced="1-abc")) == 1


def test_key_wall_with_no_verdict_yet_is_blind_not_green(capsys):
    grade = _grade_key_wall()
    assert grade(_es(None, "")) == 2
    assert capsys.readouterr().out.startswith("BLIND")
    # refused for a reason that is not the vault's (store missing, bad ref) is not the wall either
    assert grade(_es("False", 'ClusterSecretStore "estate-vault" not found')) == 2


def test_prover_workflow_calls_key_wall_without_a_swallow():
    text = (ROOT / ".github/workflows/verdict-backstage.yml").read_text()
    lines = [ln for ln in text.splitlines() if "bin/idp-verdict key-wall" in ln]
    assert lines, "verdict-backstage never asks whether the wall stands"
    assert all("|| true" not in ln.split("#", 1)[0] for ln in lines)


def _verdict_module():
    import importlib.machinery
    import importlib.util

    loader = importlib.machinery.SourceFileLoader(
        "idp_verdict", str(ROOT / "bin" / "idp-verdict")
    )
    spec = importlib.util.spec_from_loader("idp_verdict", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class _Ran:
    def __init__(self, rc, out):
        self.returncode, self.stdout, self.stderr = rc, out, ""


def test_key_wall_is_dispatched_never_the_usage_banner(capsys, monkeypatch):
    """2026-08-31, run 33354177734: the merged grader existed but main() did not dispatch
    `key-wall`, so the runner printed the usage banner and exit 2 every hour; the tests had
    graded the function and never the command. This one runs the command."""
    import json

    mod = _verdict_module()
    generic = _es("False", "could not get secret data from provider")
    events = {
        "items": [
            {
                "involvedObject": {"name": "verdict-key-wall"},
                "reason": "UpdateFailed",
                "message": "error processing spec.data[0] (key: verdict-hmac-key), err: Secrets service "
                "failed to GetSecretBundleByName, HTTP status code 404: Authorization failed or "
                "requested resource not found.",
            }
        ]
    }

    def fake_run(argv, **kw):
        return _Ran(0, json.dumps(events if "events" in argv else generic))

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    assert mod.main(["key-wall"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("ok      verdict  key-wall"), out
    assert "404" in out
    assert "bin/idp-verdict sign" not in out  # the usage banner


def test_key_wall_generic_condition_without_a_refusal_event_stays_blind(capsys):
    """A vault outage also leaves the secret unsynced with the same generic condition; without
    the vault's refusal in the events that is not a standing wall, it is BLIND (silent-green class)."""
    grade = _grade_key_wall()
    assert grade(_es("False", "could not get secret data from provider"), []) == 2
    assert capsys.readouterr().out.startswith("BLIND")
