# Estate Agent Enforcement Platform — Day 0

**Status: OPERATIONAL**

Executor: `~/.estate/bin/estate-execute` — Python, no heredocs, parameterized SQL, all logs to stderr, output to stdout.

---

## Implemented

| Intent | Status | Verified |
|--------|--------|----------|
| `shell.parse` | ✅ | Tested on `bin/idp-ci` |
| `shell.locate` | ✅ | Context around error lines |
| `shell.suggest` | ✅ | Unified diff to stdout |
| `shell.verify` | ✅ | Sandbox + bash -n + shellcheck |
| `git.branch` | ✅ | New branch from HEAD |
| `git.commit` | ✅ | Apply patch + commit |
| `ci.run` | ✅ | Push + gh run watch |
| `ci.errors` | ✅ | GH API failures |
| SQLite ledger | ✅ | Tickets with steps, status, dur |
| Design guide | ✅ | `docs/specs/this-file` |

---

## Full pipeline (tested end-to-end)

```
estate-execute shell.parse bin/idp-ci
→ structured shellcheck errors

estate-execute shell.locate bin/idp-ci 802
→ block context around line 802

estate-execute shell.suggest bin/idp-ci 550 /tmp/fixed.txt > /tmp/patch.diff
→ unified diff to stdout

estate-execute shell.verify bin/idp-ci /tmp/patch.diff
→ ALL PASS

estate-execute git.branch fix/sc2086-550
estate-execute git.commit bin/idp-ci /tmp/patch.diff "fix: quote XD"
→ committed

estate-execute ci.run fix/sc2086-550
→ CI green → PR ready
```

---

## Intent authoring rules

1. One verb per intent — `parse`, `suggest`, `verify` are separate
2. Write to stdout. Never touch the source file.
3. Helpers in `~/.estate/libexec/*.py`. Intents in `~/.estate/intents/*.yaml`
4. `{{var}}` for paths (executor quotes). `<<var>>` for raw values (already quoted)
5. `tools: []` means no LLM, zero cost
6. `halt_on_failure: true` for `verify`, `ci.run`. `false` for `parse`, `locate`
7. Complex logic in Python helpers, not in YAML cmd fields

---

## Families

- **shell.*** — static analysis, no model
- **git.*** — bounded to new branches, never main
- **ci.*** — read CI state, trigger runs
- **k8s.*** — read-only cluster inspection
- **flux.*** — Flux operations
