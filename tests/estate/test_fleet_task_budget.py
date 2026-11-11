import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "platform/estate/gates/protocol_gate.py"
LAUNCHER = ROOT / "platform/estate/libexec/agent-invoke.sh"


class FleetBudgetTest(TestCase):
    def setUp(self):
        import tempfile

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.state = self.root / "budget.json"
        self.settings = self.root / "settings.json"
        self.settings.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": f'python3 "{GATE}" hook pre',
                                    }
                                ],
                            }
                        ]
                    }
                }
            )
        )
        self.env = dict(
            os.environ,
            ESTATE_BREAKS_DIR=str(self.root / "breaks"),
            ESTATE_BUDGET="off",
            ESTATE_FLEET_BUDGET_STATE=str(self.state),
        )

    def initialize(self):
        return subprocess.run(
            [
                sys.executable,
                str(GATE),
                "fleet-budget-init",
                "--state",
                str(self.state),
                "--settings",
                str(self.settings),
            ],
            env=self.env,
            capture_output=True,
            text=True,
        )

    def pre(self, _=None):
        return subprocess.run(
            [sys.executable, str(GATE), "hook", "pre", "--format", "json"],
            input=json.dumps(
                {"session_id": "run", "tool_name": "Read", "tool_input": {}}
            ),
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def test_admits_twenty_parallel_calls_and_refuses_the_rest(self):
        initialized = self.initialize()
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as workers:
            results = list(workers.map(self.pre, range(32)))
        denied = [json.loads(result) for result in results if result]
        self.assertEqual(len(denied), 12)
        self.assertTrue(all("tool_call_cap" in item["reason"] for item in denied))
        self.assertEqual(json.loads(self.state.read_text())["calls"], 20)

    def test_elapsed_deadline_refuses_first_call(self):
        self.assertEqual(self.initialize().returncode, 0)
        self.state.write_text(
            json.dumps(
                {
                    "started": time.clock_gettime(time.CLOCK_MONOTONIC) - 1201,
                    "calls": 0,
                    "denials": 0,
                }
            )
        )
        self.assertIn("deadline", json.loads(self.pre())["reason"])
        self.assertEqual(json.loads(self.state.read_text())["calls"], 0)

    def test_missing_state_refuses_even_with_legacy_budget_off(self):
        self.assertIn("FLEET_BUDGET_UNAVAILABLE", json.loads(self.pre())["reason"])

    def test_filtered_hook_registration_refuses_to_start(self):
        self.settings.write_text(
            self.settings.read_text().replace('"matcher": ""', '"matcher": "Read"')
        )
        self.assertNotEqual(self.initialize().returncode, 0)
        self.assertFalse(self.state.exists())

    def test_local_entrypoint_injects_budget_and_returns_a_receipt(self):
        home = self.root / "home"
        gate = home / ".estate/gates/protocol_gate.py"
        gate.parent.mkdir(parents=True)
        shutil.copyfile(GATE, gate)
        harness = home / ".estate/harness/cc"
        harness.mkdir(parents=True)
        (harness / "settings.json").write_text(
            self.settings.read_text().replace(str(GATE), str(gate))
        )
        mock = self.root / "mock-claude"
        mock.write_text(
            "#!/bin/bash\n"
            "for i in {1..21}; do\n"
            '  printf \'{"session_id":"fallback","tool_name":"Read"}\' | '
            f'{sys.executable} "{gate}" hook pre --format json\n'
            "done\n"
        )
        mock.chmod(0o755)
        result = subprocess.run(
            [
                "bash",
                str(LAUNCHER),
                "--json",
                json.dumps(
                    {
                        "task": "proof",
                        "repo": str(self.root),
                        "runner": "claude",
                        "budget": 20,
                    }
                ),
            ],
            env=dict(
                self.env,
                HOME=str(home),
                ESTATE_CLAUDE=str(mock),
                CRITICAL_WATCH_TEMPORAL="127.0.0.1:0",
            ),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        response = json.loads(result.stdout)
        self.assertEqual(response["invoked_via"], "local-claude")
        log = Path(response["log"])
        end = time.monotonic() + 30
        while "exit=" not in log.read_text() and time.monotonic() < end:
            time.sleep(0.02)
        self.assertIn("FLEET_BUDGET_EXHAUSTED: tool_call_cap", log.read_text())
        self.assertIn("exit=0", log.read_text())
        state = json.loads(log.with_name(log.name + ".budget.json").read_text())
        self.assertEqual((state["calls"], state["denials"]), (20, 1))
