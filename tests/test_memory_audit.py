import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "bin", "estate-memory-audit")
NOW = "2026-10-31T12:00:00Z"


def run(root, reg, *extra):
    rp = os.path.join(root, "reg.json")
    json.dump(reg, open(rp, "w"))
    r = subprocess.run(
        [
            sys.executable,
            TOOL,
            "audit",
            "--root",
            root,
            "--register",
            rp,
            "--now",
            NOW,
            *extra,
        ],
        capture_output=True,
        text=True,
    )
    return r.returncode, r.stdout + r.stderr


def base(**kw):
    reg = {
        "verified_at": "2026-10-30",
        "max_age_days": 7,
        "required_runtimes": [],
        "lanes": [],
        "documents": {},
    }
    reg.update(kw)
    return reg


def lane(i, verdict="KEEP", **kw):
    d = {
        "id": i,
        "name": i,
        "layer": "store",
        "verdict": verdict,
        "probes": [],
        "live": [],
        "owns": [],
    }
    d.update(kw)
    return d


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.home = tempfile.mkdtemp()

    def put(self, rel, text="x", root=None):
        p = os.path.join(root or self.d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(text)
        return p

    def test_empty_register_is_red_not_green(self):
        code, out = run(self.d, base())
        self.assertEqual(code, 1)
        self.assertIn("EMPTY_REGISTER", out)

    def test_keep_lane_with_code_but_no_live_probe_is_built_never_green(self):
        self.put("a.py")
        code, out = run(
            self.d, base(lanes=[lane("door", probes=[{"t": "file", "path": "a.py"}])])
        )
        self.assertEqual(code, 1)
        self.assertIn("| door | store | KEEP | built |", out)
        self.assertIn("KEEP_WITHOUT_LIVE_PROBE", out)

    def test_live_probe_cannot_run_without_home_is_blind(self):
        self.put("a.py")
        ln = lane(
            "door",
            probes=[{"t": "file", "path": "a.py"}],
            live=[{"t": "ledger_recent", "path": "~/l.jsonl"}],
        )
        code, out = run(self.d, base(lanes=[ln]))
        self.assertIn("| door | store | KEEP | blind |", out)
        self.assertEqual(code, 1)

    def test_operating_needs_recent_live_evidence_and_then_exits_zero(self):
        self.put("a.py")
        self.put("l.jsonl", "{}\n", root=self.home)
        os.utime(os.path.join(self.home, "l.jsonl"), (time.time(), time.time()))
        ln = lane(
            "door",
            probes=[{"t": "file", "path": "a.py"}],
            live=[{"t": "ledger_recent", "path": "~/l.jsonl", "max_age_h": 24}],
        )
        # real clock: the evidence file is fresh relative to now
        rp = os.path.join(self.d, "reg.json")
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.put("c.json", json.dumps({"surfaces": {"fleet": True}}), root=self.home)
        sf = {
            "id": "fleet",
            "needs": ["door"],
            "probes": [{"t": "file", "path": "a.py"}],
            "live": [{"t": "canary_surface", "path": "~/c.json", "surface": "fleet"}],
        }
        json.dump(
            base(lanes=[ln], founder_surfaces=[sf], verified_at=now[:10]), open(rp, "w")
        )
        r = subprocess.run(
            [
                sys.executable,
                TOOL,
                "audit",
                "--root",
                self.d,
                "--register",
                rp,
                "--home",
                self.home,
                "--now",
                now,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("| door | store | KEEP | operating |", r.stdout)

    def test_stale_live_evidence_is_down(self):
        self.put("a.py")
        p = self.put("l.jsonl", "{}\n", root=self.home)
        old = time.time() - 72 * 3600
        os.utime(p, (old, old))
        ln = lane(
            "door",
            probes=[{"t": "file", "path": "a.py"}],
            live=[{"t": "ledger_recent", "path": "~/l.jsonl", "max_age_h": 24}],
        )
        rp = os.path.join(self.d, "reg.json")
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        json.dump(base(lanes=[ln], verified_at=now[:10]), open(rp, "w"))
        r = subprocess.run(
            [
                sys.executable,
                TOOL,
                "audit",
                "--root",
                self.d,
                "--register",
                rp,
                "--home",
                self.home,
                "--now",
                now,
            ],
            capture_output=True,
            text=True,
        )
        self.assertIn("down", r.stdout)
        self.assertEqual(r.returncode, 1)

    def test_dangling_launcher_is_broken(self):
        self.put(
            "bin/memory-mcp",
            '#!/bin/bash\nexec "$(dirname "$0")/../.memory/.venv/bin/python" "$(dirname "$0")/../.memory/mcp_server.py"\n',
        )
        ln = lane("stubs", probes=[{"t": "launcher_target", "path": "bin/memory-mcp"}])
        code, out = run(self.d, base(lanes=[ln]))
        self.assertIn("| stubs | store | KEEP | broken |", out)
        self.assertIn("launcher points at nothing", out)

    def test_retire_lane_with_code_still_present_is_pending(self):
        self.put("old.py")
        ln = lane("old", "RETIRE", probes=[{"t": "absent", "path": "old.py"}])
        code, out = run(self.d, base(lanes=[ln]))
        self.assertIn("RETIRE_PENDING", out)
        os.remove(os.path.join(self.d, "old.py"))
        code, out = run(self.d, base(lanes=[ln]))
        self.assertIn("| old | store | RETIRE | retired |", out)
        self.assertNotIn("RETIRE_PENDING", out)

    def test_retire_lane_that_cannot_be_checked_is_not_silently_retired(self):
        ln = lane(
            "hindsight",
            "RETIRE",
            blind_reason="lives in another repo; this checkout cannot see it",
        )
        code, out = run(self.d, base(lanes=[ln]))
        self.assertIn("RETIRE_UNVERIFIABLE", out)

    def test_runtime_with_no_memory_path_is_named(self):
        self.put(
            "platform/estate/memory/runtimes.json",
            json.dumps(
                {
                    "runtimes": {
                        "claude-code": {"mcp": {}, "hook": {}},
                        "cursor": {"mcp": {}},
                    }
                }
            ),
        )
        reg = base(
            required_runtimes=["claude-code", "cursor", "cline"], lanes=[lane("x")]
        )
        code, out = run(self.d, reg)
        self.assertIn("RUNTIME_GAP", out)
        self.assertIn("cline", out)
        self.assertIn("RUNTIME_NO_INJECTION", out)
        self.assertIn("cursor", out)

    def test_machine_capture_covers_a_runtime_without_a_hook(self):
        self.put(
            "platform/estate/memory/runtimes.json",
            json.dumps({"runtimes": {"cursor": {"mcp": {}}}}),
        )
        reg = base(
            required_runtimes=["cursor", "cline"],
            runtimes_covered_by_machine_capture=["cursor", "cline"],
            lanes=[lane("x")],
        )
        code, out = run(self.d, reg)
        self.assertNotIn("RUNTIME_GAP", out)
        self.assertNotIn("RUNTIME_NO_INJECTION", out)

    def test_unowned_memory_code_is_a_finding(self):
        self.put("bin/estate-memory-new")
        self.put("bin/estate-memory-known")
        reg = base(
            scan_code=["bin/*memory*"],
            lanes=[lane("k", owns=["bin/estate-memory-known"])],
        )
        code, out = run(self.d, reg)
        self.assertIn("UNOWNED_CODE bin/estate-memory-new", out.replace("**", ""))
        self.assertNotIn("UNOWNED_CODE** bin/estate-memory-known", out)

    def test_unclassified_memory_doc_and_duplicate_adr_number(self):
        self.put("docs/decisions/0036-one-memory-plane.md")
        self.put("docs/decisions/0036-a-claim-is-stored-only-if-reexecuted.md")
        self.put("docs/specs/hosted-session-memory.md")
        reg = base(
            scan_docs=["docs/decisions", "docs/specs"],
            lanes=[lane("x")],
            documents={"docs/decisions/0036-one-memory-plane.md": "KEEP-AMEND"},
        )
        code, out = run(self.d, reg)
        self.assertIn("ADR_NUMBER_DUPLICATE", out)
        self.assertIn("UNREGISTERED_DOC", out)
        self.assertIn("hosted-session-memory.md", out)

    def test_stale_register_is_red(self):
        reg = base(verified_at="2026-09-01", lanes=[lane("x")])
        code, out = run(self.d, reg)
        self.assertIn("REGISTER_STALE", out)

    def test_door_down_is_down_not_ok(self):
        self.put("a.py")
        ln = lane(
            "door",
            probes=[{"t": "file", "path": "a.py"}],
            live=[{"t": "door", "url": "http://127.0.0.1:9/", "timeout_s": 2}],
        )
        code, out = run(self.d, base(lanes=[ln]))
        self.assertIn("| door | store | KEEP | down |", out)

    def test_lane_with_nothing_measurable_is_unknown_not_built(self):
        code, out = run(self.d, base(lanes=[lane("claude-mem", "DECIDE")]))
        self.assertIn("| claude-mem | store | DECIDE | unknown |", out)

    def test_blind_ok_does_not_hide_a_broken_lane(self):
        ln = lane(
            "door",
            probes=[{"t": "file", "path": "missing.py"}],
            live=[{"t": "ledger_recent", "path": "~/x"}],
        )
        code, out = run(self.d, base(lanes=[ln]), "--blind-ok")
        self.assertEqual(code, 1)
        self.assertIn("broken", out)

    def test_blind_ok_lets_a_purely_blind_register_pass_in_ci(self):
        self.put("a.py")
        ln = lane(
            "door",
            probes=[{"t": "file", "path": "a.py"}],
            live=[{"t": "ledger_recent", "path": "~/x"}],
        )
        sf = {
            "id": "fleet",
            "needs": [],
            "probes": [{"t": "file", "path": "a.py"}],
            "live": [{"t": "canary_surface", "path": "~/c.json", "surface": "fleet"}],
        }
        code, out = run(self.d, base(lanes=[ln], founder_surfaces=[sf]), "--blind-ok")
        self.assertIn("blind", out)
        self.assertEqual(code, 0)

    def test_status_file_is_generated_with_expiry_notice_and_narrative(self):
        out_dir = os.path.join(self.d, "out")
        reg = base(
            lanes=[lane("x")],
            where_we_are={"as_of": "2026-10-31", "summary": ["door is down"]},
        )
        run(self.d, reg, "--out", out_dir)
        txt = open(os.path.join(out_dir, "STATUS.md")).read()
        self.assertIn("Memory status: as of 2026-10-31T12:00:00Z UTC", txt)
        self.assertIn("older than 8 hours", txt)
        self.assertIn("- door is down", txt)
        self.assertIn("| x |", txt)

    def test_failures_emit_events_for_the_alerter(self):
        self.put("a.py")
        out_dir = os.path.join(self.d, "out")
        ln = lane("door", probes=[{"t": "file", "path": "a.py"}])
        run(self.d, base(lanes=[ln]), "--out", out_dir)
        ev = [json.loads(x) for x in open(os.path.join(out_dir, "events.jsonl"))]
        self.assertTrue(
            any(e["event"] == "fail" and e["stage"] == "LANE_NOT_OPERATING" for e in ev)
        )
        self.assertEqual(ev[-1]["event"], "done")

    def test_cross_surface_canary_needs_every_pair(self):
        p = self.put(
            "canary.json", json.dumps({"pairs": {"a->b": True}}), root=self.home
        )
        ln = lane(
            "canary",
            probes=[],
            live=[{"t": "canary", "path": "~/canary.json", "max_age_h": 24}],
        )
        rp = os.path.join(self.d, "reg.json")
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        json.dump(
            base(lanes=[ln], required_runtimes=["a", "b", "c"], verified_at=now[:10]),
            open(rp, "w"),
        )
        r = subprocess.run(
            [
                sys.executable,
                TOOL,
                "audit",
                "--root",
                self.d,
                "--register",
                rp,
                "--home",
                self.home,
                "--now",
                now,
            ],
            capture_output=True,
            text=True,
        )
        self.assertIn("cross-surface pairs not proven", r.stdout)

    def test_no_founder_surfaces_declared_is_red(self):
        code, out = run(self.d, base(lanes=[lane("x")]))
        self.assertIn("FOUNDER_SURFACES_NONE", out)

    def test_surface_is_uncovered_when_a_lane_it_needs_is_not_operating(self):
        self.put("a.py")
        reg = base(
            lanes=[lane("door", probes=[{"t": "file", "path": "a.py"}])],
            founder_surfaces=[
                {
                    "id": "fleet",
                    "needs": ["door"],
                    "probes": [{"t": "file", "path": "a.py"}],
                    "live": [],
                }
            ],
        )
        code, out = run(self.d, reg)
        self.assertIn("| fleet | uncovered |", out)
        self.assertIn("Covered 0 of 1", out)
        self.assertIn("Memory is operational: NO", out)

    def test_surface_is_covered_only_when_canary_was_seen_there(self):
        self.put("a.py")
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for seen, want in (
            (False, "not seen on the fleet surface"),
            (True, "Covered 1 of 1"),
        ):
            self.put(
                "c.json", json.dumps({"surfaces": {"fleet": seen}}), root=self.home
            )
            ln = lane(
                "door",
                probes=[{"t": "file", "path": "a.py"}],
                live=[{"t": "ledger_recent", "path": "~/c.json"}],
            )
            sf = {
                "id": "fleet",
                "needs": ["door"],
                "probes": [{"t": "file", "path": "a.py"}],
                "live": [
                    {"t": "canary_surface", "path": "~/c.json", "surface": "fleet"}
                ],
            }
            rp = os.path.join(self.d, "reg.json")
            hb = os.path.join(self.d, "hb", "memory-audit.json")
            json.dump(
                base(lanes=[ln], founder_surfaces=[sf], verified_at=now[:10]),
                open(rp, "w"),
            )
            r = subprocess.run(
                [
                    sys.executable,
                    TOOL,
                    "audit",
                    "--root",
                    self.d,
                    "--register",
                    rp,
                    "--home",
                    self.home,
                    "--now",
                    now,
                    "--heartbeat",
                    hb,
                ],
                capture_output=True,
                text=True,
            )
            self.assertIn(want, r.stdout + r.stderr)
            h = json.load(open(hb))
            self.assertEqual(h["healthy"], 1 if seen else 0)
            self.assertEqual(r.returncode, 0 if seen else 1, r.stdout)

    def test_blind_ok_does_not_pass_an_uncovered_surface(self):
        self.put("a.py")
        reg = base(
            lanes=[
                lane(
                    "door",
                    probes=[{"t": "file", "path": "a.py"}],
                    live=[{"t": "ledger_recent", "path": "~/x"}],
                )
            ],
            founder_surfaces=[
                {
                    "id": "fleet",
                    "needs": ["door"],
                    "probes": [{"t": "file", "path": "missing.py"}],
                    "live": [],
                }
            ],
        )
        code, out = run(self.d, reg, "--blind-ok")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
