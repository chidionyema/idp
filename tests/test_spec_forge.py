import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_l = importlib.machinery.SourceFileLoader("sf", str(ROOT / "bin" / "spec-forge"))
_s = importlib.util.spec_from_loader("sf", _l)
sf = importlib.util.module_from_spec(_s)
_l.exec_module(sf)

SEED = {
    "slug": "demo-gate",
    "title": "Demo gate",
    "date": "2026-10-31",
    "area": "gates",
    "why": "A demo.",
    "scenarios": [
        {
            "name": "Refuses",
            "given": ["x"],
            "when": ["y happens"],
            "then": ["it refuses"],
        }
    ],
    "proof": "python3 -m pytest tests/test_spec_demo_gate.py -q",
}


def test_same_seed_gives_same_bytes_and_digest():
    assert sf.outputs(SEED) == sf.outputs(SEED)
    assert sf.digest(sf.outputs(SEED)) == sf.digest(sf.outputs(dict(SEED)))


def test_invalid_seeds_are_named():
    bad = dict(
        SEED, scenarios=[{"name": "n", "when": [], "then": ["t"]}], slug="Bad Slug"
    )
    e = sf.validate(bad)
    assert any("slug" in x for x in e) and any("when" in x for x in e)


def test_written_files_bind_and_pass_their_own_test(tmp_path):
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps(SEED))
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "spec-forge"),
            "write",
            str(seed),
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout
    t = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            str(tmp_path / "tests" / "test_spec_demo_gate.py"),
        ],
        capture_output=True,
        text=True,
    )
    assert t.returncode == 0, t.stdout
    again = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "spec-forge"),
            "write",
            str(seed),
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert again.returncode == 0


def test_it_refuses_to_overwrite_different_content(tmp_path):
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps(SEED))
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "spec-forge"),
            "write",
            str(seed),
            "--root",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
    )
    (tmp_path / "features" / "gates" / "demo-gate.feature").write_text("edited")
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "bin" / "spec-forge"),
            "write",
            str(seed),
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1 and "REFUSED" in r.stdout


def test_from_edge_seeds_a_valid_spec_from_the_flow_model():
    s = sf.from_edge("vision", "intent")
    assert s and sf.validate(s) == []
    assert sf.from_edge("nope", "nada") is None


def test_lint_names_missing_boundary_classes_and_unknown_tags():
    s = dict(
        SEED,
        scenarios=[
            dict(SEED["scenarios"][0], boundary="empty"),
            dict(SEED["scenarios"][0], boundary="nonsense"),
        ],
    )
    cov, miss, unk = sf.boundary_gaps(s)
    assert cov == ["empty"] and "tamper" in miss and unk == ["nonsense"]
    full = dict(
        SEED, scenarios=[dict(SEED["scenarios"][0], boundary=b) for b in sf.BOUNDARIES]
    )
    assert sf.boundary_gaps(full)[1:] == ([], [])
