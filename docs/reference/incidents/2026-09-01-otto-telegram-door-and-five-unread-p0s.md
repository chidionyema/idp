# Incident report: Otto's Telegram door closed for eleven hours, and five P0 issues nobody read

Date: 2026-09-01. Author session: `a2aed3c9`. Founder words that opened this report, 11:30Z, verbatim
from the prompt: "icident reort, shoud be auto, should not nneed to renind any agennt." His earlier
analysis of the same outage is captured as
`~/.claude/docs/founder/2026-09-01T1117Z-whats-a-clthe-crew-s-read-holds-and-f12e798c.md`.

Every fact below was read from GitHub, git or the public door in the hour it was written, and the
command or run that produced it is beside it. No cluster command was run by an agent; the founder
holds that access.

## What the founder saw

He merged [the Otto Platform v1 code](https://github.com/chidionyema/hermes-v2/pull/62) at 04:40Z and [the image bump](https://github.com/chidionyema/idp/pull/1099) at 05:00Z,
asked "did this ship," and was told the rollout was blocked. It was not. The image rolled at 05:17Z.
What was, and still is, blocked is the bot's public door: `https://otto.mumchimp.com/telegram`
serves the Traefik placeholder certificate, and Telegram will not deliver to a host without a real
one. Nobody had written that down as an incident. The estate's own pipeline had opened five P0
issues about other things and nobody had read those either.

## Timeline (UTC)

| When | What | Receipt |
|------|------|---------|
| 08-31 23:07 | [The storefront change](https://github.com/chidionyema/prospector/pull/800) adds the `https-otto` listener to the shared edge Gateway | `deploy/k8s/base/edge.yaml` (prospector) |
| 08-31 23:18 | [The platform change](https://github.com/chidionyema/idp/pull/1078) switches Otto from polling to the webhook at `otto.<zone>/telegram` | `platform/hermes-agent/gateway.yaml:315` |
| 09-01 00:15 | cert-manager opens an Order for the new names; three `cm-acme-http-solver` pods appear in `prospector` and stay | [founder's doctor run at 06:18Z](https://github.com/chidionyema/idp/actions/runs/33477023541) |
| 09-01 05:01:50 | Flux `scheduling` fails: `mutate.kyverno.svc-fail … EOF` | [Flux event run](https://github.com/chidionyema/idp/actions/runs/33472027384); [P0 issue](https://github.com/chidionyema/idp/issues/1101) opened at 05:02:04 |
| 09-01 05:12:20 | Flux `hermes-agent` applies revision `843868bd`: "Deployment/hermes-agent/hermes-agent-gateway configured" | [Flux event run](https://github.com/chidionyema/idp/actions/runs/33472690860) |
| 09-01 05:17:01 | "Health check passed in 4m40s" — Otto v1 image `main-56-78e54b5` is running | [Flux event run](https://github.com/chidionyema/idp/actions/runs/33472999435) |
| 09-01 05:02–06:13 | P0 issues open automatically for `edge`, `robusta`, `observability` ([one](https://github.com/chidionyema/idp/issues/1104), [two](https://github.com/chidionyema/idp/issues/1105), [three](https://github.com/chidionyema/idp/issues/1106)); none is read or closed | `gh issue list --label P0` |
| 09-01 10:59 | Founder's doctor run: only `guacamole` and `tailscale` not Ready — `scheduling`, `edge`, `robusta`, `observability` recovered; their P0s stay open | [doctor run](https://github.com/chidionyema/idp/actions/runs/33500103107), `bin/idp-cluster-state` |
| 09-01 11:0x | `openssl s_client -servername otto.mumchimp.com` still returns `CN=TRAEFIK DEFAULT CERT`; the live certificate's names are frozen at the 08-27 issue (api, auth, catalogue, hc, langfuse, llm, mcp, apex, signoz, www) | public probe |

## Two defects, one class

**Defect 1 — the outage nobody detected.** A public door serving a placeholder certificate is
invisible to every instrument the estate has. Flux is green (the Gateway applied). The Deployment is
healthy (its probes hit the pod, not the door). There is no alert rule on `certmanager_certificate_ready_status`,
no probe that checks the name on the certificate a door serves, and no reader of Telegram's
`getWebhookInfo.last_error_message`. The receipt: `grep -rnE 'certmanager_|probe_ssl' platform/observability platform/edge`
returns nothing.

**Defect 2 — the incidents nobody read.** `flux-events.yml` does exactly what the law on unread instruments asks: a red
failed apply opens a P0 issue, a "Health check passed" closes it. Five are open now ([tailscale](https://github.com/chidionyema/idp/issues/1093), [scheduling](https://github.com/chidionyema/idp/issues/1101),
[edge](https://github.com/chidionyema/idp/issues/1104), [robusta](https://github.com/chidionyema/idp/issues/1105), [observability](https://github.com/chidionyema/idp/issues/1106)). Four of those objects recovered hours ago. They did not close because the
close rule keys on one message, "Health check passed," which only a folder of manifests with `wait: true`
and health checks ever emits; `scheduling` recovered without emitting any event at all (zero
flux-events runs for it after 05:02). An issue that stays open after recovery trains every reader
to ignore the label, and by 11:00Z they had: two agent sessions answered "did this ship" from Flux
run logs without opening [the scheduling P0 issue](https://github.com/chidionyema/idp/issues/1101), which held the exact failure message.

The class is the one the founder named: **the record is produced by an agent remembering, not by
the pipeline.** The detector-to-issue half exists and fired. The issue-to-report half, and the
detector for the door itself, do not exist, so the report waited for a human to ask for it.

## What "auto" has to mean, in commands

The rule that ends the class has three parts, each graded by a command a buyer's engineer can run:

1. **The door is an instrument.** A blackbox probe per public hostname in the edge Gateway asserts
   the served certificate carries that name and is not the Traefik default, plus one rule on
   `certmanager_certificate_ready_status == 0` for more than 30 minutes. Both route to the same
   GitHub issue path the Flux alerts use. Graded by: the alert inventory (`bin/idp-alert-rows`)
   lists one row per public hostname, and a drill that removes a name from the Certificate turns
   the row red within the rule's window.
2. **The P0 issue is the incident report.** `flux-events.yml` closes on any `info` event for the
   object (Flux emits `info` only when it applied the declared state), and `oke-check`'s `cluster-state`
   step closes any open P0 whose object it finds Ready (the silent-recovery case). On close the
   workflow appends the recovery time and duration. Graded by: after the change, `gh issue list --label P0 --state open`
   names only objects `bin/idp-cluster-state` reports not Ready.
3. **The register is generated from the issues.** The docs build hook that already writes
   `docs/reference/incident-register.yaml` from `tests/test_incident_*.py` also reads closed P0
   issues, so every incident has a row and a page without an agent typing one. Graded by:
   `bin/incident-register --check` is stale the moment a P0 closes and the register has no row for it.

None of this is a new script. It is three rows of configuration on tools already running
(Prometheus rules, a GitHub Actions workflow, an mkdocs hook), and the fault-class keywords in
`bin/incident-register` already know `tls|certificate` as `network`.

## The cause, confirmed from two angles

Session code-0c found it and this session checked it independently. Every listener on the shared
edge Gateway uses one Secret, `prospector-edge-tls`, so cert-manager orders one certificate carrying
every listener's name. Two listeners added on 2026-08-30 (`https-alertmanager`, `https-prometheus`)
have no route on the platform's main branch, and the DNS publisher writes records only from
routes (`platform/dns/external-dns.yaml:76`, source `gateway-httproute`). `dig +short alertmanager.mumchimp.com`
and `prometheus.mumchimp.com` return nothing; `otto` and `api` return the edge address. An ACME
order fails whole when two of its thirteen names cannot be reached, so the ten-name certificate
from 2026-08-27 stays, and `otto` — which has a route, a record and a running server — is refused
along with the two dead names. The Kyverno failure at 05:01Z was real but unrelated: the solver
pods predate it (00:15Z) and the Otto image rolled through it at 05:17Z.

The fix (pushed by code-0c, no pull request, the founder merges): prospector branch
`fix/edge-drop-listeners-without-dns`, commit `1b053318`, drops the two dead listeners. The class
fix is a gate that refuses a Gateway listener whose hostname has no route, or one Certificate per
listener, so one dead name can never freeze twelve live ones again.

## The third peer reply, and what it settled

The founder's third peer reply (captured verbatim as
`~/.claude/docs/founder/2026-09-01T1147Z-count-this-as-the-third-peer-reply-the-f60bf5c1.md`)
accepted the mechanism and left three threads open. Two close from git and public DNS:

- **Three stuck solvers, two dead names.** Exactly three listener hostnames on the storefront's main
  branch are missing from the live certificate: `otto`, `alertmanager`, `prometheus`. The other ten
  were authorised on 2026-08-27 and need no new challenge. The third solver is otto's own, starved
  by the order it shares with the two dead names. No third dead listener exists.
- **Rule or hand-deletion?** The fix commit (`1b053318`) deletes the two listeners and pins the
  remaining set in `tests/unit/test_edge_platform_listeners.py`. That is an instance fix with a
  list, not the input-side rule "no listener without a resolving record" — that rule is still to
  build, and it belongs with the containment fix below.
- **Drop, or publish DNS?** Drop. The alert console and the metrics store are the monitoring plane;
  they belong behind the private network, not on the public edge beside the shop. The outage forced
  a question the 2026-08-30 change skipped.

His line for the record, verbatim: "The two names that broke your cert were alertmanager and
prometheus: the monitoring stack took down its own alarm wiring."

**Containment, class level.** Second incident in two days with one shape: a shared control-plane
object turns one bad input into estate-wide failure (yesterday a fail-closed admission webhook froze
every apply; today a shared-name certificate let two unused hostnames hold the Telegram money path
hostage). The containment is splitting the edge certificate — core serving names on one
Certificate, everything experimental on another — so no new listener can ever poison the order the
shop and Otto ride on. And `Certificate Ready=False` ran silent from 2026-08-30 to now; it has to
page (row 1 above).

## What is still not done

- The door is still closed until the founder merges and deploys the prospector fix; cert-manager
  then retries the order on its own. Runbook: `docs/runbooks/otto-telegram-webhook.md`.
- The three parts above are a decision record until the founder's word; this page names them so
  the next session does not rediscover them.
- Class question he raised and this report does not settle: one fail-closed Kyverno webhook can
  freeze the whole apply path, certificate issuance included. Either Kyverno earns that blast radius
  (replicas, a disruption budget, memory headroom) or fail-closed is scoped to the namespaces where
  enforcement matters.
