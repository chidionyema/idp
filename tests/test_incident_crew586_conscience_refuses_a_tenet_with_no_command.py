"""crew#586 CP1: a tenet without a measure command is refused (LAW 44), and the score is a receipt.

Both ways: the good fixture scores 2/2 and exits 0, the bad fixture 1/2 and exits 1, the
fixture with no `measure` exits 2 naming LAW 44 and writes no receipt.
"""
import json
import os
import pathlib
import subprocess
import sys

IDP = pathlib.Path(__file__).resolve().parents[1]
FX = IDP / "tests" / "fixtures" / "conscience"


def run(fixture: str, tmp_path: pathlib.Path):
    rep = tmp_path / f"{fixture}.json"
    p = subprocess.run([sys.executable, str(IDP / "bin" / "idp-conscience")], capture_output=True, text=True,
                       env={**os.environ, "CONSCIENCE_TENETS": str(FX / f"{fixture}.yaml"), "CONSCIENCE_REPORT": str(rep)})
    return p, rep


def test_good_scores_all_green(tmp_path):
    p, rep = run("good", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert json.loads(rep.read_text())["score"] == {"green": 2, "total": 2}


def test_bad_scores_one_red(tmp_path):
    p, rep = run("bad", tmp_path)
    assert p.returncode == 1, p.stdout + p.stderr
    r = json.loads(rep.read_text())
    assert r["score"] == {"green": 1, "total": 2} and r["tenets"][1]["value"] == 0


def test_tenet_with_no_command_is_a_wish(tmp_path):
    p, rep = run("wish", tmp_path)
    assert p.returncode == 2 and "LAW 44" in p.stderr
    assert not rep.exists()


def test_real_tenets_each_carry_a_command():
    import yaml
    rows = yaml.safe_load((IDP / "conscience" / "tenets.yaml").read_text())["tenets"]
    assert len(rows) == 16  # 7 ethos rows + 9 engineering rows (crew#584)
    assert all(r["measure"] and r["ethos"] and r["pr_rule"] for r in rows)
