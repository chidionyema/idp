# Runbook: writing a diagnosis record

Founder, 2026-09-29: "no theories without bayesian reasoning and evidence gathering", "we don't
do guesswork", "why is this not enforced". A theory about *why* the router is failing used to be
a sentence in a PR description. It is now a record `bin/estate-diagnose` can grade, and a change
that touches the router's config or code cannot land without one that clears posterior >= 0.95 on
its winning hypothesis.

## What is gated

A change touching `llm/config.yaml`, `platform/llm/config.yaml`, any `platform/llm/*.py`, or
`bin/litellm-local` must carry, on the commit range `bin/idp-ci`'s fast gate is grading, a
commit-message line:

```
Diagnosis: docs/diagnoses/<file>.yaml
```

`bin/diagnosis-gate` (wired into `bin/idp-ci`'s `IDP_CI_FAST=1` rung, so it runs in
`.github/workflows/fast-gate.yml` and on every laptop pre-push) finds that line, loads the
record it names, and runs `bin/estate-diagnose` against it fresh -- it never trusts a `posteriors`
block already sitting in the file, because a stale or hand-edited number would defeat the point.
A change whose diff is entirely under `docs/` or `tests/` is exempt (it cannot touch the router by
construction of the path list above).

## Writing a record

A record is a YAML file under `docs/diagnoses/`, named `<date>-<what-broke>.yaml`. It has three
parts, and the order they must be written in matters as much as their shape:

1. **Hypotheses, with priors, fixed before you read the evidence.** Every competing explanation
   you are willing to consider, each with a prior (they must sum to 1, tolerance `1e-6`). No
   uniform requirement, but starting uniform is honest when nothing yet favors one hypothesis
   over another.

2. **For every hypothesis, a likelihood distribution over each evidence item's categories --
   also fixed before you look at the observed counts.** This is the discipline the founder is
   asking for: write down what each hypothesis PREDICTS before you check what happened. A
   likelihood you tune after seeing the data is not evidence, it is the answer dressed up as a
   test of itself, and `estate-diagnose` cannot tell the difference from the file alone -- the
   discipline is on the person or agent writing the record.

3. **Evidence: what was actually observed**, as category counts (`observed: {category: count,
   ...}`). Each evidence item needs an `observed` block and a `likelihoods` block with an entry
   for every declared hypothesis and every observed category -- `estate-diagnose` refuses a
   record where any of those is missing, or where the priors don't sum to 1.

Optional: `n_eff_divisor` downweights evidence drawn from one correlated incident window (e.g.
60,000 log lines from one retry storm are not 60,000 independent observations) -- it divides
every observed count before the log-likelihood is accumulated, which pulls the posterior back
toward the prior without changing which hypothesis wins.

## Computing it

```
bin/estate-diagnose docs/diagnoses/<file>.yaml
```

Prints a table (prior vs. posterior per hypothesis, winner marked) and writes the computed
`posteriors`, `winner` and `computed_at` back into the file -- run this once after writing a
record, commit the result, and reference it in the commit message. `--json` emits a
machine-readable summary instead of the table (what `bin/diagnosis-gate` uses); `--no-write`
computes without touching the file (what the gate uses, so grading never mutates the tree);
`--min-posterior 0.95` exits 3 when the winner falls short.

The math: log-space Bayes over a multinomial likelihood --
`log P(H|D) ~ log(prior[H]) + sum over evidence of sum over categories (observed/n_eff_divisor) *
log(likelihood[H][category])`, normalized by log-sum-exp so it never under/overflows a plain
float product. See `bin/estate-diagnose`'s own docstring for the full derivation and every
refusal condition.

## Example

`docs/diagnoses/2026-09-29-laptop-router-auth-errors.yaml` is the first real record: three
hypotheses for a wave of auth errors in the laptop router's log (fault inside the `fast` pool
specifically, a global/caller-key fault that should hit every pool proportional to its traffic
share, or a bad key on the `minimax` lane alone), against two evidence items (two distinct
auth-error message shapes, each broken down by model group). The `fast`-pool hypothesis clears
the bar by a wide margin on both.
