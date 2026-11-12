"""Fail-closed wiring regression tests for the shared IDP fast gate.

These are structural falsifiers, not substitutes for real runner execution,
BDD proof evaluation or the estate's protected Greenlane admission.
"""

from __future__ import annotations

import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/fast-gate.yml"
TOOLS = "      - uses: ./.github/actions/estate-tools\n"
GATE = "      - name: fast gate (all actors, fail closed)\n"
GH_ENV_BINDING = "          GH_TOKEN: ${{ github.token }}\n"
PYTHON_DEPS = "      - name: install Python gate dependencies\n"
COMMAND = "        run: IDP_CI_FAST=1 IDP_CI_BASE=$(git merge-base origin/main HEAD) bin/idp-ci"


def require_valid_gate(source: str) -> None:
    assert (
        "    permissions:\n      contents: read\n      pull-requests: read\n" in source
    ), "fast gate must use minimum read-only token permissions"
    assert "steps.actor.outputs.bot" not in source and "bot exemption" not in source, (
        "bot/agent authors must not receive a synthetic green check"
    )
    assert PYTHON_DEPS in source, (
        "Python gate dependencies must execute as a separate step"
    )
    assert (
        "      - name: prove fast-gate wiring with falsifying contract tests\n"
        in source
    ), "the workflow must actually execute its fail-closed structural falsifiers"
    tools = source.find(TOOLS)
    gate = source.find(GATE)
    command = source.find(COMMAND)
    assert 0 <= tools < gate < command, "pinned estate tools must run before bin/idp-ci"
    assert GATE + "        env:\n" + GH_ENV_BINDING in source, (
        "GH_TOKEN must be bound to the actual fast-gate step"
    )
    assert "      - name: python-strict (estate standard, one copy)\n" in source, (
        "the independent Python strict verifier must remain in the job"
    )


class FastGateWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = WORKFLOW.read_text()

    def test_current_workflow(self) -> None:
        require_valid_gate(self.source)

    def test_negative_missing_pinned_tool(self) -> None:
        with self.assertRaises(AssertionError):
            require_valid_gate(self.source.replace(TOOLS, "", 1))

    def test_negative_tool_installed_after_gate(self) -> None:
        with self.assertRaises(AssertionError):
            require_valid_gate(
                self.source.replace(TOOLS, "", 1).replace(
                    COMMAND, COMMAND + "\n" + TOOLS.rstrip("\n"), 1
                )
            )

    def test_negative_missing_token(self) -> None:
        with self.assertRaises(AssertionError):
            require_valid_gate(self.source.replace(GH_ENV_BINDING, "", 1))

    def test_negative_bot_skip(self) -> None:
        with self.assertRaises(AssertionError):
            require_valid_gate(
                self.source.replace(
                    GATE, GATE + "        if: steps.actor.outputs.bot != '1'\n", 1
                )
            )

    def test_negative_unscoped_permissions(self) -> None:
        with self.assertRaises(AssertionError):
            require_valid_gate(
                self.source.replace(
                    "      pull-requests: read", "      pull-requests: write", 1
                )
            )

    def test_negative_missing_python_dependencies(self) -> None:
        with self.assertRaises(AssertionError):
            require_valid_gate(self.source.replace(PYTHON_DEPS, "", 1))


CALLERS = (
    Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml",
    Path(__file__).resolve().parents[1] / ".github/workflows/build-multiarch.yml",
    Path(__file__).resolve().parents[1] / ".github/workflows/portal-app.yml",
)


def require_caller_pr_read(source: str) -> None:
    """A reusable workflow cannot elevate the calling job's GITHUB_TOKEN."""
    lines = source.splitlines()
    positions = [
        i
        for i, line in enumerate(lines)
        if line == "    uses: ./.github/workflows/fast-gate.yml"
    ]
    assert len(positions) == 1, "expected one fast-gate reusable invocation"
    expected = [
        "    permissions:",
        "      contents: read",
        "      pull-requests: read",
        "    uses: ./.github/workflows/fast-gate.yml",
    ]
    assert lines[positions[0] - 3 : positions[0] + 1] == expected, (
        "fast-gate caller must explicitly grant contents and pull-requests read"
    )


class FastGateCallerPermissionTests(unittest.TestCase):
    def test_all_real_callers_grant_pr_read(self) -> None:
        for path in CALLERS:
            with self.subTest(caller=path.name):
                require_caller_pr_read(path.read_text())

    def test_all_callers_fail_without_pr_read(self) -> None:
        for path in CALLERS:
            with self.subTest(caller=path.name):
                source = path.read_text()
                with self.assertRaises(AssertionError):
                    require_caller_pr_read(
                        source.replace("      pull-requests: read", "", 1)
                    )

    def test_all_callers_fail_if_pr_read_is_write(self) -> None:
        for path in CALLERS:
            with self.subTest(caller=path.name):
                source = path.read_text()
                with self.assertRaises(AssertionError):
                    require_caller_pr_read(
                        source.replace(
                            "      pull-requests: read", "      pull-requests: write", 1
                        )
                    )


if __name__ == "__main__":
    unittest.main()
