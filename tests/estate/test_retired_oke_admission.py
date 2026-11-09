"""Negative admission tests for the founder-retired OKE execution surface (#7387).

This protects against a recurrence of run 42540429909, which executed
mutation-capable OKE apply-targets after retirement. Tests do not call OCI.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/oke-check.yml"
SCRIPT = ROOT / "bin/idp-oke-rebuild"


class RetiredOkeAdmissionTests(unittest.TestCase):
    def test_workflow_has_no_scheduled_oke_or_oidc_authority(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        header, jobs = source.split("\njobs:\n", 1)
        self.assertNotIn("  schedule:", header)
        self.assertNotIn("id-token: write", header)
        self.assertIn("contents: read", header)
        self.assertIn("  retired-substrate:", jobs)

    def test_legacy_job_is_disabled_at_job_level_not_only_first_step(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        retirement = source.split("\n  retired-substrate:\n", 1)[1]
        retirement = retirement.split("\n  check:\n", 1)[0]
        legacy = source.split("\n  check:\n", 1)[1]
        self.assertIn("RETIRED_SUBSTRATE", retirement)
        self.assertIn("exit 78", retirement)
        self.assertIn("EVENT_NAME", retirement)
        self.assertNotIn("secrets.", retirement)
        self.assertNotIn("id-token: write", retirement)
        # Several legacy steps use always(); failing only an early step is unsafe.
        self.assertIn("    if: ${{ false }}", legacy)
        self.assertIn("always()", legacy)

    def test_all_legacy_modes_refuse_before_oci_or_state_commands(self) -> None:
        modes = (
            "--check", "--probe", "--apply", "--apply-targets",
            "--replace-cluster", "--break-glass", "--surge-node",
            "--surge-finish", "--teardown-rebuild",
        )
        with tempfile.TemporaryDirectory() as directory:
            fake_bin = Path(directory) / "bin"
            fake_bin.mkdir()
            marker = Path(directory) / "effect-attempted"
            for name in ("oci", "tofu", "kubectl", "flux", "curl", "gh"):
                command = fake_bin / name
                command.write_text(
                    "#!/bin/sh\n"
                    "printf 'attempt\\n' >> \"$OKE_EFFECT_MARKER\"\n"
                    "exit 91\n",
                    encoding="utf-8",
                )
                command.chmod(0o755)
            env = dict(os.environ)
            env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
            env["OKE_EFFECT_MARKER"] = str(marker)
            for mode in modes:
                with self.subTest(mode=mode):
                    result = subprocess.run(
                        ["bash", str(SCRIPT), mode],
                        cwd=ROOT,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 78, result.stderr)
                    self.assertIn("RETIRED_SUBSTRATE", result.stderr)
                    self.assertFalse(
                        marker.exists(), "a retired OKE mode reached an effect tool"
                    )


if __name__ == "__main__":
    unittest.main()
