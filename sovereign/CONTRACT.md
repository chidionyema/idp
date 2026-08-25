# Sovereign Bus — build contract (2026-08-25)

Everything under `idp/sovereign/` and `idp/bin/sb`. Specs: `features/sovereign-bus/cp1..cp13` (cp8–cp13 added after Master Spec v1.0 review; phase 2 after cp1–cp7 are green).
Python 3.10+, venv at `sovereign/.venv` (created by `bin/sb` on first run via `uv venv` + `uv pip install -r sovereign/requirements.txt`).
Deps: temporalio, httpx, langfuse (optional, guarded import). Nothing else.

## Layout (one owner per directory)
- `sovereign/engine/`  (owner: builder A)  Temporal workflow + activities + worker + client + receipts + runners + `cli.py`
- `sovereign/otto/`    (owner: builder B)  Otto card writer (Telegram Bot API via httpx) + hermes plugin
- `sovereign/cockpit/` (owner: builder C)  cockpit http server (stdlib http.server or aiohttp? -> stdlib only) + Mini App page + menu button
- `bin/sb`             (owner: A) bash shim: ensures venv, `exec sovereign/.venv/bin/python -m sovereign.cli "$@"`
- `sovereign/cli.py`   (owner: A) argparse; core subcommands; then `for m in (sovereign.otto.cli, sovereign.cockpit.cli): try import m; m.register(subparsers)`
- `launchd/ai.estate.temporal.plist.tmpl`, `launchd/ai.estate.sovereign-worker.plist.tmpl`, `launchd/ai.estate.cockpit.plist.tmpl` (A, A, C) — use `${IDP}` `${HOME}` `${PATH}` only, installed by `bin/idp-install-launchd`.

