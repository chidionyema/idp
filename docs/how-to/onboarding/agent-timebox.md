# Onboarding: agent timebox

LAW 32 (founder 2026-08-25): every feature ships with this onboarding so
the portal shows the founder the path, not just the code. This page is
the half of LAW 32 the onboarding carries.

## When you would run this

`agent-timebox` exists to agent timebox. Run it from the repo root on any machine
with `bin/` on PATH; the script reads its config from the environment
and from this checkout.

## The one-line answer

```
bin/agent-timebox --help
```

That prints the script's argument list. From there the script's
specific flag set is documented in `--help`. The `--self-test` flag is
always available and exercises the import path -- it is what the
pre-push hook runs to confirm the script loads after every change.

## If it broke

A failing `--self-test` means a dependency is missing or the
surrounding code drifted. Re-run `bin/idp-install-deps` to refresh
the tool set; if that does not help, the most recent commit touching
this file is the place to start.
