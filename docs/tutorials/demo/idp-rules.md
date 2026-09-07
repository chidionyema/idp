# Demo: idp-rules

Every rule in this repository is a row in `rules.yaml`, and `bin/idp-rules` is
the only thing that reads it. Ask it what it knows:

```
$ bin/idp-rules list
flux-subst               ci           3 case(s)  incident 2026-09-06, otto-gateway
cloud-agnostic           ci           3 case(s)  R36
estate-zone              ci           6 case(s)  R46
...
one-scheduler            ci           3 case(s)  THE HEADLINE (one platform layer, not a stitched one)
```

Grade one rule, by name:

```
$ bin/idp-rules run --only jit-grants
ok    jitgrant idp-jit-grants refuses the escalating catalogue; the live one cannot become standing access
```

Each row carries its own cases, and a case says what the answer must be —
`expect: refuse` for the fixture that must be caught, `expect: pass` for the
one that must be admitted, `live: true` for the run against the real estate.
A rule proved only one way is not proved (LAW 38), and a rule whose tool is
not installed prints `BLIND` and fails rather than passing quietly, because a
gate that could not run has graded nothing.

The table in `AGENTS.md` is generated from the same file:

```
$ bin/idp-rules render-agents-md
wrote 37 rules into AGENTS.md
$ bin/idp-rules render-agents-md --check
ok    table    AGENTS.md's rule table is generated from rules.yaml (37 rules)
```

`bin/idp-ci` runs that check, so a rule and the row that publishes it cannot
drift apart. Adding a rule is a row and two fixtures — never a new rung in the
CI script, never another gate runner.
