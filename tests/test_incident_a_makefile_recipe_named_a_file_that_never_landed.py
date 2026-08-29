"""`make catalogue-deploy` built the catalogue from a compose file that is on no branch of main.

Measured 2026-08-29: the recipe's first line was
`docker compose -f backstage/compose.yml build catalogue`, and `backstage/compose.yml` was added
on 2026-08-24 by 0c12a211 on branch `backstage-container` -- a bridge whose own header says
"Phase 2 points ArgoCD at those manifests and this file is deleted". Main IS Phase 2
(`platform/backstage/base` plus overlays), so the file correctly never merged, and the recipe,
two onboarding pages and a kustomization comment kept naming it. The documented way to build the
founder's catalogue therefore failed on its first line, and nothing said so.

A path in a recipe is the same class of claim as a path in a sentence (see
test_incident_docs_name_paths_that_do_not_exist.py): unexecutable prose that decays silently.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"

#: `-f <file>` in a recipe is a file the command opens. Narrow on purpose: `kubectl apply -f -`
#: reads stdin and has no extension, and grading bare words would be grading English.
FLAG = re.compile(r"-f\s+([A-Za-z0-9_./-]+\.(?:ya?ml|json|toml))")


def missing() -> list[str]:
    return sorted({p for p in FLAG.findall(MAKEFILE.read_text()) if not (ROOT / p).exists()})


def test_every_file_a_recipe_opens_exists():
    assert not missing(), (
        "these Makefile recipes name files this repo does not have, so the target fails on that "
        "line: " + ", ".join(missing()))


def test_the_check_reads_the_recipes_it_claims_to():
    """A guard that matched nothing would pass forever. It sees the two SPIRE values files."""
    found = set(FLAG.findall(MAKEFILE.read_text()))
    assert "platform/spire/values.yaml" in found and len(found) >= 2, found
