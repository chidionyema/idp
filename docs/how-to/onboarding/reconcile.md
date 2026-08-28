# Reconcile: running state equals git state

`bin/idp-reconcile` is crew#186 CP3 (R22 mechanism 3). The manifest is the set
of compose files named in `catalog/reconcile.yaml`; anything docker runs that no
manifest, allowed foreign project or name prefix owns is drift.

| Command | Does |
|---|---|
| `bin/idp-reconcile` | report; exit 1 on any drift, one line per finding |
| `bin/idp-reconcile --fix` | remove rogue containers, re-run every idp compose file with `--remove-orphans`, append to `run/reconcile.jsonl` |
| Dagster job `ai.idp.reconcile` | runs `--fix` every 10 minutes; open the run in the scheduler UI to see what it removed |

Drift classes: `rogue` (nothing owns it), `config-path` (an idp project started
from a compose file outside this checkout, for example a worktree), `stale`
(started from an idp compose file that is no longer in the manifest).

Proof, 2026-08-24: `docker run -d --name rogue-cp3 ...` then `--fix` removed it
and logged it; the same tick moved `mcp-github` from a worktree's compose file
back onto `mcp/agentgateway.yml`. `bin/idp-ci` row `reconcile` proves the rogue
fixture fails and the clean fixture passes on every run.

To allow a container that is not in an idp compose file, add a row to
`catalog/reconcile.yaml` with a reason. There is no other way past it.
