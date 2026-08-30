"""crew#66, idp#895: `bin/idp-portal-buttons` was committed as mode 644, so the PR's own
`Verify:` line failed in CI with `/bin/sh: bin/idp-portal-buttons: Permission denied` (run
33283341328, exit 126). The sweep found a second instance the same minute: `bin/matrix-gate`,
invoked directly by `.github/workflows/matrix-review.yml`, had never been executable either.

The guard: every file under bin/ that starts with a shebang carries the executable bit in git's
index (the bit CI checks out, not the one on this machine's disk). Proved red on a tree that
holds one such file without the bit.
"""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _non_executable_scripts(root):
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-s", "bin"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    bad = []
    for line in out.splitlines():
        mode, _sha, _stage, path = line.split(None, 3)
        if mode == "100755":
            continue
        with open(root / path, "rb") as fh:
            if fh.read(2) == b"#!":
                bad.append(path)
    return bad


def test_every_bin_script_with_a_shebang_is_executable_in_git():
    assert _non_executable_scripts(ROOT) == []


def test_a_script_without_the_bit_is_red(tmp_path):
    root = tmp_path / "tree"
    (root / "bin").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "bin" / "tool").write_text(f"#!{sys.executable}\nprint('hi')\n")
    (root / "bin" / "notes.txt").write_text("not a script\n")
    subprocess.run(["git", "-C", str(root), "add", "bin"], check=True)
    assert _non_executable_scripts(root) == ["bin/tool"]
    subprocess.run(
        ["git", "-C", str(root), "update-index", "--chmod=+x", "bin/tool"], check=True
    )
    assert _non_executable_scripts(root) == []
