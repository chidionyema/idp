# Demo: spec-gate

Founder ruling R29 (2026-08-25): a pull request that changes code must also
change the executable spec. `bin/spec-gate` compares the PR base to HEAD and
refuses code that arrives alone.

In a throwaway repository, change code only:

```
$ git init -q -b main t && cd t && echo 'x = 1' > app.py && git add . && git commit -qm base && git branch base
$ echo 'x = 2' > app.py && git commit -qam 'code only'
$ ~/dev/code/idp/bin/spec-gate base
FAIL  spec-gate 1 code file(s) changed and no executable spec changed (R29):
      app.py
      add or change a *.feature scenario, a test, or bin/estate-diagram in this PR
```

Add the scenario and run it again:

```
$ mkdir features && echo 'Feature: x is 2' > features/app.feature && git add . && git commit -qm spec
$ ~/dev/code/idp/bin/spec-gate base
ok    spec-gate 1 code file(s) changed with 1 spec file(s)
```

Both runs are the incident test `sovereign/tests/test_incident_r29_spec_gate.py`,
so CI proves the gate refuses and permits on every push. In every active
estate repository the same script runs as the `spec-gate` job through
`chidionyema/idp/.github/actions/spec-gate`; the ruleset
`estate-security-scan` makes it a required check.
