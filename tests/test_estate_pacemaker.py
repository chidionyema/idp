"""estate-pacemaker: a missed clock is run, and a silent pacemaker home is a ticket (idp#8026).

The kill-one-home drill is test_a_dead_home_is_named_and_the_survivors_still_run_the_missed_clock:
two homes knock, one is dead, the run still dispatches the missed clock and names the dead home.
"""

from __future__ import annotations

import datetime as dt
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "bin" / "estate-pacemaker"
NOW = dt.datetime(2026, 11, 13, 2, 0, tzinfo=dt.timezone.utc)
HOMES = {"github-cron": 90, "cloudflare": 30, "mac": 90}


def _mod():
    loader = importlib.machinery.SourceFileLoader("estate_pacemaker_t", str(TOOL))
    spec = importlib.util.spec_from_loader("estate_pacemaker_t", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _run(title: str, minutes_ago: float) -> dict:
    at = NOW - dt.timedelta(minutes=minutes_ago)
    return {"title": title, "created": at.isoformat().replace("+00:00", "Z")}


def test_every_home_knocking_inside_its_tolerance_is_quiet():
    runs = [
        _run("pacemaker · github-cron", 40),
        _run("pacemaker · cloudflare", 4),
        _run("pacemaker · mac", 10),
    ]
    assert _mod().silent_homes(HOMES, runs, NOW) == []


def test_a_home_past_its_tolerance_or_never_seen_is_silent():
    runs = [_run("pacemaker · github-cron", 40), _run("pacemaker · cloudflare", 31)]
    silent = {s["home"]: s for s in _mod().silent_homes(HOMES, runs, NOW)}
    assert set(silent) == {"cloudflare", "mac"}
    assert silent["mac"]["note"] == "never seen"
    assert silent["cloudflare"]["age_minutes"] == 31.0


def test_a_run_from_an_unknown_title_does_not_keep_a_home_alive():
    runs = [_run("pacemaker · manual", 1), _run("something else", 1)]
    assert {s["home"] for s in _mod().silent_homes(HOMES, runs, NOW)} == set(HOMES)


def test_plan_dispatches_a_miss_respects_cooldown_and_never_runs_itself():
    rows = [
        {
            "id": "relay",
            "workflow": "argon-guardian-relay.yml",
            "verdict": "MISSED_CYCLE",
        },
        {
            "id": "busy",
            "workflow": "argon-guardian-relay.yml",
            "verdict": "MISSED_CYCLE",
        },
        {"id": "self", "workflow": "estate-pacemaker.yml", "verdict": "MISSED_CYCLE"},
        {"id": "fine", "workflow": "ping.yml", "verdict": "MEASURED_OK"},
    ]
    recent = iter([None, 3.0])
    acts = _mod().plan(
        {"pacemaker": {"cooldown_minutes": 30}}, rows, lambda wf: next(recent)
    )
    assert [(a["id"], a["action"]) for a in acts] == [
        ("relay", "dispatch"),
        ("busy", "cooldown"),
    ]


def test_a_miss_with_no_dispatch_trigger_is_named_not_hidden(tmp_path, monkeypatch):
    mod = _mod()
    monkeypatch.setattr(mod, "dispatchable", lambda wf: False)
    acts = mod.plan(
        {},
        [{"id": "x", "workflow": "x.yml", "verdict": "MISSED_CYCLE"}],
        lambda wf: None,
    )
    assert acts[0]["action"] == "cannot-dispatch"


def test_a_dead_home_is_named_and_the_survivors_still_run_the_missed_clock(tmp_path):
    """The kill-one-home drill, end to end through the CLI with pinned history."""
    (tmp_path / "runs.json").write_text(json.dumps({"argon-guardian-relay.yml": []}))
    (tmp_path / "recent.json").write_text(json.dumps({}))
    pm = [
        _run("pacemaker · github-cron", 20),
        _run("pacemaker · mac", 12),
    ]  # cloudflare killed
    (tmp_path / "pm.json").write_text(json.dumps(pm))
    out = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--json",
            "--home",
            "mac",
            "--now",
            NOW.isoformat(),
            "--runs-json",
            str(tmp_path / "runs.json"),
            "--recent-json",
            str(tmp_path / "recent.json"),
            "--pacemaker-runs-json",
            str(tmp_path / "pm.json"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    got = json.loads(out.stdout)
    assert [s["home"] for s in got["silent_homes"]] == ["cloudflare"]
    assert ("argon-guardian-relay", "dispatch") in [
        (a["id"], a["action"]) for a in got["actions"]
    ]
    assert out.returncode in (
        1,
        2,
    )  # a finding; 2 only if a fixture-less clock is unreadable


def test_the_registry_declares_three_homes_and_chronos_grades_the_pacemaker():
    reg = json.loads((ROOT / "legions" / "estate-clocks.json").read_text())
    assert set(reg["pacemaker"]["homes"]) == {"github-cron", "cloudflare", "mac"}
    assert "estate-pacemaker" in {o["id"] for o in reg["obligations"]}
    wf = (ROOT / ".github" / "workflows" / "estate-pacemaker.yml").read_text()
    assert "pacemaker · ${{ inputs.home || 'github-cron' }}" in wf
    assert (
        "home=cloudflare" not in wf
    )  # the cloudflare home knocks from the Worker, not from here
    assert '"cloudflare"' in (ROOT / "platform" / "pacemaker" / "worker.js").read_text()
    assert (
        "home=mac" in (ROOT / "launchd" / "ai.estate.pacemaker.plist.tmpl").read_text()
    )


def test_the_cloudflare_home_mints_an_app_jwt_github_would_accept(tmp_path):
    """The Worker signs RS256 with WebCrypto from a PKCS#8 key; node verifies it with the public
    key. A JWT that does not verify is a Cloudflare home that knocks and is never let in."""
    key = tmp_path / "k.pem"
    subprocess.run(
        [
            "openssl",
            "genpkey",
            "-algorithm",
            "RSA",
            "-pkeyopt",
            "rsa_keygen_bits:2048",  # noqa: S607
            "-out",
            str(key),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    script = tmp_path / "v.mjs"
    script.write_text(
        "import fs from 'node:fs'; import crypto from 'node:crypto';\n"
        f"const m = await import({json.dumps((ROOT / 'platform/pacemaker/worker.js').as_uri())});\n"
        f"const pem = fs.readFileSync({json.dumps(str(key))}, 'utf8');\n"
        "const jwt = await m.appJwt(12345, pem, 1800000000);\n"
        "const [h, p, s] = jwt.split('.');\n"
        "const ok = crypto.verify('RSA-SHA256', Buffer.from(h + '.' + p), crypto.createPublicKey(pem),"
        " Buffer.from(s, 'base64url'));\n"
        "const claims = JSON.parse(Buffer.from(p, 'base64url'));\n"
        "console.log(JSON.stringify({ok, iss: claims.iss, ttl: claims.exp - claims.iat}));\n"
    )
    out = subprocess.run(
        ["node", str(script)], capture_output=True, text=True, timeout=60, check=True
    )  # noqa: S607
    got = json.loads(out.stdout)
    assert got == {"ok": True, "iss": "12345", "ttl": 600}


def test_the_surface_snapshot_says_unknown_for_a_missing_input_never_zero():
    snap = _mod().snapshot({}, {}, {}, "u")
    assert (
        snap["clocks"]["graded"] == "UNKNOWN" and snap["loops"]["closed"] == "UNKNOWN"
    )
    assert "homes not yet graded" in snap["line"]


def test_the_surface_snapshot_names_dispatches_and_silent_homes():
    beat = {
        "home": "cloudflare",
        "observed_at": "2026-11-13T02:00:00Z",
        "homes_graded": True,
        "actions": [
            {"id": "relay", "action": "dispatched"},
            {"id": "g", "action": "cooldown"},
        ],
        "silent_homes": [{"home": "mac"}],
        "blind": [],
    }
    board = {
        "summary": {"graded": 10, "ok": 7, "missed": 3, "unknown": 0},
        "obligations": [],
    }
    loops = {
        "declared": 141,
        "closed": 8,
        "open": 133,
        "coverage_floor": 8,
        "by_home": {},
    }
    snap = _mod().snapshot(beat, board, loops, "u")
    assert snap["pacemaker"]["dispatched"] == ["relay"]
    assert snap["line"] == (
        "Clocks 7/10 ran on time · loops 8/141 closed · pacemaker ran 1 missed · homes silent: mac"
    )
