# Onboarding: pr-report

## What it is

`bin/pr-report <n> [--comment]` reads pull request `n` with `gh` (body, labels,
changed files, added lines), writes `reports/pr.json`, and runs
`conftest test -p policy` over it. The budget the cost rule compares against is
`estate-defaults.yaml` `infrastructure.monthly_cap_usd`; the script never holds a
number of its own. With `--comment` it posts every deny line as one PR comment.

## What a PR body needs

- `Approval-word: <word>` when the PR touches `backstage/`, `platform/identity/`,
  `platform/edge/`, `docs/policy/` or `estate-defaults.yaml`. The founder answers
  `APPROVE: <word>` or `DENY: <word>`.
- `Cost-delta-usd-month: <number>` when the PR touches `platform/oci/` (0 for a
  change that costs nothing), and the `canary` label
  (`gh pr edit <n> --add-label canary`).
- A grant, policy or group membership in the same diff as any new identity
  resource (`oci_identity_user`, `oci_identity_domains_app`, ...).
- No instruction line (`FOUNDER ACTION:`, `STAGED:`, `Use:`) that says sign in,
  click, console, dashboard or browser. Express the step as a command, a
  Terraform block or an approval word; if you lack the privilege, open a
  privilege-elevation issue in the shape of crew#287.

## Run it before you push

```
$ bin/pr-report 163
PASS    operating-model gate #163
```

A non-zero exit prints one `rule=... | ... | fix: ...` line per violation. Fix the
body or the diff and run it again; nothing else is needed.

## Where it runs

`.github/workflows/ci.yml` job `operating-model-gate`, on every pull request, with
`pull-requests: write` so it can comment. The fixtures that prove each rule both
ways live in `policy/fixtures/opmodel-*.json` and run under `bin/policy-test`.
