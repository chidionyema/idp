# Onboarding: keeping the session engine vendor-agnostic

Founder ruling, 2026-09-15: "this is idiotic, nothing claude-code specific should exist, we
are building enterprise model agnostic, gut it out" -- said of a proposal that parsed Claude
Code's own local file format directly inside the engine. `sovereign/CONTRACT.md:41` already
states the invariant this gate makes structural: "Registry is the ONLY place a vendor name
appears; engine/workflow.py and engine/client.py import no vendor." This page is what that
means when you touch `sovereign/engine`.

## Where a vendor may be named

- `sovereign/engine/runners.py`: the `REGISTRY` dict. A runner is added as one entry
  (`"acme": _acme`), keyed by a plain string; nothing else in the engine branches on that
  string.
- `sovereign/engine/adapters/`: a real vendor CLI wrapper (subprocess invocation, response
  parsing) lives here, one file per vendor, imported only by the registry entry that names it.

Everywhere else in `sovereign/engine` -- `workflow.py`, `client.py`, `activities.py` and any
new file added beside them -- takes a runner name as an opaque string and never inspects,
compares or branches on which vendor it names.

## What the gate refuses

`bin/vendor-agnostic-gate` scans `sovereign/engine/**/*.py` for the tokens `claude` or
`anthropic` (case-insensitive, so it also catches `.claude` as a path fragment), skipping
comment lines, `runners.py` and anything under an `adapters/` directory. It prints every
offending line and exits 1; `bin/idp-ci` runs it on every pull request after proving it on
`tests/fixtures/vendor-agnostic/{good,bad}`.

## How to add a new provider

Write the runner function and add one line to `REGISTRY` in `runners.py`
(`"acme": _acme`); if it wraps a real CLI or SDK, put that wrapper under
`sovereign/engine/adapters/`. Nothing in `workflow.py` or `client.py` changes --
`sovereign/tests/bdd/test_cp6_provider_agnostic.py`'s last scenario proves exactly this by
registering a throwaway `"acme"` runner at test time and running a step through it with no
other code touched.
