"""Incident 2026-08-26 (crew#289, run 32930359052): tofu-apply failed on an OCI 400 from
UpdateNodePool, and step() printed only the last 8 lines, which were tofu's footer. The cause line
was never on screen (LAW 28). Rule: a failing step prints its Error/Message lines, whatever the
tail holds. Rung 4, incident test."""
import os, re, subprocess, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-oke-rebuild"


def _step_fn() -> str:
    src = SCRIPT.read_text()
    m = re.search(r"^step\(\) \{.*?^\}\n", src, re.S | re.M)
    assert m, "step() not found"
    return m.group(0)


def _run(body: str) -> str:
    script = "FAILED=''\n" + _step_fn() + body
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True).stdout


LONG_FAIL = textwrap.dedent("""
    fake() { printf 'Error: 400-InvalidParameter, node cycling is not supported on basic clusters\\n'
             for i in 1 2 3 4 5 6 7 8 9 10; do printf 'footer line %s\\n' "$i"; done; return 1; }
    step tofu-apply fake || true
""")


def test_error_line_above_the_tail_is_printed():
    out = _run(LONG_FAIL)
    assert "400-InvalidParameter" in out, out
    assert "footer line 10" in out, out


def test_a_passing_step_prints_one_line_only():
    out = _run("fake() { printf 'Error: none\\nok\\n'; return 0; }\nstep tofu-plan fake\n")
    assert out.count("\n") == 1, out
    assert "| " not in out


def test_the_cycling_keys_are_gone_from_the_basic_cluster_pool():
    tf = (ROOT / "platform" / "oci" / "main.tf").read_text()
    for key in ("node_cycling_enabled", "node_cycling_max_surge", "node_cycling_max_unavailable"):
        assert not re.search(rf"^\s*{re.escape(key)}\s*=", tf, re.M), key
    # placement_ads stays: A1.Flex is not offered in AD-3 and the PVs pin AD-1 (review idp#186 #1)
    assert re.search(r"^\s*placement_ads\s*=\s*\[1\]", tf, re.M)
