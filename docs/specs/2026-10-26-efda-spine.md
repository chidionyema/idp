# EFDA-SPINE: the event spine, reviewed against the estate and built

Founder-supplied specification, reviewed and implemented. 2026-10-26.

**Provenance.** The build kit in Appendix A was supplied as a reference document and marked
*"This response is AI-generated, for reference only."* It is treated as a reference
specification, not an authority: every requirement is graded against the estate's measured
state before anything is built from it, and where the kit and the estate disagree the
estate wins and the disagreement is written down.

**What landed.** The spine is wired into the estate: the notification-controller publishes
reconcile events onto the estate's NATS bus, a bridge turns them into Temporal signals, a
workflow wakes on the signal, checks the reconciliation against the object's own status,
and leaves a receipt. The code is `spine/`, the manifests are `platform/spine/`, and the
grade is 53 offline tests plus a Gherkin feature that runs.

---

## 1. The headline of the review

**Three of the kit's four nodes already exist, and the fourth is small.** The estate has
the fabric (NATS with JetStream, `platform/event-bus`), the clock (Temporal,
`platform/temporal`, and the sovereign `SessionWorkflow`), and the Flux event source
(the notification-controller, with `type: nats` in its own CRD enum). What did not exist is
the wire between them: no `SignalWorkflow` call exists anywhere in the repository (measured
by search), and no NATS→Temporal bridge exists. That gap is what this change closes.

**The kit's subject is not a subject the estate speaks.** The kit proposes
`evt.flux.kustomization.reconciled`. The estate's D1 grammar (ADR 0012, implemented in Go
at `platform/messaging/subject/subject.go`) requires five lower-case tokens
`{domain}.{kind}.{aggregate}.{action}.{version}`, a kind of `event`, `command` or `dlq`, a
past-tense action and a version. The kit's subject is four tokens, its kind is `evt`, and it
has no version. The spine publishes `flux.event.kustomization.reconciled.v1` instead, and
`tests/test_spine_contracts.py` proves the two answers differ — the kit's subject raises
`SubjectError`, the spine's passes.

**The kit's dead-letter path would have been a second one.** The estate already has a DLQ
processor (`platform/messaging/dlq/dlq.go`): it watches JetStream's
`MAX_DELIVERIES` advisory, copies the original message with its headers intact into the
`dlq` subject of the same grammar, and `ops replay` can replay it. The spine's consumer
uses `MaxDeliver=5` and lets that processor take the message when the deliveries run out.
The spine writes no dead-letter path of its own.

**The kit's Go bridge is a Python bridge here, and the reason is the estate's, not the
port's.** The estate's Temporal client is `temporalio`, pinned at `temporalio==1.32.0` in
`sovereign/requirements.txt`, and the sovereign worker that serves `SessionWorkflow` is
Python. A Go client would have been a second Temporal client stack for one bridge. The
kit's decision table — dedup before the signal, write-after-success, NAK on failure,
terminate on an unusable event, `MaxDeliver=5` — is ported line for line.

**One kit rule is deliberately not implemented as written, because the measurement says it
would answer nothing.** The kit says: *"Nats-Msg-Id required: events without it are
terminated, not silently dropped."* The notification-controller's NATS provider publishes
the event body and sets **no headers at all** (read from upstream
`internal/notifier/nats.go`: `nc.Publish(subject, eventPayload)`, and no header call
anywhere in the file). Terminating every Flux event would have built a spine that receives
everything and delivers nothing. The bridge therefore *derives* the id from the event
itself — the involved object's uid and resourceVersion, the reason, the timestamp — which
is stable across redeliveries, so the dedup still works; and it logs the derivation,
because a publisher that ought to set the id and does not is a fact somebody should see.

---

## 2. The goal tree, measured

