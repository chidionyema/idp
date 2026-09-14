package main

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/nats-io/nats.go/jetstream"

	"github.com/chidionyema/idp/platform/messaging/subject"
)

var githubReceived = subject.MustParse("epistemic.event.github.received.v1")

// runGitHub is the GitHub webhook receiver: one real HTTP input, HMAC-verified
// against the GitHub App/repo webhook secret, one CloudEvent published per
// delivery. GitHub's own delivery id (X-GitHub-Delivery) is the dedup key: a
// webhook GitHub retries on a non-2xx response must land on the same
// Nats-Msg-Id as the first attempt, not a second stored copy.
func runGitHub(ctx context.Context, js jetstream.JetStream) error {
	if _, err := ensureStream(ctx, js, githubStream); err != nil {
		return fmt.Errorf("ensure stream %s: %w", githubStream.name, err)
	}
	secret, err := secretFromFile("GITHUB_WEBHOOK_SECRET_FILE")
	if err != nil {
		return err
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/webhook", func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(io.LimitReader(r.Body, 5<<20))
		if err != nil {
			http.Error(w, "read body", http.StatusBadRequest)
			return
		}
		if err := verifyGitHubSignature(secret, r.Header.Get("X-Hub-Signature-256"), body); err != nil {
			http.Error(w, err.Error(), http.StatusUnauthorized)
			return
		}
		deliveryID := r.Header.Get("X-GitHub-Delivery")
		if deliveryID == "" {
			http.Error(w, "missing X-GitHub-Delivery", http.StatusBadRequest)
			return
		}
		eventKind := r.Header.Get("X-GitHub-Event")
		ack, err := publish(r.Context(), js, githubStream.wireSubject, githubReceived,
			"/epistemic-ingest/github/"+eventKind, deliveryID, body)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadGateway)
			return
		}
		w.WriteHeader(http.StatusAccepted)
		fmt.Fprintf(w, "{\"stream\":%q,\"seq\":%d}", githubStream.name, ack.Sequence)
	})
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusOK) })

	addr := ":8080"
	if p := os.Getenv("PORT"); p != "" {
		addr = ":" + p
	}
	srv := &http.Server{Addr: addr, Handler: mux}
	errCh := make(chan error, 1)
	go func() { errCh <- srv.ListenAndServe() }()
	touchReady()
	fmt.Println("github webhook receiver listening on", addr)

	select {
	case <-ctx.Done():
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = srv.Shutdown(shutdownCtx)
		return ctx.Err()
	case err := <-errCh:
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return err
	}
}

// verifyGitHubSignature checks the sha256=<hex hmac> header GitHub sends on
// every webhook delivery, constant-time, against the secret configured on the
// GitHub App/repo side (platform/epistemic-fabric/external-secret.yaml).
func verifyGitHubSignature(secret, header string, body []byte) error {
	const prefix = "sha256="
	if !strings.HasPrefix(header, prefix) {
		return errors.New("missing or malformed X-Hub-Signature-256")
	}
	want, err := hex.DecodeString(strings.TrimPrefix(header, prefix))
	if err != nil {
		return errors.New("X-Hub-Signature-256 is not hex")
	}
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(body)
	if !hmac.Equal(mac.Sum(nil), want) {
		return errors.New("signature does not match GITHUB_WEBHOOK_SECRET")
	}
	return nil
}
