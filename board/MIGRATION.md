# Board migration runbook: removing the login form

Phase 1 artefact under founder ruling R19 (migration-as-code, 2026-08-24): *"first-time setup is
allowed to be manual, but it must generate a structured migration doc before automation is
written."* This is that doc. **No automation exists yet and nothing below has been run.**

`idp/docs/decisions/0001-gateway-api-is-the-routing-standard.md` cited this file as the record of
the board's login blocker. The file did not exist. That is why the founder had to ask twice, and
it is tracked as crew#185.

## Current state, measured 2026-08-24

```
$ curl -sI http://localhost:3300/ | head -2
HTTP/1.1 302 Found
Location: http://localhost:3300/login

$ docker ps --format '{{.Names}}\t{{.Ports}}' | grep kanboard
kanboard	443/tcp, 127.0.0.1:3300->80/tcp
```

### Everything the running board depends on

Read from `kanboard.yml` and `docker inspect kanboard` on 2026-08-24.

| Thing | Value | Notes |
|---|---|---|
| Image | `kanboard/kanboard:v1.2.46` | pinned, AGPL-3.0 |
| Container | `kanboard` | compose project `board`, service `kanboard` |
| Compose file | `idp/board/kanboard.yml` | working dir `idp/board` |
| Published port | `127.0.0.1:3300 -> 80/tcp` | already loopback-only; compliant with R20 |
| Also exposed | `443/tcp` | container-internal only, not published |
| Volume | `./data -> /var/www/app/data` | **the entire database**, `db.sqlite`. gitignored |
| Volume | `./plugins -> /var/www/app/plugins` | currently empty |
| Memory cap | `512m` | the laptop is slow; this was deliberate |
| Restart policy | `unless-stopped` | |
| Env set today | `PLUGIN_INSTALLER=true` | **no auth or session variable is set at all** |
| API | JSON-RPC at `/jsonrpc.php` | token lives in the sops vault, never in the compose file |

Confirmed by `docker inspect kanboard`: none of `REVERSE_PROXY_AUTH`, `REVERSE_PROXY_USER_HEADER`,
`SESSION_DURATION`, `REMEMBER_ME_AUTH` or `HIDE_LOGIN_FORM` is currently set.

### The one piece of state that matters

`idp/board/data/db.sqlite` is the whole board. It is gitignored and it is not backed up anywhere
else. **Every step below is preceded by copying it.** R19 law 2 — zero unintended side effects —
means this migration must not be able to lose a card.

## Target state

From `idp/docs/decisions/0003-identity-is-oidc-and-the-gateway-enforces-it.md`:

```
browser -> Traefik (the only non-loopback bind) -> forward-auth subrequest -> Authelia
                          |  200 + Remote-User: <founder>
                          v
                    kanboard:80  (no published port at all)
```

Kanboard needs no patch. Its own `config.default.php` carries the seam:

| Constant | Ships as | Becomes | Why |
|---|---|---|---|
| `REVERSE_PROXY_AUTH` | `false` | `true` | trust the proxy's header |
| `REVERSE_PROXY_USER_HEADER` | `'REMOTE_USER'` | the header Authelia sets | Authelia sets `Remote-User` |
| `REVERSE_PROXY_DEFAULT_ADMIN` | `''` | the founder's username | auto-creates him as admin on first request |
| `HIDE_LOGIN_FORM` | `false` | `true` | there is no form left to meet |
| `SESSION_DURATION` | `0` (until browser closes) | unchanged | the proxy holds the session now |
| `REMEMBER_ME_AUTH` | `true` | unchanged | |

## The ordering constraint — this is the part that can go wrong

`REVERSE_PROXY_AUTH` **trusts a header**. Anyone who can reach Kanboard directly and set
`Remote-User` is the admin. So the port must be unreachable except through the proxy *before* the
flag is turned on. Turning it on first is strictly worse than the login form we are removing.

Correct order, and it is not negotiable:

1. Traefik is up and routing `board.localhost` to the container over the compose network.
2. Authelia is up and Traefik's forward-auth middleware is proving a 302-to-login for an
   unauthenticated request.
3. `ports:` is **removed** from `kanboard.yml` — the container publishes nothing.
4. Verified: `curl -sI http://127.0.0.1:3300/` returns nothing at all (connection refused).
5. Only then, the six constants above are set.

## Phase 2 — the lifecycle script that does not exist yet

Per R19, it needs four entry points. Written here so the automation has a spec, not prose.

| Entry point | Must prove |
|---|---|
| `can_apply` | `db.sqlite` copied; Traefik reachable; Authelia `/api/verify` returns 401 for an anonymous request; port 3300 still loopback |
| `apply` | writes the six env vars, removes `ports:`, recreates the container |
| `healthcheck` | anonymous request to `http://board.localhost/` gets the Authelia login; an authenticated one gets HTTP 200 with **no** `Location: /login` |
| `rollback` | restores `kanboard.yml` and `db.sqlite`, recreates the container, `curl -sI http://localhost:3300/` returns the 302 it returns today |

Idempotency test R19 law 1 demands: run `apply` twice. The second run exits 0, changes nothing,
and does not create a second admin user. Kanboard auto-creates the
`REVERSE_PROXY_DEFAULT_ADMIN` user on first request, so this is the specific place a duplicate
resource could appear — the test is a row count on the `users` table before and after.

## Blocked on

- Traefik is not deployed. ADR 0001 chose it; nothing has been booted.
- Authelia is not deployed. ADR 0003 chose it 2026-08-24; nothing has been booted.
- `board.localhost` needs an `/etc/hosts` line, which needs sudo, which needs the founder once
  (LAW 27). **Tested on this machine 2026-08-24, and the convenient assumption is false:**

  ```
  $ ping -c1 -t1 board.localhost
  ping: cannot resolve board.localhost: Unknown host
  ```

  macOS does not synthesise `*.localhost`. So the hosts line is genuinely required. Ask him once,
  for every hostname the estate will ever need, not once per service — that is what LAW 27 means
  here. The list comes from the Backstage catalog, so it is generated, not typed.

Only the founder moves this to live (R16).
