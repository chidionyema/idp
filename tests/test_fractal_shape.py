"""Falsifiers for the architecture boundary: invalid modules must be named."""
import json
import runpy
import tempfile
import unittest
from pathlib import Path

MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "bin" / "fractal-shape"))

def component(root: Path, folder: str, **overrides) -> Path:
    base = root / folder
    for directory in ("src", "contracts", "tests"):
        (base / directory).mkdir(parents=True, exist_ok=True)
    (base / "contracts" / "interface.json").write_text("{}")
    obj = {
        "schema": "estate.fractal.component/v1",
        "id": folder,
        "version": "1.0.0",
        "kind": "primitive",
        "owner": "architecture",
        "stage": "candidate",
        "source": "src",
        "provides": [{"capability": folder, "version": "1.0.0", "interface": "contracts/interface.json"}],
        "requires": [],
        "effects": ["none"],
        "state": "stateless",
        "verification": {"contract_tests": "tests"},
    }
    obj.update(overrides)
    path = base / "component.json"
    path.write_text(json.dumps(obj))
    return path

class ComponentConformanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_valid_component(self):
        component(self.root, "memory/retrieval")
        self.assertEqual(MODULE["scan"](self.root)["invalid"], 0)

    def test_missing_contract_is_refused(self):
        component(self.root, "memory/retrieval", provides=[
            {"capability": "memory/retrieval", "version": "1.0.0", "interface": "../outside.json"}])
        self.assertIn("interface missing", json.dumps(MODULE["scan"](self.root)["errors"]))

    def test_versions_are_mandatory(self):
        component(self.root, "memory/retrieval", version="latest")
        self.assertIn("SemVer", json.dumps(MODULE["scan"](self.root)["errors"]))

    def test_unknown_effect_is_refused(self):
        component(self.root, "memory/retrieval", effects=["superuser"])
        self.assertIn("effects", json.dumps(MODULE["scan"](self.root)["errors"]))

    def test_duplicate_id_is_refused(self):
        component(self.root, "memory/retrieval")
        component(self.root, "memory/competitor", id="memory/retrieval")
        self.assertGreater(MODULE["scan"](self.root)["invalid"], 0)

    def test_stateful_requires_state_contract(self):
        component(self.root, "memory/retrieval", state="stateful")
        self.assertIn("state_contract", json.dumps(MODULE["scan"](self.root)["errors"]))

    def test_recursive_dependency_cycle_is_refused(self):
        component(self.root, "memory/retrieval",
                  requires=[{"capability": "memory/storage", "version": "^1.0.0"}])
        component(self.root, "memory/storage",
                  requires=[{"capability": "memory/retrieval", "version": "^1.0.0"}])
        self.assertIn("dependency cycle", json.dumps(MODULE["scan"](self.root)["errors"]))

    def test_architecture_changes_are_classified_for_review(self):
        self.assertEqual(MODULE["classify"]("modules/memory/contracts/retrieve.json"), "architecture-review")
        self.assertEqual(MODULE["classify"]("modules/memory/component.json"), "architecture-review")
        self.assertEqual(MODULE["classify"]("modules/memory/src/retrieval.py"), "normal-change")

if __name__ == "__main__":
    unittest.main()
