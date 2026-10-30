"""The structured-format gate proves it can fail before any agent is graded by it (idp#7089).

The founder's ask (2026-10-25) is structural: treat a model less like a chat partner and more like
a compiler function, so that a plausible-sounding invention is refused by the shape rather than
believed. The estate already has the worked example -- `bin/intent-compile` refuses an intent whose
vocabulary is outside its schema, by name, exit 1 -- and it covers four cluster-config payloads.
`bin/schema-conformance` applies the same three refusals to the 340 intents an agent actually calls.

Each test here is one reason to distrust such a gate:

  * a gate that cannot fail is not a gate         -> test_a_clean_intent_passes / test_untyped_arg_fails
  * a gate that reports BLIND as clean            -> test_a_missing_root_is_blind_not_clean
  * a citation check that cannot see a bad id     -> test_verify_refuses_an_unharvested_citation
  * a diagnosis of the door that never ran the door -> test_the_live_executor_accepts_an_undeclared_arg

The last three execute the estate's own code: `platform/estate/bin/estate-execute` (the file
`~/.estate/bin/estate-execute` symlinks to through `~/.estate/runtime/idp/`) and
`bin/arxiv-harvest`. A test that only re-implements resolve_args in the test file would prove
nothing about the door an agent calls.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "bin" / "schema-conformance"
HARVEST = REPO / "bin" / "arxiv-harvest"
OSS = REPO / "bin" / "oss-harvest"
BASELINE = REPO / "docs" / "research" / "2026-10-25-constrained-formats.baseline.json"
HARVEST_JSON = (
    REPO / "docs" / "research" / "2026-10-25-constrained-formats-harvest.json"
)
OSS_JSON = REPO / "docs" / "research" / "2026-10-25-constrained-formats-oss.json"
DIGEST = REPO / "docs" / "research" / "2026-10-25-constrained-formats-research.md"
EXECUTOR = REPO / "platform" / "estate" / "bin" / "estate-execute"


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, timeout=60, **kw)


def write_intent(root: Path, name: str, body: str) -> Path:
    p = root / f"{name}.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def load_executor_module():
    """The door itself, loaded under a private name (it is a script, not an importable module).

    `spec_from_file_location` answers None for a path with no `.py` suffix -- which is every bin/
    script in this estate, and the reason this needs an explicit SourceFileLoader rather than the
    two-line idiom.
    """
    loader = importlib.machinery.SourceFileLoader("estate_execute_live", str(EXECUTOR))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


CLEAN = """\
name: clean
description: Reads the most recent commits of one repository so a caller can see what changed lately.
args:
  repo: { type: string, required: true, help: "owner/name" }
  count: { type: int, default: 1, description: "how many commits to read" }
steps:
  - name: read commits
    cmd: >
      gh api "repos/{{repo}}/commits?per_page={{count}}"
"""


def test_a_clean_intent_passes(tmp_path):
    """The gate must be able to say yes, or a green result means nothing."""
    write_intent(tmp_path, "clean", CLEAN)
    r = run([sys.executable, str(GATE), "intents", "--root", str(tmp_path)])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "violations             0" in r.stdout


def test_an_arg_with_no_type_fails(tmp_path):
    """R1: an untyped arg is a string that a shell step will interpolate."""
    write_intent(
        tmp_path,
        "untyped",
        "name: untyped\nargs:\n  repo: { help: 'no type here' }\nsteps:\n  - cmd: >\n      gh api {{repo}}\n",
    )
    r = run([sys.executable, str(GATE), "intents", "--root", str(tmp_path)])
    assert r.returncode == 1
    assert "R1" in r.stdout and "repo" in r.stdout


def test_an_undeclared_interpolation_fails(tmp_path):
    """R2: the shape a hallucinated argument takes -- interpolated, declared nowhere, resolves to ''."""
    write_intent(
        tmp_path,
        "phantom",
        "name: phantom\nargs:\n  repo: { type: string, required: true }\n"
        "steps:\n  - cmd: >\n      gh api repos/{{repo}}/commits/{{sha}}\n",
    )
    r = run([sys.executable, str(GATE), "intents", "--root", str(tmp_path)])
    assert r.returncode == 1
    assert "R2" in r.stdout and "sha" in r.stdout


def test_a_raw_interpolation_fails(tmp_path):
    """R3: <<var>> bypasses the shlex.quote that makes {{var}} safe."""
    write_intent(
        tmp_path,
        "raw",
        "name: raw\nargs:\n  repo: { type: string, required: true }\nsteps:\n  - cmd: >\n      gh api <<repo>>\n",
    )
    r = run([sys.executable, str(GATE), "intents", "--root", str(tmp_path)])
    assert r.returncode == 1
    assert "R3" in r.stdout and "<<repo>>" in r.stdout


def test_an_arg_with_no_default_must_be_required(tmp_path):
    """R4: 309 of the estate's 314 declared args are not required, so a caller that omits one is handed ''."""
    write_intent(
        tmp_path,
        "optional",
        "name: optional\nargs:\n  repo: { type: string }\nsteps:\n  - cmd: >\n      gh api {{repo}}\n",
    )
    r = run([sys.executable, str(GATE), "intents", "--root", str(tmp_path)])
    assert r.returncode == 1
    assert "R4" in r.stdout and "repo" in r.stdout


