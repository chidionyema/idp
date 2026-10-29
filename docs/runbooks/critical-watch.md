# Runbook: the critical-function spine

Founder, 2026-10-28: "we can't have critical functions failing, this is an estate wide mandate so
build the spine and use this to prove it", and "anythign watchin critical fuction that dies needs
alert and auto invoation of agent, with structured data to resolve."

## What this is

One generic layer that watches every critical function the estate cannot work without, and one
proof case for it: the disk guardian.

```
catalog/critical-functions.json             the registry: one row per critical function
platform/estate/libexec/critical-watch.py   the detector: probe, verdict, incident, alert, invoke
platform/estate/libexec/agent-invoke.sh     the waker: session door first, local claude lane second
launchd/ai.estate.critical-watch.plist.tmpl the scheduler: every 60 seconds
```

A function is a **row**, not a special case. Adding a function to the estate's critical set is a
line of JSON, not a new watcher.

## The three verdicts

| Verdict | Meaning | Alerts | Wakes an agent |
|---|---|---|---|
| `PASS` | the probe measured, and the function is alive and (if declared) meeting its goal | no | no |
| `FAIL` | the function is dead, or alive and missing its goal | yes | yes |
| `BLIND` | the probe could not be measured (the socket is not there to check, the file is unreadable) | yes, at warning level | no |

`BLIND` is a verdict, not a quiet `PASS`. A probe that cannot be measured proves nothing, and
reporting it as `PASS` is how a gate stops being a gate. A `BLIND` function alerts and is left
for a human, because waking an agent about a measurement failure is how an agent storm starts.

**A goal probe is what catches "alive but ineffective".** The old disk watcher was running,
ticking, exiting 0, and freeing nothing: liveness alone would have called that `PASS`. The
registry row for `disk-guardian` declares a goal (`free_space_mb` on `/System/Volumes/Data`), so
a guardian that is running and reclaiming nothing is `FAIL`.

## The registry

```json
{
  "id": "disk-guardian",
  "probe": {"kind": "heartbeat_file", "path": "~/.estate/heartbeats/disk-guardian.json", "max_age_s": 180},
  "goal":  {"kind": "free_space_mb", "path": "/System/Volumes/Data", "min": 1500},
  "remediation": {"runner": "claude", "repo": "...", "budget": 20, "task": "..."}
}
```

Probe kinds: `heartbeat_file`, `unix_socket`, `tcp`, `http`, `launchd`, `command`, `file`.
Goal kinds: `free_space_mb`, `heartbeat_field_min`, `launchd_running`.

Paths written as `~/.estate/...` resolve inside `ESTATE_STATE_DIR`, so a test never measures the
founder's laptop. A registry path that does not exist is `BLIND`, never a silent fall back to
another registry.

## What happens when a function dies

1. A **structured incident** is written: `~/.estate/incidents/<id>-<timestamp>.json`, appended to
   `~/.estate/incidents/ledger.jsonl`, and mirrored in `~/.estate/incidents/latest.json`. It
   carries the function id, the verdict, the probe that failed, the measurement, and the
   remediation task.
2. An **alert** is raised: a macOS notification and a line in `~/.estate/alerts/inbox.jsonl`.
3. An **agent is woken** with the incident attached: `sb start` (the estate's session door) first,
   and the local `claude -p` lane when the session door is down. The lane that was used is
   recorded as `invoked_via` in the result, because a claim of "an agent was invoked" that does
   not say how is not a claim.

Alerts and invocations are **deduplicated and backed off** (300 s, 600 s, 1200 s, 1800 s). The
backoff row is deleted when the function recovers, so a later failure alerts immediately instead
of inheriting an old backoff.

## Running it by hand

```bash
estate_invoke critical-watch                    # measure and act
estate_invoke critical-watch only=disk-guardian # one function
estate_invoke critical-watch dry_run=1          # measure only, raise nothing
python3 ~/.estate/libexec/critical-watch.py --json --dry-run
```

Exit 0: every function passes. Exit 1: at least one fails. Exit 2: at least one is blind and
none failed.

## The proof case: the disk guardian

`bin/idp-disk-watch` is the resident guardian. It runs a 20 s cycle; each cycle writes a
heartbeat and runs **one bounded incremental cleaner step** (never one massive run that times
out). It never deletes anything itself -- it drives the cleaner, which owns the never-delete
rules.

The cleaner is target-driven (`DISK_WATCH_TARGET_MB`, default 2500 MB): it stops the moment the
volume is back above the target, and it prints a ranked, measured "blocked by" table when the
target cannot be reached. The executor's own floor is 1500 MB (`MIN_FREE_MB` in
`mcp/plugins/estate_executor.py`), so the guardian's target is the floor the estate's own doors
need to stay open, with 1000 MB of headroom above it. The target has to be *reachable*: a target
that no reclaim can meet turns the guardian into a perpetual reclaim that eats the tool cache's
last-of-all entry and still misses the target, so 2500 MB is the measured working level
(2011 MB free, plus ~660 MB of regenerable tool-cache weight and the 534 MB uv cache when no uv
process is running).

### The drill

1. `launchctl bootout gui/$(id -u)/ai.estate.disk-watch` -- stop the guardian.
2. Wait one cycle of the spine (60 s).
3. `cat ~/.estate/incidents/latest.json` -- the structured incident.
4. `tail ~/.estate/alerts/inbox.jsonl` -- the alert.
5. The invocation is recorded with its lane (`invoked_via`: `session` or `local-claude`).
6. `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.estate.disk-watch.plist` and
   watch the heartbeat come back.

A drill that is not run is not a drill. The evidence for the C11 certification gate is the
incident file, the alert line and the invocation record from a real failure.

## Adding a function

1. Add a row to `catalog/critical-functions.json`.
2. Give it a probe. If it has a number that must hold, give it a goal.
3. Give it a remediation: what the woken agent is told to do, in the repo it may touch, and the
   constraint it must not break ("do not touch another agent's worktrees").
4. Run `estate_invoke critical-watch only=<id> dry_run=1` and read the verdict.

A function that cannot be probed should not be in the registry: an unprobeable row is a
`BLIND` on every cycle, which is noise, not signal.
