# Onboarding: the reference decision matrix

Every build-or-buy, tool, vendor or design choice on the estate is scored once, in one file, against criteria the founder weighted: `docs/decisions/decision-matrix.yaml`. This page is how you use it; ADR 0009 is why it exists.

## When you must use it

- You are about to add an ADR under `docs/decisions/`, or bring a new chart (`kind: HelmRelease`) onto a platform layer. The operating-model gate refuses that PR without a `Matrix: <slug>` line in the body naming a scored entry.
- The founder asks a "which one?" question. The answer is a scored entry, not a paragraph.

## How to score a decision

1. Add an entry under `decisions:` with a `slug`, the `requirement` in one sentence, `status: proposed`, and at least two `candidates`. Any candidate the founder proposed goes in as a candidate, named as his.
2. Score every candidate on every criterion, 0–5 (0 fails the estate's bar, 3 meets it, 5 best in class). Every cell is `{score: n, evidence: …}`; the evidence is a URL, a path in this repository, or `cmd: <command>`. If you cannot point at something, you do not have a score.
3. Run `python3 bin/matrix-gate`. It prints the refusal if any of the rules above is broken. The recorded `decision` must be the top total; if the top two are within `tie_band`, the founder decides and his comment URL goes in `tie_receipt`.
4. Set `next_review` (seven days out) and cite the slug in the PR body: `Matrix: <slug>`.

## What you never do

- Change a weight. The weights are the founder's input; a change is a new `weights_history` entry carrying his comment URL, and the gate checks the sha256 of the weights against it.
- Add a criterion as a score cell. A founder question the matrix does not hold becomes a weighted row (with his receipt) first, then every candidate is scored on it.
- Present a number without a source. The weekly review (`bin/matrix-gate --review --verify-receipts`, run by `.github/workflows/matrix-review.yml` every Monday) re-reads every evidence URL and every receipt and posts the result on crew#562; a dead URL or a receipt not written by the repository owner turns it red.

## Honest limit

Sessions post to GitHub with the founder's own token, so "the receipt is by the repository owner" proves the comment came through his account, not that he typed it. A receipt therefore quotes him verbatim, every STAGED change carries his 60-minute veto (LAW 49), and the weekly review puts every receipt in front of him.
