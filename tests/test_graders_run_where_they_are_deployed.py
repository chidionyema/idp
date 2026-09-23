"""The six graders read `bin/` programs by path. That path must be right in BOTH places the
plugin runs: a plain repository checkout (`<root>/mcp/plugins/estate_simulate.py`, where the
root is `parents[2]`) and the estate-mcp image (`/app/plugins/estate_simulate.py`, where
`parents[2]` is `/` and holds no `bin/` at all).

The image case is what was broken: the door opened, `simulate_change` returned a real
proposal, and every grader answered `could not run: ValueError` because `base` resolved to
`/` and `/bin/idp-admission-dryrun` does not exist. The live pod was running like that.

These tests pin the resolution rule rather than the paths themselves: ESTATE_REPO_ROOT wins
when set, `parents[2]` is the fallback, and the graders are silent about a missing tree
instead of claiming a verdict.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

PLUGIN_FILE = (
    Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_simulate.py"
)
REPO_ROOT = PLUGIN_FILE.parents[2]

# Every program _live_graders shells to, as the plugin names them.
GRADER_PROGRAMS = (
    "idp-admission-dryrun",
    "idp-rules",
    "idp-shadow-verify",
    "idp-calico-deny-log",
    "idp-fits-a-node",
    "idp-blast-grade",
)


@pytest.fixture()
def estate_simulate(tmp_path, monkeypatch):
    """Load the plugin by file path (the way pluggy loads it under --plugins-dir)."""
    spec = importlib.util.spec_from_file_location("estate_simulate_paths", PLUGIN_FILE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module.__name__] = module
    spec.loader.exec_module(module)
    monkeypatch.delenv("ESTATE_REPO_ROOT", raising=False)
    return module


def test_every_grader_program_exists_in_the_repository():
    """The plugin names six programs; all six must exist in the tree it ships from. A rename
    in bin/ that the plugin does not follow is a grader that can never run."""
    missing = [p for p in GRADER_PROGRAMS if not (REPO_ROOT / "bin" / p).is_file()]
    assert not missing, f"graders name programs that do not exist: {missing}"


def test_base_follows_estate_repo_root_when_the_deployment_states_it(
    estate_simulate, monkeypatch, tmp_path
):
    """The image layout: the deployment states the root, because the plugin's own file sits at
    /app/plugins/ and parents[2] would be /. The graders must resolve against the stated root."""
    stated = tmp_path / "app"
    (stated / "bin").mkdir(parents=True)
    monkeypatch.setenv("ESTATE_REPO_ROOT", str(stated))

    graders = estate_simulate._live_graders("hello")
    assert set(graders) == set(estate_simulate.GRADER_NAMES), (
        "all six graders must be offered"
    )

    # With the stated root holding no programs, each grader must answer UNKNOWN rather than
    # crash -- a grader that cannot run is a fail-closed UNKNOWN, never a fabricated verdict.
    for name, grader in graders.items():
        result = grader()
        assert isinstance(result, dict), f"{name} must return a dict"
        assert result.get("verdict") == "UNKNOWN", (
            f"{name} answered {result.get('verdict')!r} with no program on disk; "
            "a grader that could not run is UNKNOWN"
        )


def test_base_falls_back_to_the_plugin_files_own_location(estate_simulate):
    """A plain checkout states nothing. The computed default is the repository root derived
    from this file -- parents[2] of mcp/plugins/estate_simulate.py."""
    graders = estate_simulate._live_graders("hello")
    assert set(graders) == set(estate_simulate.GRADER_NAMES)

    # In the checkout the programs DO exist, so the graders reach their program. They may
    # still answer UNKNOWN (an inline manifest that is not a manifest, no kubeconfig), but
    # the detail must never be "not present" -- that is the wrong path, which is the bug.
    for name, grader in graders.items():
        result = grader()
        detail = str(result.get("detail", ""))
        assert "not present" not in detail, (
            f"{name} could not find its program in the checkout: {detail!r}"
        )


def test_a_graders_absence_is_named_not_swallowed(
    estate_simulate, monkeypatch, tmp_path
):
    """When the root points at a tree with no bin/, the grader says which program is missing.
    The operator must be able to read the reason off the proposal, not guess."""
    empty = tmp_path / "empty-root"
    empty.mkdir()
    monkeypatch.setenv("ESTATE_REPO_ROOT", str(empty))

    graders = estate_simulate._live_graders("hello")
    admission = graders["admission"]()
    assert admission["verdict"] == "UNKNOWN"
    assert "idp-admission-dryrun" in admission["detail"], (
        "the refusal must name the program it could not find"
    )


def test_a_graders_own_unknown_keeps_its_reason(estate_simulate):
    """A grader's UNKNOWN is an ANSWER, and its `detail` names the input it lacks. It must be
    carried through verbatim, never replaced by a synthetic error.

    This was a live defect: `simulate_change` raised `ValueError(f"grader {name} did not answer
    SAFE/UNSAFE")` for any grader that answered UNKNOWN, then caught its own raise and reported
    `"<name> could not run: ValueError"`. So a grader correctly saying "no shadow observation
    supplied" was reported as a program that could not run -- and an operator reading that goes
    looking for a missing binary instead of supplying the missing input. Every live grader showed
    `could not run: ValueError`, which is what made the door look broken when it was not.
    """

    def honest_grader():
        return {
            "verdict": "UNKNOWN",
            "detail": "no shadow observation supplied; convergence unproven",
        }

    graders = {name: honest_grader for name in estate_simulate.GRADER_NAMES}
    proposal = estate_simulate.simulate_change("hello", graders=graders)

    assert proposal["verdict"] == "UNKNOWN"
    for name in estate_simulate.GRADER_NAMES:
        detail = proposal["grader_results"][name]["detail"]
        assert "could not run" not in detail, (
            f"{name} replaced its own reason with a synthetic error: {detail!r}"
        )
        assert "no shadow observation supplied" in detail, (
            f"{name} lost the reason it gave: {detail!r}"
        )


def test_a_grader_that_raises_is_named_with_its_exception(estate_simulate):
    """A grader that actually raises is a different thing from one that answers UNKNOWN, and the
    two must not read the same. The raising one names the exception and its message."""

    def raising_grader():
        raise RuntimeError("kubectl exploded")

    graders = {name: raising_grader for name in estate_simulate.GRADER_NAMES}
    proposal = estate_simulate.simulate_change("hello", graders=graders)

    assert proposal["verdict"] == "UNKNOWN"
    detail = proposal["grader_results"]["admission"]["detail"]
    assert "RuntimeError" in detail and "kubectl exploded" in detail, detail


def test_a_grader_answering_a_malformed_verdict_is_refused(estate_simulate):
    """A grader that answers something other than SAFE/UNSAFE/UNKNOWN is the one case that IS a
    malformed answer, and it must be reported as such -- never folded into a pass."""

    def malformed_grader():
        return {"verdict": "PROBABLY_FINE", "detail": "looks good to me"}

    graders = {name: malformed_grader for name in estate_simulate.GRADER_NAMES}
    proposal = estate_simulate.simulate_change("hello", graders=graders)

    assert proposal["verdict"] == "UNKNOWN", "a malformed verdict must never yield SAFE"
    detail = proposal["grader_results"]["admission"]["detail"]
    assert "PROBABLY_FINE" in detail, detail


def test_the_image_can_actually_copy_every_grader_path():
    """A Docker build can only COPY from its own context, and bin/dockerfiles decides that
    context as the Dockerfile's own directory. Naming a file outside the context is not caught
    by any lint here -- it fails at build time, which is what happened: the graders were named,
    the context was still mcp/, and every COPY line became unresolvable.

    This test asserts the contract that has to hold: every COPY source in estate-mcp.Dockerfile
    exists under the context bin/dockerfiles emits for that image. It needs no Docker daemon.
    """
    import re
    import subprocess

    repo = Path(__file__).resolve().parents[1]
    dockerfile = repo / "estate-mcp.Dockerfile"
    assert dockerfile.is_file(), (
        "the estate-mcp Dockerfile must exist at the repository root"
    )

    rows = subprocess.run(
        [str(repo / "bin" / "dockerfiles")],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    row = [ln.split() for ln in rows.splitlines() if ln.startswith("estate-mcp ")]
    assert row, f"bin/dockerfiles does not list estate-mcp. It emits:\n{rows}"
    _, listed_dockerfile, context = row[0]
    assert listed_dockerfile == "estate-mcp.Dockerfile", listed_dockerfile

    context_dir = repo / context
    sources = re.findall(r"^\s*COPY\s+(?!--from=)(\S+)", dockerfile.read_text(), re.M)
    assert sources, "the Dockerfile copies nothing; the graders cannot be in the image"

    missing = [s for s in sources if not (context_dir / s).exists()]
    assert not missing, (
        f"COPY sources outside the build context {context!r}: {missing}. "
        "The graders live at bin/ and rules.yaml at the repository root, so this image's "
        "context must be the root."
    )
