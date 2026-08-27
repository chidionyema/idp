"""Incident test (rung 4): 2026-08-26, crew#325, oke-check run 33008917584. `bin/idp-vault-put
litellm-upstream` said "created" in the tofu vault while a secret of that name was ACTIVE in the
other vault left by the 02:26Z lost-state apply, and github-app was BLIND. Rule: a compartment where
a vault other than the tofu vault holds ACTIVE secrets is refused, names only are printed, and a
compartment whose only populated vault is the tofu vault passes.
crew#66 CP5c: the vaults and their secret names are read through the one cloud layer, so the fake
here is a fake bin/idp-cloud in a temp IDP tree, never a fake provider CLI."""
import os, shutil, stat, subprocess, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "bin" / "idp-vault-split-guard"
TOFU = "ocid1.vault.oc1..tofu00"
OTHER = "ocid1.vault.oc1..other0"


def _fake(bin_dir: Path, name: str, body: str) -> None:
    f = bin_dir / name
    f.write_text("#!/usr/bin/env bash\n" + textwrap.dedent(body))
    f.chmod(f.stat().st_mode | stat.S_IEXEC)


def _run(tmp: Path, other_secrets: list[str]) -> subprocess.CompletedProcess:
    # the guard resolves "$IDP/bin/idp-cloud" beside itself, so it is copied into tmp/bin next to the fake layer
    b = tmp / "bin"; b.mkdir(exist_ok=True); m = tmp / "mod"; m.mkdir(exist_ok=True)
    shutil.copy(GUARD, b / GUARD.name)
    (m / "terraform.tfvars").write_text('compartment_ocid = "ocid1.compartment.oc1..test"\n')
    _fake(b, "tofu", f'[ "$1 $2" = "output -raw" ] && printf "%s" "{TOFU}"')
    # the fake answers per vault id: the tofu vault holds langfuse-init-* plus litellm-upstream; the
    # other vault holds whatever the case says (values are never listed, only names). `vault list`
    # prints "<display-name> <id>" per ACTIVE vault and `secret list --vault ID` one name per line,
    # sorted, exactly as bin/idp-cloud does.
    other = " ".join(f"'{s}'" for s in sorted(other_secrets))
    other_cmd = f"printf '%s\\n' {other}" if other else ":"   # an empty vault answers nothing, exit 0
    _fake(b, "idp-cloud", f'''
        case "$1 $2" in
          "vault list") printf '%s\\n' 'estate-secrets {TOFU}' 'estate-secrets {OTHER}';;
          "secret list")
            case "$*" in
              *"--vault {TOFU}"*) printf '%s\\n' 'langfuse-init-public-key' 'litellm-upstream';;
              *"--vault {OTHER}"*) {other_cmd};;
              *) echo "unexpected vault: $*" >&2; exit 2;;
            esac;;
          *) echo "unexpected layer call: $*" >&2; exit 2;;
        esac''')
    env = {**os.environ, "PATH": f"{b}:{os.environ['PATH']}"}
    return subprocess.run(["bash", str(b / GUARD.name), str(m)], env=env, capture_output=True, text=True)


def test_incident_crew325_secrets_split_across_two_vaults_is_refused(tmp_path: Path) -> None:
    r = _run(tmp_path, ["github-app", "litellm-upstream"])
    assert r.returncode == 1
    assert "REFUSE  vault-split" in r.stdout and "github-app litellm-upstream" in r.stdout
    assert f"tofu import oci_kms_vault.estate {OTHER}" in r.stdout
    assert "...tofu00" in r.stdout and TOFU not in r.stdout.split("REFUSE")[0]  # tofu row shows a 6-char tail only


def test_one_populated_vault_that_is_the_tofu_vault_passes(tmp_path: Path) -> None:
    r = _run(tmp_path, [])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok      vault-split  tofu vault" in r.stdout and "is empty" in r.stdout
    assert "        secret: langfuse-init-public-key" in r.stdout and "(ACTIVE)" in r.stdout
    assert "REFUSE" not in r.stdout


def test_the_guard_reads_the_vaults_through_the_layer() -> None:
    # crew#66 CP5c: one cloud layer, no provider CLI in the guard
    s = GUARD.read_text()
    assert '"$IDP/bin/idp-cloud" vault list' in s
    assert '"$IDP/bin/idp-cloud" secret list --vault "$id"' in s


def test_rebuild_runs_the_guard_in_check_and_apply() -> None:
    s = (ROOT / "bin" / "idp-oke-rebuild").read_text()
    i = s.index('VS=$("$IDP/bin/idp-vault-split-guard" "$TF"')
    assert i < s.index('case "$MODE" in'), "the row runs before the mode switch, so --check and --apply both print it"


def test_trace_drill_refuses_a_name_active_in_two_vaults() -> None:
    s = (ROOT / "bin" / "idp-trace-drill").read_text()
    # crew#66 CP3: the split is detected in bin/idp-cloud (exit 3) and the drill fails on that code
    assert '"$IDP/bin/idp-cloud" secret get' in s and "3) fail vault" in s
    cloud = (ROOT / "bin" / "idp-cloud").read_text()
    assert "Split: secret" in cloud and "exit 3" in cloud


def test_incident_crew325_optional_app_secret_does_not_sit_in_secret_store() -> None:
    """secret-store is what every workload row waits on (wait: true). A credential that only exists
    after a founder click (the GitHub App) froze llm/identity/alerts from 14:59Z; it lives with its
    consumer, image-automation, and secret-store carries only the store (flux-telegram moved to
    alerts-secret in crew#284 for the same reason)."""
    store = (ROOT / "platform/secret-store/kustomization.yaml").read_text()
    assert "github-app" not in store and "flux-telegram.yaml" not in store and "store.yaml" in store
    assert (ROOT / "platform/image-automation/flux-writer.yaml").exists()
    assert "flux-writer.yaml" in (ROOT / "platform/image-automation/kustomization.yaml").read_text()
