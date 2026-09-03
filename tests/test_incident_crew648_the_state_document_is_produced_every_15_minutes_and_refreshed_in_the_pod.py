"""crew#648: estate ingestion through the model context protocol was "shipped" as a reader with
nothing writing (founder 2026-08-30: `get_estate_state` returned available:false on every call).
This pins the producer: a workflow on a 15-minute clock builds the document from the estate's own
receipts, validates it against the schema and publishes one artifact; the MCP pod refreshes that
artifact in place inside the 30-minute stale line; the builder turns every source into the
document shape and says BLIND, never ok, for a source it could not read."""

from __future__ import annotations

import datetime as dt
import importlib.machinery
import importlib.util
import json
import pathlib
import re
import sys

import jsonschema
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT = "oci://ghcr.io/chidionyema/idp/estate-state:latest"
SCHEMA = json.loads((ROOT / "platform/estate-state/schema.json").read_text())


def _builder():
    loader = importlib.machinery.SourceFileLoader(
        "estate_state_build", str(ROOT / "bin/idp-estate-state-build")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _cron_minutes(expr: str) -> int:
    m = re.fullmatch(r"\*/(\d+) \* \* \* \*", expr)
    assert m, expr
    return int(m.group(1))


def test_the_workflow_runs_every_15_minutes_builds_validates_and_publishes_the_one_artifact():
    wf = yaml.safe_load((ROOT / ".github/workflows/estate-state.yml").read_text())
    crons = [c["cron"] for c in wf[True]["schedule"]]
    assert crons and all(_cron_minutes(c) <= 15 for c in crons), crons
    job = wf["jobs"]["build"]
    assert job["env"]["ARTIFACT"] == ARTIFACT
    steps = job["steps"]
    build = next(s for s in steps if "build and validate" in s.get("name", ""))
    assert "bin/idp-estate-state-build" in build["run"]
    publish = next(s for s in steps if s.get("name", "").startswith("publish"))
    assert "flux push artifact" in publish["run"] and '"$ARTIFACT"' in publish["run"]
    assert publish["if"] == "github.event_name != 'pull_request'", (
        "a pull request never publishes"
    )
    assert wf["permissions"]["packages"] == "write"


def test_the_pod_refreshes_the_same_artifact_inside_the_stale_line_and_the_server_reads_it():
    docs = list(yaml.safe_load_all((ROOT / "platform/mcp/estate-mcp.yaml").read_text()))
    dep = next(d for d in docs if d["kind"] == "Deployment")
    spec = dep["spec"]["template"]["spec"]
    side = next(c for c in spec["containers"] if c["name"] == "refresh-estate-state")
    script = " ".join(side["args"])
    assert f"flux pull artifact {ARTIFACT} --output /data" in script
    sleep = int(re.search(r"sleep (\d+)", script).group(1))
    assert sleep <= 30 * 60 // 2, (
        "refresh at least twice inside the 30-minute stale line"
    )
    assert any(
        m["name"] == "data" and not m.get("readOnly") for m in side["volumeMounts"]
    )
    assert side["securityContext"]["readOnlyRootFilesystem"] is True
    for probe in ("livenessProbe", "readinessProbe"):
        assert "-mmin -30" in " ".join(side[probe]["exec"]["command"]), (
            "the probe is the stale line: a document older than 30 min restarts the refresh"
        )
    server = next(c for c in spec["containers"] if c["name"] == "estate-mcp")
    env = {e["name"]: e["value"] for e in server["env"]}
    assert env["ESTATE_STATE_JSON_PATH"] == "/data/estate-state.json"


