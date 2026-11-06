"""Regression: the kubeconform result label must not inherit an unrelated failure."""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-ci"


class DiagnosticTruthTests(unittest.TestCase):
    def test_kubeconform_reports_its_own_result_even_if_another_rung_is_red(self):
        script = SCRIPT.read_text(encoding="utf-8")
        matching = [
            line.strip()
            for line in script.splitlines()
            if 'say "ok    kubeconform clusters/"' in line
        ]
        self.assertEqual(len(matching), 1)
        line = matching[0]
        self.assertIn('$_kubeconform_exit', line)
        self.assertNotIn('"$fail"', line)
        for prior, local, expected in (
            (1, 0, "ok    kubeconform clusters/"),
            (0, 0, "ok    kubeconform clusters/"),
            (0, 1, "FAIL  kubeconform  clusters/"),
            (1, 1, "FAIL  kubeconform  clusters/"),
        ):
            with self.subTest(prior_failure=prior, local_exit=local):
                command = (
                    'say() { printf "%s\\n" "$*"; }; '
                    f'fail={prior}; _kubeconform_exit={local}; '
                    f'{line}'
                )
                result = subprocess.run(
                    ["bash", "-c", command], capture_output=True, text=True, check=False
                )
                self.assertEqual(result.stdout.strip(), expected)

    def test_real_kubeconform_failure_still_sets_the_aggregate_gate_red(self):
        script = SCRIPT.read_text(encoding="utf-8")
        start = script.index("_kubeconform_exit=${PIPESTATUS[0]}")
        block = script[start : start + 600]
        self.assertIn('if [ "$_kubeconform_exit" -ne 0 ]; then', block)
        self.assertIn("fail=1", block)


if __name__ == "__main__":
    unittest.main()
