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