| Node | The kit's "done when" | The estate's state, measured | What this change did |
|---|---|---|---|
| **SPINE-0** | a Flux event wakes a workflow, the workflow verifies the outcome, Aevum records the receipt | Temporal runs (`platform/temporal`, namespace `estate`); the Aevum server runs (`platform/observability/aevum.yaml`, service `aevum.observability.svc:8000`, `POST /v1/ingest`); **no NATS→Temporal bridge exists** — `SignalWorkflow` appears nowhere in the tree | Built the bridge and the observer. The receipt is written to Aevum's ingest API; the workflow's own history keeps the receipt even if the ledger write fails |
| **SPINE-1** | a durable stream with `Nats-Msg-Id` dedup, and a dead-letter stream | The bus exists: NATS 2.14.6 with JetStream, file store, PVC (`platform/event-bus/nats.yaml`). The messaging plane has D1 subjects, CloudEvents 1.0 in binary mode with `Nats-Msg-Id` = event id, a 15-minute duplicate window, an inbox table and the DLQ processor. The chart has **no declarative stream key** (measured: no `streams:` in the 2.14.6 `values.yaml`) | The bridge creates its own stream (`FLUX_EVENTS`, subjects `flux.event.>`, file storage, 10-minute duplicate window) — the estate's own pattern (`platform/messaging/cmd/epistemic-ingest/main.go` `ensureStream`) — and the DLQ is the estate's processor |
| **SPINE-2** | Flux events reach NATS through a `type: nats` Provider and an Alert | The notification-controller's own CRD lists `nats` among its provider types (measured on the OKE cluster: the `v1beta3` `spec.type` enum has 33 entries and `nats` is one of them). The estate uses `githubdispatch` and `telegram` today. The image-reflector-controller already runs with `--events-addr` (measured in `clusters/oke/flux-system/gotk-components.yaml`) | Two Providers and two Alerts (Kustomization, HelmRelease), one per kind because a Provider has one channel and the aggregate is part of the subject. The channels are D1 subjects |
| **SPINE-3** | events become Temporal signals, exactly once, with a DLQ on failure | Nothing exists. The estate's Temporal client is `temporalio` (Python) | `spine/bridge.py`: durable consumer `signal-bridge`, `AckExplicit`, 30s ack wait, `MaxDeliver=5`, a JetStream KV bucket `BRIDGE_DEDUP` (24h) for the processed ids, dedup **before** the signal and the record **after** it, NAK on a failed signal, terminate on an unusable event, terminate a subject/event mismatch |
| **SPINE-4** | a workflow suspends on a signal, wakes, verifies, and emits a receipt | The estate's Temporal plane runs the sovereign `SessionWorkflow`; the decision register already names the shape (`dec:spine-woken-verification`, mode *machine*, decided_by `cap:intent/flux-status`: "the workflow that runs it is the trigger, not the decider") | `spine/workflow.py`: the `ObserverWorkflow` on its own task queue `spine`. It waits on a condition (it does not poll), verifies through an activity that reads the object's own status, writes a receipt, and continues as new from the main loop — never from the signal handler |

---

## 3. How the event spine works with the Greenlane

This is the question the founder asked, and it is the one that decides whether the spine
is an addition or a stitch.

### What the Greenlane already is

The Greenlane is the estate's gated trunk (`greenlane/engine.py`, `docs/runbooks/greenlane.md`).
Its invariants are explicit:

- **I1** main only ever moves to a sha whose required checks all passed at that exact sha.
- **I2** nothing but the engine moves main — the GitHub ruleset `idp-main-writer` refuses
  everyone else, admins included.
- **I3** a pull request exists only for a lane that is already proven green on top of the
  current main, and it is landed in the same act it is raised.
- **I4** no work is lost.
- **I5** a green lane lands within a bounded number of batches, whatever the other lanes do.

The flow is: an agent pushes `lane/<name>` → the engine stacks the lanes into one
candidate → the six required checks run on that exact sha → the engine raises the pull
requests and fast-forwards main → **Flux reconciles the cluster** → the image rolls, the
manifests apply, the workloads restart.

### Where the spine sits in that flow

The spine is the **arm after Flux**, not a second road to main:

```
   agent ──push lane/──▶ GREENLANE ──▶ main ──▶ FLUX ──reconcile──▶ cluster
   (writes code)         (proves it)          (applies it)            (the truth)
                                                                   │
                                                                   ▼
                                            SPINE: the environment emits the fact,
                                            the agent reads it back and leaves a receipt
```

Three consequences, and they are the whole answer:

1. **The spine never moves main.** It has no write path into the trunk: it consumes an
   event, it reads a status, it writes a receipt. If the spine could merge, `I2` would be
   a convention instead of a ruleset — and the estate's whole proof of the Greenlane is
   that `I2` is enforced by GitHub, not by prose. The spine's authority is to *observe and
   record*, and nothing in this change gives it a token that could do otherwise.
