# Onboarding: idp-rules

## What it is

`rules.yaml` is the estate's rule registry: one row per rule, holding the
statement, the law it serves, the argv that grades it, the fixture pair that
proves it both ways, and the planes it is enforced on. `bin/idp-rules` is the
only program that reads it.

```
bin/idp-rules list                     every rule, its planes and its case count
bin/idp-rules run --plane ci           grade this repository
bin/idp-rules run --only jit-grants    grade one rule
bin/idp-rules cluster                  every rule that names a Kyverno policy has one on disk
bin/idp-rules session --files a.yaml   grade the files a session hook hands it
bin/idp-rules render-agents-md         write the table in AGENTS.md from the registry
```

## Why it exists

Until 2026-09-07 a rule was written in four places: a bash rung in
`bin/idp-ci`, a hand-typed row in `AGENTS.md`, a case list inside a second
runner (`bin/policy-test`), and the gate script itself. Adding a rule meant
touching all four, so the wording, the grading and the published list drifted
apart — and fifteen fixtures under `policy/fixtures` were named by no runner
at all, graded by nothing. The founder named the shape of the defect on
2026-09-07: an additive system with no compaction phase, where every new law
adds a script and none is ever removed.

One registry, one engine, three thin adapters. Adding a rule is a row and two
fixtures. The engine, not the author, decides what "proved both ways" means:
a case declares `expect: pass` or `expect: refuse`, and a rule whose tool is
missing prints `BLIND` and fails, because a gate that could not run has graded
nothing (LAW 28).

## When it runs

`bin/idp-ci` calls it three times: the rules marked `fast: true` in the
60-second fast gate, the rest in the full offline gate, and
`render-agents-md --check`, which fails when the table in `AGENTS.md` has
drifted from the registry.

## Related files

```
rules.yaml                 the registry: every rule, one row each
bin/idp-rules              the one engine that reads it
AGENTS.md                  the generated table, between the two marker comments
policy/                    the Rego rules several rows grade through conftest
tests/fixtures/            the fixture pairs the rows name
```
