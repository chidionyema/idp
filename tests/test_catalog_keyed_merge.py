"""The keyed catalogs merge by identity, not by line (idp#8615).

Every shipping lane appends one class to catalog/issue-classes.json and one metric to
catalog/optimus-metrics.json. Git's line merge sees two lanes edit the same last lines, so any
two shipping lanes refused each other: pre-push's claim-gate said "does not merge onto
origin/main" and the Greenlane said "does not rebase". Measured 2026-11-27: four hand rebases
across three lanes in one session (#8606, #8609, #8611).

The falsifier both ways: two DIFFERENT keys must merge, at the driver, at claim-gate's
merge-check and at the Greenlane's cherry-pick; the SAME key changed differently on both sides,
and anything unparseable, must still conflict.

    python3 tests/test_catalog_keyed_merge.py --optimus
        -> optimus.catalog.disjoint_registration_conflicts=<n>   (main before the fix: 2, fix: 0)
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "bin" / "catalog-merge"
CLASSES = "catalog/issue-classes.json"
METRICS = "catalog/optimus-metrics.json"
GIT_ENV = {
    **{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _load(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _doc(*keys: str, coll: str = "classes", key: str = "class", **top) -> dict:
    return {"revision": 1, **top, coll: [{key: k, "note": f"{k} note"} for k in keys]}


def _drive(tmp: Path, base, ours, theirs, path: str = CLASSES) -> tuple[int, object]:
    files = []
    for name, doc in (("O", base), ("A", ours), ("B", theirs)):
        f = tmp / name
        f.write_text(doc if isinstance(doc, str) else json.dumps(doc, indent=2) + "\n")
        files.append(str(f))
    rc = subprocess.run(
        [sys.executable, str(DRIVER), *files, path], capture_output=True, text=True
    ).returncode
    text = Path(files[1]).read_text()
    try:
        return rc, json.loads(text)
    except ValueError:
        return rc, text


# -- the driver ------------------------------------------------------------------------------


def test_two_different_keys_merge(tmp_path):
    rc, out = _drive(tmp_path, _doc("a"), _doc("a", "mine"), _doc("a", "theirs"))
    assert rc == 0
    assert [e["class"] for e in out["classes"]] == ["a", "mine", "theirs"]


def test_same_key_changed_differently_conflicts_and_keeps_ours(tmp_path):
    ours = _doc("a", "x")
    theirs = _doc("a", "x")
    ours["classes"][1]["note"] = "mine"
    theirs["classes"][1]["note"] = "theirs"
    rc, out = _drive(tmp_path, _doc("a"), ours, theirs)
    assert rc == 1
    assert out == ours, (
        "a refused merge must leave %A as ours, git's own conflict outcome"
    )


def test_one_side_deletes_the_other_left_it(tmp_path):
    rc, out = _drive(tmp_path, _doc("a", "b"), _doc("a", "b", "new"), _doc("a"))
    assert rc == 0
    assert [e["class"] for e in out["classes"]] == ["a", "new"]


def test_delete_against_edit_conflicts(tmp_path):
    ours = _doc("a", "b")
    ours["classes"][1]["note"] = "edited"
    rc, _ = _drive(tmp_path, _doc("a", "b"), ours, _doc("a"))
    assert rc == 1


def test_identical_additions_merge_once(tmp_path):
    rc, out = _drive(tmp_path, _doc("a"), _doc("a", "same"), _doc("a", "same"))
    assert rc == 0
    assert [e["class"] for e in out["classes"]] == ["a", "same"]


def test_top_level_field_three_way(tmp_path):
    rc, out = _drive(tmp_path, _doc("a"), _doc("a"), _doc("a", revision=2))
    assert rc == 0 and out["revision"] == 2
    rc, _ = _drive(tmp_path, _doc("a"), _doc("a", revision=3), _doc("a", revision=2))
    assert rc == 1


def test_metrics_catalog_keys_on_name(tmp_path):
    def m(*k):
        return _doc(*k, coll="metrics", key="name")

    rc, out = _drive(tmp_path, m("a"), m("a", "p"), m("a", "q"), METRICS)
    assert rc == 0
    assert [e["name"] for e in out["metrics"]] == ["a", "p", "q"]


def test_what_it_cannot_judge_is_a_conflict(tmp_path):
    good = _doc("a")
    assert _drive(tmp_path, good, good, "{not json")[0] == 1
    assert _drive(tmp_path, good, good, _doc("a"), "catalog/other.json")[0] == 1
    dup = _doc("a", "a")
    assert _drive(tmp_path, good, dup, good)[0] == 1
    assert (
        _drive(tmp_path, good, good, {"revision": 1, "classes": [{"note": "no key"}]})[
            0
        ]
        == 1
    )


# -- the duplication that was inherited (measured 2026-11-28) -------------------------------


def test_an_inherited_duplicate_merges_and_the_merge_repairs_it(tmp_path):
    """A duplication the BASE carried must not block every lane that registers a metric.

    Measured 2026-11-28: main's catalog/optimus-metrics.json carried
    `admission.code_plus_test_refusals` twice -- two byte-identical copies -- so the base of
    every merge was ambiguous and claim-gate's merge-check refused EVERY lane that touches the
    catalog with "does not merge onto origin/main: catalog/optimus-metrics.json". Identical
    copies carry no disagreement, so they collapse to one value and the merged catalog comes out
    repaired.
    """
    base = _doc("a", "a")
    ours = _doc("a", "a", "mine")
    theirs = _doc("a", "a")
    rc, out = _drive(tmp_path, base, ours, theirs)
    assert rc == 0, "an inherited duplicate blocked the merge"
    assert [e["class"] for e in out["classes"]] == ["a", "mine"], out["classes"]


def test_a_duplicate_whose_copies_differ_is_still_a_conflict(tmp_path):
    base = _doc("a")
    ours = _doc("a", "a")
    ours["classes"][1]["note"] = "different"
    theirs = _doc("a", "a")
    theirs["classes"][1]["note"] = "different too"
    assert _drive(tmp_path, base, ours, theirs)[0] == 1


def test_a_side_that_introduces_the_duplication_is_still_refused(tmp_path):
    """Only an INHERITED duplication is tolerated; a lane that adds one owns the defect."""
    base = _doc("a")
    ours = _doc("a", "a")
    theirs = _doc("a")
    assert _drive(tmp_path, base, ours, theirs)[0] == 1


def test_editing_an_inherited_duplicated_key_merges(tmp_path):
    """Editing one copy of an identical pair makes the two copies DIFFER, which is a real
    disagreement and stays a conflict; editing both copies keeps them identical and merges."""
    base = _doc("a", "a")
    ours = _doc("a", "a")
    ours["classes"][0]["note"] = "mine"
    theirs = _doc("a", "a")
    assert _drive(tmp_path, base, ours, theirs)[0] == 1, (
        "editing one copy of an identical pair is a disagreement and must stay a conflict"
    )

    ours = _doc("a", "a")
    for entry in ours["classes"]:
        entry["note"] = "mine"
    rc, out = _drive(tmp_path, base, ours, _doc("a", "a"))
    assert rc == 0
    assert [e["class"] for e in out["classes"]] == ["a"], out["classes"]
    assert out["classes"][0]["note"] == "mine", out["classes"]


def test_it_writes_the_catalogs_byte_for_byte():
    """The driver's output format is the catalogs' own, so a merge never churns the diff."""
    for rel in (CLASSES, METRICS):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n" == text


# -- the two places that judge a merge -------------------------------------------------------


def _git(repo: Path, *a: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *a], capture_output=True, text=True, env=GIT_ENV
    )


def _repo(tmp: Path, same_key: bool = False, gate_root: Path = ROOT) -> Path:
    """main + lane `mine` + lane `theirs`, each adding one class and one metric to the REAL
    catalogs. `mine` is merged into main first: `theirs` is then judged against it."""
    repo = tmp / "repo"
    (repo / "catalog").mkdir(parents=True)
    (repo / "bin").mkdir()
    for rel in (CLASSES, METRICS, ".gitattributes"):
        src = gate_root / rel
        if src.exists():
            shutil.copy2(src, repo / rel)
    if (gate_root / "bin" / "catalog-merge").exists():
        shutil.copy2(
            gate_root / "bin" / "catalog-merge", repo / "bin" / "catalog-merge"
        )
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")

    def add(branch: str, ident: str, note: str) -> None:
        _git(repo, "checkout", "-q", "-b", branch, "main")
        for rel, coll, key in (
            (CLASSES, "classes", "class"),
            (METRICS, "metrics", "name"),
        ):
            doc = json.loads((repo / rel).read_text())
            doc[coll].append({key: ident, "note": note})
            (repo / rel).write_text(
                json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
            )
        _git(repo, "commit", "-qam", branch)

    add("mine", "lane-mine", "mine")
    add("theirs", "lane-mine" if same_key else "lane-theirs", "theirs")
    _git(repo, "checkout", "-q", "main")
    assert _git(repo, "merge", "-q", "--ff-only", "mine").returncode == 0
    _git(repo, "checkout", "-q", "theirs")  # the lane's own checkout, as at pre-push
    return repo


def _claim_gate_problems(repo: Path, gate: Path) -> list[str]:
    mod = _load(gate, f"claim_gate_{abs(hash(str(repo)))}")
    mod._judge_base = lambda: ("main", "main")
    cwd = os.getcwd()
    old = {k: os.environ.get(k) for k in GIT_ENV}
    os.environ.update(GIT_ENV)
    os.chdir(repo)
    try:
        return mod.merge_problems(_git(repo, "rev-parse", "theirs").stdout.strip())
    finally:
        os.chdir(cwd)
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_claim_gate_passes_two_lanes_that_registered_different_keys(tmp_path):
    repo = _repo(tmp_path)
    assert _claim_gate_problems(repo, ROOT / "bin" / "claim-gate") == []


def test_claim_gate_still_refuses_the_same_key_written_twice(tmp_path):
    repo = _repo(tmp_path, same_key=True)
    problems = _claim_gate_problems(repo, ROOT / "bin" / "claim-gate")
    assert len(problems) == 1 and CLASSES in problems[0] and METRICS in problems[0]


def test_claim_gate_judges_with_mains_rule_not_the_lanes(tmp_path):
    """A lane that deletes the rule from its own checkout is still judged by main's."""
    repo = _repo(tmp_path)
    (repo / ".gitattributes").write_text("")
    assert _claim_gate_problems(repo, ROOT / "bin" / "claim-gate") == []


