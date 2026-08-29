"""crew#628 CP1: a claim is a command the pipeline runs, never text the author types.

Founder 2026-08-29: "NO ONE IS PROVING OR VERIFYING ANYTHING"; 30 guards read PR bodies, none read
the world; bin/idp-catalog-push exited 0 on a 403 across 10 green merges. This pins the verifier:
it parses `Verify:` lines, refuses world-changing verbs, writes generated output into the body,
grades red on a red command or on a world change with no claim, and is wired on pull_request.
"""

import importlib.machinery
import importlib.util
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def tool():
    spec = importlib.util.spec_from_file_location(
        "verify_claims", ROOT / "bin/idp-verify-claims"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_selftest_decision_table_is_green():
    assert tool().selftest() == 0


def test_verifier_only_observes_never_acts():
    m = tool()
    for cmd in (
        "kubectl apply -f x",
        "flux reconcile ks x",
        "gh pr merge 1",
        "gh workflow run x",
        "bin/idp-oke-rebuild --apply",
    ):
        assert m.allowed(cmd) is not None, cmd
    for cmd in (
        "bin/idp-cluster-state",
        "kubectl get pods -A",
        "flux get ks",
        "curl -sSf https://x/",
    ):
        assert m.allowed(cmd) is None, cmd


def test_a_world_change_with_no_claim_is_red_and_a_doc_change_is_not():
    m = tool()
    assert m.verdict([], touches_world=True) == 1
    assert m.verdict([], touches_world=False) == 0
    assert (
        m.WORLD_PATHS.match("platform/x.yaml")
        and m.WORLD_PATHS.match("bin/idp-x")
        and not m.WORLD_PATHS.match("docs/x.md")
    )


def test_generated_section_replaces_itself_and_never_the_authors_text():
    m = tool()
    body = (
        "Author text\n\n"
        + m.START
        + "\nold\n"
        + m.END
        + "\n\n## Definition of done\nrows"
    )
    out = m.splice(
        body, m.section([{"cmd": "true", "exit": 0, "out": "x"}], "run", False)
    )
    assert (
        "old" not in out
        and "Author text" in out
        and "## Definition of done" in out
        and "ok  `true` exit 0" in out
    )


def test_workflow_runs_on_every_pull_request_edit_and_can_write_the_body():
    wf = yaml.safe_load((ROOT / ".github/workflows/verify-claims.yml").read_text())
    assert set(wf[True]["pull_request"]["types"]) >= {"opened", "edited", "synchronize"}
    assert (
        wf["permissions"]["pull-requests"] == "write"
        and wf["permissions"]["contents"] == "read"
    )
    run = "\n".join(s.get("run", "") for s in wf["jobs"]["verify"]["steps"])
    assert "bin/idp-verify-claims --pr" in run