2. **The Greenlane proves the code; the spine proves the deployment.** The Greenlane's
   checks prove that the bytes on main are good. They say nothing about whether the
   cluster then converged — and the estate has already been bitten by exactly that gap:
   the `flux-events.yml` workflow's own comment records a Deployment that "stopped rolling"
   for seventeen hours while every CI gate stayed green and nobody read a ledger
   (`crew#307`, 2026-08-28). The spine is the arm that answers "did the reconcile the
   Greenlane's merge caused actually land?".
3. **The spine is downstream of the Greenlane, so it can never block it.** A broken
   reconcile must not be able to stop a lane from landing, and a landed lane must not wait
   for the spine. The two loops are independent: the Greenlane's verdict is the checks on
   the sha; the spine's verdict is the object's own status. Neither is derived from the
   other.

### The two loops, side by side

| | Greenlane | Spine |
|---|---|---|
| Trigger | a lane pushed to `lane/<name>` | a Flux reconcile event |
| Question | "are these bytes good?" | "did the apply land?" |
| Decider | the six required checks on the exact sha | the object's own `status.conditions` — a state fetch, a *machine* decision (`dec:spine-woken-verification`) |
| Authority | the only thing that moves main (`I2`) | none: it reads and records |
| Output | a merge, and a Flux reconciliation | a receipt in the evidence ledger |
| When it fails | the lane stays, with the reason on its head commit's `greenlane` status | the receipt says `failed` / `missing`, and a missing object is routed to a human |

### What the spine must never become

- **A second merge path.** The runbook records that the estate deleted
  `merge-when-green`, `deploy-when-green` and friends precisely because a second lane
  grading pull requests after they exist is stitching. The spine is the same shape of
  danger — a reaction to a deployment event that could grow into a reaction that *acts* on
  the deployment. So the observer's activity is a **read**, its RBAC is get/list/watch on
  three Flux kinds and nothing else, and its receipt is an assertion.
- **A second ledger.** The spine asserts through the Aevum server's API. It does not hold
  the signing key, and it must not: the estate's own recorder says the key stays in one
  container for exactly that reason (`platform/observability/recorder/recorder.py`).
- **A second decision surface.** The spine makes no judgement calls. Every verdict is a
  comparison on a status field, and every other case is a gap routed to a human.

### The one seam the founder should know about

The spine's consumer and the Greenlane's `flux/image-updates` lane both sit downstream of
Flux. Flux's image automation writes the new tag and opens a lane; the Greenlane lands it;
Flux applies it; the spine observes the apply. If the spine's read ever contradicts the
Greenlane's proof, the contradiction is a fact about the estate, not a disagreement to be
settled by preference — and the receipt is where that fact lands, so a human can see it.

---

## 4. What is production and what is not, in this build

| Component | Status | Note |
|---|---|---|
| The `nats` Provider and the Alerts | **production** | the provider type is native to the deployed notification-controller (measured), and the manifests are ordinary Flux objects |
| The JetStream stream and the dedup bucket | **production** | created by the bridge on start, the estate's own consumer pattern; a durable consumer, so a restart resumes |
| The bridge | **production** | dedup before the signal, record after it, NAK on failure, terminate on an unusable event, `MaxDeliver=5` and the estate's DLQ processor behind it |
| The observer workflow | **production** | suspends on a signal, verifies through an activity, writes a receipt, continues as new from the main loop |
| The receipt into Aevum | **wired, one dependency short** | the API is the estate's (`POST /v1/ingest`, `X-Aevum-Key`); the key is a new property of the vault entry `aevum-evidence`, which `bin/idp-estate-seed` now mints as a *missing* property — the Postgres password and the signing key already in the vault are untouched. Until the vault carries it, the receipt says `ingested: false` and the workflow reports the gap: visible, not silent, and the receipt is still in the workflow's own history |
| The DLQ adapter | **not written, deliberately** | the estate's `platform/messaging/dlq` processor is the DLQ writer, and "one writer per stream" is its rule |
| The image-reflector events | **not wired** | the controller already runs with `--events-addr`; a third Provider is three lines, and it is not needed for the spine's question |

---

## 5. The verification playbook, in the estate's own terms

The kit's playbook is written in `kubectl apply` and the `temporal` CLI. The estate's rules
forbid a hand-applied manifest (`AGENTS.md` §2: never hand-apply; changes flow through git
→ main → Flux), and the `temporal` CLI is not in the image. So the playbook is the same
questions, asked of the estate's own doors.

