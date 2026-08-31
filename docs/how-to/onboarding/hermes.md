# Onboarding: Cursor as Otto's WORK worker

## What it is

Otto's WORK jobs run Cursor CLI on the founder's Mac (`agent -p --force`). The
pod reaches the Mac through `cursor-agent`, which reads `CURSOR_API_KEY` from
the vault file and passes it on ssh stdin. Architect, Telegram and the watch
lane stay on the one model router. Cursor single sign-on is for people in a
browser; it does not mint this key.

## What it costs

Cursor usage on the key, billed on Cursor's usage page. No extra cluster
compute: the wrapper is a hashed ConfigMap next to `mac-run`. Until the seed
exists, WORK fails closed (exit 2) and nothing is charged.

## Where it lives

```
platform/hermes-agent/estate.yaml          dispatch.runtime: cursor
platform/hermes-agent/cursor-agent.tpl     vault key required; execs mac-run then agent
platform/hermes-agent/gateway.yaml         subPath mount of cursor-agent
platform/vendors/consoles.yaml             SEED_CURSOR_API_KEY, dashboard page, verify GET /v1/me
backstage/founder/catalog-info.yaml        founder-cursor card, dependsOn vendor-cursor
docs/reference/policy/credential-lifecycle.md   the SEED_CURSOR_API_KEY row
```

## Direct login (no automation)

1. Open https://cursor.com/dashboard/integrations and create an API key.
2. Put the value in the GitHub Actions secret `SEED_CURSOR_API_KEY` on
   `chidionyema/idp` (Settings → Secrets and variables → Actions).
3. The next `oke-check` apply (`bin/idp-bootstrap-vendors`) proves the key and
   writes vault field `hermes-agent-env.CURSOR_API_KEY`.

Do not paste the key into chat, into git, or onto a command line. Do not use
this Mac's Cursor IDE login. Do not run a laptop set-root command.

## How to turn it off

Set `dispatch.runtime` in `platform/hermes-agent/estate.yaml` back to `claude`
and ship that change. Delete the dashboard key to revoke. Removing the GitHub
secret stops the next apply from refreshing the vault field; the wrapper then
refuses WORK until a new key is seeded.

Tracked on [this ticket](https://github.com/chidionyema/crew/issues/751).
