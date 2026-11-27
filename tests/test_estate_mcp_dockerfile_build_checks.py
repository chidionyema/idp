"""Every build-time check in estate-mcp.Dockerfile runs before merge, against the files it copies.

The image's `RUN ... python -c "..."` checks assert facts about the plugin. They used to run only
inside build-multiarch on main, so a plugin change that broke one shipped green and turned main
red: #6590 renamed ci-status (estate-mcp did not ship for ~40 h), and idp#8061 replaced the
laptop door with the cloud door while the check still asserted `_invoke_remote` (every build red
from d32c484a2, run 46012162636). Pinning one assertion by regex fixed one instance; this runs
every check, so the class fails here first (idp#8650).

The Dockerfile's COPY layout is staged under a temporary /app. A check that imports a package
the image pip-installs but this environment lacks is SKIPPED by name, never passed.
"""

import os
import pathlib
import re
import site
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "estate-mcp.Dockerfile"


def _logical_lines(text: str) -> list[str]:
    return text.replace("\\\n", "").splitlines()


def build_checks(text: str) -> list[str]:
    checks = []
    for line in _logical_lines(text):
        m = re.match(r'RUN cd /tmp && python -c "(.*)"\s*$', line)
        if m:
            checks.append(m.group(1).replace('\\"', '"'))
    return checks


def copies(text: str) -> list[tuple[str, str]]:
    out = []
    for line in _logical_lines(text):
        m = re.match(r"COPY (\S+) (/app/\S*)$", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


CHECKS = build_checks(DOCKERFILE.read_text())


def test_the_dockerfile_still_carries_build_checks():
    # A parser that finds nothing would make every case below vacuous.
    assert len(CHECKS) >= 3, CHECKS


def test_the_parser_reads_a_known_bad_check():
    bad = "RUN cd /tmp && python -c \"import os; \\\nassert False, 'x'\"\n"
    assert build_checks(bad) == ["import os; assert False, 'x'"]


@pytest.fixture
def app(tmp_path):
    app = tmp_path / "app"
    for src, dest in copies(DOCKERFILE.read_text()):
        target = tmp_path / dest.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(ROOT / src)
    return app


def _run(code: str, app: pathlib.Path) -> subprocess.CompletedProcess:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("ESTATE_CLOUD_", "ESTATE_LAPTOP_"))
    }
    env["HOME"] = str(app.parent)  # no ~/.estate: the pod has no local executor
    # A new HOME hides the user site-packages; keep this interpreter's packages visible.
    env["PYTHONPATH"] = os.pathsep.join([*sys.path[1:], site.getusersitepackages()])
    env["ESTATE_INTENTS_DIR"] = str(app / "intents")
    code = code.replace("/app/", str(app) + "/")
    return subprocess.run(  # noqa: S603 -- the Dockerfile's own check, staged paths
        [sys.executable, "-c", code],
        cwd=app.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.parametrize("index", range(len(CHECKS)))
def test_build_check_passes_against_the_repo(index, app):
    p = _run(CHECKS[index], app)
    missing = re.search(r"ModuleNotFoundError: No module named '([^']+)'", p.stderr)
    if (
        p.returncode
        and missing
        and missing.group(1).split(".")[0] in ("mcp", "datasette")
    ):
        pytest.skip(
            f"check {index} needs {missing.group(1)}, installed only in the image"
        )
    assert p.returncode == 0, p.stderr[-1500:]


def test_a_check_against_a_removed_helper_fails(app):
    # Falsifier: the d32c484a2 check, run against today's plugin, must fail here.
    stale = (
        "import importlib.util,sys; "
        "spec=importlib.util.spec_from_file_location('estate_mcp','/app/plugins/estate_mcp.py'); "
        "m=importlib.util.module_from_spec(spec); sys.modules['estate_mcp']=m; "
        "spec.loader.exec_module(m); "
        "assert hasattr(m,'_invoke_remote'), 'no laptop forwarding helper in the plugin'"
    )
    p = _run(stale, app)
    assert p.returncode != 0
    assert "no laptop forwarding helper" in p.stderr


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        r = subprocess.run(  # noqa: S603 -- this file under pytest
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", __file__],
            capture_output=True,
            text=True,
            check=False,
        )
        m = re.search(r"(\d+) failed", r.stdout)
        failing = int(m.group(1)) if m else (0 if r.returncode == 0 else 1)
        print(f"optimus.estate_mcp.build_checks_failing={failing}")
        raise SystemExit(0)
    raise SystemExit("run under pytest, or with --optimus")
