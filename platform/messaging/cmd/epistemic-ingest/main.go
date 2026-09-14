// Command epistemic-ingest is idp#3448 CP1: four small ingestion connectors for
// Layer 1 of the cognitive stack (the Epistemic Fabric). Each turns one real
// external source into CloudEvents on the estate's existing NATS JetStream
// event-bus (platform/event-bus) -- not a new broker (founder, 2026-09-14:
// "dont use kakfa we have etsrean"; docs/specs/issue-3448.md CP1).
//
//	epistemic-ingest github     HTTP webhook receiver, HMAC-verified, one push/PR/issue event per call
//	epistemic-ingest slack      polls conversations.history for one channel
//	epistemic-ingest cicd       polls the GitHub Actions run list for one repo
//	epistemic-ingest incidents  polls GitHub Issues by label for one repo
//
// One binary, one image, four modes -- the same shape as
// platform/messaging/cmd/demo's `demo basic|advanced`, so `bin/dockerfiles`
// discovers one Dockerfile and four Deployments select their mode with one
// argv element (platform/epistemic-fabric/ingest.yaml).
package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"

	"github.com/chidionyema/idp/platform/messaging/cloudevent"
	"github.com/chidionyema/idp/platform/messaging/subject"
)

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: epistemic-ingest github|slack|cicd|incidents")
		os.Exit(2)
	}
	mode := os.Args[1]
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer stop()

	natsURL := os.Getenv("NATS_URL")
	if natsURL == "" {
		fmt.Fprintln(os.Stderr, "NATS_URL not set (the Deployment names nats.event-bus.svc:4222, per router-events' own pattern)")
		os.Exit(2)
	}
	nc, js, err := connect(natsURL)
	if err != nil {
		fmt.Fprintln(os.Stderr, "RED epistemic-ingest:", err)
		os.Exit(1)
	}
	defer nc.Close()
	startHealthServer()

	var run func(context.Context, jetstream.JetStream) error
	switch mode {
	case "github":
		run = runGitHub
	case "slack":
		run = runSlack
	case "cicd":
		run = runCICD
	case "incidents":
		run = runIncidents
	default:
		fmt.Fprintln(os.Stderr, "usage: epistemic-ingest github|slack|cicd|incidents")
		os.Exit(2)
	}
	if err := run(ctx, js); err != nil && ctx.Err() == nil {
		fmt.Fprintln(os.Stderr, "RED epistemic-ingest", mode+":", err)
		os.Exit(1)
	}
	fmt.Println("ok epistemic-ingest", mode, "stopped on", ctx.Err())
}

// connect opens the connection to the event-bus NATS deployment. Production
// carries no NATS auth yet: platform/event-bus/nats.yaml configures no
// accounts/nkeys/JWTs, so the door this namespace's fence opens
// (platform/ns-fences/allowances.yaml: epistemic-fabric -> egress: [event-bus])
// is the NetworkPolicy, not a credential. platform/messaging/local documents
// nsc-issued JWTs as the future state (ADR 0012 D4); this connects the same
// unauthenticated way router-events' own publisher does today
// (platform/router-events/publisher.yaml: NATS_URL with no user/pass).
func connect(natsURL string) (*nats.Conn, jetstream.JetStream, error) {
	nc, err := nats.Connect(natsURL, nats.Name("epistemic-ingest"), nats.MaxReconnects(-1))
	if err != nil {
		return nil, nil, fmt.Errorf("connect %s: %w", natsURL, err)
	}
	js, err := jetstream.New(nc)
	if err != nil {
		nc.Close()
		return nil, nil, err
	}
	return nc, js, nil
}

// streamDef is one of the four JetStream streams CP1 requires -- one subject
// each, the literal two-token subjects docs/specs/issue-3448.md and
// features/cognitive-stack/cp1_ingestion_topics.feature name, not the estate's
// locked D1 five-token grammar. JetStream stream Names cannot contain a dot, so
// the ALL-CAPS underscore form follows platform/messaging/cmd/demo's own
// ORDERS_EVENTS/ORDERS_DLQ convention; Subjects carries the real wire subject.
type streamDef struct {
	name, wireSubject string
}

var (
	githubStream    = streamDef{"EPISTEMIC_GITHUB", "epistemic.github"}
	slackStream     = streamDef{"EPISTEMIC_SLACK", "epistemic.slack"}
	cicdStream      = streamDef{"EPISTEMIC_CICD", "epistemic.cicd"}
	incidentsStream = streamDef{"EPISTEMIC_INCIDENTS", "epistemic.incidents"}
)

// ensureStream is idempotent (CreateOrUpdateStream), matching
// platform/messaging/cmd/demo's ordersStream/basic pattern -- each connector
// provisions only the one stream it publishes to, so running one mode alone
// never creates a stream with no matching ingestion source (the feature file's
// own "no stream is created outside those four" line).
func ensureStream(ctx context.Context, js jetstream.JetStream, d streamDef) (jetstream.Stream, error) {
	return js.CreateOrUpdateStream(ctx, jetstream.StreamConfig{
		Name:       d.name,
		Subjects:   []string{d.wireSubject},
		Storage:    jetstream.FileStorage,
		Retention:  jetstream.LimitsPolicy,
		MaxAge:     30 * 24 * time.Hour,
		Duplicates: 15 * time.Minute,
		DenyDelete: true,
		DenyPurge:  true,
		Replicas:   1, // ADR 0012's own replicas note: 1, on the estate's small pool
	})
}

