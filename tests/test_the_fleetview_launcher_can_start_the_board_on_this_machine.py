"""The FleetView launcher must be able to start FleetView, and say why when it cannot.

These three defects were measured on this laptop on 2026-09-22, with the board unreachable and
`bin/serve-fleetview` -- the file whose whole job is a reliable local start -- unable to start it:

  1. `exec python3` took whatever `python3` meant. Here that is macOS's 3.9.6, which imports
     fastapi and then cannot mount a route, so the documented start died in pydantic before a
     single route existed.
  2. The launcher refused over an unset ESTATE_ZONE while standing in the checkout that declares
     it, in the very file its own error message named.
  3. `--self-test` reported "serve.py imports" having executed nothing: it called
     `spec_from_file_location`, which builds a spec and never runs the module. It passed on a
     machine where the service could not start -- a gate that cannot fail.

None of it had a test, which is why each one had to be found by hand. Each test below fails
against the code as it was.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "bin" / "serve-fleetview"
SRC = ROOT / "backstage" / "plugins" / "fleetview-backend" / "src"


def _check(env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run the launcher's --check path: it resolves everything and starts no listener."""
    env = dict(os.environ)
    env.pop("ESTATE_ZONE", None)
    env.update(env_extra or {})
    return subprocess.run(
        [str(LAUNCHER), "--check"],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
        cwd=str(ROOT),
    )


