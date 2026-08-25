# Demo — the sovereign bus (`sb`)

Recorded 2026-08-25 from `scratchpad/phase1.sh` on commit 3141eeb. Tokens and keys are never printed.

Start the engine, then a session, and read it back:

    $ bin/sb up
    {'temporal': 'started pid=83662', 'worker': 'started pid=83669'}
    $ bin/sb start --runner echo --task 'count to 5' --json
    $ bin/sb show sb-… --json
    status=done step=1 budget_remaining=998

Stop a session while the worker is dead. The stop is durable: the worker picks it up when it returns.

    $ bin/sb stop sb-… --by founder --reason 'laptop asleep' --json
    ok=True
    $ bin/sb show sb-… --json
    status=stopped stopped_by=founder

A session that needs a dangerous command waits for a decision. Deny, approve, or say nothing:

    status=waiting asking=git push --force
    status=denied
    status=done
    status=waiting

The budget wall halts a session at zero tokens and signs the halt:

    $ bin/sb start --runner burn --task burn --budget 100 --json
    status=halted reason=budget budget_remaining=0
    kind=halt counter=12 backend=keychain

The receipt chain catches an edit, a deleted middle, and a cut-off tail:

    $ bin/sb audit --verify --json
    ok=True count=12
    ok=False first_broken_counter=3
    ok=False

Every setting is one table:

    $ bin/sb config --json | python3 -c '…print(len(d))'
    180
    $ bin/sb config --lint
    0

The cockpit serves the same sessions the CLI lists, and refuses a bad Telegram signature:

    healthz: ok
    sessions match sb list
    bad initData -> 401

## Phase 2 — the DB sidecar and the shadow root (cp8, cp9)

Recorded 2026-08-25 on a disposable estate, `sidecar.target` pointed at a throwaway sqlite file. The sidecar sits on maestro's `episodes` table (`sidecar.target` in `bin/sb config --json`) via `sovereign.sidecar.attach(conn, "episodes")`; every drained write appends one Merkle DAG node, one `sidecar_write` receipt, and advances `.estate/heads/shadow_main`:

    $ bin/sb config --json | python3 -c "import json,sys; print(json.load(sys.stdin)['sidecar.target'])"
    /Users/…/.maestro/experience_graph.db#episodes
    $ bin/sb root --json
    {"nodes": 3, "parent": "d06f199642e…", "root": "62c576b6692…", "verified": true}

If the DAG directory goes read-only mid-write the legacy write still lands; the sidecar catches up and flags the gap once it can write again:

    missed=1, no sidecar_write receipt yet
    (permissions restored)
    sidecar_degraded receipt: {"missed": 1, "table": "episodes"}

## Phase 2 — dual-read router (cp10)

Every read runs twice -- legacy DB, then the DAG walk from `shadow_main` -- and a `dualread` receipt records both hashes and both latencies. 1000 drained reads, measured 2026-08-25 on a disposable estate: p50 2.41ms, p95 4.57ms, p99 5.80ms overhead, all under `dualread.max_overhead_ms` (15ms default). An undrained row (write not yet drained into the DAG) is reported as a real mismatch, never a silent pass.

## Phase 2 — consensus check (cp11)

A dual-read mismatch is an alert, never a freeze -- one `consensus_mismatch` line lands in the cockpit's existing Inbox (`ESTATE_ALERT_INBOX`, served at `/api/inbox`) with both hashes and the query, and the caller still gets the legacy answer, unblocked:

    $ bin/sb consensus --json
    {"matches": 1, "mismatches": 1, "rate": 0.5, "reads": 2}
    $ cat $ESTATE_HOME/alerts/inbox.jsonl
    {"kind": "consensus_mismatch", "table": "episodes", "rowid": 2, "query": {"table": "episodes", "rowid": 2}, "legacy_hash": "69d8071…", "dag_hash": "bf81b47…", "ts": 1787631765.74}

## Phase 2 — AI sandbox / zero-cost forks (cp12)

A fork is a second head pointer under `.estate/heads/<name>`, copied from `shadow_main`'s current root -- one small JSON file, never a row of the legacy DB. Measured 2026-08-25 on a disposable estate:

    $ bin/sb fork staging --json
    {"elapsed_ms": 0.9058319992618635, "name": "staging", "root": null, "storage": "memory"}
    $ cat $ESTATE_HOME/.estate/heads/staging
    {"root": null, "storage": "memory"}

Writes an agent makes against a fork's own connection (`sovereign.engine.fork.attach_sidecar(name, table)`) advance that fork's own root and chain into that fork's own receipts file (`fork.fork_receipts_paths(name)`) -- `sovereign.engine.receipts.append()`/`verify()` and `sovereign.engine.shadow_root.update_head()`/`verify()` all take the fork's paths as overrides now, so production's `shadow_main` and `receipts.jsonl` never move. The cap is a key, `fork.max_parallel` (default 3): the 4th fork open at once gets `"storage": "disk"` (`fork.dir`) instead of an in-memory connection, never a code change.

    $ bin/sb switch staging --json
    {"working": "staging"}
    $ bin/sb drop staging --json
    {"dropped": "staging"}

`drop` removes only the pointer file; every DAG node and receipt line the fork ever wrote stays on disk, archived -- deleting a Merkle DAG node another branch's history might still reference is exactly the class of edit a hash chain exists to catch.
