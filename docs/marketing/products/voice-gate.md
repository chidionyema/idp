# Voice Gate

> A deterministic, version-controlled prose linter that enforces your house voice
> on every commit and PR — no inference, no surprises, no model drift.

## The problem

Your team writes in your voice. Your AI tools write in their voice. The two
are not the same, and the difference shows up in every commit a model has
touched: assistant residue ("Certainly!", "I hope this helps"), cadence that
runs one sentence per breath, vocabulary that pads, punctuation that hedges.

You can ask a person to clean it up. You can ask a model to clean it up at
inference time, paying per call, with no consistency between runs. You can
write a style guide nobody reads. None of these is a fix; each is a tax.

Voice Gate is the fix. It runs in CI the way a type checker runs in CI: a
binary, a policy file, a verdict on every commit. The verdict is
deterministic — the same input produces the same output, today and next year,
because the rule is a rule, not a guess.

## What you get

- **Deterministic detection.** Voice Gate is a regex-and-rule engine. There is
  no model in the loop, so there is no model to drift. The output of "is this
  in our voice?" is the same on Monday as it is in March. *Benefit: your CI
  does not flake when a model version bumps.*

- **A version-controlled policy.** House voice is `voice-policy.yaml` in the
  repo. PRs to the policy are PRs to the policy; they show up in code review
  the way any other config change does. *Benefit: marketing and engineering
  agree on the same file.*

- **A pre-commit hook and a CI step.** Voice Gate runs where you want it —
  before the commit lands, or in the GitHub Action that gates merge. *Benefit:
  the voice is checked before review, not after.*

- **Detection rules that match the actual problem.** Assistant residue
  ("Certainly!", "I'd be happy to"), cadence (one-sentence paragraphs),
  banned tokens, punctuation density, sentence length distribution, paragraph
  rhythm. *Benefit: the rules catch the patterns a human editor would catch,
  at machine speed.*

- **A test suite that proves a rule.** Every detection rule has a fixture:
  input, expected verdict. The fixture is a test. *Benefit: when you change a
  rule, you see what you break.*

- **Multiple languages out of the box.** English, Spanish, Japanese — bundled
  with rules tuned for each. *Benefit: a global team runs the same gate.*

- **Open formats, no lock-in.** Policy is YAML. Output is JSON. Voice Gate is a
  binary you can run in a container or a Cloudflare Worker. *Benefit: you do
  not rent a vendor, you own a tool.*

## How it works

Voice Gate is two pieces: a Python implementation (the spec, used in tests and
in prospector's dogfood), and a Rust implementation (the production binary,
port 8420, 12 tests passing on `fix/cyrus-webhook-routes`). The Rust binary is
single-purpose, statically linked, and small.

A team runs Voice Gate by:

1. Adding `voice-policy.yaml` to the repo. The policy names the rules: which
   patterns are flagged, which severity they carry, which are warnings vs.
   errors.
2. Adding a CI step: `voice-gate check --policy voice-policy.yaml --input
   "$FILE"`. Voice Gate returns a verdict — pass, warn, or fail.
3. Wiring the verdict into the merge gate: a fail blocks the PR; a warn is
   a comment.

The rule set is the engine. The engine does not call a model. The engine does
not phone home. The binary is open-source; the policy is yours.

## Why us

- **One engine, deterministic, no semantic tier.** That is the product strategy
  on record (founder, 2026-09-06). Voice Gate does not score your prose on a
  bell curve; it answers the question your house voice answers: does this match?
- **CI-time, not inference-time.** Your spend on a model is your spend on
  judgment. Voice Gate is the cheap part: it runs in 30 ms, it does not call a
  vendor, and it is the same answer every time.
- **The estate dogfoods it.** The portal copy is graded by Voice Gate before
  it lands (Lane 7 of the portal-100 spec). The product is real because the
  buyer can see it in use.

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $50/seat/month | Single repo, single policy, Cloudflare Worker or CLI |
| Team | $250/month, up to 10 seats | Multi-repo, multi-policy, GitHub Action, audit log |
| Enterprise | Contact us | SSO, custom rules, dedicated support, on-prem binary |

A 30-day trial of the Team tier is available with the install wedge.

## Get started

- **Run the binary locally.** `cargo install voice-gate` (or the pre-built
  container). `voice-gate init` writes a starter `voice-policy.yaml`. Edit
  the rules; commit; add the CI step.
- **Read the spec.** `docs/specs/voice-gate-2026-09-06.md` (in the prospector
  repo) is the canonical design.
- **See it in action.** The estate's own portal copy is graded by Voice Gate
  before it lands. The drill runs hourly.
- **Call us.** For the Enterprise tier, for on-prem, for a custom rule, or
  for a procurement-grade security one-pager.

Voice Gate is the smallest surface area in our catalogue. It ships first.
