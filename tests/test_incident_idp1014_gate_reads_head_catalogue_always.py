"""Incident, 2026-08-30: the operating-model gate refused idp#1014 with
`Drill: otto-parity names no entry in drills/catalogue.yaml` although the branch carried the row.

bin/pr-report fetched the PR-head catalogue only when the PR's OWN diff touched
drills/catalogue.yaml. idp#1014 was stacked on edcf54d4 (#1013), which added the otto-parity row,
so #1014's diff did not touch the catalogue; the gate judged against main at f92233e4, which did
not yet hold the row, and refused correct work (LAW 38). Run 33330388899.

The head copy is now fetched unconditionally by bin/idp-pr-catalogues. Proved both ways against a
fake gh: the stacked shape resolves two catalogues, and an unfetchable head degrades to main alone
without failing the gate. Rung 4.
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "idp-pr-catalogues"
NAMES = ROOT / "bin" / "idp-drill-names"

HEAD_SHA = "edcf54d4edcf54d4edcf54d4edcf54d4edcf54d4"


def fake_gh(tmp_path: Path, *, head_catalogue: str | None) -> Path:
    """A gh that answers the three calls idp-pr-catalogues makes. head_catalogue None = the
    contents call fails, standing for no network or no such path on that ref."""
    d = tmp_path / "bin"
    d.mkdir(exist_ok=True)
    body = tmp_path / "head.yaml"
    if head_catalogue is not None:
        body.write_text(head_catalogue)
    gh = d / "gh"
    gh.write_text(
        "#!/usr/bin/env bash\n"
        'case "$1 $2" in\n'
        '  "pr view") echo "%s" ;;\n'
        '  "repo view") echo "chidionyema/idp" ;;\n'
        '  "api repos/chidionyema/idp/contents/drills/catalogue.yaml?ref=%s") %s ;;\n'
        "  *) exit 1 ;;\n"
        "esac\n"
        % (
            HEAD_SHA,
            HEAD_SHA,
            f'cat "{body}"' if head_catalogue is not None else "exit 1",
        )
    )
    gh.chmod(0o755)
    return d


def run(
    tmp_path: Path, ghdir: Path, idp: Path, out: Path
) -> subprocess.CompletedProcess:
    env = {"PATH": f"{ghdir}:/usr/bin:/bin", "HOME": str(tmp_path)}
    return subprocess.run(
        [str(TOOL), "1014", str(idp), str(out)],
        capture_output=True,
        text=True,
        env=env,
    )


def _idp_root(tmp_path: Path, main_catalogue: str) -> Path:
    idp = tmp_path / "idp"
    (idp / "drills").mkdir(parents=True)
    (idp / "drills" / "catalogue.yaml").write_text(main_catalogue)
    return idp


def test_incident_stacked_pr_resolves_the_head_catalogue_though_its_diff_does_not_touch_it(
    tmp_path: Path,
) -> None:
    # main at f92233e4: no otto-parity row. The PR's own diff touches no catalogue at all.
    idp = _idp_root(tmp_path, "drills:\n  - name: oke-check\n  - name: login-drill\n")
    head = (
        "drills:\n  - name: oke-check\n  - name: login-drill\n  - name: otto-parity\n"
    )
    out = tmp_path / "pr-catalogue.yaml"
    r = run(tmp_path, fake_gh(tmp_path, head_catalogue=head), idp, out)
    assert r.returncode == 0, r.stdout + r.stderr

    paths = r.stdout.split()
    assert len(paths) == 2, r.stdout
    assert paths[0] == str(idp / "drills" / "catalogue.yaml")
    assert paths[1] == str(out)

    # the incident shape: main alone cannot see the row the branch carries
    main_only = json.loads(
        subprocess.run(
            [str(NAMES), paths[0]], capture_output=True, text=True, check=True
        ).stdout
    )
    assert "otto-parity" not in main_only

    # the fixed shape: the gate's drill list holds it, so drill_named passes
    both = json.loads(
        subprocess.run(
            [str(NAMES), *paths], capture_output=True, text=True, check=True
        ).stdout
    )
    assert "otto-parity" in both


def test_unfetchable_head_catalogue_degrades_to_main_and_is_named(
    tmp_path: Path,
) -> None:
    idp = _idp_root(tmp_path, "drills:\n  - name: oke-check\n")
    out = tmp_path / "pr-catalogue.yaml"
    r = run(tmp_path, fake_gh(tmp_path, head_catalogue=None), idp, out)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.split() == [str(idp / "drills" / "catalogue.yaml")]
    assert "head catalogue skipped" in r.stderr
