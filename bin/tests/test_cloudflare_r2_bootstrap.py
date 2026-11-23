"""Falsify the Cloudflare R2 bucket decision with the real bootstrap shell block."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "idp-bootstrap-cloudflare"


def bucket_block():
    source = SOURCE.read_text()
    first = source.index("# Use the scoped R2 principal.")
    last = source.index("unset R2_VAL bk created", first) + len("unset R2_VAL bk created")
    return source[first:last]


HARNESS = r'''set -euo pipefail
R2_VAL=R2_NARROW_TOKEN; ROOT=ROOT_TOKEN; ACCOUNT_ID=ACC; BUCKET=prospector-meridianlabs
fail() { echo "FAIL $1 $2"; exit 1; }
cf() {
  local token=$1 method=$2 path=$3
  echo "$token $method $path" >> "$CALL_LOG"
  case "$method:$path" in
    GET:/accounts/ACC/r2/buckets/prospector-meridianlabs)
      if [[ "$token" != R2_NARROW_TOKEN ]]; then echo '{"success":false,"errors":[{"code":10000}]}'; return; fi
      case "$SCENARIO" in
        exists) echo '{"success":true,"result":{"name":"prospector-meridianlabs"}}';;
        missing|create-denied) echo '{"success":false,"errors":[{"code":10006}]}';;
        forbidden) echo '{"success":false,"errors":[{"code":10000}]}';;
        entitlement) echo '{"success":false,"errors":[{"code":10042}]}';;
      esac;;
    POST:/accounts/ACC/r2/buckets)
      if [[ "$token" != R2_NARROW_TOKEN ]]; then echo '{"success":false,"errors":[{"code":10000}]}'; return; fi
      if [[ "$SCENARIO" = create-denied ]]; then
        echo '{"success":false,"errors":[{"code":10042}]}'
      else
        echo '{"success":true,"result":{"name":"prospector-meridianlabs"}}'
      fi;;
    *) return 55;;
  esac
}
'''


class R2BootstrapTests(unittest.TestCase):
    def test_r2_principal_and_decision_table(self):
        scenarios = [
            ("exists", 0, 1, "PASS"),
            ("missing", 0, 2, "PASS"),
            ("forbidden", 1, 1, "code 10000"),
            ("entitlement", 1, 1, "code 10042"),
            ("create-denied", 1, 2, "code 10042"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for scenario, rc, count, marker in scenarios:
                with self.subTest(scenario=scenario):
                    log = str(Path(directory) / (scenario + ".log"))
                    script = HARNESS + "\n" + bucket_block() + "\necho PASS\n"
                    outcome = subprocess.run(
                        ["bash", "-c", script],
                        env={**os.environ, "SCENARIO": scenario, "CALL_LOG": log},
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    calls = Path(log).read_text().splitlines()
                    self.assertEqual(outcome.returncode, rc, outcome.stdout + outcome.stderr)
                    self.assertEqual(len(calls), count)
                    self.assertTrue(all(s.startswith("R2_NARROW_TOKEN ") for s in calls))
                    self.assertIn(marker, outcome.stdout)
                    self.assertNotIn("ROOT_TOKEN", outcome.stdout + outcome.stderr)

    def test_fail_closed_token_cleanup_before_vault(self):
        source = SOURCE.read_text()
        self.assertIn("trap cleanup EXIT", source)
        self.assertIn("ESCROW_STARTED=1", source)
        self.assertIn('MINTED_R2_ID=$(jq -r .id <<<"$r2tok")', source)
        self.assertNotIn('cf "$ROOT" POST "/accounts/$ACCOUNT_ID/r2/buckets"', source)


if __name__ == "__main__":
    unittest.main()
