# Onboarding: `bin/reasoning_gateway_hook.py`

The `Stop` hook that grades a real Claude Code session with D1 (PRM) and D2 (budget) the moment
it ends, so the reasoning-gateway gates cover live work, not only two CI fixtures.

## Commands

| command | what it does |
|---|---|
| `idp-reasoning-gateway-hook --hook` | reads Claude Code's Stop-hook JSON on stdin (`transcript_path`, `session_id`), grades that transcript with `bin/idp-prm --grade` and `bin/idp-budget --run`, writes the verdict, always exits 0 |
| `idp-reasoning-gateway-hook --report [N]` | prints the last `N` (default 10) session verdicts, newest first |
| `idp-reasoning-gateway-hook --self-test` | proves grading and the blind case both work, using a throwaway fixture |

## Where the verdict lives

`~/.pi/agent/reasoning-gateway/<session_id>.json` -- one file per session, holding the PRM and
budget gate's exit code and stdout. `--report` reads this directory back.

## What it does not do

It never blocks a session. PRM and budget grade a whole transcript from turn one; blocking `Stop`
on a step from early in a long session that was already corrected would make the gate something
an agent learns to route around. Report, don't fail, is the same convention `bin/idp-budget` and
`bin/idp-prm`'s own bare-invocation sweep already use for historical runs (R38) -- extended here
on purpose to a live session's own end-of-run grade.

It does not grade D3 (contract). Contract gates a single tool call's declared pre/post-condition
against observations a caller supplies; there is no way to derive those from a bare transcript, so
wiring D3 into a session means the specific tool wrapper that makes the call declares them and
calls `bin/idp-contract` itself, not a blanket end-of-session sweep.

## Wiring

`.claude/settings.json`, `hooks.Stop`, runs `bin/idp-reasoning-gateway-hook --hook` with a 30s
timeout after every turn a session ends on. No further setup: every session in this checkout
already gets graded.
