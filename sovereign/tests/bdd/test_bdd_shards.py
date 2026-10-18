"""The acceptance suite runs as shards (conftest.SB_BDD_SHARD); no test may fall between them.

A shard that is not in ci.yml's matrix is a share of the suite that no runner runs, and every
leg would still be green -- the failure mode is silence, so it is checked here, from the tree.
"""

from __future__ import annotations

import yaml

from .conftest import _RENDERERS, REPO_ROOT, shard_of

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _acceptance_shards() -> list[str]:
    job = yaml.safe_load(CI.read_text())["jobs"]["bdd-suites"]
    return [
        row["shard"]
        for row in job["strategy"]["matrix"]["include"]
        if row.get("suite") == "acceptance"
    ]


def test_every_file_lands_in_exactly_one_shard() -> None:
    counts = {f"t{i}.py": (i * 7) % 5 + 1 for i in range(40)}
    texts = {
        f: (f"bin/{_RENDERERS[-1]}" if f in ("t3.py", "t9.py") else "") for f in counts
    }
    for n in (1, 2, 3, 5):
        shard = shard_of(counts, texts, n)
        assert set(shard) == set(counts)
        assert {f for f, s in shard.items() if s == "render"} == {"t3.py", "t9.py"}
        assert set(shard.values()) <= {"render", *map(str, range(1, n + 1))}


def test_the_shares_are_even_by_test_count() -> None:
    counts = {f"t{i}.py": (i * 7) % 5 + 1 for i in range(40)}
    shard = shard_of(counts, {}, 3)
    load = [sum(c for f, c in counts.items() if shard[f] == str(k)) for k in (1, 2, 3)]
    assert max(load) - min(load) <= max(counts.values())


def test_ci_runs_the_render_shard_and_every_share() -> None:
    shards = _acceptance_shards()
    shares = [s for s in shards if s != "render"]
    assert "render" in shards, f"ci.yml runs no render shard: {shards}"
    assert shares, f"ci.yml runs no k/n share: {shards}"
    n = {int(s.split("/")[1]) for s in shares}
    assert len(n) == 1, f"the shares disagree on how many there are: {shares}"
    (total,) = n
    assert sorted(shares) == sorted(f"{k}/{total}" for k in range(1, total + 1)), (
        f"ci.yml's acceptance shards {shards} leave a share of the suite to no runner"
    )
