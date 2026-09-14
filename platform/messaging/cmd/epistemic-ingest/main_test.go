package main

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
	"time"

	"github.com/nats-io/nats-server/v2/server"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"

	"github.com/chidionyema/idp/platform/messaging/subject"
)

// startEmbeddedBroker gives the test a real, unauthenticated JetStream broker
// -- the same shape platform/event-bus/nats.yaml runs today (no accounts, no
// nkeys, no JWTs configured; ADR 0012 D4's nsc-issued JWTs are the future
// state, not the deployed one). This does not reuse
// platform/messaging/local: that package's embedded server locks every user
// to orders.>, which would refuse every epistemic.* publish this test proves,
// and widening its permission set would be a change to the ORDERS_EVENTS demo
// this ticket has no reason to touch (LAW 23, smaller road).
func startEmbeddedBroker(t *testing.T) (*nats.Conn, jetstream.JetStream) {
	t.Helper()
	dir := t.TempDir()
	ns, err := server.NewServer(&server.Options{
		Host: "127.0.0.1", Port: -1, JetStream: true,
		StoreDir: filepath.Join(dir, "js"), NoSigs: true, NoLog: true,
	})
	if err != nil {
		t.Fatalf("embedded nats-server: %v", err)
	}
	go ns.Start()
	if !ns.ReadyForConnections(10 * time.Second) {
		t.Fatal("embedded nats-server not ready in 10s")
	}
	t.Cleanup(ns.Shutdown)
	nc, js, err := connect(ns.ClientURL())
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	t.Cleanup(nc.Close)
	return nc, js
}

// TestEnsureStreamAndPublish is CP1's own acceptance check, in Go: each of the
// four streams gets created with the literal wire subject
// docs/specs/issue-3448.md and the feature file name, and one CloudEvent
// published through this package's own publish() lands on it with the D1
// ce-type header intact. This is the test that catches CP1 being reverted:
// drop ensureStream/publish's wire-subject override and this fails with
// "message on epistemic.github: wanted 1, ORDERS_EVENTS holds 0".
func TestEnsureStreamAndPublish(t *testing.T) {
	_, js := startEmbeddedBroker(t)
	ctx := context.Background()

	cases := []struct {
		name   string
		def    streamDef
		ceType subject.Subject
		source string
	}{
		{"github", githubStream, githubReceived, "/epistemic-ingest/github/push"},
		{"slack", slackStream, slackExported, "/epistemic-ingest/slack/C123"},
		{"cicd", cicdStream, cicdReported, "/epistemic-ingest/cicd/chidionyema/idp"},
		{"incidents", incidentsStream, incidentLogged, "/epistemic-ingest/incidents/chidionyema/idp"},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if _, err := ensureStream(ctx, js, c.def); err != nil {
				t.Fatalf("ensure stream %s: %v", c.def.name, err)
			}
			ack, err := publish(ctx, js, c.def.wireSubject, c.ceType, c.source, "ext-1", []byte(`{"k":"v"}`))
			if err != nil {
				t.Fatalf("publish: %v", err)
			}
			if ack.Stream != c.def.name {
				t.Fatalf("published landed on stream %q, wanted %q", ack.Stream, c.def.name)
			}

			cons, err := js.OrderedConsumer(ctx, c.def.name, jetstream.OrderedConsumerConfig{})
			if err != nil {
				t.Fatalf("consumer: %v", err)
			}
			m, err := cons.Next()
			if err != nil {
				t.Fatalf("read back: %v", err)
			}
			if m.Subject() != c.def.wireSubject {
				t.Fatalf("message landed on subject %q, wanted %q (the literal subject issue#3448 locks)", m.Subject(), c.def.wireSubject)
			}
			if got := m.Headers().Get("ce-type"); got != c.ceType.String() {
				t.Fatalf("ce-type header = %q, wanted the D1 subject %q", got, c.ceType.String())
			}
			if m.Headers().Get("ce-specversion") != "1.0" {
				t.Fatalf("ce-specversion missing or wrong: %q", m.Headers().Get("ce-specversion"))
			}

			info, err := js.Stream(ctx, c.def.name)
			if err != nil {
				t.Fatalf("stream info: %v", err)
			}
			si, _ := info.Info(ctx)
			if si.State.Msgs != 1 {
				t.Fatalf("stream %s holds %d messages, wanted 1", c.def.name, si.State.Msgs)
			}
		})
	}
}

