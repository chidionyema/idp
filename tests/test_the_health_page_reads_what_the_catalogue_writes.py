"""The portal must name the annotations and the entities a real catalogue run puts in the file.

Founder, 2026-09-07, on the Health page and the Map: every one of seventeen drills read
"Never run" while the catalogue held `estate/last-status: PASS` for some of them, and the Map
drew an empty graph. Both were one class of mistake -- the TypeScript named something the
generated catalogue does not contain -- and nothing caught it, because the unit tests beside
the code supplied their own fixtures using the same wrong names. A fixture written by the same
hand as the code cannot disagree with it.

So this runs `bin/catalog-gen` for real, over a two-row inventory, and grades the portal
against the YAML that comes out -- not against the generator's source, which would be the same
mistake one level up. The generated catalogue is not in git (`.gitignore` line 3: it is built
from this machine's inventory), which is why the run happens here.

What a real run catches that a hand-written fixture does not: the generator emits
`estate/stale: 'True'` -- Python's repr, capital T -- so any comparison against the string
`true` is false for every stale drill. That value is in the output below, and the page has to
survive it.
"""

import json
import os
import re
import subprocess
import sys

import pytest
import yaml

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "catalog-gen"
OPEN_REDS = ROOT / "backstage/packages/app/src/modules/home/openReds.ts"
NAV = ROOT / "backstage/packages/app/src/modules/nav/EstateNav.tsx"

# One repository so the drill has a product to sit in, and one drill that PASSED and is stale:
# the exact row the founder was shown as "Never run". No path on this machine is named (LAW 46).
INVENTORY = {
    "at": "2026-09-07T00:00:00Z",
    "rows": [
        {
            "kind": "repo",
            "id": "idp",
            "path": "/nowhere/idp",
            "root": "~/idp",
            "remote": "https://github.com/chidionyema/idp.git",
            "branch": "main",
            "dirty": 0,
            "tracked_files": 1,
            "coupling": "none",
            "offsite": True,
        },
        {
            "kind": "drill",
            "id": "a-drill-that-passed",
            "path": "/nowhere/idp/register.json",
            "root": "~/idp",
            "last_status": "PASS",
            "age_h": 98.6,
            "max_age_days": 2,
            "stale": True,
            "coupling": "none",
        },
    ],
}


@pytest.fixture(scope="module")
def catalogue(tmp_path_factory):
    """The entities a real `bin/catalog-gen` run writes for that inventory."""
    work = tmp_path_factory.mktemp("catalogue")
    inv = work / "inventory.json"
    inv.write_text(json.dumps(INVENTORY))
    out = work / "out"
    env = dict(os.environ, INV=str(inv), OUT=str(out), ESTATE_ENV="dev")
    run = subprocess.run(
        [sys.executable, str(GEN)], env=env, capture_output=True, text=True, timeout=300
    )
    assert run.returncode == 0, f"bin/catalog-gen refused this inventory:\n{run.stderr}"
    written = out / "catalog-info.yaml"
    assert written.exists(), "bin/catalog-gen wrote no catalog-info.yaml"
    return [d for d in yaml.safe_load_all(written.read_text()) if d]


@pytest.fixture(scope="module")
def drill(catalogue):
    rows = [
        e
        for e in catalogue
        if e.get("kind") == "Resource" and e.get("spec", {}).get("type") == "drill"
    ]
    assert len(rows) == 1, f"expected one drill entity, got {len(rows)}"
    return rows[0]


def _annotations_the_page_reads() -> set:
    """The `A` table in openReds.ts: the drill keys, apart from the door and alert ones."""
    block = re.search(r"const A = \{(.*?)\} as const;", OPEN_REDS.read_text(), re.S)
    assert block, "openReds.ts no longer names its drill annotations in one table"
    return set(re.findall(r"'(estate/[a-z-]+)'", block.group(1)))


def test_every_drill_annotation_the_health_page_reads_is_one_a_real_run_writes(drill):
    read = _annotations_the_page_reads()
    assert read, (
        "openReds.ts names no estate annotation, so it reads nothing off a drill"
    )
    written = set(drill["metadata"]["annotations"])
    unknown = sorted(read - written)
    assert not unknown, (
        f"the Health page reads {unknown}, which a catalogue run never writes on a drill; "
        f"the run wrote {sorted(written)}"
    )


def test_a_drill_that_passed_carries_a_status_and_a_staleness_the_page_reads(drill):
    """The bug in one line: a drill that PASSED was rendered red, so the page must read both."""
    ann = drill["metadata"]["annotations"]
    assert ann.get("estate/last-status") == "PASS", (
        "a drill row whose last_status is PASS no longer reaches the catalogue as PASS; "
        f"it reached it as {ann.get('estate/last-status')!r}"
    )
    read = _annotations_the_page_reads()
    for needed in ("estate/last-status", "estate/stale"):
        assert needed in read, (
            f"the Health page never reads {needed}, so it cannot grade a drill"
        )


def test_the_page_survives_the_shape_the_generator_actually_writes_staleness_in(drill):
    """`estate/stale` comes out as Python's `True`, not JSON's `true`; `=== 'true'` is a bug.

    R76: this grades the predicate, not the prose. It parses the staleness comparison out of
    openReds.ts -- the transform chain applied to the annotation and the literal it is compared
    against -- rebuilds that comparison in Python, and runs it over the value bin/catalog-gen
    actually wrote. A page that compares the raw annotation against 'true' fails here because
    the generator writes 'True'.
    """
    written = drill["metadata"]["annotations"]["estate/stale"]
    src = OPEN_REDS.read_text()

    # String(ann[A.stale]).toLowerCase() === 'true'   ->  ("tolowercase",), "true"
    m = re.search(
        r"String\(\s*ann\[A\.stale\]\s*\)((?:\.[A-Za-z]+\(\))*)\s*===\s*'([^']*)'",
        src,
    )
    assert m, (
        "openReds.ts no longer compares String(ann[A.stale]) against a literal, so the Health "
        "page's staleness predicate cannot be graded; find it and update this test"
    )
    transforms = tuple(t.lower() for t in re.findall(r"\.([A-Za-z]+)\(\)", m.group(1)))
    literal = m.group(2)

    APPLY = {"tolowercase": str.lower, "touppercase": str.upper, "trim": str.strip}
    unknown = [t for t in transforms if t not in APPLY]
    assert not unknown, (
        f"openReds.ts applies {unknown} to the annotation; this test cannot run it"
    )

    value = str(written)
    for t in transforms:
        value = APPLY[t](value)

    assert value == literal, (
        f"the catalogue writes staleness as {written!r}; the page turns that into {value!r} "
        f"and compares it against {literal!r}, so a stale drill never reaches the founder as red"
    )


def test_every_root_the_map_draws_from_is_a_domain_a_real_run_writes(catalogue):
    block = re.search(r"MAP_ROOTS = \[(.*?)\]", NAV.read_text(), re.S)
    assert block, "EstateNav.tsx names no roots for the Map, so the graph draws nothing"
    roots = set(re.findall(r"'domain:default/([a-z0-9-]+)'", block.group(1)))
    assert roots, "MAP_ROOTS is empty, which is the empty graph the founder was shown"
    domains = {e["metadata"]["name"] for e in catalogue if e.get("kind") == "Domain"}
    missing = sorted(roots - domains)
    assert not missing, (
        f"the Map is rooted on {missing}; a run writes {sorted(domains)}"
    )
    left_out = sorted(domains - roots)
    assert not left_out, f"a run writes domains the Map leaves out: {left_out}"
