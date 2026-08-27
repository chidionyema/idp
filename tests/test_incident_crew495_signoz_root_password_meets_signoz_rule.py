"""crew#495 CP8: signoz-0 crashed 37 times (CrashLoopBackOff, Helm rollback stalled) and every
receipt carried only cobra frames until idp#426 kept the head of the fatal line:
`failed to validate config "user"`. SigNoz's IsPasswordValid (pkg/types/factor_password.go)
wants at least one upper, one lower, one digit and one symbol; platform/oci/signoz.tf generated
the root password with `special = false`, so no symbol could ever appear and the process
refused its own config. This test holds the generator to the rule SigNoz enforces.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "platform" / "oci" / "signoz.tf"
BLOCK = re.compile(r'resource "random_password" "signoz_root" \{(?P<body>.*?)\n\}', re.S)
# What a shell, a URL, a YAML scalar or a Kubernetes env value would read: none of these may be
# in the symbol set, or the password that satisfies SigNoz breaks the path that carries it.
UNSAFE = set("$&`'\"\\/:#;,?=@ ")


def _block(text: str) -> dict[str, str]:
    m = BLOCK.search(text)
    assert m, "signoz.tf has no random_password.signoz_root"
    out: dict[str, str] = {}
    for line in m.group("body").splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            k, v = (s.strip() for s in line.split("=", 1))
            out[k] = v.strip('"')
    return out


def _check(text: str) -> None:
    b = _block(text)
    assert b.get("special") == "true", "SigNoz wants a symbol; special = false can never carry one"
    for k in ("min_upper", "min_lower", "min_numeric", "min_special"):
        assert int(b.get(k, "0")) >= 1, f"{k} must pin at least one character of its class"
    assert int(b.get("length", "0")) >= 8, "SigNoz's minimum length"
    assert b.get("override_special"), "override_special must be set, or the provider's default set includes $ and quotes"
    bad = UNSAFE & set(b["override_special"])
    assert not bad, f"override_special carries characters the env/URL path would misread: {sorted(bad)}"


def test_incident_crew495_the_signoz_root_password_meets_the_rule_signoz_enforces() -> None:
    _check(TF.read_text())


@pytest.mark.parametrize(
    "broken",
    [
        'resource "random_password" "signoz_root" {\n  length  = 32\n  special = false\n}',  # the 2026-08-27 shape
        'resource "random_password" "signoz_root" {\n  length  = 32\n  special = true\n  override_special = "!*"\n}',  # no floor
        'resource "random_password" "signoz_root" {\n  length = 32\n  special = true\n  override_special = "$!"\n'
        "  min_upper = 1\n  min_lower = 1\n  min_numeric = 1\n  min_special = 1\n}",  # a shell reads $
    ],
)
def test_incident_crew495_the_rule_refuses_the_shapes_that_crashed_or_would(broken: str) -> None:
    with pytest.raises(AssertionError):
        _check(broken)
