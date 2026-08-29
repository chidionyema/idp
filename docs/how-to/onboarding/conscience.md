# Onboarding: conscience

## What it is

The Conscience grades the estate against the founder's ethos, one row per tenet, and
keeps everyone aligned to it without anyone remembering to look. Seven tenets live in
`conscience/tenets.yaml`; each names the command that measures it, what green means,
and the pull-request rule that judges a diff against it. A tenet with no command is
refused at load time: a tenet nobody can measure is a wish (LAW 44).

Four surfaces read those seven rows:

| Surface | Where | What it does |
|---|---|---|
| Pull request | `bin/pr-report` + `policy/conscience.rego` | every PR comment opens with `🧠 n/7`; deny rules block, warn rules advise |
| Hourly run | `.github/workflows/conscience.yml`, `23 * * * *` | grades main, writes `reports/conscience.json`, keeps one open issue per red tenet (label `conscience`) |
| Founder line | same workflow, `23 7 * * *` | one Telegram line: score, move since yesterday, red rows |
| Portal card | `docs/CONSCIENCE.md`, rendered by `bin/idp-conscience --page` | red rows first, trend from `docs/conscience-history.jsonl`; lands daily through an auto-merge PR on `bot/conscience-page` |

`@conscience <question>` on any idp issue (`conscience-ask.yml`, owner only) answers
from the tenets and the rules through the estate router's `deepseek` lane.

## Why it exists

Founder, 2026-08-28: "an eternal, ambient, active presence that keeps everyone and
everything in the estate aligned." Before crew#586 the operating-model gate judged a PR
against ten deny rules but nothing scored the estate, nothing opened an issue when a
tenet went red, and the founder had no line that said whether the estate was more
itself today than yesterday.

## What it costs

One ubuntu-latest job per hour, about a minute each; one router call per `@conscience`
question. Nothing runs on the Mac.

## Where it lives

```
conscience/tenets.yaml                    the seven tenets, each with its measure command
bin/idp-conscience                        grade | --page | --selftest | --ledger-fresh-hours
policy/conscience.rego                    the PR rules (1 deny, 4 warn on 2026-08-28)
bin/pr-report                             the 🧠 line on every PR
.github/workflows/conscience.yml          hourly grade, issues, founder line, portal page
.github/workflows/conscience-ask.yml      @conscience on an issue
docs/CONSCIENCE.md                        the portal card (generated, do not edit)
docs/conscience-history.jsonl             one line per daily render, the trend
tests/test_incident_crew586_*.py          five files, one per checkpoint
```

## How to change a tenet

Edit the row in `conscience/tenets.yaml`. `bin/idp-conscience --selftest` proves the
loader still refuses a row with no command. A rule is born `warn` and flips to `deny`
only after a measured run with zero false positives (LAW 38).

## How to stop it

Disable the two workflows: `gh workflow disable conscience.yml` and
`gh workflow disable conscience-ask.yml`. The PR line stays, because it is part of
`bin/pr-report`; remove the `🧠` block there to silence it.
