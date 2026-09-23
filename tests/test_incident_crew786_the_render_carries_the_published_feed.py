"""crew#786, 2026-09-02: the Mac sessions publish docs/FEED.md and docs/NEXT.md to
state/live-diagram through feed-guard. The render force-pushes the branch from origin/main
carrying only the inventory files, which would drop FEED.md and NEXT.md on every render.
Fix: add them to CARRIED and make estate-next read from the carried feed when available.
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RENDER = ROOT / "bin" / "catalog-render"


def test_carried_includes_feed_and_next():
    """The render must carry FEED.md and NEXT.md from the previous branch state."""
    src = RENDER.read_text()
    assert "CARRIED = [" in src, "CARRIED must be defined"
    # crew#786: FEED.md and NEXT.md must be in CARRIED
    assert "docs/FEED.md" in src, "CARRIED must include docs/FEED.md"
    assert "docs/NEXT.md" in src, "CARRIED must include docs/NEXT.md"


def test_workflows_fetch_feed_from_state_branch():
    """The workflows must try to fetch FEED.md from state/live-diagram before the bucket fallback."""
    catalog_render = (ROOT / ".github/workflows/catalog-render.yml").read_text()
    estate_state = (ROOT / ".github/workflows/estate-state.yml").read_text()

    # both workflows must contain the string to fetch from state/live-diagram
    fetch_cmd = "state/live-diagram:docs/FEED.md"
    assert fetch_cmd in catalog_render, (
        "catalog-render.yml must try to fetch FEED.md from state/live-diagram"
    )
    assert fetch_cmd in estate_state, (
        "estate-state.yml must try to fetch FEED.md from state/live-diagram"
    )


def test_sh_accepts_env_parameter():
    """The render's sh() takes an env so a step can be given a variable (first cut called
    sh(..., env=...) on a function with no such parameter: TypeError at run time)."""
    src = (ROOT / "bin" / "catalog-render").read_text()
    assert (
        "def sh(cmd: list[str], cwd: Path, timeout: int = 120, env: dict | None = None)"
        in src
    )
    assert "env=env" in src


def test_estate_next_reads_the_feed_from_the_state_branch():
    """The render hands the carried FEED.md to estate-next and always re-renders NEXT.md;
    it never keeps a carried NEXT.md over a fresh render (estate-next prints no stamp)."""
    src = (ROOT / "bin" / "catalog-render").read_text()
    assert '"--feed", str(carried_feed)' in src
    assert "carried_taken" not in src


def test_workflow_checkout_path_matches_git_commands():
    """For each workflow, the git -C path must match the checkout path."""
    workflows = {
        "catalog-render.yml": ROOT / ".github/workflows/catalog-render.yml",
        "estate-state.yml": ROOT / ".github/workflows/estate-state.yml",
    }

    for wf_name, wf_path in workflows.items():
        wf_text = wf_path.read_text()

        # Find the checkout step and extract path (absent = root)
        import re

        checkout_match = re.search(
            r"uses: actions/checkout.*?\n(?:.*?\n)*?\s+with:\s*\{([^}]+)\}", wf_text
        )
        if checkout_match:
            checkout_config = checkout_match.group(1)
            path_match = re.search(r"path:\s*(\S+)", checkout_config)
            checkout_path = (
                path_match.group(1) if path_match else None
            )  # None means root
        else:
            checkout_path = None  # default to root

        # Find all git -C commands in this workflow
        git_c_matches = re.findall(r"git (-C \S+)", wf_text)

        if checkout_path is None:
            # Checkout is at root: git commands should use no -C, or -C "$GITHUB_WORKSPACE" or equivalent
            for gc in git_c_matches:
                # -C with a specific repo path (like -C idp) is wrong when checkout is at root
                path_arg = gc.split()[1] if len(gc.split()) > 1 else None
                if path_arg and path_arg not in [
                    '"$GITHUB_WORKSPACE"',
                    "$GITHUB_WORKSPACE",
                ]:
                    # Allow -C idp only if the checkout path is idp
                    raise AssertionError(
                        f"{wf_name}: checkout is at root but git uses '{gc}'. "
                        f'Should use no -C or -C "$GITHUB_WORKSPACE"'
                    )
        else:
            # Checkout is at a specific path: git commands should use -C with that path
            for gc in git_c_matches:
                path_arg = gc.split()[1] if len(gc.split()) > 1 else None
                # The path in -C should match the checkout path
                assert path_arg == checkout_path, (
                    f"{wf_name}: checkout uses path={checkout_path} but git uses '{gc}'. "
                    f"They should match."
                )