## Config (LAW 46 + cp22: EVERYTHING configurable; no literal of any kind outside config.py)
All keys live in `sovereign/config.py` as one table {key: (default, type, env_name, help)}; resolution order default < `$ESTATE_HOME/estate.toml` < env < CLI flag; `sb config`/`sb config set`/`sb config --lint` (A owns). Every timeout, threshold, count, model alias, path, surface toggle is a key. Secrets print as set/unset.
All from env with defaults computed at runtime, read in `sovereign/config.py` (A writes it, all import it):
- `ESTATE_HOME` default `~/.estate`; state dir `$ESTATE_HOME/sovereign/`
- `TEMPORAL_ADDRESS` default `127.0.0.1:7233` is NOT allowed as a literal — read `TEMPORAL_ADDRESS` env, else `f"{os.environ.get('TEMPORAL_HOST','localhost')}:{os.environ.get('TEMPORAL_PORT','7233')}"` — the point of cp6 grep is no `host:port` literal; a default port number alone is fine.
- `TEMPORAL_NAMESPACE` default `estate`; task queue `sovereign`
- `SB_RECEIPTS` default `$ESTATE_HOME/sovereign/receipts.jsonl`
- `ESTATE_ALERT_INBOX` default `$ESTATE_HOME/alerts/inbox.jsonl`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_HOME_CHANNEL` (the DM chat id) — loaded from `$ESTATE_ENV` default `~/.config/estate/estate.env` if not in env (parse KEY=VALUE, never print values)
- `ESTATE_PUBLIC_URL` (optional; the cloudflared tunnel URL for the Mini App)
- `COCKPIT_PORT` default 8788, `COCKPIT_BIND` default loopback
- `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` optional; if absent, tracing is a no-op that logs once.
- `LITELLM_BASE_URL`, `LITELLM_API_KEY` optional, for the `llm` runner.

## Engine API (A) — the only thing B and C may import from engine
`sovereign/engine/client.py`, async, all take/return plain dicts:
- `await start(task: str, runner: str = "echo", repo: str | None = None, by: str = "cli") -> dict{session_id}`
- `await list_sessions() -> list[dict]`  each: session_id, repo, task, step, status, runner, asking (str|None), started_at, updated_at, last_output (str, ≤500 chars), line_message_id (int|None)
- `await show(session_id) -> dict` same shape + stopped_by, reason, steps (list of {n, output, ts})
- `await signal(session_id, kind: Literal["stop","approve","deny","steer"], by: str, text: str = "") -> dict{ok}`
- `await set_line_message_id(session_id, msg_id: int)` (update handler on workflow, so B can store the chat message id durably)
- `await episodes(kind: str|None) -> list[dict]` from receipts
statuses: running | waiting | stopped | denied | done | failed

Workflow: `SessionWorkflow` id = `sb-<8 hex>`; loop over steps: run `runner.step(task, repo, step_n, steer_texts)` as an activity (heartbeating, retry policy, start_to_close 30 min); runner returns {output, done: bool, ask: str|None}. If ask: status waiting until approve/deny signal. Signals: stop/approve/deny/steer. Queries: state. Every state change appends a receipt `{ts, session_id, kind, by, text, step, status}` via activity and calls the "on_change" hook: activity `notify_change(state)` that tries `sovereign.otto.card.on_change(state)` if importable (B provides), never raises.

Runners (`sovereign/engine/runners.py`), chosen by name, in a registry dict; `echo` (returns task, done), `sleep` (sleeps N seconds parsed from task in 1-s heartbeat slices, done), `ask` (task "needs: X" -> ask=X on step 1; done on step 2), `claude` (subprocess `claude -p <task> --output-format text` in cwd=repo, done), `llm` (POST `{LITELLM_BASE_URL}/chat/completions` with model `SB_MODEL` default "ollama", done). Registry is the ONLY place a vendor name appears; engine/workflow.py and engine/client.py import no vendor.

## Otto card (B)
`sovereign/otto/card.py`: `on_change(state)` (sync, called from an activity; use httpx sync) — maintains `$ESTATE_HOME/sovereign/otto.json` {card_message_id, sends, edits, lines:{session_id: message_id}}. Card = pinned message; if `card_message_id` missing, send once and pin (unpinAll first), else editMessageText (ignore "message is not modified"). Per session: first change sends one line message and calls `set_line_message_id`; later changes edit it; done/stopped/denied collapse to one line. Inline keyboard: if ESTATE_PUBLIC_URL set, `web_app` buttons to `{url}/s/<id>`; else no buttons, card footer shows `/sb_stop <id>` etc. Existing pinned card message id 13659 in the DM may be adopted: if otto.json is absent and `SB_ADOPT_CARD_ID` env set, use it.
`sovereign/otto/cli.py`: `register(sub)` adds `card` (prints otto.json + `--json`), `card-reset`.
`sovereign/otto/hermes_plugin/` : a hermes-agent plugin dir (`plugin.yaml` + `__init__.py` with `register(ctx)`), registering commands `sb-list, sb-stop, sb-approve, sb-deny, sb-steer, sb-show` that shell out to `$IDP/bin/sb ... --json` and return a short text. Install = symlink into `$HERMES_HOME/plugins/sovereign` (document; `bin/sb install-plugin` does it, A exposes `install-plugin` by importing otto.cli).

## Cockpit (C)
`sovereign/cockpit/server.py` stdlib `http.server` + `ThreadingHTTPServer`, runs asyncio client calls via `asyncio.run` per request. Routes: `GET /` page, `GET /s/<id>` page focused on one session, `GET /api/sessions`, `GET /api/sessions/<id>`, `POST /api/sessions/<id>/{stop,approve,deny,steer}` JSON body {by, text}, `GET /api/inbox` (last 200 lines), `GET /healthz`. Page: single HTML file `sovereign/cockpit/index.html`, no external assets, loads Telegram `window.Telegram.WebApp` if present (script tag to telegram-web-app.js is allowed, it is Telegram's own), three panels Sessions / Decisions (waiting sessions with Approve/Deny) / Inbox, buttons POST and refresh every 3 s, dark+light. Identity: if `X-Telegram-Init-Data` present verify HMAC per Telegram docs with bot token and check user id ∈ TELEGRAM_ALLOWED_USER_IDS; if absent and request is from loopback, allow (laptop use).
`sovereign/cockpit/cli.py`: `register(sub)` adds `cockpit` (serve), `menu` (setChatMenuButton web_app to `$ESTATE_PUBLIC_URL`, `--json` prints getChatMenuButton), `tunnel` (prints the exact cloudflared commands to create a named tunnel; does not run them).

## Rules
- No secrets printed, ever. Tests assert presence only.
- No `/Users/`, no `host:port` literals in `sovereign/` or `bin/sb`.
- Each builder writes `sovereign/<dir>/README.md` (≤40 lines): what it is, how to run, how to prove it (the cp commands).
- Each builder proves its part with real commands and reports the exact output lines. Temporal dev server: `temporal server start-dev --db-filename $ESTATE_HOME/temporal/dev.db --namespace estate` (A adds `bin/sb up` that starts it if absent, and the worker).
- Do not touch files outside your directory except: A also owns bin/sb, sovereign/cli.py, sovereign/config.py, sovereign/requirements.txt, launchd/*temporal*, launchd/*worker*; C owns launchd/*cockpit*. Do NOT git commit; the coordinator commits.