def test_the_builder_turns_every_source_into_a_schema_valid_document():
    b = _builder()
    now = dt.datetime(2026, 8, 30, 9, 0, tzinfo=dt.timezone.utc)
    receipt = (
        "ok cluster-state at 2026-08-30T08:45:02Z nodes=3 ready=3 pods=200 pods_not_ready=0 flux=41 flux_not_ready=1\n"
        + json.dumps(
            {
                "flux_not_ready": [
                    {
                        "kind": "HelmRelease",
                        "ns": "tailscale",
                        "name": "tailscale-operator",
                        "ready": False,
                        "message": "upgrade failed",
                    }
                ]
            }
        )
        + "\n"
    )
    cluster = b.parse_cluster_receipt(receipt)
    assert (
        cluster["state"] == "FAIL"
        and cluster["flux_rows"][0]["namespace"] == "tailscale"
    )
    assert (
        b.parse_cluster_receipt(
            "ok cluster-state at 2026-08-30T08:45:02Z flux_not_ready=0\n{}\n"
        )["state"]
        == "ok"
    )
    assert b.parse_cluster_receipt("")["state"] == "BLIND", (
        "an empty receipt is BLIND, never ok"
    )
    feed = (
        "## 2026-08-30T08:08Z · a7b41022 · science\n🔴 Blocked: founder ruling\n🟡 Active: crew#684 doors\n"
        "## 2026-08-30T07:44Z · 2d8b3bd0 · code\n🟡 Active: nothing.\n"
        "## 2026-08-30T08:30Z · a7b41022 · science\n🟡 Active: crew#648 producer\n"
    )
    sessions = b.parse_feed_sessions(feed, now)
    assert sessions == [
        {
            "id": "a7b41022",
            "lane": "science",
            "last_handoff_at": "2026-08-30T08:30:00Z",
            "active": "crew#648 producer",
        },
        {
            "id": "2d8b3bd0",
            "lane": "code",
            "last_handoff_at": "2026-08-30T07:44:00Z",
            "active": "nothing.",
        },
    ]
    assert b.parse_feed_sessions(feed, now + dt.timedelta(hours=3))[0][
        "active"
    ].startswith("parked: no handoff for ")
    rulings = b.parse_rulings(
        {
            "rulings": [
                {
                    "id": "R1-no-fly-revival",
                    "date": "2026-08-24",
                    "verbatim": "for the last time",
                }
            ]
        }
    )
    assert rulings == [
        {"id": "R1-no-fly-revival", "date": "2026-08-24", "text": "for the last time"}
    ]
    drill = (
        "sso login-drill signoz landed on signoz.example (200), 0 password field(s)\n"
        "paths login-drill 12/12 published paths render their own content\n"
        "FAIL login-drill second-hop langfuse is still on its sign-in page\n"
    )
    surfaces = {
        s["name"]: s["verdict"]
        for s in b.parse_drill_surfaces(drill, "2026-08-30T08:14:44Z")
    }
    assert surfaces == {"signoz": "ok", "published-paths": "ok", "second-hop": "FAIL"}
    issues = [
        {
            "repo": "crew",
            "number": 804,
            "title": "P0: login drill failed",
            "labels": ["P0"],
            "created_at": "2026-08-29T13:37:53Z",
            "url": "u",
        },
        {
            "repo": "crew",
            "number": 677,
            "title": "security audit",
            "labels": ["security", "P1"],
            "created_at": "2026-08-30T00:00:00Z",
            "url": "u",
        },
    ]
    freeze, board, p0, findings = b.parse_issues(issues)
    assert freeze == {"active": False} and [r["number"] for r in p0] == [804]
    assert [(r["number"], r["priority"]) for r in board] == [(677, "P1"), (804, "P0")]
    assert findings == [
        {
            "repo": "crew",
            "severity": "high",
            "count": 1,
            "source": "issues labelled security",
        }
    ]
    runs = b.parse_runs(
        [
            {
                "repo": "idp",
                "workflow": "login-drill",
                "conclusion": "failure",
                "created_at": "2026-08-30T08:10:50Z",
            }
        ]
        * 2,
        6,
    )
    assert runs == [
        {
            "repo": "idp",
            "workflow": "login-drill",
            "failed": 2,
            "window_hours": 6,
            "last_run": "2026-08-30T08:10:50Z",
        }
    ]


def test_a_built_document_validates_and_a_missing_source_is_blind(tmp_path):
    b = _builder()
    (tmp_path / "cluster.txt").write_text(
        "ok cluster-state at 2026-08-30T08:45:02Z flux_not_ready=0\n{}\n"
    )
    (tmp_path / "feed.md").write_text("## 2026-08-30T08:08Z · a7b41022 · science\n")
    out = tmp_path / "estate-state.json"
    rc = b.main(
        [
            "--now",
            "2026-08-30T09:00:00Z",
            "--cluster-receipt",
            str(tmp_path / "cluster.txt"),
            "--feed",
            str(tmp_path / "feed.md"),
            "--main-sha",
            "idp=abc",
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    doc = json.loads(out.read_text())
    jsonschema.Draft202012Validator(SCHEMA).validate(doc)
    assert (
        doc["runtime"]["clusters"][0]["state"] == "ok"
        and doc["overview"]["sessions"][0]["id"] == "a7b41022"
    )
    _, blind = b.build(
        type(
            "A",
            (),
            dict(
                cluster_receipt=None,
                feed=None,
                rulings=None,
                drill_log=None,
                drill_at=None,
                issues=None,
                runs=None,
                window_hours=6,
                main_sha=["idp=abc"],
            ),
        )(),
        dt.datetime(2026, 8, 30, 9, 0, tzinfo=dt.timezone.utc),
    )
    # six version-1 sources plus eight version-2 ones (vendor registry, secret ages, last apply
    # run, router lanes, pull requests, incidents, decision commits, merges): each missing
    # source is its own BLIND line, never a quiet green row
    assert len(blind) == 14, blind


def test_incident_crew648_a_bare_main_sha_is_refused_in_a_sentence_and_the_workflow_passes_repo_equals_sha():
    """Run 33301723691 died on `--main-sha "$GITHUB_SHA"` with a dict traceback."""
    import subprocess

    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin/idp-estate-state-build"),
            "--main-sha",
            "abc123",
            "--out",
            "/dev/null",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2 and "repo=sha" in r.stderr and "Traceback" not in r.stderr
    wf = (ROOT / ".github/workflows/estate-state.yml").read_text()
    assert '--main-sha "idp=$GITHUB_SHA"' in wf
