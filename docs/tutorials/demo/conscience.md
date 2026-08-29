# Demo: conscience

What the founder sees, with the command above each piece of real output
(2026-08-28, the CP5 worktree on the Mac; the hourly run measures the same on ubuntu).

## 1. The grade

```
$ bin/idp-conscience
ok    portable        exit 0                           green when == 0  [deny]
red   secure          exit 1                           green when == 0  [deny]
ok    enterprise      exit 0                           green when == 0  [warn]
ok    survivable      exit 0                           green when == 0  [deny]
ok    future-looking  stdout 0                         green when == 0  [warn]
BLIND research        exit 2 (BLIND)                   green when == 0  [warn]
ok    better          stdout 357                       green when >= 1  [warn]
score 5/7 tenets green -> reports/conscience.json (BLIND: a row could not be measured)
```

Exit 0 all green, 1 any red, 2 BLIND. `research` is BLIND here because the crew
checkout is not beside this worktree; the workflow checks crew out beside idp, so
the run on main measures it.

## 2. The line on every pull request

From idp#614, posted by `bin/pr-report --comment`:

```
🧠 7/7 — every tenet green; the estate is more itself than it was
```

## 3. The hourly run and its issues

`.github/workflows/conscience.yml` at `23 * * * *`. A red tenet opens
`conscience: <tenet> is red` (label `conscience`), comments while it stays red, and is
closed with the receipt line when it goes green. Never two issues for one tenet.

## 4. The founder's line, 07:23 every day

```
🧠 conscience 7/7, moved +1 since yesterday — every tenet green; the estate is more itself than it was
https://github.com/chidionyema/idp/actions/runs/<run>
```

## 5. The portal card

```
$ bin/idp-conscience --page
page docs/CONSCIENCE.md <- reports/conscience.json: 5/7, 1 readings in docs/conscience-history.jsonl
```

`docs/CONSCIENCE.md` opens with the score, then the table with red rows first, then
the trend, one row per daily render. The portal lists it under **Conscience** in the
nav. The daily run commits it through an auto-merge PR on `bot/conscience-page`.

## 6. Ask it

Comment `@conscience does this PR keep us portable?` on any idp issue. It answers
`🧠 …` from the tenets and the rules, through the estate router.

## Prove it both ways

```
$ bin/idp-conscience --selftest
ok    selftest good=0 (want 0) bad=1 (want 1) wish=2 (want 2, names LAW 44)
$ python -m pytest -q tests/test_incident_crew586_conscience_page_reads_the_receipt_and_lands_through_a_pr.py
4 passed in 1.08s
```