```bash
# 1. The stream exists, and the bridge is the only writer of it.
kubectl --context context-estate-crq7jwxsjxq -n event-bus exec nats-0 -- \
  nats stream ls
#    FLUX_EVENTS ... subjects: flux.event.> ... duplicate window: 10m

# 2. The Flux side exists: the Provider and the Alert, and their channels.
kubectl --context context-estate-crq7jwxsjxq -n flux-system get providers.notification.toolkit.fluxcd.io
kubectl --context context-estate-crq7jwxsjxq -n flux-system get alerts.notification.toolkit.fluxcd.io

# 3. The bridge is running and its consumer is attached.
kubectl --context context-estate-crq7jwxsjxq -n spine get deploy,po
kubectl --context context-estate-crq7jwxsjxq -n spine logs deploy/spine-bridge | tail -20
#    bridge ready: stream=FLUX_EVENTS consumer=signal-bridge subject=flux.event.>
#    signalled spine-verify-kustomization-flux-system-<name> on flux.reconciled

# 4. An event really is on the bus.
kubectl --context context-estate-crq7jwxsjxq -n event-bus exec nats-0 -- \
  nats stream view FLUX_EVENTS --subject 'flux.event.>' --count 5

# 5. The receipt exists -- in the workflow's history, and in the ledger.
kubectl --context context-estate-crq7jwxsjxq -n temporal logs deploy/sovereign-worker | tail -40
#    (or, on the workflow id: the ObserverWorkflow's own result, which carries the receipt
#     and its digest)

# 6. The estate's own read of the same question: is the row reconciled?
bin/idp-greenlane status        # the trunk
bin/idp-flux-status             # the reconcile -- the same capability the observer uses
```

The spine's own proof is the receipt: it names the event, the object, the verdict, the
revision it saw and a digest of its own body, and it lands in the evidence ledger where
`aevum-verify` can check it against the chain.

---

## 6. The honest caveats

1. **The receipt into the ledger is one mint short.** The vault entry has to carry the
   `api-key` property, and the mint is a machine action on a machine with a vault session.
   The seed script is changed and tested; the mint itself is not something a pull request
   can do. Until it is minted, the spine says so in every receipt rather than pretending.
2. **The spine observes Flux, it does not observe the whole estate.** One Kustomization
   reconcile is one fact. A workload that comes up unready behind a successful
   Kustomization is not an event the spine sees — that is the estate's existing health
   layer's question, and the spine does not duplicate it.
3. **The DLQ is the estate's, not the kit's.** The kit wanted a `dlq.flux.events` stream.
   The estate's DLQ processor writes the `dlq` subject of the same grammar
   (`flux.dlq.kustomization.reconciled.v1`), which is the same idea expressed in the
   estate's own vocabulary. Anything that expects the literal subject `dlq.flux.events`
   will not find it, and that is deliberate.
4. **Two kinds are wired, not three.** Kustomization and HelmRelease. A GitRepository
   Provider is the same three lines; it is not wired because the spine's question is
   "did the apply land", and a source sync is not an apply.
5. **The Go code in Appendix A is a reference, not a port.** The logic is ported; the
   language is not, and the reason is the estate's client stack. Anyone reading the kit's
   Go and expecting to find it in this tree will not; the decision table is in
   `spine/bridge.py` and it is graded by `tests/test_spine_bridge.py`.

---

## Appendix A: the supplied build kit, verbatim

> The following is the founder-supplied text, kept as it was supplied, including its
> statement about its own provenance.

