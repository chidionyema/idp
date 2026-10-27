"""The compile reuses a chart index it already has, and downloads it once per repository.

2026-10-27: `bin/idp-compile-helm` looked hung on a laptop. It was not hung -- it was
downloading the same chart indexes over and over. `compile_release` called `_ensure_repo`
once per RELEASE, and `_ensure_repo` ran `helm repo add <name> <url> --force-update`, which
downloads the whole index of that repository. The estate's 31 releases name 28 repositories,
so one compile fetched every index 31 times' worth: measured 0.5s (coroot) to 21.3s (traefik)
per index on this machine's link, 6.6MB for prometheus-community alone, and a compile that had
not finished after thirteen minutes -- which meant the gate that needs this document could not
be run locally at all.

So the compiler now asks for an index only when it does not already have it:

  * a repository helm already knows under the same URL, whose index is on disk, is not re-added
    -- no network at all;
  * a repository is added at most once per process, not once per release;
  * a reused index can be stale, and a stale index hides a chart version published after it
    was downloaded, so a render that fails against a reused index is retried once against a
    freshly downloaded index. A chart that is genuinely wrong still fails.

These grade the compiler through a fake helm, so the suite pays nothing to run them.
"""

import importlib.machinery
import importlib.util
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_loader(
    "idp_compile_helm",
    importlib.machinery.SourceFileLoader(
        "idp_compile_helm", str(ROOT / "bin" / "idp-compile-helm")
    ),
)
compiler = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compiler)

TRAEFIK_URL = "https://traefik.github.io/charts"


def _ok(args, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr=stderr)


def _fail(args, stderr="boom"):
    return subprocess.CompletedProcess(args, 1, stdout="", stderr=stderr)


def _cached_index(tmp_path, name="traefik"):
    """An index helm already downloaded, sitting in the cache directory."""
    cache = tmp_path / "repository"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / f"{name}-index.yaml").write_text("apiVersion: v1\n")
    return cache


def _prepare(monkeypatch, tmp_path, configured, handler):
    """Point the compiler at a fake helm and an empty index cache. Returns the call log."""
    calls = []

    def fake_run(args, **kw):
        args = list(args)
        calls.append(args)
        if args[:3] == ["helm", "repo", "list"]:
            return _ok(args, stdout=json.dumps(configured))
        if args[:3] == ["helm", "repo", "add"]:
            return handler.get("add", _ok(args))
        return handler.get("other", _ok(args))

    monkeypatch.setattr(compiler, "_run", fake_run)
    compiler._REPO_STATE.clear()
    compiler._CONFIGURED_REPOS = None
    compiler._REPO_INDEX_DIR = tmp_path / "repository"
    (tmp_path / "repository").mkdir(parents=True, exist_ok=True)
    return calls


def _adds(calls):
    return [c for c in calls if c[:3] == ["helm", "repo", "add"]]


def test_a_cached_index_is_reused_and_nothing_is_downloaded(monkeypatch, tmp_path):
    """The repository is known under the same URL and its index is on disk: no add, no network."""
    _cached_index(tmp_path)
    calls = _prepare(
        monkeypatch,
        tmp_path,
        configured=[{"name": "traefik", "url": TRAEFIK_URL}],
        handler={},
    )

    reused, error = compiler._ensure_repo("traefik", TRAEFIK_URL)

    assert error is None
    assert reused is True, (
        "the index on disk was used, so the caller knows it may be stale"
    )
    assert _adds(calls) == [], "an index already on disk is not downloaded again"


def test_a_repository_is_added_once_and_not_once_per_release(monkeypatch, tmp_path):
    """Two releases sharing a repository cause one add, not two."""
    calls = _prepare(monkeypatch, tmp_path, configured=[], handler={})

    first_reused, first_error = compiler._ensure_repo("traefik", TRAEFIK_URL)
    second_reused, second_error = compiler._ensure_repo("traefik", TRAEFIK_URL)

    assert (first_error, second_error) == (None, None)
    assert (first_reused, second_reused) == (False, False)
    assert len(_adds(calls)) == 1, "the repository index is downloaded once per process"


