# Otto

One pinned Telegram card, edited in place, plus one line message per live
session, collapsed when the session ends. Owner: builder B. See
`sovereign/CONTRACT.md` ("Otto card (B)") and
`features/sovereign-bus/cp4_otto_card.feature`, `cp22_everything_configurable.feature`.

## Files
- `card.py` — `on_change(state) -> {session_id: line_message_id}`, sync,
  never raises, never calls the engine back (A stores the id itself, no
  workflow reentrancy). httpx timeout capped at `telegram.request_timeout_s`
  (<=5s); `httpx`'s own logger forced to WARNING at import (LAW 21: its
  INFO logs put the bot token in the URL). State in
  `$ESTATE_HOME/sovereign/otto.json` (`card_message_id`, `sends`, `edits`
  — card-only counters — `lines`, `sessions_cache`).
- `cli.py` — `sb card [--json]`, `sb card-reset`, `sb install-plugin`.
- `hermes_plugin/` — hermes-agent plugin: `sb-list/show/stop/approve/deny/steer`,
  each shelling `$IDP/bin/sb <verb> ... --json`. `$IDP` is resolved from the
  plugin's own real path (it runs as a symlink), never an env var.
- `config_keys.py` — cp22: every otto/telegram literal as `OTTO_KEYS =
  {key: (default, type, env_name, help)}`; `get(key)` resolves env-or-default
  standalone, `sovereign/config.py` merges it in for `sb config --lint`.

## Config
Adopting: if `otto.json` is absent and `SB_ADOPT_CARD_ID` is set, that id
seeds `card_message_id` so the first `on_change` edits the existing pinned
message instead of sending a new one.
`card.py`/`cli.py` prefer `sovereign.config` (owner: A) when importable,
else `TELEGRAM_BOT_TOKEN`/`TELEGRAM_HOME_CHANNEL`/`ESTATE_HOME`/
`ESTATE_PUBLIC_URL` env or `$ESTATE_ENV` — standalone before `config.py`
exists. `_list_sessions` prefers `sovereign.engine.client.list_sessions()`,
else `otto.json`'s own `sessions_cache`. Never prints a secret.

## Proving it
```
sb card --json                       # card_message_id, sends, edits
sb card --json                       # after a change: id unchanged, edits +1, sends unchanged
sb install-plugin --json             # symlinks into $HERMES_HOME/plugins/sovereign
bin/sb config --lint | grep otto     # cp22: only config_keys.py lines
```
