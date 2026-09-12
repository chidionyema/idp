# Onboarding: the gate demo pages

## What it is for

Every rule in `rules.yaml` is a gate that refuses something. This renders one page per rule
into `docs/gates/`, carrying the gate's own output for its refusing and permitting cases. It
answers "what does this gate actually do" with the gate's own words rather than a description
of them, and it is how a buyer or a new engineer sees that the estate's guards work.

## What it costs

Nothing to run and nothing at rest: it is a local Python script that runs the gates against
their committed fixtures. A full render runs each gate twice and takes minutes, because it is
really running 65 gates. Nothing is deployed.

## Where it lives

| | |
|---|---|
| the generator | `bin/idp-gate-demo` |
| the pages | `docs/gates/<rule-id>.md`, plus `index.md` |
| the registry it reads | `rules.yaml` |
| the runner it reuses | `bin/idp-rules` |
| the tests | `tests/test_gate_demo.py` |
| the nav | `mkdocs.yml`, the "Gates" section |

## How to run it

```bash
bin/idp-gate-demo --out docs/gates           # render
bin/idp-gate-demo --out docs/gates --check   # CI-style: exit 1 when stale
bin/idp-gate-demo --only grader-exit         # one page while working on a rule
```

Add or change a rule in `rules.yaml`, then re-render. **Never edit a page under `docs/gates/`
by hand** — `--check` fails the build when a page is not what a render produces, which is what
keeps the demo honest.

## How to stop it

It stops when it returns. It writes only into the `--out` directory. To remove the pages,
delete `docs/gates/` and the "Gates" section from `mkdocs.yml`.

## What it is not

It is not a gate itself. It grades nothing and blocks no merge; it renders what the gates
already do. If it is failing, the estate is fine — the pages are just out of date.
