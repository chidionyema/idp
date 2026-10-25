# A dependency advisory is judged against the diff that brought it

Date: 2026-10-25. Issue: [idp#7080](https://github.com/chidionyema/idp/issues/7080).

## The defect

`bin/estate-security-scan` fails on every published advisory it finds in a pin, whoever
introduced it and whenever it appeared. Measured 2026-10-24: two advisories in the estate's own
pins, both pre-existing on `main`, made every Greenlane candidate red on `ci-success` — so
nothing could land, including the very lane that would fix the advisory. A gate that no change
can pass is not a gate; it is a wall.

## The fork

Two ways to tell whether an advisory is a change's own:

1. **Re-audit the base.** Check out the base ref, run the audit there, compare the advisory
   sets. Truthful about the base's advisories, but it costs a full resolution and a full
   advisory fetch for a tree nobody is changing, and it answers a subtly different question:
   the base is re-measured against *today's* advisory database, so the comparison is against a
   moving target, and it burns the CI minutes the scan already spends.
2. **Compare the pins.** The same package at the same version is the same code, so it carries
   the same advisory; the diff did not bring it. The two refs' own trees are read from git: no
   network, no advisory database, no resolution, and the answer is exactly the question the
   gate asks — *did this change move a vulnerable pin?*

**Chose (2).** The judgement has to be deterministic and cheap enough to run on every
candidate, and the pin is the thing the change actually owns.

## The shape

`ESTATE_DEPS_BASE` names the ref a change is measured from:

| the change is | the base is |
|---|---|
| a candidate on `queue/**`, a merge-queue build | `origin/main` |
| a push to `main` | `github.event.before` — the commit `main` was before |
| anything else, or no base | none: every advisory gates, exactly as before |

A base that does not resolve here (a first push, an all-zero `before`) **widens** the
judgement: every advisory gates. The gate may only ever get more careful, never less.

An advisory whose package is pinned the same way on both refs is **pre-existing**: it is
reported — named, versioned, printed in the receipt — and deferred. An advisory whose pin the
change moved, or on a package the base did not pin at all, is the change's own and fails
exactly as it did before.

For python the comparison is the `name==version` pin in `requirements*.txt`; for npm it is the
resolved version of the package in `package-lock.json`, both sides read from the refs' own
trees.

## What this is not

- It is **not a dismissal**. The advisory is still reported, still named, still visible on every
  run. What changes is that it no longer holds a change that did not bring it.
- It does **not** say the estate is clean. A deferred advisory is still an advisory, and the
  receipt says so in those words.
- It does not touch anything but dependency pins. Secrets, gitleaks and the manifest policy
  are unchanged, and they still fail a change that brings them.

## The limit, stated

The comparison is over pins. A vulnerable package that arrives **transitively** — not pinned
directly, but resolved in — has no pin to compare, so its finding is never deferrable and
always gates. That is the conservative direction (it fails), and it is the right one: the
estate prefers a false refusal to a silent pass.

## The other half

Deferring a pre-existing advisory does not remove it, and nobody owned the pin that carried
it. So `bin/advisory-remediation` turns an advisory with a fix version into a lane carrying
only the bumped pin, and a scheduled workflow runs it daily. The lane is proved green on top
of `main` by the Greenlane like any other lane, so a bump that breaks the resolution never
lands. A major bump is an API change, so it is reported and left to a human.

## The cost

- The gate is now two steps instead of one, and the second reads two refs. That is a few
  seconds of `git show`, not minutes.
- A change that moves a pin in a way that keeps the package vulnerable still fails, because
  the pin differs. That is intended: the pin moved, so the change owns it.
- The deferral is visible in the receipt, so an operator can see how many advisories are
  being held, and the remediation lane is what brings the number down.
