"""Binds features/identity/front-door-oidc-client.feature (crew#269, crew#281, crew#288, crew#297).
Steps run bin/cloud-agnostic-gate over the repository and grep the tracked tree for real."""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/identity/front-door-oidc-client.feature")

IDP = Path(__file__).resolve().parents[3]
POD = IDP / "platform" / "identity" / "oauth2-proxy.yaml"
PROVIDER_KEYS = ("oidc-issuer-url", "login-url", "redeem-url", "oidc-jwks-url", "profile-url")
RETIRED = ("platform/access", "access-apply", "ESTATE_LOGIN_GITHUB_USER")
ALLOWED = ("features/identity/front-door-oidc-client.feature", "docs/decisions/")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=IDP, capture_output=True, text=True, check=True).stdout


@pytest.fixture
def state() -> dict:
    return {}


@given("platform/identity/oauth2-proxy.yaml")
def _pod(state: dict) -> None:
    assert POD.is_file()
    state["pod"] = POD.read_text()


@when("bin/cloud-agnostic-gate runs")
def _gate(state: dict) -> None:
    state["gate"] = subprocess.run([sys.executable, str(IDP / "bin" / "cloud-agnostic-gate")],
                                   env={**os.environ, "CLOUD_AGNOSTIC_ROOT": str(IDP)}, capture_output=True, text=True)


@then("every provider URL is a ${ESTATE_OIDC_*} substitution from clusters/oke/estate-config.yaml")
def _substituted(state: dict) -> None:
    r = state["gate"]
    assert r.returncode == 0, r.stdout + r.stderr
    config = (IDP / "clusters" / "oke" / "estate-config.yaml").read_text()
    for key in PROVIDER_KEYS:
        m = re.search(rf'^\s+{key}:\s*"(\$\{{(ESTATE_OIDC_[A-Z_]+)\}}[^"]*)"', state["pod"], re.M)
        assert m, f"{key} is not a ${{ESTATE_OIDC_*}} substitution in {POD.name}"
        assert re.search(rf"^\s+{m.group(2)}:", config, re.M), f"{m.group(2)} is not declared in estate-config.yaml"


@given("the repository at HEAD")
def _head(state: dict) -> None:
    state["tracked"] = _git("ls-files").split()


@then("the directory platform/access does not exist")
def _no_dir(state: dict) -> None:
    assert not (IDP / "platform" / "access").exists()
    assert not any(p.startswith("platform/access/") for p in state["tracked"])


@then(".github/workflows/access-apply.yml and bin/idp-access-apply do not exist")
def _no_files(state: dict) -> None:
    for p in (".github/workflows/access-apply.yml", "bin/idp-access-apply"):
        assert p not in state["tracked"] and not (IDP / p).exists(), p


@then("no tracked file names platform/access, access-apply or ESTATE_LOGIN_GITHUB_USER, except this feature and the decision record that retires them")
def _nobody_names_it(state: dict) -> None:
    hits = subprocess.run(["git", "grep", "-l", *sum((["-e", n] for n in RETIRED), []), "--", "."],
                          cwd=IDP, capture_output=True, text=True).stdout.split()
    offenders = [h for h in hits if not h.startswith(ALLOWED)]
    assert not offenders, offenders
