# Onboarding: conformity-report

## What it is

`bin/conformity-report` prints an EU AI Act Annex VI internal-control
assessment to stdout, as markdown. It runs `bin/ai-act-gate`,
`bin/security-policy-gate`, `bin/policy-test` and `bin/multiarch-gate` and
pastes each one's own summary line into the report, then lists every AI
system from `platform/ai/systems.yaml` with its risk tier, role, owner and
review-due date. Nothing about the assessment is computed by this script
itself — it assembles what the gates already say.

## Why it exists

Annex VI internal-control assessment is voluntary for systems below the
high-risk tier, which is where prospector currently sits. A buyer's engineer
or an auditor still wants to see it, and a hand-written version of it drifts
from the repository the moment any of the underlying gates changes state.
Rendering it from the gates' live output means the report can never claim a
control passes when the gate that owns that control disagrees.

## When it runs

By hand, whenever the assessment is needed — for a review, or ahead of a
buyer conversation. It is referenced from
`docs/ai-systems/prospector/technical-file.md` and
`docs/how-to/declare-an-ai-system.md` as the command that produces this
document. It is not wired into `bin/idp-ci`; the gates it calls are each
proved there independently.

## Related files

```
bin/conformity-report                     assembles the report
bin/ai-act-gate                           Annex IV per-system check
bin/security-policy-gate                  the 14 ISO 27001-mapped controls
bin/policy-test                           licence and placement policy fixtures
bin/multiarch-gate                        R24 build coverage
platform/ai/systems.yaml                  the systems this report lists
docs/ai-systems/prospector/technical-file.md  cites this command
docs/how-to/declare-an-ai-system.md       cites this command
```
