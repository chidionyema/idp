# Claims are commands

Founder, 2026-08-29: "NO ONE IS PROVING OR VERIFYING ANYTHING", "CREW HAVE TO MONITOR THEIR
STATEMENTS AGAINST REALITY". Tracked as crew#628.

## The rule

A statement in a pull request about the world (a pod is Ready, a door answers, a test passes,
a receipt exists) is written as a command, one per line:

    Verify: `bin/idp-cluster-state`
    Verify: `python3 -m pytest -q tests/test_incident_crew628_claims_are_commands.py`

The `verify-claims` workflow runs each on every push and every edit of the pull request and
writes the real output into the body between the `verify-claims` markers. The author never
types that section. A red command is a red check. A pull request that touches `platform/`,
`clusters/` or `bin/idp-*` with no `Verify:` line is red: a change to the world with no claim
about the world.

## What a command may be

Only an observation: `bin/idp-*`, `kubectl get` or `describe`, `flux get`, `curl`, `gh`,
`python3`, `pytest`. A command naming `apply`, `delete`, `patch`, `push`, `merge`,
`dispatch`, `create`, `edit`, `rollout`, `scale`, `exec` is refused before it runs. The
verifier proves; it never acts. There is no crew path to production.

## What it does not prove

That the command was the right claim. A weak command (`ls`) passes. Reading whether the
claims are the right ones is the guard audit's job (crew#652), and the founder's.
