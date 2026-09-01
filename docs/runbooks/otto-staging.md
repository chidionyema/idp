# Otto staging, the bot token

Otto staging (`platform/otto-staging/`) is a second, separate pod from the production Architect
gateway. It has its own area of the cluster and its own webhook path, running the new boot process
ahead of production. It needs one thing only a person can give it: a Telegram bot token.
Everything else in this lane — its own area, the fences, the route, the deployment — ships from
git and needs no hand.

## What runs today
The Deployment (`platform/otto-staging/deployment.yaml`) runs one pod, one replica, listening on
port 8080 for `GET /healthz` and `POST /telegram-webhook`. The route
(`platform/otto-staging/httproute.yaml`) exposes exactly those two paths on the shared
`otto.<zone>` host, next to the production gateway's own `/telegram` path. The bot token arrives
as a vault-fed secret (`platform/otto-staging/telegram-secret.yaml`), mounted as a file, never as
a pod environment variable — the cluster's own admission policy refuses the latter.

## Founder action — create the bot and hand over its token

This is the one physical step; nothing else in this lane waits on a console.

1. **Create the bot with @BotFather**, in Telegram:
   - Open a chat with `@BotFather` and send `/newbot`.
   - It replies: *"Alright, a new bot. How are we going to call it? Please choose a name for your
     bot."* Send the display name (anything; changeable later).
   - It replies: *"Good. Now let's choose a username for your bot. It must end in `bot`. Like this,
     for example: TetrisBot or tetris_bot."* Send a username ending in `bot` (this one cannot be
     changed later).
   - It replies: *"Done! Congratulations on your new bot. ... Use this token to access the HTTP
     API: `<token>`"* — that token is the one secret this runbook exists for. Do not paste it
     anywhere but the env file in the next step: not this page, not a chat, not a ticket, not a
     log.

2. **Hand the token to the vault**, from a shell with estate access, using the same tool every
   other estate secret is seeded with rather than a console step:
   ```
   printf 'OTTO_STAGING_TELEGRAM_BOT_TOKEN=%s\n' '<token from BotFather>' >> "${ESTATE_ENV_FILE:-$HOME/.estate/.env}"
   bin/idp-vault-put otto-staging-telegram token=OTTO_STAGING_TELEGRAM_BOT_TOKEN
   ```
   `bin/idp-vault-put` is the estate's one sanctioned way to seed a vault entry (the same tool
   that seeded `flux-telegram` and every other estate secret); it reads the named key from the env
   file, writes it to the vault, and prints only the key name back — never the value. The
   vault-fed secret in git already names this exact vault key (`otto-staging-telegram`, property
   `token`). The next sync (10 minutes, or `kubectl annotate -n otto-staging externalsecret
   otto-staging-telegram force-sync=$(date +%s) --overwrite` for immediately) creates the
   Kubernetes Secret and Reloader rolls the pod.

Until step 2 runs, the vault-fed secret's own status names the missing vault entry by name. No
token value ever appears in that status, in a log, or on this page.

## If the webhook goes quiet
Read the pod's own health first: `GET https://otto.<zone>/healthz` answers from the edge whether
or not Telegram can reach it. If `/healthz` answers but updates stop arriving, the fault is
between Telegram and the edge (the route, the listener, or the token in step 2 above going stale);
if `/healthz` itself stops answering, the fault is the pod, and `kubectl -n otto-staging get pods`
is the next read.

## Rollback
This is a staging lane behind its own area of the cluster and its own path. Reverting the pull
request that added `platform/otto-staging/` removes that area, the route and the pod together, and
touches nothing the production Architect gateway (`platform/hermes-agent/`) depends on.
