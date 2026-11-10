"""Falsifiers for the pre-push hook's interpreter resolution.

A git hook inherits a PATH that does not carry a version manager's shims. The measured defect: the
hook refused platform/lifeboat/src/brain.js as unparseable with `node is not installed` while node
v22.15.1 was installed and answering, because nvm's bin directory is added by the interactive shell
and never by a hook. A guard that refuses a file it could have parsed taxes every agent (R14) and a
guard that cannot judge must look harder before it refuses (R1), so this file pins both halves:
the resolution finds node behind a stripped PATH, and the hook still refuses when node is genuinely
absent rather than passing silently.
"""

import os
import shutil
import subprocess
from pathlib import Path


IDP = Path(__file__).resolve().parents[1]
HOOK = IDP / ".githooks" / "pre-push"

# The resolution the hook performs, extracted so it can be exercised without running a whole push.
# Kept as a shell fragment rather than reimplemented in Python: the hook IS the contract, and a
# Python copy of its logic would be the second implementation this estate deletes.
RESOLVE = """
if ! command -v node >/dev/null 2>&1; then
  for cand in "$HOME"/.nvm/versions/node/*/bin/node /usr/local/bin/node /opt/homebrew/bin/node; do
    if [ -x "$cand" ]; then NODE_BIN="$cand"; break; fi
  done
  NODE_BIN="${NODE_BIN:-node}"
  if ! command -v "$NODE_BIN" >/dev/null 2>&1; then echo ABSENT; exit 1; fi
else
  NODE_BIN=node
fi
echo "FOUND $NODE_BIN"
"""


def run_resolve(env):
    # bash is invoked by absolute path: the whole point of these tests is a PATH that cannot see
    # version managers, and one of them needs a PATH that sees nothing at all.
    return subprocess.run(
        [shutil.which("bash") or "/bin/bash", "-c", RESOLVE],
        capture_output=True,
        text=True,
        env=env,
    )


# ---- the guard looks before it refuses ----------------------------------
def test_a_stripped_path_still_finds_node():
    """`env -i` is the hook's real environment: no nvm, no shell profile. If this answers ABSENT
    while node is installed, the hook refuses correct files and every JS change is blocked."""
    env = {"HOME": os.environ.get("HOME", ""), "PATH": "/usr/bin:/bin"}
    out = run_resolve(env)
    assert out.returncode == 0, (
        "a stripped PATH found no node at all, so the hook would refuse every JavaScript file on "
        f"this machine. stdout={out.stdout!r} stderr={out.stderr!r}"
    )
    assert "FOUND" in out.stdout
    assert "ABSENT" not in out.stdout


def test_the_resolved_node_actually_parses_the_estates_javascript():
    """Finding *a* node is not enough: it must be a node that parses the file the hook refused."""
    env = {"HOME": os.environ.get("HOME", ""), "PATH": "/usr/bin:/bin"}
    out = run_resolve(env)
    node = out.stdout.strip().split(" ", 1)[1]
    target = IDP / "platform" / "lifeboat" / "src" / "brain.js"
    parsed = subprocess.run(
        [node, "--check", str(target)], capture_output=True, text=True
    )
    assert parsed.returncode == 0, f"{node} cannot parse {target}:\n{parsed.stderr}"


# ---- and still refuses when the interpreter is truly absent -------------
def test_with_no_node_anywhere_it_refuses_rather_than_passes(tmp_path):
    """The other direction of the same law: if there is genuinely no interpreter, silence is a
    fail-open and the guard must refuse. Simulated with an empty HOME so the nvm glob cannot match."""
    env = {"HOME": str(tmp_path), "PATH": str(tmp_path)}
    out = run_resolve(env)
    assert out.returncode != 0, (
        "with no interpreter anywhere the resolution succeeded, which would let an unparsed file "
        f"land. stdout={out.stdout!r}"
    )
    assert "ABSENT" in out.stdout


# ---- the hook's own text carries the resolution -------------------------
def test_the_hook_resolves_node_instead_of_assuming_it():
    text = HOOK.read_text()
    assert "is not installed, so it cannot be parsed" not in text, (
        "the hook still declares node absent without looking -- the measured refusal is back"
    )
    assert ".nvm/versions/node/*/bin/node" in text, (
        "the hook does not look where node actually lives"
    )


def test_the_hook_still_parses_as_shell():
    out = subprocess.run(["bash", "-n", str(HOOK)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