def test_an_unreadable_intent_is_never_clean(tmp_path):
    """A file the gate cannot parse is a file the gate did not grade."""
    (tmp_path / "broken.yaml").write_text(
        "name: broken\n  args: [unclosed\n", encoding="utf-8"
    )
    r = run([sys.executable, str(GATE), "intents", "--root", str(tmp_path)])
    assert r.returncode == 1
    assert "R0" in r.stdout


def test_a_missing_root_is_blind_not_clean(tmp_path):
    """Exit 2, not 0. An absent directory is a gate that graded nothing."""
    r = run([sys.executable, str(GATE), "intents", "--root", str(tmp_path / "absent")])
    assert r.returncode == 2
    assert "BLIND" in r.stderr


def test_an_empty_root_is_blind_not_clean(tmp_path):
    r = run([sys.executable, str(GATE), "intents", "--root", str(tmp_path)])
    assert r.returncode == 2
    assert "BLIND" in r.stderr


def test_the_summary_is_machine_readable(tmp_path):
    """--json is what a trend line is built from, so the fields have to be named and counted."""
    write_intent(tmp_path, "clean", CLEAN)
    r = run([sys.executable, str(GATE), "intents", "--root", str(tmp_path), "--json"])
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    s = doc["summary"]
    assert s["intents"] == 1
    assert s["args_declared"] == 2
    assert s["args_typed"] == 2
    assert s["args_required"] == 1
    assert s["violations"] == 0


# ---- the ratchet: the estate's shape may not get worse in one change -------------------------
#
# A gate that fails on the 74 violations main already carries blocks every lane in the fleet, and a
# gate that is born exempt grades nothing. So the same gate runs in two modes: strict (proves the
# defect, exit 1) and ratchet (fails only on a NEW violation). Both modes are tested here, because
# a ratchet nobody proved can fail is the same decoration as a gate that cannot.

WELL = "description: " + "x" * 70 + "\n"
KNOWN = (
    "name: known\n" + WELL + "args:\n  repo: { type: string, help: r }\n"
    "steps:\n  - name: s\n    cmd: >\n      gh api {{repo}}\n"
)
WORSE = (
    "name: worse\n" + WELL + 'args:\n  other: { help: "no type" }\n'
    "steps:\n  - name: s\n    cmd: >\n      gh api {{other}}\n"
)


