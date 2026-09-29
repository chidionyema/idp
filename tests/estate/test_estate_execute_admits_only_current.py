"""estate-execute runs only the current release; --from admits an unmerged worktree, labelled.

docs/tickets/2026-09-27-merged-is-operating.md: a hand-copied intent is refused, an unconverged
laptop (IDP-Estate.pkg not installed) still runs its local copy labelled `unconverged`, and
--from runs a worktree's intent labelled `unmerged`. Hermetic: tmp HOME, tmp ESTATE_PREFIX.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess  # noqa: S404 -- fixed argv, no shell
import sys
from pathlib import Path

import yaml

EXE = Path(__file__).resolve().parents[2] / "platform/estate/bin/estate-execute"
# HOME is overridden below, which hides the user site-packages yaml may live in.
_YAML_SITE = str(Path(yaml.__file__).resolve().parents[1])


def intent_yaml(name: str) -> str:
    return f"name: {name}\ndescription: t\nsteps:\n  - name: s\n    cmd: echo hello-{name}\n"


def composing_yaml(name: str, sub: str) -> str:
    return f"name: {name}\ndescription: t\nsteps:\n  - name: call\n    intent: {sub}\n"


def setup(tmp_path: Path):
    home = tmp_path / "home"
    (home / ".estate").mkdir(parents=True)
    exe = tmp_path / "bin" / "estate-execute"
    exe.parent.mkdir()
    shutil.copyfile(EXE, exe)
    return home, exe


def release(tmp_path: Path, home: Path, intents: dict) -> Path:
    """A converged layout: prefix/releases/r1/intents, current -> r1, ~/.estate/intents -> it."""
    rel = tmp_path / "prefix" / "releases"
    (rel / "r1" / "intents").mkdir(parents=True)
    for name, text in intents.items():
        (rel / "r1" / "intents" / f"{name}.yaml").write_text(text)
    (rel / "current").symlink_to("r1")
    (home / ".estate" / "intents").symlink_to(rel / "current" / "intents")
    return rel / "r1" / "intents"


def run(
    tmp_path: Path, home: Path, exe: Path, *args: str
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["ESTATE_PREFIX"] = str(tmp_path / "prefix")
    env["PYTHONPATH"] = _YAML_SITE + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(  # noqa: S603
        [sys.executable, str(exe), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def tickets(home: Path) -> list:
    conn = sqlite3.connect(str(home / ".estate" / "estate.db"))
    try:
        return conn.execute(
            "SELECT intent, harness, status FROM intent_tickets ORDER BY started_at"
        ).fetchall()
    finally:
        conn.close()


def test_intent_from_the_current_release_runs_as_direct(tmp_path: Path) -> None:
    home, exe = setup(tmp_path)
    release(tmp_path, home, {"ok": intent_yaml("ok")})
    r = run(tmp_path, home, exe, "ok")
    assert r.returncode == 0, r.stderr
    assert "hello-ok" in r.stdout
    assert [(i, h) for i, h, _ in tickets(home)] == [("ok", "direct")]


def test_hand_copy_outside_the_release_is_refused(tmp_path: Path) -> None:
    home, exe = setup(tmp_path)
    release(tmp_path, home, {"ok": intent_yaml("ok")})
    (home / ".estate" / "intents").unlink()
    (home / ".estate" / "intents").mkdir()
    (home / ".estate" / "intents" / "hand.yaml").write_text(intent_yaml("hand"))
    r = run(tmp_path, home, exe, "hand")
    assert r.returncode == 2
    assert "REFUSED" in r.stderr
    assert "hello-hand" not in r.stdout


def test_from_worktree_runs_and_is_labelled_unmerged(tmp_path: Path) -> None:
    home, exe = setup(tmp_path)
    release(tmp_path, home, {"ok": intent_yaml("ok")})
    wt = tmp_path / "wt"
    (wt / "platform" / "estate" / "intents").mkdir(parents=True)
    (wt / "platform" / "estate" / "intents" / "hand.yaml").write_text(
        intent_yaml("hand")
    )
    r = run(tmp_path, home, exe, "--from", str(wt), "hand")
    assert r.returncode == 0, r.stderr
    assert "hello-hand" in r.stdout
    assert "UNMERGED" in r.stderr
    assert [(i, h) for i, h, _ in tickets(home)] == [("hand", "unmerged")]


def test_from_a_dir_without_intents_is_an_error(tmp_path: Path) -> None:
    home, exe = setup(tmp_path)
    r = run(tmp_path, home, exe, "--from", str(tmp_path), "ok")
    assert r.returncode == 1
    assert "no platform/estate/intents" in r.stderr


def test_without_a_release_the_local_copy_runs_labelled_unconverged(
    tmp_path: Path,
) -> None:
    home, exe = setup(tmp_path)
    (home / ".estate" / "intents").mkdir()
    (home / ".estate" / "intents" / "ok.yaml").write_text(intent_yaml("ok"))
    r = run(tmp_path, home, exe, "ok")
    assert r.returncode == 0, r.stderr
    assert "hello-ok" in r.stdout
    assert "UNCONVERGED" in r.stderr
    assert [(i, h) for i, h, _ in tickets(home)] == [("ok", "unconverged")]


def test_intent_only_in_a_moved_aside_hand_copy_says_not_merged(tmp_path: Path) -> None:
    home, exe = setup(tmp_path)
    release(tmp_path, home, {"ok": intent_yaml("ok")})
    aside = home / ".estate" / "intents.pre-converge-20260927T000000"
    aside.mkdir()
    (aside / "gone.yaml").write_text(intent_yaml("gone"))
    r = run(tmp_path, home, exe, "gone")
    assert r.returncode == 2
    assert "NOT MERGED" in r.stderr
    assert str(aside / "gone.yaml") in r.stderr


def test_an_unknown_intent_is_still_unknown(tmp_path: Path) -> None:
    home, exe = setup(tmp_path)
    release(tmp_path, home, {"ok": intent_yaml("ok")})
    r = run(tmp_path, home, exe, "nosuch")
    assert r.returncode == 1
    assert "unknown harness or intent" in r.stderr


def test_composition_inside_the_release_runs(tmp_path: Path) -> None:
    home, exe = setup(tmp_path)
    release(
        tmp_path,
        home,
        {"ok": intent_yaml("ok"), "outer": composing_yaml("outer", "ok")},
    )
    r = run(tmp_path, home, exe, "outer")
    assert r.returncode == 0, r.stderr
    assert "hello-ok" in r.stdout


def test_composed_intent_linked_out_of_the_release_fails_the_step_and_closes(
    tmp_path: Path,
) -> None:
    home, exe = setup(tmp_path)
    intents = release(tmp_path, home, {"outer": composing_yaml("outer", "sneak")})
    outside = tmp_path / "outside.yaml"
    outside.write_text(intent_yaml("sneak"))
    (intents / "sneak.yaml").symlink_to(outside)
    r = run(tmp_path, home, exe, "outer")
    assert r.returncode == 1
    assert "hello-sneak" not in r.stdout
    assert "intent refused: sneak" in r.stderr
    [(intent, harness, status)] = tickets(home)
    assert (intent, harness) == ("outer", "direct")
    assert status not in ("running", None)
