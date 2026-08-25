# sovereign/engine (owner: builder A)

A Temporal workflow (`workflow.py: SessionWorkflow`) is one agent session:
durable across a worker crash (cp1), a `stop` applies even while the
worker was down (cp2), an approval gate parks in `waiting` and never
proceeds on silence (cp3), and it halts at zero token budget until a
signed `refill` (cp18). `client.py` is the only module B/C import from
here -- plain dicts only, every query time-boxed so one stuck session can
never hang `sb list`.

- `workflow.py` — the state machine: steps, budget, approvals. No vendor
  import, no I/O; side effects are activities, called by string name, so
  it stays out of the cp6 grep and the Temporal sandbox. Tuning rides in
  on `params`, resolved by `client.py` from `sovereign/config.py`.
- `activities.py` — `run_step` (`runners.py`), `append_receipt` (adds
  `state_hash`), `notify_change` (Langfuse + best-effort `otto.card`).
- `runners.py` — the only file with a vendor name (`claude`) or a model
  gateway path. Registry: `echo`, `sleep`, `ask`, `burn`, `claude`, `llm`;
  each returns a `tokens` spend estimate. `worker.py` runs one
  `temporalio.worker.Worker` on the `sovereign` queue.
- `receipts.py` — a signed hash chain (cp19): counter, prev_hash, an HMAC
  sig under an estate key in the macOS Keychain (0600-file fallback,
  `backend` records which); `sb verify-receipts` walks it.
- `tracing.py` — Langfuse, a no-op if `LANGFUSE_*` is unset.

## Run it

```
bin/sb up
bin/sb start --runner echo --task 'hi' --budget 1000 --json
bin/sb show <session_id> --json
bin/sb down
```

## Prove it

`features/sovereign-bus/cp1_*.feature` through `cp3`, `cp6`, `cp18`,
`cp19`, `cp22` are the acceptance specs; each names its own `bin/sb`
commands, not restated here so this file can never match the grep checks
it describes.
