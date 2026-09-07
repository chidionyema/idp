"""The portal must name the annotations and the entities the generator actually writes.

Founder, 2026-09-07, on the Health page and the Map: every one of seventeen drills read
"Never run" while the catalogue held `estate/last-status: PASS` for some of them, and the Map
drew an empty graph. Both were one class of mistake -- the TypeScript named something the
generated catalogue does not contain -- and nothing caught it, because the unit tests beside the
code supplied their own fixtures using the same wrong names.

The generated catalogue is not in git (`.gitignore` line 3: it is built from this machine's
inventory), so the thing to grade against is its generator, `bin/catalog-gen`, which is. Rename a
key there and this test goes red before the portal does.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "catalog-gen"
OPEN_REDS = ROOT / "backstage/packages/app/src/modules/home/openReds.ts"
NAV = ROOT / "backstage/packages/app/src/modules/nav/EstateNav.tsx"


def _drill_annotations_the_generator_writes() -> set:
    """The keys catalog-gen puts on a drill Resource, prefixed the way it emits them.

    Two facts from the generator, both read here rather than restated: the `elif k == "drill":`
    branch names the keys, and the emit step prefixes any key without a slash with `estate/`.
    """
    src = GEN.read_text()
    branch = re.search(r'elif k == "drill":(.*?)\n        elif ', src, re.S)
    assert branch, (
        "bin/catalog-gen no longer has a drill branch; this test is looking at nothing"
    )
    keys = set(re.findall(r'"([a-z-]+)":', branch.group(1)))
    assert keys, "the drill branch sets no annotations"
    prefix = re.search(r"k if '/' in k else '(estate/)' \+ k", src)
    assert prefix, "bin/catalog-gen no longer prefixes its own annotations with estate/"
    return {prefix.group(1) + k for k in keys}


def _drill_annotations_the_page_reads() -> set:
    """The `A` table in openReds.ts: the drill keys, apart from the door and alert ones."""
    block = re.search(r"const A = \{(.*?)\} as const;", OPEN_REDS.read_text(), re.S)
    assert block, "openReds.ts no longer names its drill annotations in one table"
    return set(re.findall(r"'(estate/[a-z-]+)'", block.group(1)))


def test_every_drill_annotation_the_health_page_reads_is_one_the_generator_writes():
    read = _drill_annotations_the_page_reads()
    assert read, (
        "openReds.ts names no estate annotation, so it reads nothing off a drill"
    )
    written = _drill_annotations_the_generator_writes()
    unknown = sorted(read - written)
    assert not unknown, (
        f"the Health page reads {unknown}, which bin/catalog-gen never writes on a drill; "
        f"it writes {sorted(written)}"
    )


def test_the_health_page_reads_the_status_and_the_staleness_at_least():
    """A drill row that ignored last-status would call a passing drill red, which is the bug."""
    read = _drill_annotations_the_page_reads()
    for needed in ("estate/last-status", "estate/stale"):
        assert needed in read, (
            f"the Health page never reads {needed}, so it cannot grade a drill"
        )


def test_every_root_the_map_draws_from_is_a_domain_the_generator_defines():
    block = re.search(r"MAP_ROOTS = \[(.*?)\]", NAV.read_text(), re.S)
    assert block, "EstateNav.tsx names no roots for the Map, so the graph draws nothing"
    roots = re.findall(r"'domain:default/([a-z0-9-]+)'", block.group(1))
    assert roots, "MAP_ROOTS is empty, which is the empty graph the founder was shown"
    companies = re.search(r"^COMPANIES = \{(.*?)^\}", GEN.read_text(), re.S | re.M)
    assert companies, "bin/catalog-gen no longer has a COMPANIES table"
    defined = set(re.findall(r'^    "([a-z0-9-]+)":', companies.group(1), re.M))
    missing = sorted(set(roots) - defined)
    assert not missing, (
        f"the Map is rooted on {missing}; catalog-gen defines {sorted(defined)}"
    )
    assert defined - set(roots) == set(), (
        f"catalog-gen defines domains the Map leaves out: {sorted(defined - set(roots))}"
    )