```
The spine is not a new system you deploy. It is a declared wiring of Temporal, NATS JetStream, Flux, and Reflect into one event-driven loop where the environment emits facts and agents respond. This build kit gives you the goal tree, BDD features, production-grade bridge code, Flux configuration, stream definitions, and the verification playbook — as much as is buildable today.

EFDA-SPINE BUILD KIT
0. GOAL TREE
SPINE-0: Event-Driven Agent Spine Operational
    DONE when: a Flux reconciliation event wakes a Temporal agent workflow,
    the workflow verifies the outcome, and Aevum records the receipt.

├── SPINE-1: Event Fabric (NATS JetStream)
│   DONE when: Flux events land in a durable stream with Nats-Msg-Id dedup.
│   ├── SPINE-1.1 JetStream stream for flux.events
│   ├── SPINE-1.2 Idempotent publisher with Nats-Msg-Id
│   └── SPINE-1.3 Dead-letter stream for exhausted retries
│
├── SPINE-2: Flux → NATS Wiring
│   DONE when: Kustomization/HelmRelease events appear on flux.events.
│   ├── SPINE-2.1 Flux Provider type=nats
│   ├── SPINE-2.2 Flux Alert selects Kustomization/HelmRelease
│   └── SPINE-2.3 Image Reflector event forwarding
│
├── SPINE-3: Signal Bridge (NATS → Temporal)
│   DONE when: evt.flux.* messages become Temporal Signals that wake workflows.
│   ├── SPINE-3.1 Subject-to-signal routing
│   ├── SPINE-3.2 Idempotency key from Nats-Msg-Id
│   └── SPINE-3.3 DLQ on signal failure
│
└── SPINE-4: Agent Workflow (Temporal)
    DONE when: a workflow suspends on Signal, wakes on Flux event,
               verifies outcome, and emits a receipt.
    ├── SPINE-4.1 Observer workflow with signal channel
    ├── SPINE-4.2 continue-as-new with state handoff
    └── SPINE-4.3 Activity verifies Flux reconciliation result

1. THE ARCHITECTURE IN ONE DIAGRAM
Flux controllers (Kustomization, HelmRelease, ImageReflector)
   │ emit events
   ▼
Flux notification-controller ──Provider type=nats──► NATS subject flux.events
   │
   ▼
NATS JetStream stream FLUX_EVENTS (durable, replay, dedup window)
   │
   ▼
Signal Bridge (Go) ──consumes evt.flux.*──► Temporal SignalWorkflow
   │
   ▼
Temporal Workflow (ObserverWorkflow) suspended on signal channel
   │ wakes
   ▼
Activity verifies reconciliation outcome (Flux Kustomization status)
   │
   ▼
Aevum receipt (signed, hash-chained) ──► next step unlocked
The bridge is the only component that knows both NATS and Temporal. Every Flux controller speaks NATS; every agent speaks Temporal; neither leaks into the other's domain.

2. FEATURE: SPINE-1 — EVENT FABRIC
Feature: NATS JetStream Event Fabric
  The event fabric must durably store Flux events and reject duplicates.

  Scenario: Flux event is persisted to a durable stream
    Given the FLUX_EVENTS stream exists with subjects ["flux.events", "evt.flux.>"]
    When Flux publishes a Kustomization reconciliation event to "flux.events"
    Then the message is stored in FLUX_EVENTS
    And the stream sequence increments
    And the message is retrievable after bridge restart

  Scenario: Duplicate Flux event is rejected by Nats-Msg-Id
    Given a Flux event with Nats-Msg-Id "flux-abc-123" is stored
    When the same event is published again with the same Nats-Msg-Id
    Then the server rejects it as a duplicate
    And the PubAck marks it as duplicate
    And only one copy exists in the stream[reference:1]

  Scenario: Exhausted retries land in dead-letter stream
    Given a signal bridge consumer fails to process an event 5 times
    When the consumer's retry limit is exceeded
    Then the event is published to "dlq.flux.events"
    And the original stream still retains the event
    And an alert fires on the DLQ subject
2.1 Stream definition
deploy/nats/flux-events-stream.yaml:

apiVersion: jetstream.nats.io/v1beta2
kind: Stream
metadata:
  name: flux-events
  namespace: nats-system
spec:
  name: FLUX_EVENTS
  subjects:
    - "flux.events"
    - "evt.flux.>"
  retention: limits
  maxAge: 168h          # 7 days
  maxMsgs: 1000000
  maxBytes: 1GB
  storage: file
  replicas: 1
  duplicateWindow: 10m   # dedup window
  discard: old
---
apiVersion: jetstream.nats.io/v1beta2
kind: Stream
metadata:
  name: flux-dlq
  namespace: nats-system
spec:
  name: FLUX_DLQ
  subjects:
    - "dlq.flux.>"
  retention: limits
  maxAge: 720h          # 30 days
  storage: file
2.2 Idempotent publisher
The bridge must set Nats-Msg-Id on every publish. Without it, a lost ack causes a duplicate store.

go
// publish with stable ID derived from CloudEvent ID
msg := nats.NewMsg(subject)
msg.Header.Set("Nats-Msg-Id", ce.ID())
msg.Data = body
_, err := js.PublishMsg(msg)
3. FEATURE: SPINE-2 — FLUX → NATS WIRING
Feature: Flux Event Emission to NATS
  Flux must publish reconciliation events as JSON to NATS.

  Scenario: Kustomization reconciliation event is published
    Given a Provider with type "nats" and channel "flux.events"
    And an Alert selecting Kustomization events
    When a Kustomization reconciles successfully
    Then a JSON message appears on "flux.events"
    And the message contains the Kustomization name and namespace

  Scenario: Failed HelmRelease is published with error severity
    Given a HelmRelease upgrade fails
    When the notification controller evaluates the Alert
    Then the event is published with severity "error"
    And the payload includes the failure reason

  Scenario: Image Reflector event is forwarded
    Given the image-reflector-controller is configured with --events-addr
    When a new image tag is detected
    Then an event is emitted to the configured receiver
    And the bridge can route it to a waiting workflow
3.1 Flux Provider and Alert
deploy/flux/provider-nats.yaml:

apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Provider
metadata:
  name: nats-provider
  namespace: flux-system
spec:
  type: nats
  channel: flux.events
  secretRef:
    name: nats-secret
---
apiVersion: v1
kind: Secret
metadata:
  name: nats-secret
  namespace: flux-system
type: Opaque
stringData:
  address: nats://nats.nats-system.svc.cluster.local:4222
---
apiVersion: notification.toolkit.fluxcd.io/v1beta3
kind: Alert
metadata:
  name: nats-alert
  namespace: flux-system
spec:
  providerRef:
    name: nats-provider
  eventSeverity: info
  eventSources:
    - kind: Kustomization
      name: "*"
    - kind: HelmRelease
      name: "*"
    - kind: GitRepository
      name: "*"
The notification-controller publishes Flux events as JSON messages to the configured NATS subject.

3.2 Image Reflector event forwarding
The image-reflector-controller has an --events-addr flag for an events receiver. Point it at the bridge's HTTP event receiver (or a NATS adapter) so image-update events enter the same fabric.

4. FEATURE: SPINE-3 — SIGNAL BRIDGE
Feature: NATS-to-Temporal Signal Bridge
  The bridge converts Flux facts into Temporal Signals.

  Scenario: Flux success event wakes the waiting workflow
    Given a workflow "deploy-verify-abc" is waiting on signal "flux.reconciled"
    And a Flux event "evt.flux.kustomization.reconciled" arrives
    When the bridge processes the event
    Then it calls SignalWorkflow with signal "flux.reconciled"
    And the workflow wakes
    And the signal payload contains the event body

  Scenario: Duplicate event does not double-signal
    Given the bridge has already processed Nats-Msg-Id "msg-001"
    When the same message is redelivered
    Then the bridge detects the duplicate via its idempotency store
    And does not signal the workflow again

  Scenario: Signal failure routes to DLQ
    Given the bridge cannot reach Temporal
    When it exhausts retries for an event
    Then it publishes the event to "dlq.flux.events"
    And logs the failure with the Nats-Msg-Id
4.1 Production bridge (Go)
cmd/signal-bridge/main.go:

go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "log"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/nats-io/nats.go"
    "github.com/nats-io/nats.go/jetstream"
    "go.temporal.io/sdk/client"
)

type FluxEvent struct {
    InvolvedObject struct {
        Kind      string `json:"kind"`
        Name      string `json:"name"`
        Namespace string `json:"namespace"`
    } `json:"involvedObject"`
    Severity  string `json:"severity"`
    Message   string `json:"message"`
    Reason    string `json:"reason"`
    Timestamp string `json:"timestamp"`
}

func main() {
    nc, err := nats.Connect(envOr("NATS_URL", "nats://nats.nats-system:4222"))
    if err != nil { log.Fatal(err) }
    defer nc.Close()

    js, err := jetstream.New(nc)
    if err != nil { log.Fatal(err) }

    tc, err := client.Dial(client.Options{
        HostPort: envOr("TEMPORAL_ADDR", "temporal-frontend:7233"),
    })
    if err != nil { log.Fatal(err) }
    defer tc.Close()

    // Idempotency: NATS-based KV bucket keyed by Nats-Msg-Id
    kv, _ := js.CreateOrUpdateKeyValue(context.Background(), jetstream.KeyValueConfig{
        Bucket: "BRIDGE_DEDUP",
        TTL:    24 * time.Hour,
    })

    cons, err := js.CreateOrUpdateConsumer(context.Background(), "FLUX_EVENTS", jetstream.ConsumerConfig{
        Durable:       "signal-bridge",
        AckPolicy:     jetstream.AckExplicitPolicy,
        AckWait:       30 * time.Second,
        MaxDeliver:    5,
        FilterSubject: "evt.flux.>",
        DeliverPolicy: jetstream.DeliverAllPolicy,
    })
    if err != nil { log.Fatal(err) }

    ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
    defer cancel()

    _, err = cons.Consume(func(msg jetstream.Msg) {
        msgID := msg.Headers().Get("Nats-Msg-Id")
        if msgID == "" {
            log.Printf("missing Nats-Msg-Id, rejecting: %s", msg.Subject())
            msg.Term()
            return
        }

        // Dedup check
        if _, err := kv.Get(ctx, msgID); err == nil {
            log.Printf("duplicate event %s, acking", msgID)
            msg.Ack()
            return
        }

        var evt FluxEvent
        if err := json.Unmarshal(msg.Data(), &evt); err != nil {
            log.Printf("invalid JSON: %v", err)
            msg.Term()
            return
        }

        signalName, workflowID := routeSignal(msg.Subject(), evt)
        if workflowID == "" {
            log.Printf("no workflow mapping for %s", msg.Subject())
            msg.Ack()
            return
        }

        err := tc.SignalWorkflow(ctx, workflowID, "", signalName, evt)
        if err != nil {
            log.Printf("signal failed for %s: %v", workflowID, err)
            msg.Nak() // retry up to MaxDeliver, then DLQ via consumer policy
            return
        }

        // Record dedup AFTER successful signal
        kv.Put(ctx, msgID, []byte(time.Now().UTC().Format(time.RFC3339)))
        msg.Ack()
        log.Printf("signalled %s on %s", workflowID, signalName)
    })

    if err != nil { log.Fatal(err) }
    <-ctx.Done()
}

func routeSignal(subject string, evt FluxEvent) (string, string) {
    // Subject format: evt.flux.<kind>.<reason>
    // Workflow ID convention: deploy-verify-<namespace>-<name>
    return "flux." + evt.InvolvedObject.Kind + "." + evt.Reason,
        "deploy-verify-" + evt.InvolvedObject.Namespace + "-" + evt.InvolvedObject.Name
}

func envOr(k, d string) string {
    if v := os.Getenv(k); v != "" { return v }
    return d
}
Key production properties:

Dedup before signal, write-after-success: if the signal fails, the event is not marked processed and will be retried.

Nats-Msg-Id required: events without it are terminated, not silently dropped.

DLQ via consumer policy: MaxDeliver=5; after exhaustion, use a NATS DLQ adapter or a separate consumer on the DLQ subject.

5. FEATURE: SPINE-4 — AGENT WORKFLOW
Feature: Temporal Agent Workflow Responds to Flux Events
  The workflow suspends on a Signal; it does not poll.

  Scenario: Workflow suspends and wakes on Flux event
    Given a workflow "deploy-verify-ns-app" is running
    And it is waiting on signal "flux.Kustomization.ReconciliationSucceeded"
    When the bridge signals it with the Flux event payload
    Then the workflow wakes within 2 seconds
    And it invokes activity "verifyKustomization" with the event details
    And the activity checks Flux status and returns success

  Scenario: Workflow survives continue-as-new
    Given the workflow has processed 1000 signals
    And continueAsNewSuggested returns true
    When the workflow calls continueAsNew
    Then the new run starts with the same state
    And pending signals are not lost[reference:6]

  Scenario: Workflow times out and emits a gap artifact
    Given the workflow waits for a Flux event for 1 hour
    When no signal arrives
    Then the workflow emits a "deployment_timeout" artifact
    And routes to human review
5.1 Observer workflow (Go)
workflows/deploy_verify.go:

go
package workflows

import (
    "time"

    "go.temporal.io/sdk/workflow"
)

func DeployVerifyWorkflow(ctx workflow.Context, namespace, name string) (string, error) {
    ao := workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
        RetryPolicy: &temporal.RetryPolicy{MaximumAttempts: 3},
    }
    ctx = workflow.WithActivityOptions(ctx, ao)

    signalCh := workflow.GetSignalChannel(ctx, "flux.Kustomization.ReconciliationSucceeded")

    for {
        var evt FluxEvent
        signalCh.Receive(ctx, &evt)

        var result string
        err := workflow.ExecuteActivity(ctx, "verifyKustomization", namespace, name, evt).Get(ctx, &result)
        if err != nil {
            return "", err
        }
        if result == "verified" {
            return "deployment_verified", nil
        }

        if workflow.GetInfo(ctx).GetContinueAsNewSuggested() {
            return "", workflow.NewContinueAsNewError(ctx, DeployVerifyWorkflow, namespace, name)
        }
    }
}
Critical rule: do not call continueAsNew from inside a signal handler. Wait for the handler to finish in the main workflow loop.

6. EDGE CASES AND RESOLUTIONS
Edge Case    Resolution
Flux event fires for every Kustomization    Alert uses eventSources with specific names or label selectors; bridge routes by subject and event kind.
Duplicate event after NATS redelivery    Nats-Msg-Id dedup on stream; bridge KV dedup on processed IDs.
Bridge crashes after signal, before dedup write    Signal is idempotent at Temporal (same workflow ID + signal); on retry, signal is re-sent but workflow handles duplicate signal gracefully by checking event ID.
Temporal unreachable    Bridge Nak()s the message; NATS retries up to MaxDeliver; after exhaustion, route to DLQ.
Workflow history grows unbounded    continueAsNew on GetContinueAsNewSuggested; state handoff via input参数.
Signal arrives while workflow is in continueAsNew    Signals are buffered by Temporal and delivered to the new run; do not call continueAsNew from the signal handler.
Flux event schema changes    Bridge validates event against CloudEvents/JSON Schema before signal; invalid events are terminated and logged, not silently dropped.
Image Reflector event not emitted    Ensure --events-addr is set; if not, poll ImageRepository status as a fallback, but treat polling as a degraded mode.
7. VERIFICATION PLAYBOOK
bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== SPINE-1: NATS stream ==="
nats stream info FLUX_EVENTS --json | jq -e '.config.subjects | length > 0'

echo "=== SPINE-2: Flux event emission ==="
kubectl apply -f deploy/flux/provider-nats.yaml
kubectl apply -f deploy/flux/alert-nats.yaml
# Trigger a reconciliation
kubectl annotate kustomization -n flux-system apps reconcile.fluxcd.io/requestedAt="$(date +%s)"
sleep 10
nats stream view FLUX_EVENTS --subject flux.events | grep -q "ReconciliationSucceeded"

echo "=== SPINE-3: Bridge signal ==="
# Start a workflow
temporal workflow start --task-queue agent-queue \
  --workflow-type DeployVerifyWorkflow --workflow-id deploy-verify-default-app \
  --input '{"namespace":"default","name":"app"}'

# Publish a test event with Nats-Msg-Id
nats pub evt.flux.Kustomization.ReconciliationSucceeded \
  --header "Nats-Msg-Id:test-$(uuidgen)" \
  '{"involvedObject":{"kind":"Kustomization","name":"app","namespace":"default"},"severity":"info","reason":"ReconciliationSucceeded"}'

sleep 3
temporal workflow describe --workflow-id deploy-verify-default-app | grep -q "deployment_verified"

echo "=== SPINE-4: Dedup ==="
MSG_ID="test-dedup-$(uuidgen)"
nats pub evt.flux.Kustomization.ReconciliationSucceeded --header "Nats-Msg-Id:$MSG_ID" '{"...":"..."}'
nats pub evt.flux.Kustomization.ReconciliationSucceeded --header "Nats-Msg-Id:$MSG_ID" '{"...":"..."}'
# Expect only one signal, second PubAck is duplicate
8. WHAT IS PRODUCTION VS. STUB
Component    Status    Notes
Flux Provider/Alert    Production    Native type: nats in notification-controller
NATS stream + dedup    Production    Nats-Msg-Id is standard
Signal bridge    Production skeleton    Routing and dedup logic above is correct; add metrics and DLQ adapter
Observer workflow    Production skeleton    Signal channel + continueAsNew pattern is standard
Image Reflector events    Configuration-dependent    Requires --events-addr; otherwise degraded polling fallback
Aevum receipt    Integration point    Wrap the bridge's signal result in aevum.ingest()
The spine is buildable now for the Flux→NATS→Temporal→workflow path. The only piece that is not fully turnkey is the DLQ adapter and the Aevum receipt integration, both of which are small additions to the bridge.

The environment emits the Flux event; NATS carries it durably; the bridge converts it to a Signal; Temporal wakes the agent; the agent verifies and records the receipt. The agent responds instead of running the show.
```
