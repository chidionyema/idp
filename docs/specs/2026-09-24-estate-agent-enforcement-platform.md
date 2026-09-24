# Estate Intent Authoring Guide

**Status: Live spec. Every intent must follow this.**

---

## 1. The executor's only job

```
estate-execute <intent> [arg=val ...]
```

That's it. The executor:
- Opens a ticket in the ledger
- Runs each step sequentially
- Logs step results
- Closes the ticket

The executor does not:
- Call LLMs
- Spawn harnesses
- Make routing decisions
- Know anything about the domain

---

## 2. The six pipeline steps

```
parse  → locate → suggest → verify → git.branch → git.commit → ci.run
```

Each step is one intent. The agent picks which to call. None of them edits a source file directly.

---

## 3. Intent anatomy

```yaml
name: <family>.<verb>          # e.g. shell.parse, git.commit, ci.run
description: >
  One sentence. What this does. What it returns.
args:
  <arg>: { type: string|int, help: "...", default: "..." }
tools: []                      # empty = no LLM, no harness spawn
halt_on_failure: true|false
steps:
  - cmd: >
      python3 ~/.estate/libexec/<helper>.py {{arg}} <<other>>
```

---

## 4. The six rules

### Rule 1: One verb per intent

`shell.parse` parses. `shell.suggest` suggests. `shell.verify` verifies. Do not combine.

**Bad:** `shell.fix` — parses, suggests, verifies, commits, pushes.
**Good:** six separate intents, each doing one thing.

### Rule 2: Write to stdout. Never touch the source.

Every intent that produces output writes to stdout. Every intent that modifies something writes to a temp file or a git branch. The source file is never modified unless it's a verified patch landing on a new branch.

### Rule 3: Helpers are Python. Intents are YAML.

Complex logic goes in `~/.estate/libexec/<name>.py`. The intent YAML contains only the command that calls it. Never embed Python, shell loops, or conditionals in the YAML `cmd` field.

**Bad:** 50-line shell one-liner with awk, sed, and Python inline.
**Good:** `python3 ~/.estate/libexec/shell-suggest.py {{file}} {{line}} {{fixed}}`

### Rule 4: `{{var}}` for paths. `<<var>>` for values.

- `{{file}}` — executor shell-quotes this. Use for paths that might have spaces.
- `<<fixed>>` — executor passes raw. Use for values the agent already quoted.

### Rule 5: No `tools:` means no LLM, no cost.

An intent with `tools: []` runs in <1s with zero LLM cost. Every informational intent must have `tools: []`. Only intents that need a model for judgment get `tools: [claude]`.

### Rule 6: `halt_on_failure: true` for verify. `false` for read-only.

`shell.parse`, `shell.locate`, `ci.errors` — `halt_on_failure: false`. The agent reads the output and decides.
`shell.verify`, `ci.run` — `halt_on_failure: true`. The agent cannot proceed if these fail.

---

## 5. Families

### shell.* — static analysis, no LLM
```
shell.parse   — shellcheck -f json → structured errors
shell.locate  — context around a line number
shell.suggest — unified diff to stdout
shell.verify  — sandbox apply + bash -n + shellcheck → PASS/FAIL
```

### git.* — git operations, never main
```
git.branch  — git branch + checkout, never main
git.commit  — git apply + add + commit, never main
git.push    — git push, never force
git.pr      — gh pr create, from new branch
```

### ci.* — CI operations
```
ci.run     — push branch + gh run watch → pass/fail
ci.errors  — gh run list --failed → structured errors
ci.status  — gh run list → summary
```

### k8s.* — read-only cluster inspection
```
k8s.get         — kubectl get
k8s.describe    — kubectl describe
k8s.logs        — kubectl logs
k8s.top         — kubectl top
```

### flux.* — Flux operations
```
flux.reconcile  — flux reconcile
flux.suspend    — flux suspend
flux.status     — flux get all
```

---

## 6. How the agent uses them

The agent never types `sed`, `grep`, `awk`, `python3 -c`, `cat |`, or any inline shell pipeline. It calls intents:

```
estate-execute shell.parse bin/idp-ci
→ reads structured errors

estate-execute shell.locate bin/idp-ci 802
→ reads block context

estate-execute shell.suggest bin/idp-ci 550 /tmp/fixed550.txt > /tmp/patch.diff
→ reads unified diff

estate-execute shell.verify bin/idp-ci /tmp/patch.diff
→ PASS or HALT

estate-execute git.branch fix/sc2086-550
estate-execute git.commit bin/idp-ci /tmp/patch.diff "fix: quote $XD (SC2086)"
estate-execute ci.run fix/sc2086-550
→ green → PR ready
```

---

## 7. What an intent cannot do

- `tools: [bash]` or any shell in the tools list — the agent must not be able to run arbitrary bash
- Modify `~/.estate/bin/estate-execute`
- Write to `pending/` or move a file out of `pending/`
- Add an intent without founder approval
- Access cloud credentials directly

---

## 8. Naming convention

```
<family>.<verb>
```

- `shell.parse` — shell family, parse verb
- `k8s.describe` — k8s family, describe verb
- `git.commit` — git family, commit verb
- `ci.run` — ci family, run verb

Families are nouns (what it operates on). Verbs are what it does.

No camelCase. No underscores in intent names. Use dots to separate family from verb.
