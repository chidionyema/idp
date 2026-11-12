"""Live-code boundary tests: no Temporal dispatch, runner/tool call or shadow fork.

All gateway, quota and signature checks remain independent; these tests prove
the generic unauthenticated doors reject a typed command before side effects.
"""
import argparse
import asyncio
import contextlib
import io
import json
import unittest
from unittest.mock import AsyncMock, patch

from temporalio.exceptions import ApplicationError

from sovereign import cli, command_codes
from sovereign.engine import client, runners
from sovereign.shadow import branching


COMMAND = (
    "CC1 ACT=CORRECT_PROTOCOL TARGET=protocol:I10 EFFECT=PATCH "
    "WORK=4000 RESERVE=1200 PROTO=I10+I2 CLASS=provider-capacity "
    "PARENT=INS-8018 PROVIDER=gemini MODEL=gemini-carbon MODE=ELITE"
)


class SharedIngressTests(unittest.IsolatedAsyncioTestCase):
    async def test_client_blocks_before_temporal_connect(self):
        with patch.object(client, "get_client", new_callable=AsyncMock) as connect:
            with self.assertRaises(command_codes.InstructionAdmissionRequired) as denied:
                await client.start(COMMAND, runner="llm", by="founder", budget=20000)
            connect.assert_not_awaited()
            self.assertEqual(denied.exception.verdict["state"], "QUARANTINED")

    async def test_unknown_version_blocks_before_temporal(self):
        with patch.object(client, "get_client", new_callable=AsyncMock) as connect:
            with self.assertRaises(command_codes.InstructionAdmissionRequired):
                await client.start("CC2 ACT=RELEASE", runner="llm", budget=20000)
            connect.assert_not_awaited()

    async def test_shared_effect_runner_refuses_nonretryably(self):
        for runner in ("echo", "llm"):
            with self.subTest(runner=runner):
                with self.assertRaises(ApplicationError) as denied:
                    await runners.run(runner, COMMAND, None, 1, [], session_id="sb-test")
                self.assertTrue(denied.exception.non_retryable)
                self.assertEqual(denied.exception.type, "ESTATE_COMMAND_ADMISSION_DENIED")

    async def test_ordinary_session_still_dispatches(self):
        transport = AsyncMock()
        with patch.object(client, "get_client", new_callable=AsyncMock, return_value=transport):
            result = await client.start("inspect a harmless log", runner="echo", budget=100)
        self.assertTrue(result["session_id"].startswith("sb-"))
        transport.start_workflow.assert_awaited_once()

    async def test_direct_shadow_start_is_refused_before_workflow(self):
        transport = AsyncMock()
        with self.assertRaises(command_codes.InstructionAdmissionRequired):
            await branching.start(transport, {"task": COMMAND, "parent_id": "x"})
        transport.start_workflow.assert_not_awaited()

    async def test_direct_shadow_params_refuse_before_fork(self):
        with self.assertRaises(command_codes.InstructionAdmissionRequired):
            branching.params(COMMAND, runner="llm", repo=None, budget=10000, count=2)


class CliIngressTests(unittest.TestCase):
    def args(self, task, branches=None):
        return argparse.Namespace(task=task, runner="echo", repo=None, estate=None,
                                  by="cli", budget=20000, critical=False,
                                  json=True, branches=branches)

    def test_cli_refuses_without_forking_or_spending(self):
        with patch.object(cli.engine_client, "start", new_callable=AsyncMock) as start:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli.cmd_start(self.args(COMMAND, branches=2))
            self.assertNotEqual(rc, 0)
            outcome = json.loads(buf.getvalue())
            self.assertEqual(outcome["verdict"], "BLOCKED")
            self.assertFalse(outcome["effect_authorized"])
            start.assert_not_awaited()

    def test_plain_cli_keeps_prior_capability(self):
        with patch.object(cli.engine_client, "start", new_callable=AsyncMock,
                          return_value={"session_id": "sb-valid"}) as start:
            with contextlib.redirect_stdout(io.StringIO()):
                rc = cli.cmd_start(self.args("inspect harmless log"))
            self.assertEqual(rc, 0)
            start.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
