"""DoF is total: every incident's repair scope contains what decides the incident (the drill's inputs), so
a red state always has a legal exit. 2026-11-13 llm-router deadlocked because the leg registry and the
lifeboat deploy sat outside its hand-written scope."""

import importlib.machinery
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader(
    "dof_gate", str(ROOT / "bin" / "dof-gate")
)
spec = importlib.util.spec_from_loader("dof_gate", loader)
dg = importlib.util.module_from_spec(spec)
loader.exec_module(dg)


class EveryRedStateHasAnExit(unittest.TestCase):
    def test_each_incident_scope_holds_the_drill_inputs_and_its_deploy(self):
        reg = json.loads((ROOT / "catalog" / "dof-registry.json").read_text())
        for comp in reg["components"]:
            scope, _ = dg.scope_of(reg, comp)
            for need in (
                *dg.DRILL_INPUTS,
                f".github/workflows/{comp}-lifeboat-deploy.yml",
            ):
                with self.subTest(comp=comp, path=need):
                    self.assertTrue(any(dg.glob_match(g, need) for g in scope), need)

    def test_the_gate_and_registry_stay_frozen_while_red(self):
        reg = json.loads((ROOT / "catalog" / "dof-registry.json").read_text())
        for frozen in ("bin/dof-gate", "catalog/dof-registry.json"):
            self.assertTrue(
                any(dg.glob_match(g, frozen) for g in reg["immutableWhileRed"])
            )


if __name__ == "__main__":
    unittest.main()
