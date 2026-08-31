"""Founder, 2026-08-31: "Your agent changed 'text in config files' to fix a cluster outage, and the
system responded by running 397 Python test files ... A config change should evaluate in 3 seconds,
not 13 minutes."

bin/idp-tests-for computed a path-based selection and then threw it away: every test file not
named in tests/slow-files.txt was added unconditionally, so a 13-file diff ran 1,628 tests in
33m34s. All 14 of its failures were `subprocess.TimeoutExpired after 60 seconds` -- invented by
the load the selection itself created, with zero real reds underneath. Two defects, both pinned
here: the blanket, and basename matching (`kustomization.yaml` names 58 tracked files, so a change
to one of them selected every test that mentions the word).

The fix is not a hand-maintained list. A basename is evidence only when it identifies exactly one
tracked file, which is a property of the repository that needs no upkeep; and the blanket is CI's
job, where a clean runner can answer its own subprocesses. The heavy rung also left
.githooks/pre-push entirely (founder item 3, and R58)."""

import pathlib
import subprocess

IDP = pathlib.Path(__file__).resolve().parents[1]
TESTS_FOR = IDP / "bin/idp-tests-for"


def _select(path, **env_extra):
    """The tests bin/idp-tests-for would run for a change to `path`, via its own --for seam."""
    import os

    env = {k: v for k, v in os.environ.items() if k != "CI"}
    env.update(env_extra)
    out = subprocess.run(
        [str(TESTS_FOR), "--for", path, "--list"],
        capture_output=True,
        text=True,
        cwd=IDP,
        env=env,
        timeout=300,
    )
    return {line for line in out.stdout.split("\n") if line.endswith(".py")}


def _tracked():
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=IDP, check=True
    )
    return out.stdout.split("\n")


def _an_ambiguous_path():
    """A tracked path whose basename names more than one file, plus a test that says only the word."""
    from collections import Counter

    tracked = [p for p in _tracked() if p]
    counts = Counter(p.rsplit("/", 1)[-1] for p in tracked)
    for path in tracked:
        base = path.rsplit("/", 1)[-1]
        if counts[base] < 2 or "/" not in path:
            continue
        for t in IDP.glob("tests/test_*.py"):
            body = t.read_text(errors="ignore")
            if base in body and path not in body:
                return path, base, f"tests/{t.name}"
    raise AssertionError(
        "no ambiguous basename in the repo; the rule has nothing to guard"
    )


def test_an_ambiguous_basename_does_not_drag_in_every_test_that_says_the_word():
    path, base, mentions_word_only = _an_ambiguous_path()
    selected = _select(path)
    assert mentions_word_only not in selected, (
        f"{mentions_word_only} names {base!r} but never {path!r}; selecting it is the 397-file bug"
    )


def test_a_unique_basename_is_still_matched_because_it_identifies_one_file():
    from collections import Counter

    tracked = [p for p in _tracked() if p]
    counts = Counter(p.rsplit("/", 1)[-1] for p in tracked)
    for t in sorted(IDP.glob("tests/test_*.py")):
        body = t.read_text(errors="ignore")
        for path in tracked:
            base = path.rsplit("/", 1)[-1]
            if counts[base] == 1 and "/" in path and base in body and path not in body:
                assert f"tests/{t.name}" in _select(path), (
                    f"{base!r} names exactly one tracked file, so tests/{t.name} reading it by "
                    f"basename is a real dependency and must still be selected"
                )
                return
    # Nothing in the repo matches by unique basename alone: the rule is untestable but not broken.


def test_the_blanket_runs_in_ci_and_not_on_a_laptop():
    path, _, _ = _an_ambiguous_path()
    local = _select(path)
    everything = _select(path, TESTS_FOR_ALL="1")
    assert local < everything, (
        "TESTS_FOR_ALL=1 must add the cheap files the local selection leaves out; "
        f"local={len(local)} all={len(everything)}"
    )
    assert len(local) * 4 < len(everything), (
        f"a config change still selects {len(local)} of {len(everything)} files locally; the "
        "blanket is not actually off"
    )


def test_the_pre_push_hook_does_not_run_the_test_suite():
    """Founder item 3: the heavy rung is physically removed from the hook, not merely narrowed."""
    hook = (IDP / ".githooks/pre-push").read_text()
    ran = [
        line
        for line in hook.split("\n")
        if "idp-tests-for" in line and not line.lstrip().startswith("#")
    ]
    assert not ran, f"the hook still invokes the selector: {ran}"