def test_a_failing_add_says_why(monkeypatch, tmp_path):
    """A repository that cannot be reached is reported by name, not swallowed."""
    _prepare(
        monkeypatch,
        tmp_path,
        configured=[],
        handler={
            "add": _fail(["helm", "repo", "add"], stderr="Error: cannot be reached")
        },
    )

    reused, error = compiler._ensure_repo("traefik", TRAEFIK_URL)

    assert reused is False
    assert error is not None
    assert "traefik" in error
    assert "cannot be reached" in error


def test_a_render_that_fails_against_a_reused_index_is_retried(monkeypatch, tmp_path):
    """A stale index cannot be the reason a release fails: the index is fetched again."""
    _cached_index(tmp_path)

    templates = []

    def handler_for(args):
        if args[:2] == ["helm", "template"]:
            templates.append(args)
            if len(templates) == 1:
                return _fail(args, stderr="Error: chart version not found")
            return _ok(args, stdout="---\nkind: ConfigMap\nmetadata:\n  name: demo\n")
        return _ok(args)

    calls = []
    configured = [{"name": "traefik", "url": TRAEFIK_URL}]

    def fake_run(args, **kw):
        args = list(args)
        calls.append(args)
        if args[:3] == ["helm", "repo", "list"]:
            return _ok(args, stdout=json.dumps(configured))
        if args[:3] == ["helm", "repo", "add"]:
            return _ok(args)
        return handler_for(args)

    monkeypatch.setattr(compiler, "_run", fake_run)
    compiler._REPO_STATE.clear()
    compiler._CONFIGURED_REPOS = None
    compiler._REPO_INDEX_DIR = tmp_path / "repository"
    (tmp_path / "repository").mkdir(parents=True, exist_ok=True)

    release = {
        "metadata": {"name": "traefik", "namespace": "observability"},
        "spec": {
            "chart": {
                "spec": {
                    "chart": "traefik",
                    "version": "1.0.0",
                    "sourceRef": {"kind": "HelmRepository", "name": "traefik"},
                }
            }
        },
    }
    record = compiler.compile_release(release, {"traefik": TRAEFIK_URL})

    assert record["error"] is None, record["error"]
    assert len(templates) == 2, (
        "the render was retried against a freshly downloaded index"
    )
    assert len(_adds(calls)) == 1, "the index was downloaded once, for the retry"
    assert record["objects"], "the retried render produced the objects"


def test_a_chart_that_is_wrong_still_fails(monkeypatch, tmp_path):
    """The retry does not turn a broken chart green: the error is still reported."""
    _cached_index(tmp_path)
    configured = [{"name": "traefik", "url": TRAEFIK_URL}]

    def fake_run(args, **kw):
        args = list(args)
        if args[:3] == ["helm", "repo", "list"]:
            return _ok(args, stdout=json.dumps(configured))
        if args[:3] == ["helm", "repo", "add"]:
            return _ok(args)
        return _fail(args, stderr="Error: chart version not found")

    monkeypatch.setattr(compiler, "_run", fake_run)
    compiler._REPO_STATE.clear()
    compiler._CONFIGURED_REPOS = None
    compiler._REPO_INDEX_DIR = tmp_path / "repository"
    (tmp_path / "repository").mkdir(parents=True, exist_ok=True)

    release = {
        "metadata": {"name": "traefik", "namespace": "observability"},
        "spec": {
            "chart": {
                "spec": {
                    "chart": "traefik",
                    "version": "9.9.9",
                    "sourceRef": {"kind": "HelmRepository", "name": "traefik"},
                }
            }
        },
    }
    record = compiler.compile_release(release, {"traefik": TRAEFIK_URL})

    assert record["error"], "a chart that cannot be rendered is still an error"
    assert "not found" in record["error"]
