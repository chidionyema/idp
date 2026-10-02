"""An always-on Flux Kustomization row must never simply vanish.

Spec: this file, since there is no separate spec doc for the guard yet.
Rule: bin/idp-always-on-guard, wired into bin/idp-ci next to the existing
clusters/oke/ kubeconform and kustomize-build checks.

THE INCIDENT. c96359f4 (2026-09-26, "~80 Flux rows -> 7") deleted
clusters/oke/backstage.yaml and clusters/oke/platform.yaml outright. Both
Kustomizations it defined -- backstage-namespace and backstage, both annotated
idp.estate.io/runtime: always-on -- stopped receiving any git changes with no
error anywhere: kubeconform and `kustomize build` only validate whatever
clusters/oke/ files still exist, so a file that is gone entirely is invisible
to both. Backstage was noticed and manually restored the next day; estate-mcp
and hindsight-api were not, and sat at 0/0 Ready for two days with no
automatic path back.

bin/idp-always-on-guard diffs the set of always-on Kustomization names
committed on a base ref against the working tree and refuses when a name
present on the base ref is missing now. These tests build a throwaway git
repo with one always-on Kustomization, commit it, then delete it exactly as
c96359f4 did, and prove the guard refuses that tree and passes the
unmodified one.

THE SECOND INCIDENT. clusters/oke/quad-ledger.yaml was committed on
2026-09-27 and never added to clusters/oke/kustomization.yaml resources:.
Flux builds ./clusters/oke from that list, so the file was never applied: the
quad namespace did not exist and quad.ledger-verify exited 1 with
'namespaces "quad" not found' for a month. kubeconform and `kustomize build`
cannot see it (an unlisted file is not in what the manifest builds), and the
drop check above cannot see it (the file is still in the tree, so nothing is
missing). The file's own header claimed a test pinned the list to the
directory; no such test existed. The tests below are that test: they prove
the guard refuses an orphaned *.yaml and passes a fully wired one.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "bin" / "idp-always-on-guard"

KUSTOMIZATION = """\
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  annotations:
    idp.estate.io/runtime: always-on
  name: backstage
  namespace: flux-system
spec:
  interval: 30s
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./platform/backstage/overlays/oke
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: catalogue
      namespace: backstage
"""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
        },
    )


def _run_guard(repo: Path, base_ref: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(GUARD)],
        cwd=repo,
        capture_output=True,
        text=True,
        env={"IDP_CI_BASE": base_ref, "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )


def _repo_with_one_always_on_row(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    (repo / "clusters" / "oke").mkdir(parents=True)
    (repo / "clusters" / "oke" / "backstage.yaml").write_text(KUSTOMIZATION)
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    r = _git(repo, "commit", "-q", "-m", "add backstage always-on row")
    assert r.returncode == 0, r.stderr
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return repo, head


def test_the_shipped_defect_is_refused(tmp_path: Path) -> None:
    """Deleting the row exactly as c96359f4 did is refused, and named."""
    repo, head = _repo_with_one_always_on_row(tmp_path)
    (repo / "clusters" / "oke" / "backstage.yaml").unlink()

    r = _run_guard(repo, head)
    assert r.returncode == 1, (
        f"the guard must refuse a dropped always-on row; it answered {r.returncode}:\n{r.stdout}"
    )
    assert "backstage" in r.stdout


def test_the_unmodified_tree_passes(tmp_path: Path) -> None:
    """The row is still there: the guard passes clean."""
    repo, head = _repo_with_one_always_on_row(tmp_path)

    r = _run_guard(repo, head)
    assert r.returncode == 0, (
        f"the guard must pass an unchanged tree:\n{r.stdout}\n{r.stderr}"
    )
    assert "none dropped" in r.stdout


def test_demoting_the_row_first_is_not_a_drop(tmp_path: Path) -> None:
    """Changing always-on to on-demand in its own commit is the documented escape hatch."""
    repo, head = _repo_with_one_always_on_row(tmp_path)
    demoted = KUSTOMIZATION.replace("always-on", "on-demand")
    (repo / "clusters" / "oke" / "backstage.yaml").write_text(demoted)

    r = _run_guard(repo, head)
    assert r.returncode == 0, (
        f"a row deliberately demoted off always-on must not be treated as dropped:\n{r.stdout}"
    )


KUSTOMIZATION_YAML = """\
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - backstage.yaml
"""

WIRED_ROW = """\
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  annotations:
    idp.estate.io/runtime: always-on
  name: quad-ledger
  namespace: flux-system
spec:
  interval: 30s
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./platform/quad/ledger
"""


def _repo_with_a_wired_row(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "clusters" / "oke").mkdir(parents=True)
    (repo / "clusters" / "oke" / "backstage.yaml").write_text(KUSTOMIZATION)
    (repo / "clusters" / "oke" / "quad-ledger.yaml").write_text(WIRED_ROW)
    (repo / "clusters" / "oke" / "kustomization.yaml").write_text(
        KUSTOMIZATION_YAML + "  - quad-ledger.yaml\n"
    )
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    r = _git(repo, "commit", "-q", "-m", "add an always-on row, wired")
    assert r.returncode == 0, r.stderr
    return repo


def test_a_file_present_but_not_listed_in_resources_is_refused(tmp_path: Path) -> None:
    """The quad-ledger defect: present in the tree, absent from resources:, never applied."""
    repo = _repo_with_a_wired_row(tmp_path)
    # Exactly 390ec4875: the file is committed, the resources: row never was.
    (repo / "clusters" / "oke" / "kustomization.yaml").write_text(KUSTOMIZATION_YAML)

    r = _run_guard(repo, "HEAD")
    assert r.returncode == 1, (
        f"an orphaned *.yaml must be refused; the guard answered {r.returncode}:\n{r.stdout}"
    )
    assert "quad-ledger.yaml" in r.stdout, r.stdout


def test_a_fully_wired_tree_passes(tmp_path: Path) -> None:
    """Every *.yaml listed in resources:, as the fix wired it."""
    repo = _repo_with_a_wired_row(tmp_path)

    r = _run_guard(repo, "HEAD")
    assert r.returncode == 0, f"a fully wired tree must pass:\n{r.stdout}\n{r.stderr}"
    assert "none orphaned" in r.stdout, r.stdout


def test_an_unreachable_base_ref_skips_rather_than_blinds_a_false_pass(
    tmp_path: Path,
) -> None:
    """No base ref to diff against: the guard says so and exits clean, not silently red."""
    repo = tmp_path / "repo"
    (repo / "clusters" / "oke").mkdir(parents=True)
    (repo / "clusters" / "oke" / "backstage.yaml").write_text(KUSTOMIZATION)
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add backstage always-on row")

    r = subprocess.run(
        ["python3", str(GUARD)],
        cwd=repo,
        capture_output=True,
        text=True,
        env={
            "IDP_CI_BASE": "origin/does-not-exist",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
        },
    )
    assert r.returncode == 0
    assert "unreachable" in r.stdout
