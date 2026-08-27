"""Incident crew#66 CP5e: the three operator scripts that are the cloud provider's own adapter by
nature — signing in to the cloud session and reading the tenancy-root IAM policy — declare
themselves as the adapter, and bin/cloud-agnostic-gate grades that declaration instead of counting
their lines as accidental coupling.

Rule: bin/idp-oci-login, bin/idp-oci-whoami and bin/idp-iam-policy-drift carry
`# provider-adapter: oci` on line 2; the gate honours the marker only under
bin/idp-oci-* / bin/idp-iam-* and prints `declared outside <prefixes>` otherwise. Rung 5."""
import importlib.machinery
import importlib.util
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "cloud-agnostic-gate"
ADAPTER_FILES = ("bin/idp-oci-login", "bin/idp-oci-whoami", "bin/idp-iam-policy-drift")
MARKER = "# provider-adapter: oci — this file IS the provider door (session sign-in / tenancy-root IAM); it is not a caller of one. Every other bin/idp-* goes through bin/idp-cloud (crew#66)."


def _load_gate():
    loader = importlib.machinery.SourceFileLoader("cloud_agnostic_gate", str(GATE))
    spec = importlib.util.spec_from_loader("cloud_agnostic_gate", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _gate(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(GATE)], env={**os.environ, "CLOUD_AGNOSTIC_ROOT": str(root)},
        capture_output=True, text=True,
    )


def _write(path: Path, shebang: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{shebang}\n{MARKER}\n{body}")


def _tree_with_marker_under(tmp_path: Path, name: str = "idp-oci-fake") -> Path:
    _write(tmp_path / "bin" / f"{name}.sh", "#!/usr/bin/env bash",
           "oci iam policy list --compartment-id x --all\n")
    return tmp_path


def test_the_three_operator_scripts_carry_the_marker_on_line_two() -> None:
    for rel in ADAPTER_FILES:
        lines = (ROOT / rel).read_text().splitlines()
        assert lines[0].startswith("#!"), (rel, lines[:3])
        assert lines[1] == MARKER, (rel, lines[:3])


def test_declared_adapter_returns_oci_when_marker_is_on_line_two(tmp_path: Path) -> None:
    mod = _load_gate()
    marked = tmp_path / "marked.sh"
    _write(marked, "#!/usr/bin/env bash")
    assert mod.declared_adapter(marked) == "oci"


def test_declared_adapter_returns_none_when_marker_is_absent(tmp_path: Path) -> None:
    mod = _load_gate()
    bare = tmp_path / "bare.sh"
    bare.write_text("#!/usr/bin/env bash\n# plain comment\n# another comment\n")
    assert mod.declared_adapter(bare) is None


def test_a_marker_under_an_allowed_prefix_is_zero_findings_and_one_adapter(tmp_path: Path) -> None:
    r = _gate(_tree_with_marker_under(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "bin/idp-oci-fake.sh:1" not in r.stdout, r.stdout
    assert r.stdout.count("adapter oci  bin/idp-oci-fake.sh") == 1, r.stdout
    assert any(
        line == "cloud-agnostic-gate: 0 provider-specific line(s) outside the provisioner"
        for line in r.stdout.splitlines()
    ), r.stdout
    assert any(
        line == "cloud-agnostic-gate: 1 declared adapter file(s)"
        for line in r.stdout.splitlines()
    ), r.stdout


def test_a_marker_outside_the_allowed_prefixes_is_a_finding(tmp_path: Path) -> None:
    r = _gate(_tree_with_marker_under(tmp_path, name="idp-something"))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "declared outside" in r.stdout, r.stdout
    assert any("bin/idp-something.sh" in line for line in r.stdout.splitlines()), r.stdout
    assert any(
        line == "cloud-agnostic-gate: 0 declared adapter file(s)"
        for line in r.stdout.splitlines()
    ), r.stdout


def test_the_summary_line_still_ends_with_the_original_outside_the_provisioner(tmp_path: Path) -> None:
    r = _gate(_tree_with_marker_under(tmp_path))
    summary = [line for line in r.stdout.splitlines() if "provider-specific line(s) outside the provisioner" in line]
    assert len(summary) == 1, r.stdout
    assert summary[0].startswith("cloud-agnostic-gate: "), summary[0]


def test_an_extensionless_bin_script_is_scanned_so_the_real_adapters_count(tmp_path: Path) -> None:
    """The three real adapters carry no extension; the first cut of this gate never opened them and
    reported 0 declared adapters in production (MiniMax run, crew#66 CP5e)."""
    _write(tmp_path / "bin" / "idp-oci-door", "#!/usr/bin/env bash", "oci iam policy list --all\n")
    (tmp_path / "bin" / "idp-plain").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "bin" / "idp-plain").write_text("#!/usr/bin/env bash\ncurl https://objectstorage.example/x\n")
    r = _gate(tmp_path)
    assert "adapter oci  bin/idp-oci-door" in r.stdout, r.stdout
    assert "bin/idp-plain:2:" in r.stdout, r.stdout
    assert "cloud-agnostic-gate: 1 declared adapter file(s)" in r.stdout, r.stdout


def test_the_live_tree_reports_the_three_declared_adapters() -> None:
    r = subprocess.run([str(GATE)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    assert "cloud-agnostic-gate: 3 declared adapter file(s)" in r.stdout, r.stdout
