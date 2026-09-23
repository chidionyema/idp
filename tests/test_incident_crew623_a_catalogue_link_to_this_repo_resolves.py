"""Incident 2026-08-29 (crew#623, oke-check run 33260499807): the portal's money-layer row linked to
https://github.com/chidionyema/idp/blob/main/platform/commerce/app/lago.yaml, the file was on a
branch and not yet on main, and lychee reported a 404 the pull request could not clear -- the link
is correct and only becomes true at merge. Two things came out of it, and this file is the first.

The first: a link into this repository names a path, and that path is a fact this tree already
holds. Reading it here costs nothing, needs no network, and fails in the local rung rather than
eleven minutes into a cloud run. The second lives in .github/workflows/oke-check.yml, where a
pull_request now probes blob links at the head sha instead of at main, so a correct link to a file
the branch adds is graded against the tree being proposed.

This does not replace lychee. Lychee proves the founder's links answer; this proves the ones
pointing at our own files name something that exists."""

import pathlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "backstage/founder/catalog-info.yaml"
BLOB = re.compile(
    r"https://github\.com/chidionyema/idp/blob/(?:main|HEAD)/([^\"'\s)]+)"
)


def _missing(text: str) -> list:
    missing = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for m in BLOB.finditer(line):
            path = m.group(1).split("#")[0].split("?")[0]
            if not (ROOT / path).exists():
                missing.append(f"line {line_no} -> {path}")
    return missing


def test_every_link_into_this_repo_names_a_path_that_exists() -> None:
    assert _missing(CATALOG.read_text()) == [], (
        "the portal links to a file this repository does not hold, so the founder gets a 404: "
        + ", ".join(_missing(CATALOG.read_text()))
    )


def test_the_check_refuses_a_link_to_a_path_that_is_not_here() -> None:
    """A guard that has never said no is a guard nobody has tested."""
    bad = '      url: "https://github.com/chidionyema/idp/blob/main/platform/commerce/app/nowhere.yaml"'
    assert _missing(bad) == ["line 1 -> platform/commerce/app/nowhere.yaml"]
    good = '      url: "https://github.com/chidionyema/idp/blob/main/backstage/founder/catalog-info.yaml"'
    assert _missing(good) == []


def test_the_head_sha_rewrite_leaves_another_repository_alone() -> None:
    """oke-check 33262262675: the rewrite took the whole estate's links with it.

    A pull request that ADDS a file makes every catalogue link to it 404, because the link points
    at blob/main where it does not exist yet, so the workflow rewrites the ref to this branch's
    head sha. The first version matched the bare string `/blob/main/`, which is a proxy for "a link
    into this repository" and is wrong for every other one: five links into chidionyema/crew were
    handed an idp commit sha and came back 404. This does not read the workflow's English -- it
    lifts the actual sed line out of the workflow and runs it, so the rule is graded by doing it.
    """

    import subprocess as _sp
    import tempfile as _tf

    wf = (ROOT / ".github/workflows/oke-check.yml").read_text()
    line = next(
        ln.strip()
        for ln in wf.splitlines()
        if ln.strip().startswith("sed -i") and "HEAD_SHA" in ln
    )
    # `sed -i` takes no argument on GNU (the runner) and requires one on BSD (this laptop). The
    # substitution expression -- the thing under test -- is untouched; only the in-place flag is
    # made portable so the same line can be executed on both.
    line = line.replace("sed -i ", "sed -i.bak ", 1)
    sha = "0" * 40
    fixture = (
        "https://github.com/chidionyema/idp/blob/main/platform/commerce/app/lago.yaml\n"
        "https://github.com/chidionyema/crew/blob/main/docs/STANDARDS.md\n"
    )
    with _tf.TemporaryDirectory() as d:
        (pathlib.Path(d) / "founder-links.txt").write_text(fixture)
        _sp.run(
            ["bash", "-c", line],
            cwd=d,
            check=True,
            env={
                "PATH": "/usr/bin:/bin",
                "GITHUB_REPOSITORY": "chidionyema/idp",
                "HEAD_SHA": sha,
            },
        )
        out = (pathlib.Path(d) / "founder-links.txt").read_text()
    assert f"/idp/blob/{sha}/" in out, (
        "this repository's link was not moved to the head sha"
    )
    assert "/crew/blob/main/" in out, (
        "another repository's link was rewritten to this repository's sha; that is the 404"
    )
    assert re.search(r"/crew/blob/0{40}/", out) is None
