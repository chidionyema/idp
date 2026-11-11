import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[2]
LIBEXEC = ROOT / "platform/estate/libexec"
GATE = LIBEXEC / "fleet-task-budget.py"
LAUNCHER = LIBEXEC / "agent-invoke.sh"


class FleetBudgetTest(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.state = self.root / "budget.json"
        self.settings = self.root / "budget-settings.json"
        self.harness = self.root / "harness-settings.json"
        self.harness.write_text("{}")

    def initialize(self):
        return subprocess.run(
            [
                sys.executable,
                str(GATE),
                "init",
                "--state",
                str(self.state),
                "--settings",
                str(self.settings),
                "--harness",
                str(self.harness),
            ],
            capture_output=True,
            text=True,
        )

    def pre(self, _=None):
        return subprocess.run(
            [sys.executable, str(GATE), "pre", "--state", str(self.state)],
            capture_output=True,
            text=True,
        )

    def test_admits_twenty_parallel_calls_and_refuses_the_rest(self):
        initialized = self.initialize()
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.assertEqual(initialized.stdout.strip(), "1200")
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as workers:
            results = list(workers.map(self.pre, range(32)))
        denied = [result for result in results if result.returncode]
        self.assertEqual(len(denied), 12)
        self.assertTrue(
            all(
                item.returncode == 2 and "tool_call_cap" in item.stderr
                for item in denied
            )
        )
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
        result = self.pre()
        self.assertEqual(result.returncode, 2)
        self.assertIn("deadline", result.stderr)
        self.assertEqual(json.loads(self.state.read_text())["calls"], 0)

    def test_missing_state_refuses(self):
        result = self.pre()
        self.assertEqual(result.returncode, 2)
        self.assertIn("FLEET_BUDGET_UNAVAILABLE", result.stderr)

    def test_disabled_hooks_refuse_to_start(self):
        self.harness.write_text('{"disableAllHooks": true}')
        self.assertNotEqual(self.initialize().returncode, 0)
        self.assertFalse(self.state.exists())

    def launch(self, mock_source, gate_source=None):
        home = self.root / "home"
        libexec = home / ".estate/libexec"
        libexec.mkdir(parents=True)
        gate = libexec / GATE.name
        if gate_source is None:
            shutil.copyfile(GATE, gate)
        else:
            gate.write_text(gate_source)
        harness = home / ".estate/harness/cc"
        harness.mkdir(parents=True)
        (harness / "settings.json").write_text("{}")
        mock = self.root / "mock-claude"
        mock.write_text(mock_source)
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
                os.environ,
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
        return log

    def test_local_entrypoint_passes_its_all_tools_hook(self):
        log = self.launch(
            f"#!{sys.executable}\n"
            "import concurrent.futures, json, subprocess, sys\n"
            "args = sys.argv[1:]\n"
            "with open(args[args.index('--settings') + 1]) as file:\n"
            "    rule, = json.load(file)['hooks']['PreToolUse']\n"
            "assert rule['matcher'] == ''\n"
            "hook, = rule['hooks']\n"
            "with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:\n"
            "    list(pool.map(lambda _: subprocess.run(['bash', '-c', hook['command']]), range(21)))\n"
        )
        self.assertIn("FLEET_BUDGET_EXHAUSTED: tool_call_cap", log.read_text())
        self.assertIn("exit=0", log.read_text())
        state = json.loads(log.with_name(log.name + ".budget.json").read_text())
        self.assertEqual((state["calls"], state["denials"]), (20, 1))

    def test_local_launcher_terminates_a_hung_runner(self):
        shortened = GATE.read_text().replace("MAX_SECONDS = 20 * 60", "MAX_SECONDS = 1")
        log = self.launch("#!/bin/bash\nsleep 5\necho escaped_deadline\n", shortened)
        self.assertIn("exit=124", log.read_text())
        self.assertNotIn("escaped_deadline", log.read_text())
