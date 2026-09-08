"""A generator CI grades by --check runs at commit time, or the tree drifts and nobody is told.

idp#2477 and idp#2495 both went red within one hour on 2026-09-08, on the same cause: a workflow
was added, `bin/idp-portal-buttons` was not re-run, and the only reminder was a check ten minutes
later on another machine. 178 files in this tree are generated and committed; the hook that runs on
every commit ran none of the generators. .githooks/pre-commit now carries a `regen` row per graded
generator, and this test is what stops a new graded generator from arriving without one.
"""

import os
import re
import subprocess

ROOT = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
).stdout.strip()
HOOK = os.path.join(ROOT, ".githooks", "pre-commit")

# A generator whose --check never grades a committed file. estate-showcase's rung in bin/idp-ci
# renders into a temp fixture catalogue and greys its own output there ($sc, not docs/SHOWCASE.md),
# so there is no tracked artefact for a commit-time run to keep current.
EXEMPT = {
    "bin/estate-showcase": "graded only against a temp fixture catalogue, not a tracked file"
}


def _rows():
    """(name, inputs regex, generator argv, output paths) for each regen row in the hook."""
    text = open(HOOK).read()
    return [
        (m[0], m[1], m[2], m[3].split())
        for m in re.findall(
            r"^regen\s+(\S+)\s+'([^']*)'\s*\\?\s*\n?\s*'([^']*)'\s+'([^']*)'",
            text,
            re.M,
        )
    ]


def _graded():
    """Generators some gate runs with --check against the tree."""
    sources = [os.path.join(ROOT, "bin", "idp-ci")]
    tests = os.path.join(ROOT, "tests")
    sources += [
        os.path.join(tests, f)
        for f in os.listdir(tests)
        if f.endswith(".py") and f != os.path.basename(__file__)
    ]
    found = set()
    for path in sources:
        for line in open(path, errors="replace"):
            if "--check" not in line:
                continue
            found.update(re.findall(r"bin/[a-z0-9-]+", line))
    return found


def test_every_check_graded_generator_runs_at_commit_time():
    wired = " ".join(gen for _, _, gen, _ in _rows())
    missing = {g for g in _graded() if g not in wired and g not in EXEMPT}
    assert missing == set(), (
        f"{sorted(missing)} are graded by --check but no .githooks/pre-commit regen row runs them; "
        "add a row, or an EXEMPT entry here saying which tracked file it does not own"
    )


def test_each_row_names_a_generator_and_outputs_that_exist():
    rows = _rows()
    assert len(rows) >= 3, f"the hook lost its regen rows: {rows}"
    for name, inputs, gen, outs in rows:
        tool = os.path.join(ROOT, gen.split()[0])
        assert os.access(tool, os.X_OK), (
            f"{name}: {gen} is not an executable in this tree"
        )
        re.compile(inputs)
        for out in outs:
            assert os.path.exists(os.path.join(ROOT, out)), (
                f"{name}: output {out} does not exist"
            )


def test_each_row_regenerates_its_own_output_when_that_output_is_hand_edited():
    """The row's inputs must match its own outputs: a hand-edit of a generated file is drift too."""
    for name, inputs, _gen, outs in _rows():
        pattern = re.compile(inputs)
        assert any(pattern.match(o) or pattern.match(o + "/x") for o in outs), (
            f"{name}: the row does not fire when its own output {outs} is staged, "
            "so a hand-edit of a generated file would reach CI unrendered"
        )
