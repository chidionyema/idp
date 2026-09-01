# Onboarding: Fan-out notifications with Apprise

## What it is

Apprise API is the platform's single notification endpoint. A surface sends one POST to
`/notify/founder-telegram` with a title and body. The platform fan-out reaches Telegram, Slack,
email, Discord or any service Apprise supports. Every channel owns its own delivery URLs and
credentials, stored in the vault as `notify-apprise-<channel>`. Callers never learn what they are.

## What it costs

No cost for using it. Slack and email incur no platform overhead; Telegram is on the founder's
personal account. Each new channel URL is one vault entry and one line in
`platform/notify/external-secret.yaml`.

## Where it lives

```
platform/notify/namespace.yaml          The isolated Apprise namespace
platform/notify/apprise-api.yaml        Two-replica Deployment, health-checked
platform/notify/external-secret.yaml    Channel URLs read from the vault
platform/notify/kustomization.yaml      Wires the above, one Kustomization
clusters/oke/platform.yaml              notify row, depends on secret-store
backstage/platform/catalog-info.yaml    Generated; lists notify as Layer/Observability
```

## How to add a new channel

### Founder-Telegram (seeded at apply time)

1. Get a Telegram bot token from https://t.me/BotFather.
2. Get your chat ID by sending a message to the bot and calling
   `curl https://api.telegram.org/bot<TOKEN>/getUpdates`.
3. Put the Apprise URL in the GitHub Actions secret `SEED_NOTIFY_APPRISE_FOUNDER_TELEGRAM` on
   `chidionyema/idp` (Settings → Secrets and variables → Actions).
   Format: `tgram://bottoken/chatid/`
4. The next `oke-check apply` seeds the vault and the pod rolls automatically (Reloader).

### Slack webhook

1. Create a Slack app at https://api.slack.com/apps?new_app and enable Incoming Webhooks.
2. Create a webhook for your channel and copy the URL.
3. Put it in the GitHub Actions secret `SEED_NOTIFY_APPRISE_SLACK`.
   Format: `slack://webhook-url/`
4. Add the following to `platform/notify/external-secret.yaml`:
   ```yaml
   - secretKey: slack
     remoteRef: { key: notify-apprise-slack }
   ```
5. Apply. The endpoint `/notify/slack` becomes available.

### Email via SMTP

1. Get an SMTP server address, port, username and password from your provider.
2. Put the URL in the GitHub Actions secret `SEED_NOTIFY_APPRISE_EMAIL`.
   Format: `mailtos://user:password@smtp.provider.com?from=your@email.com`
3. Add the entry to `external-secret.yaml` like Slack above.

## How to send a notification

```python
import requests

response = requests.post(
    "http://apprise.notify.svc:8000/notify/founder-telegram",
    params={"title": "Alert", "body": "Something happened"},
)
assert response.json()["success"]
```

Or from the command line:

```bash
curl -X POST http://apprise.notify.svc:8000/notify/founder-telegram \
  -d "title=Alert&body=Something%20happened"
```

## How to turn it off

Delete the GitHub secret `SEED_NOTIFY_APPRISE_FOUNDER_TELEGRAM` and comment out the entry in
`external-secret.yaml`. The next apply removes the channel URL from the vault; the pod continues
running but that channel never fires.

To disable the entire notify platform row, remove the `notify` row from
`clusters/oke/platform.yaml` and apply. That whole area of the cluster, and everything in it, is removed.

