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


def test_bootstrap_lookup_only_returns_a_32_hex_id():
    body = re.search(
        r"^scim_find\(\) \{\n(.*?)^\}", BOOTSTRAP.read_text(), re.S | re.M
    ).group(1)
    assert "[ ${#id} -eq 32 ]" in body and "*[!0-9a-f]*" in body


def test_every_lookup_names_a_scim_endpoint():
    calls = re.findall(r"scim_find (\S+) ", BOOTSTRAP.read_text())
    assert calls, "no scim_find call sites"
    for res in calls:
        assert res[0].isupper(), (
            f"{res}: SCIM endpoints are capitalised (Users, Groups, Apps, ...)"
        )


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


def test_refuse_test_counts_a_missing_grant_as_a_refusal():
    src = VERDICT.read_text()
    assert '("append-only" in err2 or "permission denied" in err2)' in src
    assert "ACCEPTED: the statement ran" in src
