"""idp#685 and idp#697, 2026-08-29: two Kustomizations held for three hours and no line said why.

Both rows read `Health check failed after 20m: ExternalSecret/<ns>/ghcr-pull status: InProgress`
and both issues collected five identical bot posts with no cause. A Kustomization's Ready message
can only ever repeat the name of the object it is waiting on; the reason lives on that object's
own Ready condition, and on the ClusterSecretStore it reads through. `pb_diagnose` printed
kustomizations, helmreleases, pods and k8sgpt findings and not one ExternalSecret, so the estate's
own read-only diagnose was blind to the class of break that had it down.

The store is read before its dependents on purpose: one unready ClusterSecretStore is every
ExternalSecret behind it, and a reader who starts at the dependents starts at the wrong end
(LAW 29, attribute before you repair).
"""
import os
import stat
import subprocess
from pathlib import Path

IDP = Path(__file__).resolve().parents[1]
PLAYBOOK = IDP / "bin" / "idp-oke-break-glass"


def _run_diagnose(tmp_path: Path) -> list[str]:
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("kubectl", "flux", "helm"):
        f = bin_dir / tool
        f.write_text(f'#!/bin/sh\nprintf \'%s %s\\n\' "{tool}" "$*" >> "{log}"\ncat >/dev/null 2>&1 || true\necho ok\n')
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "diagnose"], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    return log.read_text().splitlines() if log.exists() else []


def _index_of(calls: list[str], needle: str) -> int:
    for i, c in enumerate(calls):
        if needle in c:
            return i
    return -1


def test_the_incident_diagnose_reads_externalsecret_conditions(tmp_path):
    """The object idp#685 and idp#697 both timed out on is read, with its Ready reason."""
    calls = _run_diagnose(tmp_path)
    hits = [c for c in calls if "externalsecrets.external-secrets.io" in c]
    assert hits, "diagnose never read an ExternalSecret; the break in idp#685/idp#697 stays invisible"
    assert any("-A" in c for c in hits), "the read must cover every namespace, not one"
    assert any(".reason" in c and ".message" in c for c in hits), (
        "an ExternalSecret row without its Ready reason and message repeats what the "
        f"Kustomization already said and explains nothing: {hits}"
    )


def test_the_incident_diagnose_reads_the_store_the_secrets_come_through(tmp_path):
    """One unready store is every ExternalSecret behind it; naming it is the attribution."""
    calls = _run_diagnose(tmp_path)
    hits = [c for c in calls if "clustersecretstores.external-secrets.io" in c]
    assert hits, "diagnose never read a ClusterSecretStore; a dead vault door reads as N broken secrets"
    assert any(".reason" in c and ".message" in c for c in hits), hits


def test_the_store_is_read_before_the_secrets_that_depend_on_it(tmp_path):
    """LAW 29: attribute before you repair. Dependents first sends the reader to the wrong end."""
    calls = _run_diagnose(tmp_path)
    store = _index_of(calls, "clustersecretstores.external-secrets.io")
    secrets = _index_of(calls, "externalsecrets.external-secrets.io")
    assert store != -1 and secrets != -1, calls
    assert store < secrets, (
        "the ClusterSecretStore must be printed before the ExternalSecrets it serves; "
        f"store at {store}, secrets at {secrets}"
    )


def test_the_guard_would_catch_the_rows_being_dropped_again(tmp_path):
    """A canary: the assertions above must fail on a playbook with the rows removed.

    Without this, deleting `pb_diagnose` outright, or renaming the CRD group, would leave every
    test above passing on an empty call log -- the shape of silent green this estate keeps
    finding (a guard that stops matching stops grading, and says nothing).
    """
    stripped = tmp_path / "playbook"
    text = PLAYBOOK.read_text()
    kept = [ln for ln in text.splitlines(keepends=True) if "external-secrets.io" not in ln]
    assert len(kept) < len(text.splitlines()), "no external-secrets row to strip; the guard has nothing to prove"
    stripped.write_text("".join(kept))
    stripped.chmod(stripped.stat().st_mode | stat.S_IEXEC)

    log = tmp_path / "calls2.log"
    bin_dir = tmp_path / "bin2"
    bin_dir.mkdir()
    for tool in ("kubectl", "flux", "helm"):
        f = bin_dir / tool
        f.write_text(f'#!/bin/sh\nprintf \'%s %s\\n\' "{tool}" "$*" >> "{log}"\ncat >/dev/null 2>&1 || true\necho ok\n')
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    subprocess.run([str(stripped), "diagnose"], capture_output=True, text=True, env=env)
    calls = log.read_text().splitlines() if log.exists() else []
    assert not [c for c in calls if "external-secrets.io" in c], (
        "the stripped playbook still read external-secrets; the guard is not measuring the rows it thinks it is"
    )
