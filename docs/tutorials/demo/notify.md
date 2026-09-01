# Demo: Apprise API, one endpoint to everywhere (R75)

Apprise publishes once and delivers to Telegram, Slack, email, Discord and 100+ other services
from a single HTTP POST. The platform names the channels in the vault and never exposes a backend
URL or key to the caller. A surface posts to `/notify/founder-telegram` and reaches the founder's
phone every time.

The live channel URLs live in the vault as `notify-apprise-*` entries; each surface reads the
Apprise Service and never touches vault directly:

```
$ kubectl port-forward -n notify svc/apprise 8000:8000 &
[1] 12345

$ curl -X POST http://localhost:8000/notify/founder-telegram \
  -d 'title=Test&body=The%20founder%20sees%20this&format=json'
{"success": true, "delivered": 1}

$ curl http://localhost:8000 | head -5
200 OK / Apprise Notification Gateway
POST /notify/<channel>?title=X&body=Y to send. GET / lists available endpoints.
...
```

The control that the channel only fires when the vault holds the key:

```
$ .venv/bin/pytest -o addopts= -q tests/test_incident_crew75_apprise_fan_out.py::test_notify_uses_vault_key
.
1 passed in 2.14s
```

The catalog lists the `notify` platform component as a Layer under Observability, and the key is
seeded once at apply time:

```
$ bin/idp-bootstrap-vendors | grep -A2 "notify-apprise"
Secret "notify-apprise-founder-telegram" does not exist; seeding from SEED_NOTIFY_APPRISE_FOUNDER_TELEGRAM
✓ Seeded notify-apprise-founder-telegram (tgram://...)
```

A breach or rotation: the vault key rolls at refresh (every 10 minutes, external-secret.io default),
and the pod rolls automatically (Reloader watches the Secret). No hand step.

