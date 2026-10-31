"""crew#85, 2026-08-25: load 236 on a 16 GB Mac while Chrome, agent scans and a pytest suite ran
at the same priority. Row 1 of that issue: a suite started from an interactive session must not
compete with the founder's foreground work. pytest loads this root conftest before collection,
so every run of this suite, from any checkout, any shell and any agent, lowers its own priority
first. `nice` on the command line was the rule that depended on every caller remembering it.

2026-08-29: estate#13 put the operator's git hooks on `core.hooksPath` in the global config, so
every `git commit` on the Mac runs python-strict and shell-strict, including the commits a test
makes inside its own throwaway repo. `sovereign/tests/test_incident_r29_spec_gate.py` commits a
fixture `.py` that ruff format rejects, and the pre-push hook refused an unrelated branch on it
(this session, 12:0xZ). CI has no global hooks, so the same test was green there: a red only
the Mac can see. A fixture repository is a test's own data, not the operator's checkout: the
suite copies the operator's global config (credentials, identity, aliases
stay) and points the hooks directory at an empty one. `GIT_CONFIG_GLOBAL` is set once here,
before collection, so every git the suite spawns inherits it."""

import os
import tempfile
from pathlib import Path

SUITE_NICE = 10

# 2026-10-31: the suite inherited the repository it was told to use. In a linked worktree,
# git exports GIT_DIR to the pre-push hook, and every `git init` a test makes inherits it:
# git then re-initialises THAT directory as a bare repository, writes `core.bare = true`
# into it, and never creates the repository the test asked for. Measured in /tmp/gitdirtest:
# `core.bare` went false -> true, the temporary directory stayed empty, and the following
# `git commit --allow-empty` exited 128 with "not a git repository". That is how the shared
# repository was corrupted and how the pre-push language gate failed.
# These are the variables git honours when it is told where the repository is. They are
# removed here, at the earliest layer every test passes through, so that every `git init` a
# test makes creates the repository it meant to create. GIT_CONFIG_GLOBAL is untouched: it
# names a configuration, not a location, and the suite sets it on purpose just below.
GIT_REPOSITORY_LOCATION_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
)


def _sanitize_git_repository_environment() -> list[str]:
    """Remove the inherited repository-location variables. Returns the names removed."""
    removed = [name for name in GIT_REPOSITORY_LOCATION_VARS if name in os.environ]
    for name in removed:
        os.environ.pop(name, None)
    return removed


REMOVED_GIT_LOCATION_VARS = _sanitize_git_repository_environment()

if os.getpriority(os.PRIO_PROCESS, 0) < SUITE_NICE:
    os.nice(SUITE_NICE - os.getpriority(os.PRIO_PROCESS, 0))


def _git_config_without_operator_hooks() -> Path:
    """The operator's global config, copied verbatim, then the hooks directory overridden
    (last value wins). A copy rather than an `[include]`: git 2.39 on the Mac did not follow
    the include from a file named by GIT_CONFIG_GLOBAL, and credentials must not drop."""
    home = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    real = [
        p for p in (home / "git" / "config", Path.home() / ".gitconfig") if p.is_file()
    ]
    root = Path(tempfile.mkdtemp(prefix="idp-suite-git-"))
    (root / "hooks").mkdir()
    text = "".join(p.read_text() + "\n" for p in real)
    text += f"[core]\n\thooksPath = {root / 'hooks'}\n"
    cfg = root / "gitconfig"
    cfg.write_text(text)
    return cfg


if "GIT_CONFIG_GLOBAL" not in os.environ:
    os.environ["GIT_CONFIG_GLOBAL"] = str(_git_config_without_operator_hooks())
