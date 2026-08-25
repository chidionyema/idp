"""cp34 acceptance: Cryptographic auditing — SOC2 by default; the first feature delivered

Owner: unclaimed -- set `owner=` in the pending mark when you claim it. The scenarios are skipped while the `pending` mark stands.
Delete the mark in the commit that lands the steps -- after that, a step with no
definition fails this suite, which is the whole point of the mark.

Steps go below the scenarios() call. Fixtures: estate_home, config, dag_root,
receipts_path, clock, budget, messages, scratch_repo, sb, context -- all in
sovereign/tests/bdd/conftest.py.
"""
from __future__ import annotations

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.pending("R17,R33", owner="unclaimed")

scenarios("features/sovereign-bus/cp34_audit_verify.feature")
