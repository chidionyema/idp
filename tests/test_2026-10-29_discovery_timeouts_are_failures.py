"""2026-10-29: discovery returned success after its critical graph source timed out."""

import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest
import tempfile
import time
from unittest.mock import patch
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "platform/estate/libexec/work-discover.py"
spec = importlib.util.spec_from_file_location("discovery_timeout_regression", SOURCE)
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


class DiscoveryTimeoutRegression(unittest.TestCase):
    def test_timeout_keeps_partial_output_and_requires_optimisation(self):
        with patch.object(
            discovery.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(
                ["growmos"],
                30,
                output=b"graph stage completed\\n",
                stderr=b"waiting on relations\\n",
            ),
        ):
            rc, output = discovery.run(["growmos"], timeout=30)
        self.assertEqual(rc, 124)
        self.assertIn("graph stage completed", output)
        self.assertIn("waiting on relations", output)
        self.assertIn("OPTIMISATION REQUIRED", output)

    def invoke(self, graph):
        names = [
            "source_tickets",
            "source_claims",
            "source_refs",
            "source_worktrees",
            "source_tree",
            "source_memory",
            "source_graph",
        ]
        with contextlib.ExitStack() as stack:
            for name in names:
                stack.enter_context(
                    patch.object(
                        discovery,
                        name,
                        graph if name == "source_graph" else lambda *a: ([], None),
                    )
                )
            stack.enter_context(patch.object(discovery.RESULTS.__class__, "mkdir"))
            stack.enter_context(patch.object(discovery.RESULTS.__class__, "write_text"))
            output = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            rc = discovery.main(["congruence", "--json"])
        return rc, json.loads(output.getvalue())

    def test_a_swallowed_internal_timeout_must_fail_the_complete_query(self):
        def graph(*args):
            with patch.object(
                discovery.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(["growmos"], 30),
            ):
                _rc, error = discovery.run(["growmos"], timeout=30)
            return [], error

        rc, payload = self.invoke(graph)
        self.assertEqual(rc, 124)
        self.assertTrue(
            next(s for s in payload["sources"] if s["name"] == "graph")["timed_out"]
        )
        self.assertTrue(
            all(not s["timed_out"] for s in payload["sources"] if s["name"] != "graph")
        )

    def test_an_empty_successful_search_remains_successful(self):
        rc, payload = self.invoke(lambda *a: ([], None))
        self.assertEqual(rc, 0)
        self.assertEqual(payload["total_hits"], 0)

    def test_a_child_timeout_exit_cannot_be_reported_as_success(self):
        def graph(*args):
            result = subprocess.CompletedProcess(
                ["growmos"], 124, "", "child deadline exceeded"
            )
            with patch.object(discovery.subprocess, "run", return_value=result):
                _rc, error = discovery.run(["growmos"], timeout=30)
            return [], error

        rc, payload = self.invoke(graph)
        self.assertEqual(rc, 124)
        self.assertTrue(
            next(s for s in payload["sources"] if s["name"] == "graph")["timed_out"]
        )


class ExecutorTimeoutRegression(unittest.TestCase):
    def test_outer_timeout_retains_interrupted_stdout_and_stderr(self):
        source = (ROOT / "platform/estate/bin/estate-execute").read_text()
        node = next(
            n
            for n in ast.parse(source).body
            if isinstance(n, ast.FunctionDef) and n.name == "run_steps"
        )
        namespace = {
            "datetime": datetime,
            "timezone": timezone,
            "subprocess": subprocess,
            "json": json,
            "STEP_OUTPUTS": {},
            "_intent_budget": lambda intent: (1, "test caller deadline"),
            "_inject_from": lambda *args: None,
            "interpolate": lambda cmd, args: cmd,
            "log_step": lambda *args: None,
            "close_ticket": lambda *args: None,
            "log": print,
        }
        exec(
            compile(ast.Module(body=[node], type_ignores=[]), "estate-execute", "exec"),
            namespace,
        )
        output = io.StringIO()
        with (
            contextlib.redirect_stdout(output),
            patch.object(
                subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(
                    "probe",
                    1,
                    output=b"measured stage\\n",
                    stderr=b"actual stalled stage\\n",
                ),
            ),
        ):
            status = namespace["run_steps"](
                None, "ticket", {"steps": [{"cmd": "probe"}]}, {}
            )
        self.assertEqual(status, "halted")
        self.assertIn("measured stage", output.getvalue())
        self.assertIn("actual stalled stage", output.getvalue())
        self.assertIn("OPTIMISATION REQUIRED", output.getvalue())


class RuntimeAlertRegression(unittest.TestCase):
    def test_recording_an_alert_does_not_depend_on_the_macos_ui(self):
        source = (ROOT / "bin/estate-runtime-sync").read_text()
        node = next(
            n
            for n in ast.parse(source).body
            if isinstance(n, ast.FunctionDef) and n.name == "alert"
        )
        with tempfile.TemporaryDirectory() as directory:
            inbox = Path(directory) / "alerts" / "inbox.jsonl"
            namespace = {
                "INBOX": inbox,
                "json": json,
                "time": time,
                "subprocess": subprocess,
            }
            exec(
                compile(
                    ast.Module(body=[node], type_ignores=[]),
                    "estate-runtime-sync",
                    "exec",
                ),
                namespace,
            )
            with patch.object(
                subprocess,
                "run",
                side_effect=AssertionError("convergence must not call macOS UI"),
            ):
                namespace["alert"]("voice router rolled back")
            rows = [json.loads(line) for line in inbox.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source"], "estate-runtime-sync")
            self.assertEqual(rows[0]["text"], "voice router rolled back")


if __name__ == "__main__":
    unittest.main()
