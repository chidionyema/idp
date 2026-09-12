# Demo: every gate, with its own output on the page

The estate has 65 rules in `rules.yaml`. Each one is a gate that refuses something. Until now
the only way to see a gate work was to read its source, or to run it and understand what came
back.

`bin/idp-gate-demo` renders one page per rule. **Each page carries the gate's real output** —
the refusing case and the permitting case, with the exit code the gate actually returned.

## Run it

```bash
bin/idp-gate-demo --out docs/gates          # render every page
bin/idp-gate-demo --out docs/gates --check  # exit 1 if the pages are stale
bin/idp-gate-demo --only flux-subst         # one rule, to look at it
```

## What you see

```
$ bin/idp-gate-demo --out docs/gates
ok    gate-demo 65 page(s) written to docs/gates, 1 BLIND
```

The index is one row per gate, with the exit codes its page recorded:

```
| gate | id | planes | law | refused | permitted |
|---|---|---|---|---|---|
| flux-subst | `flux-subst` | ci, session | incident 2026-09-06 | `1` | `0` |
```

And a page carries what the gate said, not a summary of it. From `docs/gates/flux-subst.md`:

```
Exit code `1` (the registry expects non-zero). ✓

tests/fixtures/flux-subst/bad.yaml:12: shell expansion Flux will rewrite: if [ -n "${HERMES_ENV_DIR:-}" ] ...
```

## Why generated

A hand-written demo is a claim about what a gate does, and nothing checks it. This runs the
gate against the fixture the registry already names and writes the bytes it returned. If a
gate stops discriminating, its page changes on the next render and says so — the demo cannot
drift from the gate.

That is not theoretical. `docs/gates/convergence-proof.md` exposed a rule whose three cases
all passed the literal string `HEAD` as both the head commit and the proof's commit, so the
comparison it existed to make never fired. The page is what showed it.

## BLIND is not a pass

A rule whose case cannot run — its gate is not on disk, or it names no case with arguments —
gets a **BLIND** page that names what was missing. One rule is BLIND today, and its page says
so rather than reading as a green one.
