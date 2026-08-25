# Cockpit — one screen: Sessions, Decisions, Inbox
Stdlib `http.server` (`server.py`), single-file Mini App (`index.html`,
<400 lines, no frameworks), Telegram initData auth (`auth.py`), `bin/sb
cockpit/menu/tunnel` (`cli.py`), every literal named once in
`config_keys.py` (cp22). Spec: `sovereign/CONTRACT.md`, `cp7_cockpit.feature`,
`cp22_everything_configurable.feature`.
## Run
```
bin/sb up       # temporal dev server + worker, if not already running
bin/sb cockpit  # serves $COCKPIT_PORT (default 8788), loopback
```
launchd: `bin/idp-install-launchd` loads `ai.estate.cockpit.plist.tmpl` (KeepAlive true; blocks forever, unlike the one-shot jobs).
## Prove it (cp7 / cp22)
```
curl -s localhost:$COCKPIT_PORT/healthz          # -> ok
curl -s localhost:$COCKPIT_PORT/api/sessions     # == bin/sb list --json
curl -X POST .../api/sessions/<id>/stop -d '{"by":"founder"}'
bin/sb show <id> --json                          # stopped, within 5s
curl -s localhost:$COCKPIT_PORT/api/inbox        # tail of $ESTATE_ALERT_INBOX
curl -s localhost:$COCKPIT_PORT/api/config       # non-secret cockpit./telegram. keys
```
## Tests — 36, all passing
```
PYTHONPATH=$IDP sovereign/.venv/bin/python -m unittest \
  sovereign.cockpit.test_auth sovereign.cockpit.test_server \
  sovereign.cockpit.test_config_keys -v
```
`test_server.py` fakes `sovereign.engine.client` via `sys.modules` on a real
loopback socket. `test_auth.py` HMAC-verifies a built initData and checks
`init_data_max_age_s` freshness. Mutation-proved: reverting the HMAC check,
the max-age check or the `/api/*` gate fails its test.
## Config (cp22)
Port, bind, poll interval, inbox tail, initData max age, Telegram API base
URL, Mini App bootstrap URL, menu-button label: all in `config_keys.py`'s
`COCKPIT_KEYS` (config → env → default). `GET /api/config` returns them, no
token/key/secret-shaped key, so `index.html` reads its poll interval rather than hardcoding it.
## Auth
`X-Telegram-Init-Data` present → HMAC-SHA256 verified, freshness checked, user id checked against `TELEGRAM_ALLOWED_USER_IDS`/`_USERS`, else 401. No header + loopback → allowed. No header + not loopback → 401. Token/initData never logged. Not done: `/s/<id>` server templating, rate limiting.
