"""The breaker's enforcement, in the one place it cannot be walked past.

The rule in rules.yaml proves the breaker's logic. This proves the enforcement: that the
extension actually returns { block, reason } when the pattern is proved, and that it never blocks
a first or second look (R38).

The real sequence from 2026-09-12: an agent checked five pull requests one at a time, and the
third carried the same CVE set as the first two. The fourth check was waste. The fifth was waste.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "extensions" / "breaker" / "index.ts"


@pytest.fixture
def node_available():
    r = subprocess.run(["node", "--version"], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip("node is not installed")


class TestTheExtensionExists:
    def test_it_is_on_disk(self):
        assert EXT.is_file(), f"no enforcement extension at {EXT}"

    def test_it_intercepts_tool_call(self):
        """It must hook the same event pi-governance does: pi.on("tool_call")."""
        text = EXT.read_text()
        assert 'pi.on("tool_call"' in text, "the extension does not intercept tool_call"
        assert "block" in text, "the extension never returns a block"

    def test_it_calls_the_merged_breaker(self):
        """LAW 43: the logic lives in bin/idp-circuit-breaker. This only wires it."""
        text = EXT.read_text()
        assert "idp-circuit-breaker" in text, (
            "the extension does not call the merged breaker"
        )

    def test_it_is_installed_where_pi_discovers_it(self):
        """An extension nobody loads is decoration (LAW 28).

        pi auto-discovers `~/.pi/agent/extensions/*/index.ts` and `.pi/extensions/*/index.ts`
        (docs/extensions.md line 118), so there is no settings.json entry to check -- an earlier
        version of this test asserted one and was asserting a mechanism that does not exist.
        The property that matters is that the file sits in a discovered location and exports a
        default function, which is what pi calls.
        """
        installed = (
            Path.home() / ".pi" / "agent" / "extensions" / "breaker" / "index.ts"
        )
        if not installed.is_file():
            pytest.skip(f"not installed on this machine yet ({installed})")
        text = installed.read_text()
        assert "export default function" in text, (
            "pi calls the default export; there is none"
        )

    def test_it_exports_a_default_function(self):
        """pi calls the default export with the extension API. Without it the file loads and does
        nothing, which looks identical to working."""
        text = EXT.read_text()
        assert "export default function" in text, (
            "no default export, so pi has nothing to call"
        )


class TestItBlocksProvedRepetition:
    def test_it_blocks_on_the_third_identical_finding(self, node_available):
        """Run the extension's decision function directly, the way pi would call it."""
        js = ROOT / "extensions" / "breaker" / "decide.mjs"
        assert js.is_file(), f"no runnable decision module at {js}"
        r = subprocess.run(
            ["node", str(js)],
            input=json.dumps(
                {
                    "observations": [
                        {
                            "finding": "CVE-2026-13221 CVE-2026-42496 CVE-2026-8376",
                            "target": "pr-1",
                        },
                        {
                            "finding": "CVE-2026-8376 CVE-2026-13221 CVE-2026-42496",
                            "target": "pr-2",
                        },
                        {
                            "finding": "CVE-2026-42496 CVE-2026-8376 CVE-2026-13221",
                            "target": "pr-3",
                        },
                    ],
                    "next": {
                        "finding": "CVE-2026-13221 CVE-2026-42496 CVE-2026-8376",
                        "target": "pr-4",
                    },
                }
            ),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["block"] is True, (
            "the third identical finding did not block the fourth"
        )
        assert "423" in out["reason"] or "Locked" in out["reason"]
        assert out["lever"], "the block named no lever"

    def test_it_never_blocks_the_first_two(self, node_available):
        js = ROOT / "extensions" / "breaker" / "decide.mjs"
        for n in (1, 2):
            obs = [
                {"finding": "CVE-2026-13221", "target": f"pr-{i}"}
                for i in range(1, n + 1)
            ]
            r = subprocess.run(
                ["node", str(js)],
                input=json.dumps(
                    {
                        "observations": obs,
                        "next": {"finding": "CVE-2026-13221", "target": "pr-x"},
                    }
                ),
                capture_output=True,
                text=True,
            )
            assert json.loads(r.stdout)["block"] is False, (
                f"blocked after {n} observation(s)"
            )

    def test_it_never_blocks_nine_different_findings(self, node_available):
        """The R38 case: nine targets, nine causes, none of them blocked."""
        js = ROOT / "extensions" / "breaker" / "decide.mjs"
        obs = [
            {"finding": f"unique failure {i} on target {i}", "target": f"t-{i}"}
            for i in range(1, 10)
        ]
        r = subprocess.run(
            ["node", str(js)],
            input=json.dumps(
                {
                    "observations": obs,
                    "next": {
                        "finding": "unique failure 10 on target 10",
                        "target": "t-10",
                    },
                }
            ),
            capture_output=True,
            text=True,
        )
        assert json.loads(r.stdout)["block"] is False


class TestItIsBlindRatherThanSilent:
    """A guard that cannot run its check must say so. Measured 2026-09-12.

    The breaker lives in bin/, and this estate runs one session per git worktree: the primary
    checkout is usually on another branch, so `repoRoot/bin/idp-circuit-breaker` frequently does
    not exist. The first version of decide.mjs spawned a missing path, got nothing, and answered
    {"block": false} -- indistinguishable from a clean result. That is the calico lesson: an empty
    feed is not a clean bill.
    """

    def test_it_reports_blind_when_the_tool_is_absent(self, node_available, tmp_path):
        js = ROOT / "extensions" / "breaker" / "decide.mjs"
        r = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                (
                    "import { decide } from '" + str(js) + "';"
                    "const out = decide('/nonexistent-root', {observations:["
                    "{finding:'x',target:'1'},{finding:'x',target:'2'},{finding:'x',target:'3'}],"
                    "next:{finding:'x',target:'4'}});"
                    "process.stdout.write(JSON.stringify(out));"
                ),
            ],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out.get("blind"), (
            "a missing tool was reported as a clean result, not BLIND"
        )
        assert "idp-circuit-breaker" in out["blind"]

    def test_it_finds_the_tool_in_a_sibling_worktree(self, node_available):
        """The primary checkout is often on another branch; the tool is in a worktree."""
        js = ROOT / "extensions" / "breaker" / "decide.mjs"
        r = subprocess.run(
            ["node", str(js)],
            input=json.dumps(
                {
                    "observations": [
                        {"finding": "CVE-2026-13221 CVE-2026-42496", "target": "pr-1"},
                        {"finding": "CVE-2026-42496 CVE-2026-13221", "target": "pr-2"},
                        {"finding": "CVE-2026-13221 CVE-2026-42496", "target": "pr-3"},
                    ],
                    "next": {
                        "finding": "CVE-2026-13221 CVE-2026-42496",
                        "target": "pr-4",
                    },
                }
            ),
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "ESTATE_ROOT": str(ROOT)},
        )
        out = json.loads(r.stdout)
        assert not out.get("blind"), (
            f"lost the tool despite a worktree holding it: {out}"
        )
        assert out["block"] is True
