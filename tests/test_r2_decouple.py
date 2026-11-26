"""I-8455 Stage 1 falsifiers: R2 decoupled from the bootstrap critical path.

The 2026-11-23 estate-bootstrap failure (run 45249005413) died on
``FAIL r2 bucket prospector-meridianlabs neither exists nor could be created``
and took the freshly minted DNS/Workers credentials down with it, so the router
never got its oxygen. These tests pin the invariant: an R2 failure gates ONLY
R2 outputs; DNS and Workers mint, verify and vault regardless.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "idp-bootstrap-cloudflare"


def script_text() -> str:
    return SCRIPT.read_text()


class R2DecoupleFalsifiers(unittest.TestCase):
    def test_script_is_valid_bash(self) -> None:
        r = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_fatal_r2_failure_remains(self) -> None:
        """Known-bad fixture: the exact line that killed run 45249005413 must not
        exist in any form — an R2 failure must never abort the bootstrap."""
        text = script_text()
        self.assertNotIn(
            "fail r2",
            text,
            "a fatal 'fail r2' remains: R2 can still abort the bootstrap",
        )

    def test_r2_vault_write_is_gated_on_r2_success(self) -> None:
        """Known-good fixture: the R2 env vault write only runs when R2 itself
        succeeded (r2_ok), and DNS/Workers vault writes run unconditionally."""
        text = script_text()
        self.assertIn('if [ -n "$r2_ok" ]; then', text)
        r2_write = text.index('idp-vault-put" --merge prospector-engine-env')
        gate = text.index('if [ -n "$r2_ok" ]; then')
        dns_write = text.index("cloudflare-api-token --file")
        wrk_write = text.index("cloudflare-workers-token --file")
        self.assertLess(
            dns_write, gate, "DNS vault write must precede the R2 gate (unconditional)"
        )
        self.assertLess(
            wrk_write,
            gate,
            "Workers vault write must precede the R2 gate (unconditional)",
        )
        self.assertGreater(
            r2_write, gate, "R2 env write must live inside the r2_ok gate"
        )

    def test_keep_path_tolerates_missing_r2(self) -> None:
        """The idempotent keep-path must not demand an R2 vault entry: DNS+Workers
        verifying is enough to keep, else a chronic R2 outage forces re-mint churn."""
        text = script_text()
        self.assertNotIn(
            '[ -n "$dns" ] && verify "$dns" && [ -n "$r2id" ] && [ -n "$wrk" ]',
            text,
            "keep-path still requires r2id; R2 outage would force re-mint churn",
        )
        self.assertIn("R2 gates only R2", text)

    def test_workers_token_is_described_as_the_oxygen(self) -> None:
        """The Workers token must be vaulted on the unconditional path, never inside
        any R2 conditional — it is what SEED_CLOUDFLARE_WORKERS_TOKEN feeds."""
        text = script_text()
        wrk_line = next(
            l for l in text.splitlines() if "cloudflare-workers-token --file" in l
        )
        self.assertFalse(
            lstrip_conditional(wrk_line),
            f"Workers vault write appears conditional: {wrk_line}",
        )


def lstrip_conditional(line: str) -> bool:
    s = line.strip()
    return s.startswith("if ") or s.startswith("elif ")


if __name__ == "__main__":
    unittest.main()