// dedupID turns a source-stable external identifier (a GitHub delivery id, a
// Slack message ts, a workflow run id, an issue number+updated_at) into the
// CloudEvents id and the JetStream Nats-Msg-Id. cloudevent.New mints a fresh
// random id every call, which is right for a service raising its own event
// once; a poller that restarts and re-reads a page it already published must
// land on the SAME id, or the stream's 15-minute duplicate window (D8) never
// catches the redelivery and the same GitHub run or Slack message is stored
// twice. Deterministic (uuid v5), not random: same input, same id, always.
func dedupID(source, externalID string) uuid.UUID {
	return uuid.NewSHA1(uuid.NameSpaceURL, []byte(source+"/"+externalID))
}

// publish sends one CloudEvent on wireSubject (the literal, spec-locked
// subject) with ceType as its ce-type header (a D1-compliant
// {domain}.event.{aggregate}.{action}.{version} descriptor -- what the event
// calls itself, per ADR 0012 D1, which governs an event's own name, not
// JetStream's separate subject/stream wiring). Two uses of the word "subject"
// in one call, on purpose: cloudevent.Event.Subject is the semantic ce-type,
// the NATS wire subject is the routing key, and order_paid's own code only
// looks like they are one value because its subjects happen to be identical.
func publish(ctx context.Context, js jetstream.JetStream, wireSubject string, ceType subject.Subject, source, externalID string, data []byte) (*jetstream.PubAck, error) {
	ev := cloudevent.New(ceType, source, data)
	ev.ID = dedupID(source, externalID)
	ack, err := js.PublishMsg(ctx, &nats.Msg{Subject: wireSubject, Header: ev.Headers(), Data: ev.Data})
	if err != nil {
		return nil, fmt.Errorf("publish %s (external id %s): %w", wireSubject, externalID, err)
	}
	return ack, nil
}

// secretFromFile reads a credential mounted as a file. Kyverno's
// secrets-not-from-env-vars policy refuses env.valueFrom.secretKeyRef on any
// pod in this estate (tests/fixtures/kyverno-secrets), so every credential
// this connector needs travels as a Secret volume mount, and envVar names the
// plain, non-secret *_FILE path pointing at it (platform/otto-gateway's own
// convention: PGPASSWORD_FILE, GITHUB_APP_PRIVATE_KEY_FILE).
func secretFromFile(envVar string) (string, error) {
	path := os.Getenv(envVar)
	if path == "" {
		return "", fmt.Errorf("%s not set: FOUNDER ACTION -- this connector's credential has no ExternalSecret backing it yet (platform/epistemic-fabric/external-secret.yaml)", envVar)
	}
	b, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("reading %s (path %s): %w", envVar, path, err)
	}
	return strings.TrimSpace(string(b)), nil
}

// ready backs an HTTP readiness/liveness probe, not an exec probe: the
// runtime image is gcr.io/distroless/static-debian12 (no shell, no coreutils
// -- `sh -c "test -f ..."`, the shape platform/router-events/publisher.yaml
// uses on a python image with a shell, cannot run here). touchReady flips it
// once the connector's own connect-and-provision step has actually completed
// -- a pod that is Running is not the claim.
var ready atomic.Bool

func touchReady() { ready.Store(true) }

// startHealthServer serves /healthz on HEALTH_PORT (default 8081) for the
// Deployment's httpGet probes. Best-effort: a probe going unready is the
// signal a broken connector gives, not a process crash.
func startHealthServer() {
	addr := ":8081"
	if p := os.Getenv("HEALTH_PORT"); p != "" {
		addr = ":" + p
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		if ready.Load() {
			w.WriteHeader(http.StatusOK)
			return
		}
		w.WriteHeader(http.StatusServiceUnavailable)
	})
	go func() {
		if err := http.ListenAndServe(addr, mux); err != nil {
			fmt.Fprintln(os.Stderr, "health server:", err)
		}
	}()
}

// slackAPIBase and githubAPIBase are the real vendor API hosts in production;
// a test overrides them to an httptest.Server so pollSlackOnce/pollCICDOnce/
// pollIncidentsOnce run their real HTTP-call-and-decode path against a real,
// local HTTP server rather than being skipped for want of a live credential.
var (
	slackAPIBase  = "https://slack.com/api"
	githubAPIBase = "https://api.github.com"
)

// pollInterval reads POLL_INTERVAL_SECONDS, default 30s -- short enough that a
// founder watching `nats stream ls` during CP1's own acceptance check
// (docs/specs/issue-3448.md) sees a non-zero count inside one demo run.
func pollInterval() time.Duration {
	if v := os.Getenv("POLL_INTERVAL_SECONDS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			return time.Duration(n) * time.Second
		}
	}
	return 30 * time.Second
}

// runLoop calls once immediately, then on every tick, until ctx is done. One
// poll's error is logged and the loop continues -- a transient GitHub/Slack API
// hiccup is not a crash-loop, it is a line in the log, same as
// platform/router-events' own listener staying up through one bad payload.
func runLoop(ctx context.Context, interval time.Duration, once func(context.Context) error) error {
	if err := once(ctx); err != nil {
		fmt.Fprintln(os.Stderr, "poll:", err)
	}
	t := time.NewTicker(interval)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-t.C:
			if err := once(ctx); err != nil {
				fmt.Fprintln(os.Stderr, "poll:", err)
			}
		}
	}
}