def test_the_ratchet_refuses_a_new_violation(tmp_path):
    """The whole point: a lane that adds a bad intent goes red, even with 74 violations before it."""
    write_intent(tmp_path, "known", KNOWN)
    base = tmp_path / "base.json"
    assert (
        run(
            [
                sys.executable,
                str(GATE),
                "intents",
                "--root",
                str(tmp_path),
                "--write-baseline",
                str(base),
            ]
        ).returncode
        == 0
    )

    write_intent(tmp_path, "worse", WORSE)
    r = run(
        [
            sys.executable,
            str(GATE),
            "intents",
            "--root",
            str(tmp_path),
            "--baseline",
            str(base),
        ]
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "NEW" in r.stdout and "worse" in r.stdout


def test_the_ratchet_lets_a_known_violation_stand(tmp_path):
    """A pre-existing violation is named, not fixed by the gate, and not charged to this lane."""
    write_intent(tmp_path, "known", KNOWN)
    base = tmp_path / "base.json"
    run(
        [
            sys.executable,
            str(GATE),
            "intents",
            "--root",
            str(tmp_path),
            "--write-baseline",
            str(base),
        ]
    )
    r = run(
        [
            sys.executable,
            str(GATE),
            "intents",
            "--root",
            str(tmp_path),
            "--baseline",
            str(base),
        ]
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 new" in r.stdout and "1 known" in r.stdout


def test_the_ratchet_accepts_a_fix_and_says_so(tmp_path):
    """Removing a violation is never a failure; the count only goes down."""
    write_intent(tmp_path, "known", KNOWN)
    base = tmp_path / "base.json"
    run(
        [
            sys.executable,
            str(GATE),
            "intents",
            "--root",
            str(tmp_path),
            "--write-baseline",
            str(base),
        ]
    )
    write_intent(tmp_path, "known", CLEAN)  # the R4 violation is gone
    r = run(
        [
            sys.executable,
            str(GATE),
            "intents",
            "--root",
            str(tmp_path),
            "--baseline",
            str(base),
        ]
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "fixed" in r.stdout


def test_the_ratchet_is_blind_without_its_baseline(tmp_path):
    """Exit 2, not 0: with no recorded set a ratchet cannot tell new from old, so it must not pass."""
    write_intent(tmp_path, "known", KNOWN)
    r = run(
        [
            sys.executable,
            str(GATE),
            "intents",
            "--root",
            str(tmp_path),
            "--baseline",
            str(tmp_path / "absent.json"),
        ]
    )
    assert r.returncode == 2
    assert "BLIND" in r.stderr


def test_the_committed_baseline_matches_the_committed_intents():
    """The repo's own ratchet, run the way CI runs it: no new violation in platform/estate/intents.

    This is the rung that makes the gate operational rather than a script in a drawer. It reads the
    baseline committed beside this test, so a lane that breaks an intent fails here first.
    """
    r = run(
        [
            sys.executable,
            str(GATE),
            "intents",
            "--root",
            str(REPO / "platform" / "estate" / "intents"),
            "--baseline",
            str(BASELINE),
        ]
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "new" in r.stdout
    doc = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert doc["summary"]["intents"] > 0, "a baseline over zero intents grades nothing"


def test_the_strict_mode_fails_on_main_as_it_stands():
    """The defect, measured: the committed intents do not pass the strict gate today.

    If this ever passes, the intents have been fixed and strict mode belongs in CI; until then the
    digest's claim about the size of the gap is this number and nothing else.
    """
    r = run(
        [
            sys.executable,
            str(GATE),
            "intents",
            "--root",
            str(REPO / "platform" / "estate" / "intents"),
        ]
    )
    assert r.returncode == 1, (
        "strict mode went green; move strict into CI and invert this test"
    )
    assert "violations" in r.stdout


def test_the_live_executor_accepts_an_undeclared_arg():
    """THE DEFECT, executed rather than described.

    `resolve_args` splits `k=v` and keeps the key without asking whether the intent declares it. So
    an agent that guesses `--repo` instead of `repo`, or invents `branch=main` on an intent with no
    such arg, gets no refusal: the intent runs with its defaults, and the failure surfaces far from
    the claim. If this test ever fails, the door has been tightened and the spec's §4 ladder has
    moved on -- it should then be inverted, not deleted.
    """
    mod = load_executor_module()
    intent = {"args": {"repo": {"type": "string", "required": True}}}
    assert mod.resolve_args(intent, ["repo=owner/name"]) == {"repo": "owner/name"}
    resolved = mod.resolve_args(
        intent, ["repo=owner/name", "branch=main", "--dry-run=1"]
    )
    assert resolved["branch"] == "main", (
        "the door refused an undeclared arg; tighten the spec, invert this test"
    )
    assert resolved["--dry-run"] == "1"


def test_the_live_executor_coerces_a_bad_int_to_zero():
    """A wrong type becomes a plausible value instead of a refusal -- 0 failures like 0 successes."""
    mod = load_executor_module()
    resolved = mod.resolve_args({"args": {"count": {"type": "int"}}}, ["count=lots"])
    assert resolved["count"] == 0


def test_the_live_executor_hands_back_an_empty_string_for_an_omitted_arg():
    """...and an omitted arg is '', so the step runs half-formed rather than not at all."""
    mod = load_executor_module()
    assert mod.resolve_args({"args": {"repo": {"type": "string"}}}, [])["repo"] == ""


def test_oss_verify_refuses_an_unharvested_repo(tmp_path):
    """A named project with no harvested number is an assertion, not evidence."""
    harvest = tmp_path / "oss.json"
    harvest.write_text(
        json.dumps({"repos": [{"repo": "dottxt-ai/outlines", "stars": 1}]}),
        encoding="utf-8",
    )
    bad = tmp_path / "bad.md"
    bad.write_text(
        "`dottxt-ai/outlines` is real; `some-org/invented-tool` is not.",
        encoding="utf-8",
    )
    r = run([sys.executable, str(OSS), "--verify", str(harvest), str(bad)])
    assert r.returncode == 1
    assert "some-org/invented-tool" in r.stderr


SURFACES_HARVEST_JSON = (
    REPO / "docs" / "research" / "2026-10-25-constrained-formats-surfaces-harvest.json"
)
SURFACES = REPO / "docs" / "research" / "2026-10-25-constrained-formats-surfaces.md"


def test_oss_verify_reads_a_command_as_a_command_not_a_citation(tmp_path):
    """A path in a shell block is not a repo claim; the same token in prose is.

    The first time the verifier met a document that also contains shell (the surfaces ledger,
    2026-10-25) it reported 8 unharvested repos that were really a branch, a directory and five
    prose slash-pairs. The fix was to strip fenced blocks -- NOT to soften the check, so this
    test proves both halves: the fenced token is ignored, and the identical token in prose still
    fails. A verifier that stopped failing on prose would pass half of this and must not.
    """
    harvest = tmp_path / "oss.json"
    harvest.write_text(
        json.dumps({"repos": [{"repo": "dottxt-ai/outlines", "stars": 1}]}),
        encoding="utf-8",
    )
    fenced = tmp_path / "fenced.md"
    fenced.write_text(
        "`dottxt-ai/outlines` is measured.\n\n```bash\nwc -l some-org/not-a-repo.py\n```\n",
        encoding="utf-8",
    )
    r = run([sys.executable, str(OSS), "--verify", str(harvest), str(fenced)])
    assert r.returncode == 0, r.stderr

    prose = tmp_path / "prose.md"
    prose.write_text(
        "`dottxt-ai/outlines` and `some-org/not-a-repo`.", encoding="utf-8"
    )
    r = run([sys.executable, str(OSS), "--verify", str(harvest), str(prose)])
    assert r.returncode == 1
    assert "some-org/not-a-repo" in r.stderr


def test_the_verifier_vocabulary_shadows_no_harvested_repo():
    """The exclusion list must not silently switch the check off for a repo we DID harvest.

    NON_CODE_NAMESPACES exists to stop a path or a prose slash-pair being read as a repo. Its cost
    is that a repo whose owner is on the list is never checked -- so no owner we actually harvest
    may appear on it. Without this test, adding a vocabulary word could quietly stop verifying one
    of the projects the digest cites.
    """
    ns = _load_oss_namespaces()
    harvest = json.loads(OSS_JSON.read_text(encoding="utf-8"))
    owners = {
        r["repo"].split("/")[0].lower() for r in harvest["repos"] if r.get("repo")
    }
    assert not (owners & set(ns)), sorted(owners & set(ns))


def _load_oss_namespaces():
    """Read NON_CODE_NAMESPACES out of the script, which has no .py suffix to import."""
    src = OSS.read_text(encoding="utf-8")
    start = src.index("NON_CODE_NAMESPACES = (")
    end = src.index(")", start)
    return re.findall(r'"([^"]+)"', src[start:end])


def test_the_surface_ledger_cites_only_harvested_papers_and_repos():
    """The estate-wide ledger is held to the same rule as the digest: no unmeasured citation."""
    for args in (
        [str(HARVEST), "--verify", str(SURFACES_HARVEST_JSON), str(SURFACES)],
        [str(OSS), "--verify", str(OSS_JSON), str(SURFACES)],
    ):
        r = run([sys.executable, *args])
        assert r.returncode == 0, r.stderr


def test_the_committed_digest_cites_only_harvested_papers():
    """The digest does not get to name a paper the harvest does not carry."""
    r = run([sys.executable, str(HARVEST), "--verify", str(HARVEST_JSON), str(DIGEST)])
    assert r.returncode == 0, r.stderr


def test_the_committed_digest_cites_only_harvested_repos():
    r = run([sys.executable, str(OSS), "--verify", str(OSS_JSON), str(DIGEST)])
    assert r.returncode == 0, r.stderr


def test_verify_refuses_a_citation_that_was_never_harvested(tmp_path):
    """The digest's citations are checked against the harvest, so an invented id cannot ship."""
    harvest = tmp_path / "harvest.json"
    harvest.write_text(
        json.dumps({"records": [{"id": "2503.07314v1"}, {"id": "2410.12345v2"}]}),
        encoding="utf-8",
    )
    good = tmp_path / "good.md"
    good.write_text(
        "`2503.07314v1` and `2410.12345v2` are both real.", encoding="utf-8"
    )
    ok = run([sys.executable, str(HARVEST), "--verify", str(harvest), str(good)])
    assert ok.returncode == 0, ok.stderr

    bad = tmp_path / "bad.md"
    bad.write_text(
        "`2503.07314v1` and `2609.99999v1` -- the second is invented.", encoding="utf-8"
    )
    refused = run([sys.executable, str(HARVEST), "--verify", str(harvest), str(bad)])
    assert refused.returncode == 1
    assert "2609.99999" in refused.stderr


def test_the_harvest_refuses_to_hammer_arxiv(tmp_path):
    """A research harvest that ignores arXiv's rate limit is a harvest that gets the estate blocked."""
    q = tmp_path / "q.txt"
    q.write_text("theme | all:test\n", encoding="utf-8")
    r = run(
        [
            sys.executable,
            str(HARVEST),
            "--queries",
            str(q),
            "--out",
            str(tmp_path / "o.json"),
            "--sleep",
            "0.1",
        ]
    )
    assert r.returncode != 0
    assert "one request per 3s" in (r.stderr + r.stdout)


@pytest.mark.parametrize("script", [GATE, HARVEST])
def test_the_scripts_are_executable(script):
    """Both are invoked by path from docs and CI; a missing +x is a door that cannot be opened."""
    assert script.exists()
    assert script.stat().st_mode & 0o111


# R5-R8: each rule is proved to fire on its own, and the clean fixture is proved to pass them all.
# Every fixture below is CLEAN with exactly one thing broken, so a red result names one rule.


def _violations(tmp_path, body):
    write_intent(tmp_path, "probe", body)
    r = run([sys.executable, str(GATE), "intents", "--root", str(tmp_path), "--json"])
    assert r.returncode in (0, 1), r.stdout + r.stderr
    return r.returncode, json.loads(r.stdout)["keys"]


@pytest.mark.parametrize(
    "rule,body",
    [
        ("R5", CLEAN.replace(', description: "how many commits to read"', "")),
        ("R5", CLEAN.replace(', help: "owner/name"', "")),
        (
            "R6",
            CLEAN.replace(
                "Reads the most recent commits of one repository so a caller can see what changed lately.",
                "Reads commits.",
            ),
        ),
        ("R7", CLEAN.replace("gh api", "cd /Users/someone/code && gh api")),
        ("R7", CLEAN.replace("gh api", "cd ~/Documents/code/idp && gh api")),
        ("R8", CLEAN.replace("  - name: read commits\n    cmd:", "  - cmd:")),
    ],
)
def test_each_new_rule_fires_on_its_own_defect(tmp_path, rule, body):
    rc, keys = _violations(tmp_path, body)
    assert rc == 1, keys
    assert [k.split(":")[0] for k in keys] == [rule], keys


def test_the_clean_fixture_passes_every_new_rule(tmp_path):
    rc, keys = _violations(tmp_path, CLEAN)
    assert (rc, keys) == (0, [])


def test_an_arg_described_by_either_key_satisfies_r5(tmp_path):
    """`help:` and `description:` are both in use across the intents; either one counts."""
    assert _violations(tmp_path, CLEAN)[1] == []
