# Otto's answering floor: every surface for real, portal first

## Why (founder's own words)

> "full spec first, need the full bleeding edge" — 2026-09-06
> "the showcase has to actually wow and impress … need to see, visualise and interact" — 2026-09-05

A buyer's engineer can watch our demo today. What changes a demo from watched to *felt* is
typing a question into the page and being answered by the same agent, in the same thread,
that answers the founder's Telegram. That is the bleeding edge this spec ships: the portal
as a real surface of the one agent — then the push channel that makes it live — then the
breadth the door was already built for, one file per surface, dated.

## Ground truth, verified 2026-09-06 (not aspirations)

Every row was read on `hermes-v2` `origin/main` at `f9c2e293` (running in the cluster as
`main-89-f9c2e293`, rolled 2026-09-06 01:31Z, probe-proved 01:44Z) or in this repository.

| Fact | Receipt |
|---|---|
| Two concrete surfaces exist: Telegram (push + receive, live) and HTTP (normalise + render; **no reply address**) | `otto/ingress/plugins.py:235` (`default_plugins` returns exactly `TELEGRAM, HTTP`); `otto/surface/bindings/http.py` has no `send_reply` |
| The seam is real: a new surface is one binding + one registry entry, no gateway rework | `otto/ingress/plugins.py:232-235` ("Adding Slack is one entry here and one class above") |
| One thread per principal across surfaces, untrusted principals isolated | `otto/ingress/thread.py` design notes 1-2 (step 8, shipped in hermes-v2#91) |
| Typing + 8-second progress courtesies exist; **SSE is a recorded open item** | `otto/boot/presence.py` docstring ("Streaming … is the real answer and is not this — recorded as the open item on the decision record for 2026-09-04") |
| The answering spine is async: 202 + `task_id`; the worker replies through the plugin that minted the address; a task with no reply address is terminated, not redelivered | `otto/ingress/gateway.py:224-236`; `otto/ingress/worker.py:144-160` |
| The HTTP binding already assumes upstream authentication and maps an opaque `caller_id` to a bound principal (OPERATOR) or UNTRUSTED | `otto/surface/bindings/http.py:28-55` |
| The estate's identity law fits that shape exactly: OIDC at the gateway, never in an app | `~/AGENTS.md` SSO policy; `platform/identity/` |
| The otto.<zone> door's auth class is the channel-binding registry (a stranger cannot probe which customers exist) | `platform/otto-gateway/httproute.yaml:25`; gate branch `sovereign/tests/bdd/test_gate_front_door_login.py:182` |
| The portal already proxies to cluster services | `backstage/app-config.yaml:172` (`/holmes` → `http://robusta-holmes.robusta.svc.cluster.local`) |
| The channel registry lives in `otto_gateway` on estate-db; bindings are seeded by job | `platform/otto-gateway/binding-seed.yaml` |
| A throwaway demo cluster is one button; the showcase product spec and the marketing research exist | idp#1926, prospector#818, idp#1918, `docs/specs/backstage-as-a-product.md` levels 1-4 |

What this means: the expensive parts — the seam, the thread, the trust classes, the media
pipeline (voice/photo/presence shipped 2026-09-06 in hermes-v2#91), the demo floor — are
done and running. What is missing is exactly two pieces of plumbing and one page.

## The product, three landings

### Floor 1 — Ask Otto on the portal

A page on the portal (`/ask`, surfaced from `/showcase` as its first tile) with one box and
the conversation it returns. The path:

```
browser → catalogue.<zone> (oauth2-proxy, OIDC — the estate's one identity layer)
        → backstage backend proxy /otto          (same shape as /holmes today)
        → otto-gateway HTTP surface              (in-cluster service)
        → normalize(caller_id = OIDC header)     (HttpBinding: bound → OPERATOR, else UNTRUSTED)
        → task spine                             (the only answering path — no sync bolt-on)
        → the answer channel below               (Floor 2)
```

The page shows the thread *this principal* already has — the same thread Telegram continues
(`thread.py` note 1), never another person's (note 2). Presence is the shipped courtesy,
not a new idea: typing indicator immediately, one progress line past eight seconds
(`presence.py`, `PROGRESS_AT_SECONDS = 8.0`).

### Floor 2 — The push channel (the open item, closed)

Server-Sent Events are the reply address the HTTP surface lacks:

- `reply_to = sse:<session-id>` minted at normalize time when the caller holds an open
  stream. `HttpPlugin.send_reply` writes the answer to that stream — **the one file the
  seam promised**, per `plugins.py`'s own docstring. The worker (`worker.py:144-160`) is
  untouched: it already resolves `reply_binding` and terminates tasks with no address —
  an open session *is* an address.
- The session registry is a table in `otto_gateway` on estate-db (where the channel
  registry already lives, `binding-seed.yaml`), with TTL, per-principal stream caps, and
  reconnect by `Last-Event-ID`. **No new store, no new service, no second anything.**
- What this unlocks beyond chat: proactive delivery to the portal. Today the scheduler
  logs `no delivery target resolved for deliver=telegram` (hermes-agent log, 2026-09-06
  01:40:19Z); a portal session becomes a delivery target with the same shape.
- Model-token streaming *through* the SSE channel (the partial-output answer `presence.py`
  names as the real fix) is a named later row, not wave 1: wave 1 streams the *event* of
  the answer, then the answer.

### Floor 3 — Breadth, one file each, sequenced and dated

Each row names the file and the proof. None is claimed before its row ships (the founder's
law: a claim the file does not support is a defect).

| Order | Surface | Lands in | Trigger already in the enum | Proof |
|---|---|---|---|---|
| 1 | Portal answering floor + SSE | `otto/surface/bindings/http.py`, `otto/ingress/plugins.py`, `backstage/packages/app/src/modules/home/Ask.tsx` | TEXT, RICH | Floor 1+2 proof plan below |
| 2 | QR → camera normaliser (showcase sandbox: scan, photograph the rack, ask) | new `otto/surface/bindings/http_media.py` + media intake from #91 | IMAGE_IN | photo → envelope → answer, quoted from the door log |
| 3 | Voice session (browser mic → answer + voice out) | `http_media.py` + presence courtesies | VOICE_IN, VOICE_OUT | a spoken question answered in the page, log-quoted |
| 4 | Slack / email | one binding file each per `plugins.py`'s docstring | TEXT | the seam test: gateway untouched (asserted by diff scope) |

## Design rules that are not negotiable

1. **One identity layer.** The portal caller is authenticated by oauth2-proxy at the edge;
   the binding trusts the gateway's header and nothing else. No login in the page, no
   password anywhere, no second account system.
2. **One answering path.** The portal goes through the task spine like every surface. The
   shallow sync lanes the probe uses stay the probe's; they are not the product.
3. **One thread per principal.** Continuity is by principal, isolated by trust class, and
   the surface is a column on the turn, not a scope.
4. **One collector.** Traces, spans and cost emit to the estate collector exactly as the
   Telegram path does today; coverage is proved by querying the backend, not scanning files.
5. **Denials stay structured.** A risky ask from the portal gets the same tiered gateway
   answer as from Telegram, with the refusal's reason in the page.
6. **The door stays probed.** The answer-probe's lanes remain green on every image; the
   portal path joins the probe table (a seventh row: page-ask → answer) rather than
   claiming health by deployment color.

## Proof plan — done in commands, per landing

**Floor 1.**
- `tests/` (hermes-v2): a portal ask normalizes to the bound principal with OPERATOR trust;
  an unbound caller is UNTRUSTED and thread-isolated — executed against the real handler
  (the repo's test doctrine: run something, never re-assert source).
- `tests/` (idp): backstage proxy config renders (`kustomize build`), the route carries the
  estate's auth annotation, and the page's drill (R53: sign in, page answers, the ask box
  returns a real answer — graded by behavior, never selectors).
- Empirical: a quoted production log line of a page-ask producing a traced answer
  (`task_id` → answer → collector span) before the word DONE is used.

**Floor 2.**
- A task answered through `HttpPlugin.send_reply` lands on an open stream end-to-end in
  test (worker → registry row → SSE frame).
- Reconnect replays from `Last-Event-ID`; an expired session terminates the task with the
  reason logged (the worker's existing contract).
- Live drill: ask in the page, close the tab mid-answer, reopen — the answer is there.

**Floor 3.** Per row: the named file exists, its proving test runs something, and the door
log shows the trigger's capability on the envelope (`IMAGE_IN` / `VOICE_IN`).

## Sequencing

1. **hermes-v2 PR A** — `HttpPlugin.send_reply` + SSE endpoint + registry table migration
   (estate-db `otto_gateway`). Gates: the repo's own suites + a streamed answer in test.
2. **idp PR B** — backstage proxy `/otto`, the `/ask` page and its showcase tile, the
   catalogue entity, the route annotation, the drill. Gates: `bin/idp-ci`.
3. Image automation pins the new build (crew#267, as today); the probe table gains the
   portal row.
4. Floor 3 rows by the order above, each its own PR and proof.

Merge order within each step: hermes-v2 first, idp second, exactly as the sandbox wave ran
(idp#1926 → prospector#818).

## What this spec refuses

No second identity, no second store, no second collector, no per-surface thread, no sync
chat bolted onto the probe lanes, no new vendor where a protocol exists, and no claim of a
surface before its row's proof is green. The bleeding edge here is that everything is
*real*: one agent, one thread, one audit trail — answered live on the page.
