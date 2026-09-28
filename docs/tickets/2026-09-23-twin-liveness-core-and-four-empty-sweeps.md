# estate-twin-runtime — the liveness core is load-bearing, and 4 sweeps around it produce nothing

**Status:** open
**Opened:** 2026-09-23
**Laws:** LAW 0 (one of each layer), LAW 2 (proof, not assertion),
LAW 28 (a verdict that cannot fail the run is not a verdict),
and the standing defect class measured all day: *claim without enforcement*
**Source:** measured 2026-09-23 against `catalog/estate.db` (774,144 bytes) on this machine
**Module:** `bin/estate-twin-runtime` (2,423 lines), `tests/test_estate_twin_domains.py` (114),
`mcp/plugins/estate_twin.py` (563)
**Depends on:** nothing — every finding below is self-contained

---

## What is worth keeping, measured

The twin is the **only** thing in the estate that records pod liveness with history. Nothing else
can answer "what died, and when":

```
$ bin/estate-twin-runtime --dead
  [UNKNOWN] runtime: never read; no freshness row exists
  crashlooping  k8s:pod:kube-system:coredns-8b9777675-8blz6 restarts=7 age=177m
  crashlooping  k8s:pod:kube-system:metrics-server-854c559bd-t2zlx restarts=10 age=177m
  crashlooping  k8s:pod:kube-system:traefik-54c4f4ffd8-tlkgk restarts=7 age=177m
```

Three crashlooping pods, named, with `crashlooping` distinct from `dead`. The distinction is
deliberate and documented in the file:

> "A pod whose phase is Succeeded finished its work. It is not running and it is not a failure;
> reporting it as `dead` is how a dead list becomes 215 rows of finished Dagster runs and stops
> being read."

`sync-cluster` (estate-graph) records **structure** — Deployments, Services, Namespaces,
HelmReleases. It cannot name a dead pod. **The liveness job is unique and it earns its place.**

---

## What produces nothing, measured

Each sweep run with `--once <flag>` on 2026-09-23, counting rows added to `nodes`:

| sweep | lines | rows added | wall time |
|---|---|---|---|
| `--code` | ~135 | **+0** | **timed out at 50s** |
| `--domains` | ~498 | — | **timed out at 50s** |
| `--linear` | ~110 | **+0** | 1s |
| `--code-graph` | ~280 | +67 | 6s |

And the graph the sweeps wrote, by node type:

| type | rows |
|---|---|
| `module` | **602** |
| `network-allowance` | 97 |
| `spend` | 19 |
| `pod` | **5** |
| `deployment` | **4** |
| `worktree` | 3 |
| `spiffe-workload`, `session`, `pipeline`, `database`, `summary`, `stream` | 1 each |

**No reader queries `module`, `worktree`, or `linear`.** `rg -n "type *= *['\"](issue|linear|module|worktree)"`
over `bin/` and `mcp/` returns no query.

So: **602 of the graph's rows are a code graph nothing reads**, and the twin's own job —
pods and deployments — is **9 rows**.

---

## Defect 1 — the guard collects zero tests

`tests/test_estate_twin_domains.py` is named as a test, sits in `tests/`, and its docstring says
*"This is the test the emitter must make pass. It is written first, and it fails today."*

```
$ python3 -m pytest -q tests/test_estate_twin_domains.py
no tests ran in 3.04s
```

**Zero `def test_` functions.** It is a script with a `main()` and an `if __name__ == "__main__"`
block. Consequences, both measured:

1. `bin/idp-ci` runs `pytest tests/` → collects **nothing** from it → **passes**.
2. Nothing else invokes it: `rg -n "test_estate_twin_domains"` finds only its own docstring and
   one onboarding doc. **No workflow, no hook, no rung.**

**2,986 lines of the estate's actual-state observer are guarded by a file that executes nothing.**

Why `bin/test-executes-gate` did not catch it — line 68:

```bash
git diff --name-only --diff-filter=A "$BASE...HEAD" -- 'tests/*.py'
```

**It grades only files ADDED in the diff.** This file was added 2026-09-13; it is in no diff, so
it is never re-checked. A gate scoped to the diff cannot see a pre-existing defect — see the
companion ticket for the general form.

## Defect 2 — the status vocabulary is claimed closed and is not enforced

`bin/estate-twin-runtime:57`:

> "Status vocabulary. These are the only three a node may carry; a fourth would be a status no
> reader knows how to render, which is the class of thing this file exists to end."

```python
ACTIVE = "active"
DEAD = "dead"
CRASHLOOPING = "crashlooping"
FINISHED = "finished"      # <- the fourth
```

The comment says three; the code defines four; **nothing asserts either.** There is no
`assert status in {...}`, no `raise`, no test. A fifth status written by any future edit ships
silently — which is precisely what the comment says the file exists to prevent.

The test that was supposed to hold this, `tests/test_estate_twin_rule.py`, is referenced at
line 1087 and is on **no branch** (`git cat-file -e origin/main:tests/test_estate_twin_rule.py`
fails; it appears only in two abandoned history entries).

---

## Why this is not "delete the twin"

The same day the estate ruled on the second-copy pattern, inside this very file (line ~1085):

> "Until 2026-09-22 `bin/catalog-dark-matter` ran a **second implementation** over the same git
> state into a committed `dark-matter.json` … the committed file said **648** and the fresh scan
> said **77**. Two implementations of one measurement is the second copy the estate deletes, and
> the graders went with it."

That ruling applies to **sweeps that duplicate a tool that exists**, not to the liveness job:

- `sweep_linear` → `bin/idp-linear-dispatch` exists, and this sweep writes **+0 rows**
- `sweep_code_graph` → 602 `module` rows no reader queries

The liveness core has no duplicate and is the only source of pod history. **Keep it; cut around it.**

---

## What this ticket asks for

1. **Make the guard real.** Either give `tests/test_estate_twin_domains.py` actual `def test_`
   functions (its logic is already in `main()`), or rename it out of `tests/` so it stops
   looking like a guard. Leaving it named `test_*` while collecting nothing is the defect.
2. **Enforce the vocabulary.** One check at the write path — `upsert()` is the single seam — that
   refuses a status outside the closed set, plus the test that proves a fifth is refused. Then the
   comment and the code can no longer disagree.
3. **Decide the four sweeps on their own tickets**, with the numbers above: `--code` (0 rows,
   >50s), `--domains` (>50s), `--linear` (0 rows, duplicates a tool), `--code-graph` (67 rows,
   no reader). Each is either wired to a reader or removed — not left producing into the void.
4. **Widen `bin/test-executes-gate`** to scan all of `tests/*.py`, not only added files. Until
   that lands, every pre-existing empty test in the estate is invisible.

## Evidence

- `bin/estate-twin-runtime --dead` → 3 crashlooping pods, named (output above)
- `sqlite3 catalog/estate.db "select type, count(*) from nodes group by type"` → table above
- `python3 -m pytest -q tests/test_estate_twin_domains.py` → `no tests ran in 3.04s`
- `rg -n "test_estate_twin_domains"` → docstring + one onboarding doc, no caller
- `git cat-file -e origin/main:tests/test_estate_twin_rule.py` → absent
- Per-sweep node deltas and wall times → table above, each run this session

**Nothing in this ticket is inferred from a file name or a date.** Every row was produced by
running the thing and counting, or by the ripgrep named beside it.
