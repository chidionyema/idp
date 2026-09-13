# Demo: the breaker, enforced in the session

Three identical findings lock the primitive. This is the enforcement half: a pi extension watches
the agent's own tool calls and refuses the fourth **before it runs**, with the fleet lever named.

The rule (`rules.yaml: circuit-breaker`) proves the logic in CI, hours later. This is what stops it
in seconds, where the mistake happens.

## Run it

```bash
ESTATE_ROOT=$PWD node extensions/breaker/decide.mjs < /tmp/observations.json
```

where `/tmp/observations.json` is:

```json
{"observations": [
  {"finding": "CVE-2026-13221 CVE-2026-42496 CVE-2026-8376", "target": "pr-1"},
  {"finding": "CVE-2026-8376 CVE-2026-13221 CVE-2026-42496", "target": "pr-2"},
  {"finding": "CVE-2026-42496 CVE-2026-8376 CVE-2026-13221", "target": "pr-3"}
 ],
 "next": {"finding": "CVE-2026-13221 CVE-2026-42496 CVE-2026-8376", "target": "pr-4"}}
```

## What you see

```
{"block": true,
 "reason": "423 Locked: proven pattern (N=3). 3 target(s) carry
            cve:CVE-2026-13221,CVE-2026-42496,CVE-2026-8376; the cause is proved, so the
            linear action is disabled. This is not a refusal of the target -- it is a
            refusal to repeat the proof.",
 "lever": "the finding is in the image or the base, so it is one fix for every target: fix
           it once on main and refresh the fleet -- `gh workflow run merge-when-green.yml`"}
```

Those three findings are the real ones from 2026-09-12, in the shape three different pull requests
printed them. Same CVE set, different positions, different stacks, two different Dockerfiles — a
hash of the output would not have matched them. The fingerprint is the CVE set.

## The case it must never block

Nine targets, nine different findings:

```
{"block": false}
```

A guard that refuses correct work is an outage (R38), and nine independent failures is the common
case rather than the exception.

## What trying to enforce it found

Two bugs the unit tests could not see, because an in-process test builds one `Breaker` object:

- **No shebang.** `bin/idp-circuit-breaker` was marked executable and started with a docstring, so
  running it as a program returned nothing and the extension read that as "not locked" on a pattern
  that was already proved.
- **The record did not rebuild the lock.** A fresh process saw the findings and reported
  `locked: false`. Every CLI invocation is a fresh process, so the enforcement was blind exactly
  when it mattered.

Both now have regression tests.