class TestTheInterpreterIsResolvedNotAssumed:
    def test_it_picks_an_interpreter_that_can_actually_mount_a_route(self):
        """--check must name an interpreter, and that interpreter must survive a real route.

        Asserting on the named interpreter rather than on the exit code: a launcher that picks
        a Python which cannot mount a route still exits 0 here and dies at startup, which is
        precisely the failure being fixed.
        """
        proc = _check()
        assert proc.returncode == 0, proc.stderr
        line = [
            ln for ln in proc.stdout.splitlines() if ln.startswith("fleetview: python")
        ]
        assert line, f"--check named no interpreter:\n{proc.stdout}"
        chosen = line[0].split()[2]
        probe = subprocess.run(
            [
                chosen,
                "-c",
                "import fastapi\n"
                "app = fastapi.FastAPI()\n"
                "@app.get('/probe')\n"
                "def probe(q: str | None = None): return {}\n",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert probe.returncode == 0, (
            f"the launcher chose {chosen}, which cannot mount a FastAPI route:\n{probe.stderr}"
        )

    def test_naming_an_interpreter_that_cannot_serve_is_refused_with_the_reason(self):
        """An override is not an exemption.

        FV_PYTHON skips the search, so it must not skip the question the search asks. The system
        Python here imports fastapi and cannot mount a route -- the exact trap -- so it stands in
        for any interpreter that looks fine and is not.
        """
        system_python = "/usr/bin/python3"
        if not Path(system_python).exists():
            pytest.skip(
                "no /usr/bin/python3 on this machine to stand in for a weak interpreter"
            )
        weak = subprocess.run(
            [
                system_python,
                "-c",
                "import fastapi\napp = fastapi.FastAPI()\n@app.get('/p')\ndef p(q: str | None = None): return {}\n",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if weak.returncode == 0:
            pytest.skip(
                f"{system_python} can mount a route here; nothing weak to refuse"
            )

        proc = _check({"FV_PYTHON": system_python})
        assert proc.returncode != 0, (
            f"the launcher accepted {system_python}, which cannot mount a route:\n{proc.stdout}"
        )
        assert "cannot mount a FastAPI route" in proc.stderr, proc.stderr


class TestTheZoneIsReadFromWhereItIsDeclared:
    def test_an_unexported_zone_does_not_stop_the_launcher(self):
        """The zone is declared once in clusters/<cluster>/estate-config.yaml. A launcher
        standing in that checkout must read it rather than refuse and ask a person to export it."""
        declared = [
            line.split(":", 1)[1].strip().strip("\"'")
            for cfg in sorted(ROOT.glob("clusters/*/estate-config.yaml"))
            for line in cfg.read_text().splitlines()
            if line.strip().startswith("ESTATE_ZONE:")
        ]
        if not declared:
            pytest.skip("no cluster in this checkout declares ESTATE_ZONE")

        proc = _check()
        assert proc.returncode == 0, (
            "the launcher refused with ESTATE_ZONE unset, though the checkout declares it:\n"
            + proc.stderr
        )
        assert "ESTATE_ZONE is not set" not in proc.stderr

    def test_reporting_on_an_optional_feature_never_stops_the_service(self):
        """The zone check used to live inside the `LITELLM_API_KEY is set` arm with an exit 1
        behind it, so a line printing which router voice would use could kill the board. Voice is
        optional; the board is not. With the key set and the zone unset, --check still succeeds."""
        proc = _check(
            {"LITELLM_API_KEY": "not-a-real-key-this-test-only-sets-the-branch"}
        )
        assert proc.returncode == 0, (
            "an optional feature's reporting line stopped the launcher:\n" + proc.stderr
        )


class TestTheSelfTestExecutesWhatItClaims:
    def test_the_self_test_passes_only_where_the_modules_really_load(self):
        """--self-test must run the modules, not merely describe them.

        The old body built three specs and ran none, so it reported success on a machine where
        the service could not start. Proving it executes them: it must agree with a real load of
        the same three modules on the interpreter it chose.
        """
        proc = subprocess.run(
            [str(LAUNCHER), "--self-test"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(ROOT),
        )
        line = [
            ln for ln in proc.stdout.splitlines() if ln.startswith("fleetview: python")
        ]
        assert line, proc.stdout
        chosen = line[0].split()[2]

        real = subprocess.run(
            [
                chosen,
                "-c",
                "import importlib.util, pathlib, sys\n"
                f"root = pathlib.Path({str(ROOT)!r})\n"
                "sys.path.insert(0, str(root))\n"
                f"src = pathlib.Path({str(SRC)!r})\n"
                "for name in ('config_guard', 'routes', 'serve'):\n"
                "    spec = importlib.util.spec_from_file_location('t_' + name, src / (name + '.py'))\n"
                "    m = importlib.util.module_from_spec(spec)\n"
                "    sys.modules[spec.name] = m\n"
                "    spec.loader.exec_module(m)\n",
            ],
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
        assert (proc.returncode == 0) == (real.returncode == 0), (
            "--self-test disagrees with a real load of the same three modules: "
            f"self-test rc={proc.returncode}, real load rc={real.returncode}\n{real.stderr}"
        )


class TestAnUnsweptGraphIsNamedNotCrashed:
    """`catalog/estate.db` exists on this laptop and holds no `nodes`/`edges`: those come from
    bin/estate-twin-runtime, which needs kubectl. graph.py checked that the FILE existed, so
    sqlite raised `no such table: nodes` through the route and the board showed a 500 -- the
    real gap disguised as a broken service, which GraphUnavailable exists to prevent."""

    def _graph_module(self, monkeypatch, db_path: Path):
        import importlib.util

        monkeypatch.setenv("ESTATE_DB", str(db_path))
        spec = importlib.util.spec_from_file_location(
            "fv_graph_under_test", SRC / "graph.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    def test_a_database_without_the_graph_tables_is_unavailable_not_an_error(
        self, tmp_path, monkeypatch
    ):
        db = tmp_path / "estate.db"
        con = sqlite3.connect(db)
        con.execute(
            "CREATE TABLE assets (id TEXT)"
        )  # what a real un-swept estate.db holds
        con.commit()
        con.close()

        graph = self._graph_module(monkeypatch, db)
        with pytest.raises(graph.GraphUnavailable) as caught:
            graph.graph_snapshot()
        assert "estate-twin-runtime" in str(caught.value), (
            "the refusal must name what has not run, so the board can say so"
        )

    def test_a_swept_graph_still_answers(self, tmp_path, monkeypatch):
        """The guard must not turn a real graph into a refusal."""
        db = tmp_path / "estate.db"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE nodes (id TEXT, domain TEXT, type TEXT, status TEXT)")
        con.execute(
            "CREATE TABLE edges (source_id TEXT, target_id TEXT, relation TEXT)"
        )
        con.execute(
            "INSERT INTO nodes VALUES ('n1', 'compute', 'Deployment', 'serving')"
        )
        con.execute("INSERT INTO edges VALUES ('n1', 'n2', 'routes to')")
        con.commit()
        con.close()

        graph = self._graph_module(monkeypatch, db)
        snapshot = graph.graph_snapshot()
        assert snapshot["nodes"] == [
            {"id": "n1", "domain": "compute", "type": "Deployment", "status": "serving"}
        ]
        assert snapshot["edges"] == [
            {"source_id": "n1", "target_id": "n2", "relation": "routes to"}
        ]


def test_the_launcher_is_executable_and_lints():
    assert os.access(LAUNCHER, os.X_OK), f"{LAUNCHER} is not executable"
    if shutil.which("shellcheck") is None:
        pytest.skip("shellcheck not installed")
    proc = subprocess.run(
        ["shellcheck", str(LAUNCHER)], capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, proc.stdout
