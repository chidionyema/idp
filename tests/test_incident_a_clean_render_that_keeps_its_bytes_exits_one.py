"""Incident, 2026-08-31 (idp#1056, run 33362659743): a clean render exited 1 and CI called it red.

`bin/idp-kyverno-render` copies its rendered bytes out for the type-checker when
`IDP_RENDER_KEEP` is set, from an EXIT trap, under `set -e`. The copy loop ended in
`[ -f "$f" ] && cp -p ...`, so when the LAST glob matched nothing the loop -- and the function,
and the trap -- ended at status 1, and `set -e` turned that into the script's exit status. The
verdict said `pass: 73, fail: 0`; the exit code said 1; the CI rung printed "a HelmRelease or
workload render fails admission policy" with no failing policy underneath it, because there was
no failing policy.

It only fires for a directory that ships plain workloads and no Helm chart, because only then is
no `*.final.yaml` ever written -- which is every dir under platform/prospector, and which is why
this landed on the shop's backup job and not before.

The shipped function is lifted out of the script and run, rather than reimplemented here: a copy
of the loop in this file would pass while the estate's own copy stayed broken.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / "bin/idp-kyverno-render"


def _save_render() -> str:
    """The save_render function, exactly as bin/idp-kyverno-render ships it."""
    lines = RENDER.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("save_render()"))
    end = next(i for i, line in enumerate(lines) if i > start and line == "}")
    return "\n".join(lines[start : end + 1])


def _run(tmp_path: Path, *names: str) -> subprocess.CompletedProcess:
    """Run it the way the script does: from an EXIT trap, under set -e, on a clean exit."""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    for name in names:
        (scratch / name).write_text("kind: ConfigMap\n")
    keep = tmp_path / "keep"
    script = (
        "set -euo pipefail\n"
        f'S="{scratch}"\n'
        f"{_save_render()}\n"
        f'trap \'save_render "{keep}"; rm -rf "$S"\' EXIT\n'
        "exit 0\n"
    )
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


def test_a_render_with_no_helm_chart_still_exits_zero(tmp_path):
    done = _run(tmp_path, "kz-platform_prospector.yaml")
    assert done.returncode == 0, (
        "a clean render exits 1 when the dir ships no chart, and CI reads that as a failed "
        f"admission policy: {done.stderr}"
    )
    assert (tmp_path / "keep" / "kz-platform_prospector.yaml").exists()


def test_a_render_with_a_chart_keeps_both_kinds_of_bytes(tmp_path):
    done = _run(tmp_path, "kz-platform_llm.yaml", "litellm.final.yaml")
    assert done.returncode == 0, done.stderr
    kept = sorted(p.name for p in (tmp_path / "keep").iterdir())
    assert kept == ["kz-platform_llm.yaml", "litellm.final.yaml"]


def test_a_run_that_produced_nothing_is_not_an_error(tmp_path):
    """An early failure saves whatever it has, including nothing; the exit code is the render's."""
    done = _run(tmp_path)
    assert done.returncode == 0, done.stderr
