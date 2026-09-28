# EU AI Act — what it is, what it costs, how to stop it

## What it is for

Prospector calls three model providers on behalf of customers, which makes us a
provider and a deployer under Article 3(3). It is not an Annex III high-risk
system; it sits in the limited tier, where Article 50 (transparency) applies from
2 August 2026 and the high-risk obligations were delayed to 2 December 2027 by the
Digital Omnibus. We build the four things a high-risk system needs anyway, because
a buyer will ask for them: a risk register, data governance, a technical file and a
conformity assessment. `docs/reference/eu-ai-act.md` holds the legal reading.

## What it costs

Nothing recurring. Two YAML files, one markdown technical file per system, and a
gate that runs in `bin/idp-ci` in under a second. A review is due every quarter
(`review_due` in `platform/ai/systems.yaml`); the gate fails when the date passes,
so the cost is one session-hour every three months to re-read and re-date.

## What it watches or changes

It reads `platform/ai/systems.yaml`, `platform/ai/risk-register.yaml` and
`docs/ai-systems/<system>/technical-file.md`. It changes nothing at runtime and
touches no model call.

## Where it lives

```
platform/ai/systems.yaml                        the systems register
platform/ai/risk-register.yaml                  R-<SYSTEM>-NNN risks
docs/ai-systems/<system>/technical-file.md      Annex IV, nine sections
bin/ai-act-gate                                 the completeness and review-date check
bin/conformity-report                           the assessment, assembled from gate output
docs/how-to/declare-an-ai-system.md             how the next system is added
tests/fixtures/ai-act/{good,bad}                what the gate is proved on
```

## How to turn it off

```
sed -i '' '/ai-act-gate/d' bin/idp-ci
```

The registers stay as documents; only the check stops.

## How to turn it back on

`git checkout main -- bin/idp-ci`.

## What goes wrong

The commonest failure is the review date: the gate goes red on the day
`review_due` passes and stays red until a session re-reads the register and moves
the date. The second is a new model-calling component that nobody declared; the
catalog half (annotations generated from `systems.yaml`, crew#197) is what will
catch that, and it is not merged yet.
