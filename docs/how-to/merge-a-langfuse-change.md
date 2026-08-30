# Merge a change to Langfuse

A pull request that touches `platform/observability/langfuse*` carries the required check
`verify/verdict-fresh` (crew#631 CP6). It passes only when the newest completed run of
`verdict-langfuse.yml` on main left a signed verdict whose outcome is PASS and whose age is under
its TTL (3600 s). Any other pull request runs the same job, which prints
`ok      verdict-fresh  no langfuse file in this change` and passes.

## When the check is red

The line names the state and the one command:

    FAIL    verdict-fresh  langfuse UNVERIFIED run 33259130598 on docker.langfuse.com/lang: expired: 4100s old, ttl 3600s; a new verdict is one command: gh workflow run verdict-langfuse.yml

1. `gh workflow run verdict-langfuse.yml` and wait for it (`gh run watch`).
2. If the new verdict is FAIL, Langfuse is broken now; fix that first (the failed assertion is in
   the run's summary and its `verdict-langfuse` artifact). A red gate on a broken Langfuse is the
   gate doing its job: nothing lands on top of a service nobody has proved works.
3. Re-run the pull request's `verify/verdict-fresh` job.

`BLIND` (exit 2) means no completed prover run exists on main; the same command mints one.

## Where the requirement lives

`platform/github/ruleset.idp.required-checks.json` lists the context; `bin/repo-rulesets`
reports drift and `bin/repo-rulesets --apply` installs it. The comparison includes each rule's
parameters, so a required-check list edited in the GitHub settings page shows as DRIFT.

## Try it locally

    bin/idp-verdict-fresh langfuse --changed platform/observability/langfuse.yaml
    bin/idp-verdict-fresh langfuse --changed bin/idp-ci      # off the surface: ok
