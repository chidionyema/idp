# LAW 32 gate — what it is, what it costs, how to stop it

## What it is for

Every feature ships with two pages written for one reader on a phone: a demo with
real output, and an onboarding that says what it costs and how to turn it off. The
push-time hook only recognised `feat:` commit subjects; on 2026-08-25 five features
merged under `security:` and `catalog:` and it never fired. This gate runs at the
pull request instead, where a session cannot skip it, and it also checks that the
pages are in the portal's nav, because fourteen pages that nobody could open had
been sitting in the repository for a day.

## What it costs

Nothing recurring. One Python file, under a second, inside `bin/idp-ci` on every
pull request. The CI checkout now fetches full history (`fetch-depth: 0`) so the
gate can diff the branch against `origin/main`; that adds a few seconds per run.

## What it watches or changes

It reads the list of files added under `bin/` in the pull request, every page
under `docs/demo` and `docs/onboarding`, and `mkdocs.yml`. It changes nothing.

## Where it lives

```
bin/law32-gate          the check; --added f1 f2 overrides the diff for proofs
bin/idp-ci              the row that proves it both ways and runs the real diff
.github/workflows/ci.yml   fetch-depth: 0 so the diff has a base
mkdocs.yml              Demo and Onboarding sections, one line per page
```

## How to turn it off

```
sed -i '' '/law32-gate/d' bin/idp-ci
```

## How to turn it back on

`git checkout main -- bin/idp-ci`.

## What goes wrong

A bin file whose feature name is not a hyphen-prefix of the file name (for example
`db-gen`, which belongs to the portal feature `idp`) is refused until a pair named
for it exists. That is deliberate: the founder should be able to find the page by
the command's name. Twenty-two files that predate the gate have no pair; they are
listed in the pull request that added it and are not refused, because the gate only
binds files added from now on.
