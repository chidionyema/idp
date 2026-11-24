import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))
import oneshot_router_unblock as mod


class TestOneShotDiscriminator(unittest.TestCase):
    def test_branch_0_already_operational(self):
        d = mod.classify_branch(
            {"http_status": 200, "has_expected_marker": True},
            {"matches": []},
            {},
        )
        self.assertEqual(d["branch"], "BRANCH_0_ALREADY_OPERATIONAL")

    def test_branch_1_env_binding_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            wf = Path(td) / ".github" / "workflows"
            wf.mkdir(parents=True)
            (wf / "deploy-router.yml").write_text(
                "name: deploy-router\njobs:\n  deploy:\n    steps:\n      - run: npx wrangler deploy\n        env:\n          CLOUDFLARE_API_TOKEN: ${{ secrets.SEED_CLOUDFLARE_WORKERS_TOKEN }}\n",
                encoding="utf-8",
            )
            audit = mod.audit_workflows(Path(td))
            d = mod.classify_branch(
                {"http_status": 525, "has_expected_marker": False},
                audit,
                {"repo_secrets": {}, "environment_secrets": {"production": ["SEED_CLOUDFLARE_WORKERS_TOKEN"]}},
            )
            self.assertEqual(d["branch"], "BRANCH_1_WORKFLOW_WIRING_BUG")
            self.assertIn("production", d["next_action"])

    def test_branch_2_bootstrap_dispatch_needed(self):
        d = mod.classify_branch(
            {"http_status": 525, "has_expected_marker": False},
            {"matches": []},
            {"repo_secrets": {"SEED_MERIDIAN_ADMIN_KEY": "2026-11-22T20:38:09Z"}, "environment_secrets": {}},
        )
        self.assertEqual(d["branch"], "BRANCH_2_BOOTSTRAP_DISPATCH_NEEDED")

    def test_branch_3_cloudflare_scope_or_zone_block(self):
        d = mod.classify_branch(
            {"http_status": 525, "has_expected_marker": False},
            {"matches": []},
            {
                "repo_secrets": {},
                "environment_secrets": {},
                "latest_failed_run": {"tail_20_lines": ["Error: HTTP 403 Forbidden checking zone meridianlabs.cloud"]},
            },
        )
        self.assertEqual(d["branch"], "BRANCH_3_CLOUDFLARE_ZONE_OR_SCOPE_BLOCK")

    def test_branch_4_deploy_and_verify(self):
        d = mod.classify_branch(
            {"http_status": 525, "has_expected_marker": False},
            {"matches": [{"file": ".github/workflows/deploy.yml", "uses_wrangler": True, "environments": [], "wiring_suspects": []}]},
            {"repo_secrets": {"SEED_CLOUDFLARE_WORKERS_TOKEN": "2026-11-23T19:00:00Z"}, "environment_secrets": {}},
        )
        self.assertEqual(d["branch"], "BRANCH_4_DEPLOY_AND_VERIFY")

    def test_cli_offline_smoke(self):
        script = Path(__file__).resolve().parent.parent / "bin" / "oneshot_router_unblock.py"
        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "verdict.json"
            p = subprocess.run(
                [sys.executable, str(script), "--repo-root", td, "--skip-live-edge", "--skip-gh", "--out", str(out_file)],
                capture_output=True, text=True,
            )
            self.assertEqual(p.returncode, 10, p.stdout + p.stderr)
            data = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(data["decision"]["branch"], "BRANCH_2_BOOTSTRAP_DISPATCH_NEEDED")


if __name__ == "__main__":
    unittest.main()
