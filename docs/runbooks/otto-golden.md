# Otto staging, the bot token

Otto staging (`platform/otto-golden/`) is a second, separate pod from the production Architect
gateway. It has its own area of the cluster and its own webhook path, running the new boot process
ahead of production. It needs one thing only a person can give it: a Telegram bot token.
Everything else in this lane — its own area, the fences, the route, the deployment — ships from
git and needs no hand.

## What runs today
The Deployment (`platform/otto-golden/deployment.yaml`) runs one pod, one replica, listening on
port 8080 for `GET /healthz` and `POST /telegram-webhook`. The route
(`platform/otto-golden/httproute.yaml`) exposes exactly those two paths on the shared
`otto.<zone>` host, next to the production gateway's own `/telegram` path. The bot token arrives
as a vault-fed secret (`platform/otto-golden/telegram-secret.yaml`), mounted as a file, never as
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
     anywhere but Bitwarden in the next step: not this page, not a chat, not a ticket, not a
     log.

2. **Hand the token to Bitwarden**, straight from the same phone, through the human door
   (decision 0017; the old env-file hand was retired 2026-09-02 on the founder's word):
   open the Bitwarden web vault in the phone's browser, go to Secrets Manager, and add a
   secret named `otto-staging-telegram` in the estate project whose value is the token,
   exactly as `docs/how-to/bitwarden-human-vault.md` walks through. The vault-fed secret in
   git already names this exact secret (`otto-staging-telegram`, store `human-vault`), so the
   cluster pulls it on its own within 10 minutes and Reloader rolls the pod. Nothing is
   typed into a terminal and no file ever holds the token.

Until step 2 runs, the vault-fed secret's own status names the missing vault entry by name. No
token value ever appears in that status, in a log, or on this page.

## The webhook door is locked at the gateway, not in the pod

The pod never sees an unauthenticated webhook and holds no auth code at all (founder edict,
2026-09-02: auth is infrastructure physics). The route
(`platform/otto-golden/httproute.yaml`) forwards `POST /telegram-webhook` only when the
request carries `X-Telegram-Bot-Api-Secret-Token` exactly equal to the vault value
(`otto-staging-telegram`, property `webhook_secret`, rendered for substitution by
`platform/otto-golden-secret/webhook-substitution.yaml`). A missing or wrong header is
dropped at the edge and never reaches the pod.

The webhook secret is machine-born, unlike the token: code minted it into the estate vault
2026-09-02 (`otto-staging-telegram`, property `webhook_secret`) and no person has ever seen it.

**Connecting the webhook** (after deploy, one call): Telegram must be told the URL AND the
same secret, or every delivery will be dropped by the gateway. The registration step reads
the `webhook_secret` value from the vault and calls Telegram's `setWebhook` with
`url=https://otto.<zone>/telegram-webhook` and `secret_token` set to that value — read by
code, never typed and never printed. Telegram then echoes the secret in the header on every
delivery. Rotating the secret is the same two steps in the same order: vault first,
`setWebhook` second.

## If the webhook goes quiet
Read the pod's own health first: `GET https://otto.<zone>/healthz` answers from the edge whether
or not Telegram can reach it. If `/healthz` answers but updates stop arriving, the fault is
between Telegram and the edge (the route, the listener, or the token in step 2 above going stale);
if `/healthz` itself stops answering, the fault is the pod, and `kubectl -n otto-golden get pods`
is the next read.

## Rollback
This is a staging lane behind its own area of the cluster and its own path. Reverting the pull
request that added `platform/otto-golden/` removes that area, the route and the pod together, and
touches nothing the production Architect gateway (`platform/hermes-agent/`) depends on.
