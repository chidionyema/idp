"""bin/estate-snapshot: an unreadable source is BLIND with its reason, never a zero."""

import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader(
    "estate_snapshot", str(ROOT / "bin/estate-snapshot")
)
spec = importlib.util.spec_from_loader("estate_snapshot", loader)
snap = importlib.util.module_from_spec(spec)
loader.exec_module(snap)


def test_a_failing_source_is_blind_not_zero():
    def boom():
        raise RuntimeError("kubectl: connection refused")

    assert snap.section(boom) == {"BLIND": "RuntimeError: kubectl: connection refused"}


def test_repo_counts_only_our_commits_as_ours(tmp_path, monkeypatch):
    import subprocess

    def commit(who, name):
        (tmp_path / name).write_text("print(1)\nprint(2)\n")
        subprocess.run(["git", "add", name], cwd=tmp_path, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                f"user.name={who}",
                "-c",
                f"user.email={who}@x",
                "commit",
                "-qm",
                name,
            ],
            cwd=tmp_path,
            check=True,
        )

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    commit("upstream", "a.py")
    commit("upstream", "b.py")
    commit("Chidi Onyema", "c.py")
    s = snap.repo_stats(tmp_path)
    assert (s["ours"], s["own_commits"], s["commits"], s["code_lines"]) == (
        False,
        1,
        3,
        6,
    )
