"""Incident crew#267 / crew#301 (2026-08-26): bin/idp-github-app installation could only run from a
founder laptop because it read OCI_COMPARTMENT_OCID through sops from estate-secrets, which a
runner does not have, so crew#267 sat not-live behind an expired OCI session. Rule: every bin
script that reads OCI_COMPARTMENT_OCID via sops honours the OCI_COMPARTMENT_OCID environment
variable first, the same variable .github/workflows/oke-check.yml exports. Rung 4 (incident).
Both ways: the live scripts pass; a script text with the bare sops read is caught."""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOPS = re.compile(r"""sops -d --extract '\["OCI_COMPARTMENT_OCID"\]'""")
ENV_FIRST = re.compile(r"\$\{OCI_COMPARTMENT_OCID:-")


def _offenders(texts: dict) -> list:
    """A script offends when it reads the secret through sops and no `${OCI_COMPARTMENT_OCID:-`
    default precedes that read (inline `${X:-$(sops ...)}` or an env-first `C="${X:-}"` block)."""
    out = []
    for p, t in texts.items():
        m = SOPS.search(t)
        if m and not ENV_FIRST.search(t[: m.start()]):
            out.append(p)
    return sorted(out)


def _bin_texts() -> dict:
    out = {}
    for p in glob.glob(os.path.join(ROOT, "bin", "*")):
        if os.path.isfile(p):
            with open(p, errors="replace") as f:
                out[os.path.relpath(p, ROOT)] = f.read()
    return out


def test_every_bin_sops_compartment_read_honours_env():
    assert _offenders(_bin_texts()) == []


def test_bare_sops_read_is_caught():
    bad = {"bin/x": """C=$(sops -d --extract '["OCI_COMPARTMENT_OCID"]' f.yaml)"""}
    good = {"bin/y": """C=${OCI_COMPARTMENT_OCID:-$(sops -d --extract '["OCI_COMPARTMENT_OCID"]' f.yaml)}"""}
    assert _offenders(bad) == ["bin/x"] and _offenders(good) == []