// TestDedupIDStable proves the reason the connectors override cloudevent.New's
// random id: the same external id must always mint the same Nats-Msg-Id, or a
// poller that restarts and re-reads a page stores the same GitHub run or Slack
// message twice.
func TestDedupIDStable(t *testing.T) {
	a := dedupID("/epistemic-ingest/cicd/x", "42")
	b := dedupID("/epistemic-ingest/cicd/x", "42")
	if a != b {
		t.Fatalf("dedupID is not deterministic: %s != %s", a, b)
	}
	c := dedupID("/epistemic-ingest/cicd/x", "43")
	if a == c {
		t.Fatal("dedupID collapsed two different external ids to the same id")
	}
}

// TestPublishDuplicateWindow proves the JetStream duplicate window (D8, 15
// minutes) actually catches a republish of the same external id -- the
// concrete failure mode dedupID exists to prevent.
func TestPublishDuplicateWindow(t *testing.T) {
	_, js := startEmbeddedBroker(t)
	ctx := context.Background()
	if _, err := ensureStream(ctx, js, cicdStream); err != nil {
		t.Fatalf("ensure stream: %v", err)
	}
	if _, err := publish(ctx, js, cicdStream.wireSubject, cicdReported, "/epistemic-ingest/cicd/x", "run-1", []byte(`{}`)); err != nil {
		t.Fatalf("first publish: %v", err)
	}
	ack, err := publish(ctx, js, cicdStream.wireSubject, cicdReported, "/epistemic-ingest/cicd/x", "run-1", []byte(`{"different":"payload"}`))
	if err != nil {
		t.Fatalf("second publish: %v", err)
	}
	if !ack.Duplicate {
		t.Fatal("republishing the same external id was not caught as a duplicate")
	}
	info, _ := js.Stream(ctx, cicdStream.name)
	si, _ := info.Info(ctx)
	if si.State.Msgs != 1 {
		t.Fatalf("stream holds %d messages after a duplicate republish, wanted 1", si.State.Msgs)
	}
}

// TestVerifyGitHubSignature proves the webhook receiver's HMAC check both
// ways: the fixture a real GitHub delivery produces passes, and a body
// signed with the wrong secret is refused.
func TestVerifyGitHubSignature(t *testing.T) {
	body := []byte(`{"action":"opened"}`)
	secret := "whsec-test-only"
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(body)
	good := "sha256=" + hex.EncodeToString(mac.Sum(nil))

	if err := verifyGitHubSignature(secret, good, body); err != nil {
		t.Fatalf("a correctly signed delivery was refused: %v", err)
	}
	if err := verifyGitHubSignature(secret, "sha256=00", body); err == nil {
		t.Fatal("a wrong signature was accepted")
	}
	if err := verifyGitHubSignature("other-secret", good, body); err == nil {
		t.Fatal("a signature made with the wrong secret was accepted")
	}
}

