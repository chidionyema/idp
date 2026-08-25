# Onboarding — the sovereign bus (`sb`)

`sb` is the one command for durable agent sessions: start, stop, approve, steer and audit them from the laptop, the phone (Otto's pinned card and the cockpit Mini App) or Windows (`bin/sb-windows.ps1`).

## Once

1. `cd ~/dev/code/idp && python3 -m venv sovereign/.venv && sovereign/.venv/bin/pip install -r sovereign/requirements.txt`
2. `brew install temporal` (Windows: `winget install Temporal.CLI`).
3. Set `ESTATE_HOME` (default `~/.estate`). Every other setting has a default; see `bin/sb config`.
4. Install the launchd jobs from `launchd/ai.estate.temporal.plist.tmpl`, `ai.estate.sovereign-worker.plist.tmpl` and `ai.estate.cockpit.plist.tmpl` with `bin/idp-apply`.
5. For the phone: `bin/sb install-plugin` symlinks the Otto plugin into `$HERMES_HOME/plugins`; `bin/sb menu` registers the cockpit Mini App (needs `ESTATE_PUBLIC_URL`).

## Every day

- `bin/sb start --runner claude --task '…' --budget 20000` starts a session. `--runner llm` routes through LiteLLM; vendor names live only in `sovereign/engine/runners.py`.
- `bin/sb list`, `bin/sb show <id>`, `bin/sb stop|approve|deny|steer <id> --by <who>`.
- `bin/sb attach <repo>` mounts any repository as an estate and scaffolds its `AGENTS.md`; `bin/sb status`, `bin/sb halt --all`.
- `bin/sb audit --verify` walks the signed receipt chain; `bin/sb episodes --kind stop` reads what happened.
- `bin/sb config --json`, `bin/sb config set <key> <value>`, `bin/sb config --lint` (must print 0).
- `bin/sb root --json` shows the shadow root (`.estate/heads/shadow_main`): the DAG node cp8's sidecar last wrote, and whether the chain from there to genesis still verifies.
- `sovereign.sidecar.dualread.read(conn, table, rowid)` runs a read against both the legacy DB and the DAG, records a `dualread` receipt, and returns the legacy answer; `dualread.max_overhead_ms` caps the added p95 cost.
- `bin/sb consensus --json` reports the running legacy/DAG match rate; a mismatch also lands in the cockpit Inbox (`/api/inbox`) as a `consensus_mismatch` alert -- it never blocks the read or stops a service.
- `bin/sb rebuild --by <who> --json` replays the whole DAG from genesis and rewrites the projection store (`projection.store_path`); `sb up` runs the same check at boot and rebuilds automatically whenever the store's own root has fallen behind the current DAG head.

## When it breaks

- `sb show` prints `status=unknown`: the worker is down. `bin/sb up` restarts it; the session resumes where it stopped.
- `budget required`: set `SB_DEFAULT_BUDGET` or pass `--budget`.
- `ok=False` from `audit --verify`: the chain was edited or cut. The receipt file is evidence; do not repair it, read `first_broken_counter`.

Feature files: `features/sovereign-bus/cp1…cp35`. Ticket: crew#213.
