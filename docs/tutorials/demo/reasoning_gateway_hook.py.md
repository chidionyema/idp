# Demo: the reasoning gateway grades every real session, not only two fixtures

Ticket: `docs/tickets/2026-09-14-reasoning-gateway.md`. D1 (PRM, `bin/idp-prm`) and D2 (budget,
`bin/idp-budget`) shipped as CI gates against one `bad`/`good` fixture pair each. That proves the
grading logic is correct. It proves nothing about any session a person actually ran, because
nothing ever pointed either gate at a real transcript automatically. This hook is the fix: a
Claude Code `Stop` hook that grades the session that just happened, the moment it ends.

## Why this exists, concretely

Before this file, both gates' own "sweep the estate" bare-invocation case read
`~/.pi/agent/sessions` -- a store that had not been written to in months. Every real idp session
this ticket itself produced was invisible to its own gates. Fixed in the same commit
(`bin/epistemic_firewall.py`, `bin/trajectory_lock.py`): `_estate_sessions()` now also reads
`~/.claude/projects`, where the Claude Code CLI actually writes one line per turn.

```bash
cd ~/dev/code/idp
python3 bin/idp-prm    # bare invocation, no args
```

```
ok    prm 25 recent session(s) swept; 9 carried a step below 0.8 (1530 step(s)). Historical,
      reported not failed -- grade one session by name to act on it.
```

Nine of twenty-five real sessions on this machine already carried an unproven step. That number
was `0` before the directory fix, because the sweep found nothing at all.

## The hook itself

`.claude/settings.json` runs this on `Stop`:

```bash
echo '{"transcript_path":"tests/fixtures/integrated/db-is-up/session.jsonl","session_id":"demo"}' \
  | python3 bin/idp-reasoning-gateway-hook --hook
python3 bin/idp-reasoning-gateway-hook --report
```

```
demo: prm_exit=1 budget_exit=0
ok    reasoning-gateway 1 session(s) graded, 1 shown
```

Every real session, at `Stop`, gets its own verdict written to
`~/.pi/agent/reasoning-gateway/<session_id>.json` -- no one has to run a gate by hand, and no PR
has to remember to add one.

## Why this reports instead of blocking

A step near the start of a two-hour session that already got corrected by step 40 would re-trip
PRM at every single `Stop` otherwise, turning a real gate into a nuisance an agent learns to
ignore. This hook always exits `0`. The verdict lands on disk; a human -- or, later, a Backstage
page reading the same files the way `mcp/plugins/estate_sessions.py` already reads the catalogue's
session rows -- decides what to do with it. That UI surface does not exist yet: this hook is the
write side of it, not the whole thing.
