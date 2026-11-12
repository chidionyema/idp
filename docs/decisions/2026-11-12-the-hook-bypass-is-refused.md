# The hook bypass is refused at the door

**Date:** 2026-11-12
**Status:** accepted, enforced
**Founder, verbatim:** *"no agenbt can do that ever again i nee string mathyematic al
gyabatees and i need to knwohow you plan to prove it"*

## The failure

`.githooks/pre-commit` is healthy. It runs `ruff format` on staged Python and **applies**
the fix rather than only checking, so a staged file lands formatted.

Measured 2026-11-12 on this repo: a file containing `x = {1,3,2}` was staged and committed,
and the hook rewrote it to `x = {1, 2, 3}` before the commit landed. The gate was never the
problem.

The problem is that an agent can skip it. `git commit --no-verify` and
`git -c core.hooksPath=/dev/null commit` both bypass `.githooks/pre-commit` entirely. An
agent -- this one -- did exactly that on a stale belief that ruff was not installed. ruff
0.15.18 was installed. `bin/genesis-inbound-bridge.py` therefore reached CI unformatted and
`fast-gate` failed three jobs on PR #7981, hours after the mistake and after a full round of
fetching logs and re-pushing.

That is R3 in `AGENTS.md` section 9 -- *"deterministic checks run late (CI) instead of at write
time"* -- and R10, an agent dragging a pipeline through manual re-runs because the local door
was skipped.

## The rule

A command is refused when it would skip the repo's hooks. The decision is a pure function of
the command string (`platform/estate/governance/hook_bypass.py`), so the same input always
gives the same answer and anyone can re-derive it.

```
TOKEN        := shlex.split(command)
SEGMENT      := TOKEN split on shell separators (&& || ; | & \n)
HEAD         := first token of a segment whose basename is git/git.exe,
                past any leading VAR=value env assignment

COMMIT_FAMILY := {commit, merge, cherry-pick, revert, am, rebase, tag, push}
                 # `push` because a bypassed commit that is then pushed is the
                 # same defect one step later.

HOOK_HOK   := "--no-verify" in argv[HEAD+1:]
             | "-n" in argv[HEAD+1:] when the verb is one where git spells
               --no-verify as -n (commit, merge, cherry-pick, revert, am).
               On `push`, -n is --dry-run and is NOT a bypass.
             # --no-gpg-sign is NOT a bypass: signing is not verification.

PATH_HOK   := an argv token equal to core.hooksPath / core.hookspath
             | a token matching core\.hooksPath\s*=\s*\S       (the = form)
             | a token matching -c\s*core\.hooksPath            (the joined form)

ENV_HOK    := a leading VAR=value whose VAR is GIT_CONFIG_GLOBAL or GIT_CONFIG_SYSTEM
               assigned to /dev/null
             # it hides the global hooksPath, so hooks silently stop running

REFUSE <=> exists a SEGMENT with a git HEAD
           AND a COMMIT_FAMILY verb in that segment
           AND (HOOK_HOK OR PATH_HOK OR ENV_HOK in that segment)
```

Accepting is the default, because a gate that refuses correct work is an outage
(`AGENTS.md` section 12). `git commit -m "fix the --no-verify note"` must pass: there the dangerous
string is a message value, not an argv token.

## The proof

**P1 -- the matcher is total over a labelled corpus.**
`tests/fixtures/hook_bypass_corpus.txt` holds 45 commands, 24 labelled `REFUSE` and 21
labelled `PASS`, covering every spelling of the bypass and the near-misses that would make a
single clever regex wrong. `classify()` prints `misclassified=N/45`.

```
misclassified=0/45
```

**P2 -- the refusal is real at the door, not only in a unit test.** After installing the
matcher into `~/.estate/runtime/idp/` and restarting the daemon, the live `estate_execute`
door was driven with each vector:

| vector | result |
|---|---|
| `git commit --no-verify -m ...` | refused: *"--no-verify skips .githooks/pre-commit, the write-time ruff format/lint gate"* |
| `git -c core.hooksPath=/dev/null commit -m ...` | refused: *"core.hooksPath is being redirected away from .githooks"* |
| `GIT_CONFIG_GLOBAL=/dev/null git commit -m ...` | refused: *"GIT_CONFIG_GLOBAL=/dev/null hides the repo's hooks path"* |
| `git commit -n -m ...` | refused: *"-n is --no-verify here and skips .githooks/pre-commit"* |
| `git commit -m "docs: explain why --no-verify is refused at the door"` | **allowed**, hooks ran, commit signed |
| `git push -n origin lane/...` | **allowed** -- `-n` on push is `--dry-run` |

**P3 -- the gate can fail.** Sabotaging the matcher both ways and re-scoring the same corpus:

```
SABOTAGE 1 (always PASS):   misclassified=24   (must be > 0)
SABOTAGE 2 (always REFUSE): misclassified=21   (must be > 0)
```

Both directions are caught, so the corpus genuinely discriminates and the suite is not a
rubber stamp. `tests/test_hook_bypass_is_refused.py` pins this with `monkeypatch`, so the
falsifier runs on every CI run rather than once by hand -- `AGENTS.md` section 9 R2.

**P4 -- honest work is not refused.** `pytest tests/test_hook_bypass_is_refused.py` ->
`19 passed, 1 skipped`. The skip is `bin/estate-execute` absent in a bare checkout; the door
itself was proven live in P2.

## What this does not cover, named rather than hidden

A human typing the bypass into their own terminal. This rule sits in the executor, which
every agent on this machine goes through (`AGENTS.md` section 7). It cannot mediate a shell it never
sees. The residue is closed by the second layer: a commit that carries no hook-written trailer
is refused in CI. That layer is not built yet, and this record says so instead of implying the
hole is fully sealed.

## Where it lives

- `platform/estate/governance/hook_bypass.py` -- the algebra, pure functions only
- `mcp/plugins/estate_executor.py` -- `_hook_bypass_verdict()`, called from `execute_command`
  beside the spawn gate; BLIND is not a refusal (an unloadable matcher must not stop the
  estate, R38) and the blindness is recorded in the friction log
- `tests/test_hook_bypass_is_refused.py` + `tests/fixtures/hook_bypass_corpus.txt` -- P1 and P3

Claim: chidionyema/idp#8000