// TestPollSlackOnce runs the real HTTP-call-and-decode-and-publish path
// against a local httptest.Server standing in for slack.com/api -- a real
// network round trip over loopback, a real JSON decode of a Slack-shaped
// response, a real publish onto a real JetStream stream. No live Slack
// credential exists in this environment (FOUNDER ACTION, see
// platform/epistemic-fabric/external-secret.yaml); this is the closest
// empirical proof available for that code path here.
func TestPollSlackOnce(t *testing.T) {
	_, js := startEmbeddedBroker(t)
	ctx := context.Background()
	if _, err := ensureStream(ctx, js, slackStream); err != nil {
		t.Fatalf("ensure stream: %v", err)
	}

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if got := r.Header.Get("Authorization"); got != "Bearer xoxb-test" {
			t.Errorf("Authorization header = %q", got)
		}
		_ = json.NewEncoder(w).Encode(slackHistoryResponse{
			OK: true,
			Messages: []slackMessage{
				{Type: "message", User: "U1", Text: "deploy is live", TS: "1700000000.000100"},
			},
		})
	}))
	defer srv.Close()
	old := slackAPIBase
	slackAPIBase = srv.URL
	defer func() { slackAPIBase = old }()

	client := &http.Client{Timeout: 5 * time.Second}
	next, err := pollSlackOnce(ctx, client, "xoxb-test", "C123", "1699999999.000000", js)
	if err != nil {
		t.Fatalf("pollSlackOnce: %v", err)
	}
	if next != "1700000000.000100" {
		t.Fatalf("cursor = %q, wanted the message's own ts", next)
	}
	info, _ := js.Stream(ctx, slackStream.name)
	si, _ := info.Info(ctx)
	if si.State.Msgs != 1 {
		t.Fatalf("EPISTEMIC_SLACK holds %d messages, wanted 1", si.State.Msgs)
	}
}

// TestPollCICDOnce is TestPollSlackOnce's shape for the GitHub Actions runs
// poller: a real httptest.Server standing in for api.github.com.
func TestPollCICDOnce(t *testing.T) {
	_, js := startEmbeddedBroker(t)
	ctx := context.Background()
	if _, err := ensureStream(ctx, js, cicdStream); err != nil {
		t.Fatalf("ensure stream: %v", err)
	}

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(workflowRunsResponse{
			WorkflowRuns: []workflowRun{
				{ID: 101, Name: "ci", Status: "completed", Conclusion: "success", HeadBranch: "main"},
			},
		})
	}))
	defer srv.Close()
	old := githubAPIBase
	githubAPIBase = srv.URL
	defer func() { githubAPIBase = old }()

	client := &http.Client{Timeout: 5 * time.Second}
	max, err := pollCICDOnce(ctx, client, "ghp-test", "chidionyema/idp", 0, js)
	if err != nil {
		t.Fatalf("pollCICDOnce: %v", err)
	}
	if max != 101 {
		t.Fatalf("sinceID = %d, wanted 101", max)
	}
	info, _ := js.Stream(ctx, cicdStream.name)
	si, _ := info.Info(ctx)
	if si.State.Msgs != 1 {
		t.Fatalf("EPISTEMIC_CICD holds %d messages, wanted 1", si.State.Msgs)
	}
}

// TestPollIncidentsOnce is the same shape for the GitHub Issues poller.
func TestPollIncidentsOnce(t *testing.T) {
	_, js := startEmbeddedBroker(t)
	ctx := context.Background()
	if _, err := ensureStream(ctx, js, incidentsStream); err != nil {
		t.Fatalf("ensure stream: %v", err)
	}

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode([]issue{
			{Number: 7, Title: "prod db down", State: "open", UpdatedAt: "2026-09-14T20:00:00Z"},
		})
	}))
	defer srv.Close()
	old := githubAPIBase
	githubAPIBase = srv.URL
	defer func() { githubAPIBase = old }()

	client := &http.Client{Timeout: 5 * time.Second}
	next, err := pollIncidentsOnce(ctx, client, "ghp-test", "chidionyema/idp", "incident", "2026-09-14T00:00:00Z", js)
	if err != nil {
		t.Fatalf("pollIncidentsOnce: %v", err)
	}
	if next != "2026-09-14T20:00:00Z" {
		t.Fatalf("cursor = %q, wanted the issue's own updated_at", next)
	}
	info, _ := js.Stream(ctx, incidentsStream.name)
	si, _ := info.Info(ctx)
	if si.State.Msgs != 1 {
		t.Fatalf("EPISTEMIC_INCIDENTS holds %d messages, wanted 1", si.State.Msgs)
	}
}
