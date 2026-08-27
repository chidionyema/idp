"""crew#503, 2026-08-27: two GitHub App manifest codes were exchanged (POST /app-manifests/{code}/conversions,
one-time, the private key returned exactly once) and the vault write that followed failed both times, first on
tofu state in a worktree, then on an unset OCI profile. The key was gone with the temp file.

Guard (LAW 45): `bin/idp-github-app convert <code>` writes the vault through CI (SEED_GITHUB_APP_* repo secrets
+ vault-seed.yml) so no laptop OCI session is involved; it proves that write path (a repo secret can be set,
the workflow exists) BEFORE it touches the conversion endpoint, and a failed write after the exchange keeps the
key on disk. Every external binary is a stub on PATH here; nothing opens a socket.
"""
import os
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-github-app"
APP = '{"id":1,"slug":"stub","client_id":"c","html_url":"https://github.com/apps/stub","pem":"-----BEGIN RSA PRIVATE KEY-----\\nstub\\n-----END RSA PRIVATE KEY-----"}'


def _stub(d, name, body):
    p = d / name
    p.write_text("#!/usr/bin/env bash\n" + body)
    p.chmod(0o755)


def _run(tmp_path, gh_body):
    bins = tmp_path / "bin"
    bins.mkdir()
    _stub(bins, "gh", gh_body)
    env = {**os.environ, "PATH": f"{bins}:{os.environ['PATH']}", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)}
    return subprocess.run([str(SCRIPT), "convert", "0" * 40], env=env, capture_output=True, text=True, cwd=ROOT)


def test_incident_crew503_a_failed_ci_preflight_stops_before_the_code_is_spent(tmp_path):
    log = tmp_path / "gh.log"
    # gh can name the repo but cannot set a secret
    r = _run(tmp_path, f'echo "$@" >> "{log}"\ncase "$*" in *"repo view"*) echo o/r;; *"secret set"*) exit 1;; esac\n')
    assert r.returncode == 2, r.stdout + r.stderr
    assert "the code was NOT spent" in r.stderr, r.stderr
    assert "conversions" not in log.read_text(), f"the code was spent although CI could not write: {log.read_text()}"


def test_incident_crew503_a_failed_write_after_the_exchange_keeps_the_key(tmp_path):
    # the pre-flight secret sets fine; the real SEED_GITHUB_APP_* writes fail after the code is spent
    r = _run(tmp_path, 'case "$*" in *"repo view"*) echo o/r;; *conversions*) echo \'' + APP + '\';; '
                       '*"secret set SEED_GITHUB_APP_PREFLIGHT"*) exit 0;; *"secret set"*) exit 1;; *) exit 0;; esac\n')
    assert r.returncode != 0
    assert "key is kept at" in r.stderr, r.stderr
    kept = pathlib.Path(re.search(r"key is kept at (\S+) ", r.stderr).group(1))
    assert kept.is_file(), f"the App key was deleted after a failed write ({kept})"
    assert "GITHUB_APP_PEM_B64=" in kept.read_text()
    assert oct(kept.stat().st_mode & 0o777) == "0o600"
    kept.unlink()


def test_incident_crew503_a_good_convert_seeds_the_vault_from_ci_and_keeps_no_key_on_disk(tmp_path):
    log = tmp_path / "gh.log"
    r = _run(tmp_path, f'echo "$@" >> "{log}"\ncase "$*" in *"repo view"*) echo o/r;; *conversions*) echo \'{APP}\';; *) exit 0;; esac\n')
    assert r.returncode == 0, r.stdout + r.stderr
    calls = log.read_text()
    for k in ("SEED_GITHUB_APP_ID", "SEED_GITHUB_APP_SLUG", "SEED_GITHUB_APP_CLIENT_ID", "SEED_GITHUB_APP_PEM_B64"):
        assert f"secret set {k}" in calls, calls
    assert "workflow run vault-seed.yml" in calls and "entry=github-app" in calls, calls
    assert not list(tmp_path.glob("tmp.*")), "a key file was left on disk after a good convert"
