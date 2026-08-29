"""crew#586 CP2: the five conscience rules fire on the bad fixture and stay silent on the clean one.

Both ways through conftest over the whole policy dir, so operating_model.rego's own rules are
loaded too: the clean fixture must pass every rule (LAW 38), and every rule named by a
`pr_rule:` in conscience/tenets.yaml must exist in some policy file.
"""
import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

IDP = pathlib.Path(__file__).resolve().parents[1]
FX = IDP / "policy" / "fixtures"
CONSCIENCE_RULES = {"no_provider_in_diff", "no_floating_tag", "new_script_has_a_test", "incident_has_a_guard", "new_dependency_has_a_ledger_entry"}

pytestmark = pytest.mark.skipif(shutil.which("conftest") is None, reason="BLIND: conftest not installed")


def conftest(fixture: str) -> tuple[int, set[str]]:
    p = subprocess.run(["conftest", "test", "--parser", "json", "-p", str(IDP / "policy"), str(FX / fixture)], capture_output=True, text=True)
    return p.returncode, set(re.findall(r"rule=([a-z_]+)", p.stdout + p.stderr))


def test_bad_fixture_fires_every_conscience_rule():
    rc, fired = conftest("conscience-bad.json")
    assert rc != 0 and CONSCIENCE_RULES <= fired, fired


def test_clean_fixture_fires_nothing():
    rc, fired = conftest("conscience-clean.json")
    assert rc == 0 and not fired, fired


def test_every_tenet_names_a_rule_that_exists():
    policy = "".join(f.read_text() for f in (IDP / "policy").glob("*.rego")) + (IDP / "bin" / "pr-report").read_text()
    for r in yaml.safe_load((IDP / "conscience" / "tenets.yaml").read_text())["tenets"]:
        name = "no_secret_added" if r["pr_rule"] == "no_static_secret_in_diff" else r["pr_rule"]
        assert f"rule={name}" in policy, f"tenet {r['name']} names rule {name} which no policy defines"
