"""crew#488 CP3: the free-tier allowance is graded against what the module assumes and provisions.

Rung 4 (incident test). The incident: OCI halved the Always Free A1 allowance on 2026-06-15
(ADR 0004) and the estate learned it from a node pool that would not schedule. The grader must be
red when the granted limit drops below the free allowance the module assumes, red when it cannot
hold what the module provisions, and green otherwise with the paid remainder printed. Both ways
in one run (LAW 45 step 3). The module numbers are read from platform/oci/variables.tf for real.
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader("freetier", str(ROOT / "bin" / "idp-free-tier"))
ft = importlib.util.module_from_spec(importlib.util.spec_from_loader("freetier", _loader))
_loader.exec_module(ft)

MODULE = {"worker_ocpus": 4, "worker_memory_gb": 24, "free_ocpus": 2, "free_memory_gb": 12}


def test_grade_both_ways():
    ok = ft.grade({"a1_cores": 4, "a1_memory_gb": 24, "block_gb": 200}, MODULE)
    assert ok.startswith("ok      free-tier  A1 limit 4 OCPU / 24 GB"), ok
    assert "(2 OCPU / 12 GB paid)" in ok
    cut = ft.grade({"a1_cores": 1, "a1_memory_gb": 24, "block_gb": 200}, MODULE)
    assert cut.startswith("FAIL    free-tier  A1 core limit 1 is below the 2"), cut
    tight = ft.grade({"a1_cores": 2, "a1_memory_gb": 12, "block_gb": 200}, MODULE)
    assert "cannot hold the 4 / 24 the module provisions" in tight, tight
    free = ft.grade({"a1_cores": 2, "a1_memory_gb": 12, "block_gb": 200}, {**MODULE, "worker_ocpus": 2, "worker_memory_gb": 12})
    assert free.endswith("(all free)"), free


def test_module_numbers_come_from_variables_tf():
    m = ft.module_numbers()
    assert set(m) == set(MODULE) and all(v > 0 for v in m.values()), m
    assert m["free_ocpus"] <= m["worker_ocpus"] and m["free_memory_gb"] <= m["worker_memory_gb"], m
