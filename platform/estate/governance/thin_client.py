"""The Darwin thin-client guard: a laptop is a thin client, not a build farm.

WHY THIS EXISTS (INS-20261110-1750-INFRA-PERMANENT). On the founder's Mac a session opened a git
worktree per attempt. Worktrees are full checkouts with node_modules, and a loop that adds one per
attempt is the ENOSPC loop in AGENTS.md section 9 R5 -- measured 2026-11: 5 GB in under two hours
from looping sessions. The same machine then ran `bin/idp-ci` locally at load 40 and made every
other agent on it slower, while GitHub Actions sat idle.

So on Darwin there are three rules, and they are refusals rather than advice because advice is
what failed before:

  1. `git worktree add` and a clone into /tmp or $TMPDIR are HARD REFUSED. A worktree is not how
     work is isolated on a laptop; a branch in the one checkout, pushed to `lane/<name>`, is.
  2. When the machine is genuinely out of room (free disk < 10 GB) or already crushed (load > 16),
     a LOCAL `bin/idp-ci` is SHUNTED to the cloud rather than run on the laptop. Deterministic
     work belongs on a machine that is not also serving the founder (AGENTS.md section 9 P2).
  3. The shunt is a real command substitution, not a suggestion: the caller gets `gh workflow run`
     in place of the local gate, so the verdict still exists and still comes from CI.

NOT ON LINUX OR IN CI. In CI (GITHUB_ACTIONS=true) and on the Linux runner this module answers
ALLOW for everything, because there the worktree *is* the isolation primitive and the local gate
*is* the point. A guard that taxes the estate's own CI is the defect class in R14.
"""

from __future__ import annotations

import os
import platform
import re
import shutil

# The thresholds are named here, once, so a test can name the same numbers.
MIN_FREE_GB = 10.0
MAX_LOAD = 16.0

# Where a clone is a thin-client violation. /var/folders is macOS's real $TMPDIR root; matching
# only the literal "/tmp" would miss every `mktemp -d` on this machine.
_TMP_ROOTS = (
    "/tmp/",  # noqa: S108 -- the PATTERNS a clone is refused on, not a path we write to
    "/private/tmp/",
    "/var/folders/",
)

_WORKTREE_ADD = re.compile(r"(^|[;&|]\s*|\b)(git\s+worktree\s+add)\b")
_CLONE = re.compile(r"(^|[;&|]\s*|\b)(git\s+clone)\b")
_IDP_CI = re.compile(r"(?:^|[;&|]\s*)(?:\S*/)?bin/idp-ci\b")


def applies() -> bool:
    """True only on a founder laptop: Darwin, outside CI."""
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        return False
    if os.environ.get("ESTATE_THIN_CLIENT", "").lower() in ("0", "false", "off"):
        return False  # explicit opt-out, ledgered by the caller
    return platform.system() == "Darwin"


def free_gb(path: str | None = None) -> float | None:
    """Free space on the volume holding `path`, in GB, or None when it cannot be measured.

    None is BLIND and never read as 'plenty': an unmeasurable disk is exactly the case a refusal
    must not silently pass, and the caller below treats None as 'do not shunt on this axis'.
    """
    try:
        usage = shutil.disk_usage(path or os.path.expanduser("~"))
    except OSError:
        return None
    return usage.free / (1024.0**3)


def load_average() -> float | None:
    """The 1-minute load average, or None when it cannot be measured."""
    try:
        return os.getloadavg()[0]
    except (OSError, AttributeError):
        return None


def _tmp_literal(command: str) -> str:
    """The /tmp-ish path a clone targets, or '' when the command does not target one."""
    for root in _TMP_ROOTS:
        for m in re.finditer(re.escape(root), command):
            # the token starting at the match, up to whitespace or a shell separator
            rest = command[m.start() :]
            token = re.split(r"[\s;&|)]", rest, maxsplit=1)[0]
            if token.strip("/"):
                return token
    return ""


def verdict(command: str, cwd: str | None = None) -> tuple[bool, str, str]:
    """Judge one command. Returns (allowed, reason, replacement).

    `replacement` is the command the caller should run INSTEAD when allowed is False and a
    replacement exists; for a hard refusal it is empty and the reason carries the remedy.
    """
    if not applies() or not command:
        return True, "OK", ""

    if "ESTATE_THIN_CLIENT" in os.environ and os.environ[
        "ESTATE_THIN_CLIENT"
    ].lower() in ("0", "false", "off"):
        return True, "OK", ""

    if _WORKTREE_ADD.search(command):
        return (
            False,
            (
                "THIN CLIENT: `git worktree add` is refused on this laptop. Worktrees are full "
                "checkouts, and a loop that adds one per attempt is how the disk fills (AGENTS.md "
                "section 9 R5: 5 GB in <2 h). Branch in the one checkout and push to lane/<name>; "
                "the Greenlane does the rest."
            ),
            "",
        )

    if _CLONE.search(command) and _tmp_literal(command):
        return (
            False,
            (
                "THIN CLIENT: cloning into temp storage is refused on this laptop. A clone in /tmp is "
                "a worktree with extra steps and dies with the boot. Branch in the one checkout and "
                "push to lane/<name>."
            ),
            "",
        )

    m = _IDP_CI.search(command)
    if m:
        g = free_gb(cwd)
        load = load_average()
        reasons = []
        if g is not None and g < MIN_FREE_GB:
            reasons.append(f"{g:.1f} GB free (< {MIN_FREE_GB:.0f} GB)")
        if load is not None and load > MAX_LOAD:
            reasons.append(f"load {load:.1f} (> {MAX_LOAD:.0f})")
        if reasons:
            return (
                False,
                (
                    "THIN CLIENT: the local gate is shunted to GitHub Actions because this laptop is "
                    + " and ".join(reasons)
                    + ". Local CI on a machine that is also serving the founder is deterministic work "
                    "in the wrong place (AGENTS.md section 9 P2)."
                ),
                "gh workflow run ci.yml",
            )
    return True, "OK", ""


def probe() -> dict:
    """The measurements this guard decides on, for a caller that must show its work."""
    return {
        "applies": applies(),
        "platform": platform.system(),
        "free_gb": free_gb(),
        "load_1m": load_average(),
        "min_free_gb": MIN_FREE_GB,
        "max_load": MAX_LOAD,
    }