def _greenlane_args() -> list[str]:
    sys.path.insert(0, str(ROOT))
    try:
        from greenlane.github import GitHubBackend
    finally:
        sys.path.remove(str(ROOT))
    return GitHubBackend._witness_merge_config(None)


def test_greenlane_cherry_pick_merges_two_different_keys(tmp_path):
    repo = _repo(tmp_path)
    _git(repo, "checkout", "-q", "main")
    pick = _git(repo, *_greenlane_args(), "cherry-pick", "--no-commit", "theirs")
    assert pick.returncode == 0, pick.stderr
    names = [e["class"] for e in json.loads((repo / CLASSES).read_text())["classes"]]
    assert names[-2:] == ["lane-mine", "lane-theirs"]


def test_greenlane_cherry_pick_still_conflicts_on_the_same_key(tmp_path):
    repo = _repo(tmp_path, same_key=True)
    _git(repo, "checkout", "-q", "main")
    pick = _git(repo, *_greenlane_args(), "cherry-pick", "--no-commit", "theirs")
    assert pick.returncode != 0


# -- the registered measure ------------------------------------------------------------------


def disjoint_registration_conflicts(gate_root: Path = ROOT) -> int:
    """Catalog files claim-gate calls conflicting when two lanes register DIFFERENT keys."""
    with tempfile.TemporaryDirectory(prefix="catalog-merge-optimus-") as tmp:
        repo = _repo(Path(tmp), gate_root=gate_root)
        problems = _claim_gate_problems(repo, gate_root / "bin" / "claim-gate")
        return sum(rel in p for p in problems for rel in (CLASSES, METRICS))


if __name__ == "__main__":
    if "--optimus" in sys.argv:
        print(
            f"optimus.catalog.disjoint_registration_conflicts={disjoint_registration_conflicts()}"
        )
        raise SystemExit(0)
    raise SystemExit("run under pytest, or with --optimus")
