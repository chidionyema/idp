"""#7740: one missing census capability can never block unrelated promotion again.

Observe real executable references, refuse invented edges, and keep the original
coverage ratchet untouched. The committed witness must regenerate exactly.
"""
import importlib.machinery
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "bin" / "capability-index"
BASELINE = ROOT / "catalog" / "estate-completeness-baseline.json"
WITNESS = ROOT / "catalog" / "estate-capability-registry.json"


def door():
    name = "capability_index_workflow_dependencies"
    loader = importlib.machinery.SourceFileLoader(name, str(SOURCE))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class WorkflowDependencyEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.door = door()

    def test_real_actions_and_known_executables_become_evidence(self):
        example = """
# - uses: untrusted/false-positive@main
jobs:
  check:
    steps:
      - uses: actions/checkout@aabbcc # a real action
      - uses: ./.github/workflows/fast-gate.yml
      - run: |
          # python3 bin/phantom
          echo "bin/phantom"
          python3 - <<'PY'
          print("uses: wrong/action@main")
          print("bin/phantom")
          PY
          python3 bin/idp-ci --check
"""
        self.assertEqual(
            self.door.workflow_uses(example),
            ["./.github/workflows/fast-gate.yml", "actions/checkout@aabbcc"],
        )
        self.assertEqual(
            self.door.workflow_tool_refs(example, {"idp-ci", "phantom"}),
            ["idp-ci"],
        )

    def test_absent_tools_cannot_become_ghost_dependencies(self):
        text = "- run: python3 bin/not-an-estate-tool\n"
        self.assertEqual(self.door.workflow_tool_refs(text, {"idp-ci"}), [])
        self.assertEqual(self.door.workflow_uses(" # uses: evil/ghost@main\n"), [])

    def test_only_directly_observed_action_uses_count_for_coverage(self):
        record = {"kind": "workflow", "depends_on": [],
                  "contract": {"uses": ["actions/checkout@aabbcc"]},
                  "blind": ["dependencies"]}
        self.assertEqual(self.door.completeness_answer(record, "dependencies"), "value")
        record["contract"]["uses"] = []
        self.assertEqual(self.door.completeness_answer(record, "dependencies"), "unknown")

    def test_live_ci_has_a_real_first_party_tool_edge(self):
        ctx = self.door.Context(idp=ROOT)
        records = {r["id"]: r for r in self.door.build_repo_workflows(ctx)}
        ci = records["cap:workflow/gha-ci"]
        self.assertIn("actions/checkout@", " ".join(ci["contract"]["uses"]))
        self.assertIn(
            {"id": "cap:tool/idp-ci", "edge": "invokes"},
            ci["depends_on"],
        )
        self.assertIn(
            {"id": "cap:workflow/gha-fast-gate", "edge": "calls"},
            ci["depends_on"],
        )

    def test_tool_inventory_is_read_once_for_n_workflows(self):
        # The old implementation scanned the bin directory once PER workflow.
        # A 90-workflow census now has one inventory read, not 90.
        d = self.door
        original = d._script_names
        calls = []
        def witness(ctx):
            calls.append(1)
            return original(ctx)
        d._script_names = witness
        try:
            d.build_repo_workflows(d.Context(idp=ROOT))
        finally:
            d._script_names = original
        self.assertEqual(calls, [1])

    def test_witness_generated_from_tree_is_byte_identical(self):
        ctx = self.door.Context(idp=ROOT)
        result = self.door.snapshot_drift(ctx, WITNESS)
        self.assertEqual(result["verdict"], "OK", result)

    def test_old_ratchet_is_not_lowered(self):
        floor = json.loads(BASELINE.read_text())
        self.assertEqual(
            (floor["questions"]["dependencies"]["measured"], floor["total"]),
            (721, 1048),
        )
        snapshot = json.loads(WITNESS.read_text())
        coverage = self.door.completeness_coverage(snapshot["records"])
        self.assertEqual(self.door.completeness_regressions(coverage, floor), [])


if __name__ == "__main__":
    unittest.main()
