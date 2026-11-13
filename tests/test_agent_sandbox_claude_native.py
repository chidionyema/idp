"""Negative checks for the founder-authorized Claude Code launch path."""

import unittest
from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[1] / ".github" / "workflows" / "agent-sandbox.yml"
)


class ClaudeNativeHarnessContract(unittest.TestCase):
    def test_founder_authority_remains_mandatory(self):
        s = WORKFLOW.read_text()
        self.assertIn("github.actor == vars.ESTATE_FOUNDER_LOGIN", s)
        self.assertIn("github.event.issue.user.login == vars.ESTATE_FOUNDER_LOGIN", s)
        self.assertIn("github.event.label.name == 'claude-native'", s)
        self.assertIn("github.event.label.name == 'legion-run'", s)

    def test_all_harness_selectors_are_consistent(self):
        s = WORKFLOW.read_text()
        selector = (
            "HARNESS: ${{ github.event_name == 'issues' && "
            "(github.event.label.name == 'claude-native' && "
            "'claude-code' || 'gemini') || inputs.harness }}"
        )
        self.assertEqual(4, s.count(selector))
        self.assertNotIn("issues' && 'gemini' || inputs.harness", s)

    def test_live_claude_probe_precedes_agent_execution(self):
        s = WORKFLOW.read_text()
        p = s.index("bin/claude-anthropic --verify-live")
        run = s.index('bin/claude-anthropic -p "$TASK"')
        self.assertLess(p, run)
        self.assertIn("CLAUDE_NATIVE_PROVIDER_NOT_VERIFIED", s)
        self.assertNotIn('rc=0; claude -p "$TASK"', s)

    def test_private_receipt_is_sealed_not_printed(self):
        s = WORKFLOW.read_text()
        self.assertIn("claude-provider-receipt", s)
        self.assertIn("claude-provider-error", s)
        self.assertIn('> "$out/claude-provider-receipt"', s)
        self.assertIn('> "$out/stdout" 2>&1', s)
        self.assertNotIn('cat "$out/claude-provider-receipt"', s)

    def test_epistemic_firewall_and_patch_submission_remain(self):
        s = WORKFLOW.read_text()
        self.assertIn("needs: [agent, firewall]", s)
        self.assertIn("bin/epistemic_firewall.py", s)
        self.assertIn("persist-credentials: false", s)
        self.assertIn("contents: read", s)


if __name__ == "__main__":
    unittest.main()
