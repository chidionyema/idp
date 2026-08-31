# Otto's Telegram webhook door

The Architect (hermes-agent gateway) receives Telegram updates by webhook, not polling
([tracked on the crew board](https://github.com/chidionyema/crew/issues/736); founder blueprint 2026-08-31T15:24Z: a poller is a single consumer, so every
deploy took the bot down; a webhook is an ordinary HTTP service and Telegram queues and
retries every POST the pod misses).

## How it works
- `platform/hermes-agent/gateway.yaml` sets `TELEGRAM_WEBHOOK_URL=https://otto.<zone>/telegram`;
  the pinned fork's adapter sees the variable, starts an HTTP server on port 8443 and registers
  the URL with Telegram itself (setWebhook) on every boot. No hand step, ever.
- The route is `platform/hermes-agent/httproute.yaml` (listener `https-otto` on the shared
  Gateway, `prospector/deploy/k8s/base/edge.yaml`). external-dns writes the DNS record,
  cert-manager adds the SAN to the one edge certificate. No console, no hand step.
- Every POST must echo the token Telegram was given in the `X-Telegram-Bot-Api-Secret-Token`
  header; the adapter drops anything else and refuses to boot without the token
  (GHSA-3vpc-7q5r-276h). The token is born in the cluster by ESO's Password generator
  (`hermes-agent-webhook`), never seeded, never in git.

## What a deploy looks like now
Reloader still rolls the pod (strategy Recreate, one writer of /data/state.db). While the pod
boots, Telegram holds the updates and retries; replies are delayed by the boot, none are lost,
and no banner is announced (hermes-v2 config.yaml `gateway_restart_notification: false`).

## If the bot goes quiet
1. `gh workflow run oke-check.yml -R chidionyema/idp -f mode=break-glass -f playbook=architect-doctor`
   and read gateway-log in the run: webhook mode prints `Webhook server listening on *:8443/telegram`.
2. Telegram's own view: the adapter logs `get_webhook_info` state; `pending_update_count`
   climbing with the pod Ready means the edge path is broken — check the `https-otto` listener,
   the route, and cert-manager's certificate in that order, from the run's playbook output.

## Rollback
Revert the idp pull request: the env vars disappear, the adapter falls back to polling and deletes the
stale webhook registration itself on connect (`_delete_webhook_best_effort`). The listener and
route can stay; they serve nothing.
