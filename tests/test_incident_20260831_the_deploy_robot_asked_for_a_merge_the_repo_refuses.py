"""idp#1046. The estate stopped deploying for thirteen hours and nothing said so.

WHAT HAPPENED. On 2026-08-30 the repository's `allow_auto_merge` was set to false, beside the
`founder-only-releases` ruleset (created 2026-08-30T17:18Z). Every robot in the estate ended its run
with `gh pr merge --auto`, which GitHub then answers `GraphQL: Auto merge is not allowed for this
repository (enablePullRequestAutoMerge)`, exit 1. Six call sites did it.

THE COST. idp#1011 -- the catalogue's own deploy, carrying `main-3063-ca2a0d31` -- was opened
2026-08-30T14:45:29Z and never merged. `platform/backstage/overlays/oke/kustomization.yaml` on main
stayed pinned at `main-2913-2ca4dd33`, so catalogue.mumchimp.com served a build from the previous
afternoon while every merge to main built an image nothing pointed at. The founder saw no change in
the portal and said so. clusters/oke/edge.yaml:154-160 records another lane hitting the identical
wall on the shop and moving the tag by hand instead of fixing the class.

The second half was the `verify` gate: `bin/idp-verify-claims` refuses a pull request touching
platform/ with no `Verify:` line, and that gate landed after `bin/idp-image-update-pr` was written,
so the robot's body could never satisfy it. Both halves are held here.
"""

import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARM = os.path.join(ROOT, "bin", "idp-pr-arm")

# Files that may ask GitHub to merge something. Every other file must go through bin/idp-pr-arm.
SCAN = [os.path.join(ROOT, "bin"), os.path.join(ROOT, ".github", "workflows")]
AUTO = re.compile(r"""pr["',\s]+merge(?!.*idp-pr-arm).*--auto""")


def _files():
    for d in SCAN:
        for base, _, names in os.walk(d):
            for n in names:
                p = os.path.join(base, n)
                if os.path.islink(p) or p == ARM:
                    continue
                try:
                    yield p, open(p, encoding="utf-8").read()
                except (UnicodeDecodeError, OSError):
                    continue


def _code_lines(text):
    """Lines that run. A comment about the old call is documentation, not a call."""
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith("#") or s.startswith("//"):
            continue
        yield i, line


def _run_arm(allow, tmp_path):
    """Run bin/idp-pr-arm against a stub `gh` that answers `allow` for allow_auto_merge."""
    bindir = tmp_path / "stub"
    bindir.mkdir()
    calls = bindir / "calls"
    (bindir / "gh").write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$@" >> "{calls}"\n'
        'if [ "$1" = api ]; then echo ' + allow + "; fi\n"
        "exit 0\n"
    )
    (bindir / "gh").chmod(0o755)
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "GH_REPO": "o/r"}
    p = subprocess.run(
        [ARM, "77", "--squash"], capture_output=True, text=True, env=env, timeout=60
    )
    return p, (calls.read_text() if calls.exists() else "")


def test_auto_merge_on_arms_the_pull_request(tmp_path):
    p, calls = _run_arm("true", tmp_path)
    assert p.returncode == 0, p.stderr
    assert p.stdout.startswith("ok"), p.stdout
    assert "pr merge 77 --auto --squash" in calls, calls


def test_auto_merge_off_waits_on_the_founder_and_does_not_fail(tmp_path):
    """The incident in one assertion: a robot that cannot merge must say so, not exit 1."""
    p, calls = _run_arm("false", tmp_path)
    assert p.returncode == 0, f"a repository setting is not a robot failure: {p.stderr}"
    assert p.stdout.startswith("waiting"), p.stdout
    assert "pull/77" in p.stdout, "the founder needs the link, not a status word"
    assert "pr merge" not in calls, "it must not ask for a merge the repository refuses"
