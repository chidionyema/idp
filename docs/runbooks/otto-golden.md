# Otto staging, the bot token

Otto staging (`platform/otto-golden/`) is a second, separate pod from the production Architect
gateway. It has its own area of the cluster, running the new boot process ahead of production.
It needs one thing only a person can give it: a Telegram bot token. Everything else in this
lane — its own area, the fences, the route, the deployment — ships from git and needs no hand.

**Since crew#768 it does not receive Telegram.** A channel arrives in exactly one place in this
estate, the Universal Event Gateway (`platform/otto-gateway/`, `POST /webhook/telegram`), and
this namespace's own `/telegram-webhook` route is gone. Two processes able to receive the same
channel meant two address books and two places the channel word lived; that is the thing the
one-door design exists to remove. For everything about how a message now arrives, is
recognised and is answered, read `docs/explanation/customer-event-door.md`.

## What runs today
The Deployment (`platform/otto-golden/deployment.yaml`) runs one pod, one replica, listening on
port 8080. The route (`platform/otto-golden/httproute.yaml`) exposes one path on the shared
`otto.<zone>` host: `GET /healthz`, which is what the availability probe reads. The bot token
arrives as a vault-fed secret (`platform/otto-golden/telegram-secret.yaml`), mounted as a file,
never as a pod environment variable — the cluster's own admission policy refuses the latter.

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

## Where the webhook now lives

The channel door, the credential that locks it and the list of who is recognised on it all
belong to `platform/otto-gateway/` now, and none of them are a hand step:

- The route is `POST /webhook/telegram` on the same `otto.<zone>` host, authenticated at the
  edge against `X-Telegram-Bot-Api-Secret-Token` (founder edict, 2026-09-02: auth is
  infrastructure physics, the app holds no auth code). The webhook secret is machine-born —
  code minted it into the estate vault on 2026-09-02 (`otto-staging-telegram`, property
  `webhook_secret`) and no person has ever seen it.
- Registering that URL with Telegram is not a call anybody makes.
  `platform/otto-gateway/registration-reconciler.yaml` runs every five minutes, asks
  Telegram where the webhook actually points, and calls `setWebhook` itself when the answer
  is not this estate's door. It holds the bot token as a mounted file, so the credential
  never reaches a person, a terminal or a log line. Rotating the webhook secret is one vault
  write; the next poll carries it to Telegram.
- Who the bot recognises is a row in the `channel_binding` table, not a config file:
  `principal_allowlist` maps a chat id to a principal name. A sender who is not on it still
  reaches the estate, but as `principal:unknown` carrying the untrusted taint, which caps
  what the message may authorise at tier T1. Adding an operator is one database write.

## If the webhook goes quiet
Read the door's own health first: `GET https://otto.<zone>/healthz` answers from the edge
whether or not Telegram can reach it. If it answers but updates stop arriving, read the
reconciler's last run — its one output line carries `registration_ok`, `pending_updates` and
`repaired`, and the same three arrive at the collector as
`channel_registration_ok`, `channel_pending_updates` and `channel_registration_repaired`. A
`repaired` count that keeps rising means something outside this repository is re-pointing the
webhook. If `/healthz` itself stops answering, the fault is the pod.

## Rollback
This is a staging lane behind its own area of the cluster and its own path. Reverting the pull
request that added `platform/otto-golden/` removes that area, the route and the pod together, and
touches nothing the production Architect gateway (`platform/hermes-agent/`) depends on.
