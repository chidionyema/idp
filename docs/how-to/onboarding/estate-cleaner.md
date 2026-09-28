# Onboarding: estate-cleaner

## What it is

`bin/estate-cleaner` proposes cleanup candidates on a repository — remote topic
branches that have no open pull request and are likely dead ends — as a strict
dry-run suggestion list. It is slot 6 of the seven-agent local ops tier
(crew#929, roster in `docs/ops/local-ops-tier-roster.md`).

## Why it exists

Branch accumulation is the recurring housekeeping scan a 24/7 tier should own:
finding which pushed topic branches no longer back any work, so they can be
archived before the repository drowns in them. The cleaner names the candidates
and who must confirm; it never performs the deletion.

## What it considers a candidate

A remote branch is proposed for archive only when all of these hold:
- it is not `main`, `dev`, or `HEAD`;
- it does not back an open pull request (checked live against `gh`);
- it is not under the intentional archive namespace (`backup/`, `archive/`) —
  that is the recycle bin, not drift;
- it is a feature-looking topic branch name.

Anything else is left alone. `backup/` branches already archived are not
harassed with a second proposal.

## The contract

- Output is always a suggestion list with an owner-confirm line per candidate,
  in `--dry-run` shape. The cleaner never deletes or force-pushes.
- A "cleanup" that carries no owning review line is a refusal, not a suggestion.
- Destructive action (deleting a branch) stays with a human driver or an
  explicitly authorized executor — never this suggest-only slot.
- State is read live each run (git remote refs + `gh` open PRs), so the
  proposal is about the repository as it is now.
