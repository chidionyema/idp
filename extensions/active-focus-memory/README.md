# active-focus-memory — every session starts from the estate's bi-temporal truth

An agent's context window is not memory. The founder's standing instructions, the facts the estate
has proven, and the actions already known to fail were being re-derived by every session, and
re-derived wrongly. This extension compiles the Active Focus register — under 1,200 tokens — into
the session, from `bin/estate-memory-engine`.

## What it does

On the `context` event it prepends one system message containing the register:

- **ACTIVE FOUNDER INSTRUCTIONS** — the most recent instructions from
  `~/.estate/instructions/ledger.jsonl`.
- **CURRENT ESTATE FACTS** — rows of `bitemporal_facts` whose `valid_to_ts IS NULL`. A superseded
  fact is retained with `valid_to_ts` set rather than deleted, so the register shows what is true
  now and the history stays queryable.
- **COUNTERFACTUAL GRAVEYARD** — failed actions with their remediation hint and hit count, so the
  same dead end is not rediscovered.

## Why the `context` event

The SDK's `ExtensionAPI` exposes `on("context", handler)`, whose result is
`{ messages?: AgentMessage[] }`. There is no `appendSystemContext()`; an extension calling one
would throw at session start. The hook is registered as a directory (`index.ts`) because pi loads
extensions as directories — a loose `.ts` file under `~/.pi/agent/extensions/` never loads.

## Why the header appears exactly once

The `context` event can fire more than once per session. The handler scans the live message list for
the marker before inserting, rather than trusting a module-level flag, so a session that compacts
and loses the header gets it back — and a normal session never accumulates copies.

## Why a failed render is not an error

Memory is an optimisation, never a blocker. If the engine is missing, the database is locked, or
`sqlite3` is unavailable, the session proceeds without the header. A hook that refused a session
because memory could not be read would make the estate's own memory surface an outage, which is the
recovery-path-depends-on-what-it-recovers failure (R6).

## The budget is measured, not guessed

`render-focus` costs ~1.3 s (a bounded ledger tail plus three indexed queries) and the hook allows
4 s. An earlier version allowed 2.5 s against a 3.9 s render, which meant the header was injected
**never** — silently, because the failure path is "return no header". The engine now reads a bounded
tail of the ledger instead of all 9.3 MB of it, which is what made the render 3x faster.

## Installing

```bash
mkdir -p ~/.pi/agent/extensions/active-focus-memory
cp extensions/active-focus-memory/index.ts ~/.pi/agent/extensions/active-focus-memory/index.ts
```

The tracked copy here is the source of record; `~/.pi/agent/extensions/` is the deployment target.

## Proof

`tests/test_active_focus_hook.py` executes the shipped hook against a fake `pi` and asserts it
registers `on("context")`, injects the marker, and injects only once — and that the engine really
prints the marker the guard searches for. It does not read the file and assert on its text.
