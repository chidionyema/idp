"""Shape tests for the estate assurance plane scripts.

The live falsifiers (dispatch battery, sync benches, grade bench) run on the host; these tests keep
the repository copy honest in CI: every script is present, executable and compiles.
"""

from pathlib import Path

IDP = Path(__file__).resolve().parents[2]
FILES = [
    "bin/estate-dispatch-action",
    "bin/estate-bws-sync",
    "bin/estate-bws-check",
    "bin/estate-bws-adopt",
    "bin/estate-topology",
    "bin/estate-debug-pack",
    "bin/estate-service-grade",
    "bin/estate-metrics-push",
    "bin/estate-assurance-selftest",
    "bin/estate-certify",
    "bin/estate-fleet",
]
SHELL = [
    "bin/estate-itest",
]


def test_scripts_present_and_executable():
    for rel in FILES:
        p = IDP / rel
        assert p.is_file(), rel
        assert p.stat().st_mode & 0o111, rel


def test_scripts_compile():
    for rel in FILES:
        source = (IDP / rel).read_text()
        compile(source, rel, "exec")


def test_shell_scripts_parse():
    import subprocess

    for rel in SHELL:
        result = subprocess.run(
            ["bash", "-n", str(IDP / rel)], capture_output=True, text=True
        )
        assert result.returncode == 0, rel + ": " + result.stderr
