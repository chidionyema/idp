package intent

import (
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

const contract = `{"kind":"intent_result","intent":"ci-status","status":"ok","text":"All green.","visual":{"cue":"pulse","target":"fleet","severity":"info"},"ticket":null}`

func TestResolveReturnsTheContract(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("method = %s, want POST", r.Method)
		}
		if r.URL.Path != "/voice/intent" {
			t.Errorf("path = %s, want /voice/intent", r.URL.Path)
		}
		var got map[string]string
		if err := json.NewDecoder(r.Body).Decode(&got); err != nil {
			t.Errorf("decode body: %v", err)
		}
		want := map[string]string{"text": "check ci status", "session_id": "sess-1"}
		if got["text"] != want["text"] || got["session_id"] != want["session_id"] {
			t.Errorf("body = %v, want %v", got, want)
		}
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(contract))
	}))
	defer srv.Close()

	c := &Client{URL: srv.URL + "/voice/intent"}
	r, err := c.Resolve(context.Background(), "check ci status", "sess-1")
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if r.Status != "ok" {
		t.Errorf("Status = %q, want ok", r.Status)
	}
	if r.Text != "All green." {
		t.Errorf("Text = %q, want %q", r.Text, "All green.")
	}
	if r.Visual.Cue != "pulse" {
		t.Errorf("Visual.Cue = %q, want pulse", r.Visual.Cue)
	}
	if r.Ticket != nil {
		t.Errorf("Ticket = %v, want nil", r.Ticket)
	}
	if string(r.Raw) != contract {
		t.Errorf("Raw = %s, want %s", r.Raw, contract)
	}
}

func TestNoContentIsNotAnIntent(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	}))
	defer srv.Close()

	c := &Client{URL: srv.URL}
	r, err := c.Resolve(context.Background(), "hello", "sess-1")
	if r != nil || err != nil {
		t.Fatalf("Resolve = %v, %v, want nil, nil", r, err)
	}
}

func TestServerErrorIsAnError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()

	c := &Client{URL: srv.URL}
	if _, err := c.Resolve(context.Background(), "hello", "sess-1"); err == nil {
		t.Fatal("Resolve: want error, got nil")
	}
}

func TestWrongShapeIsAnError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"kind":"other"}`))
	}))
	defer srv.Close()

	c := &Client{URL: srv.URL}
	if _, err := c.Resolve(context.Background(), "hello", "sess-1"); err == nil {
		t.Fatal("Resolve: want error, got nil")
	}
}

func TestContextCancelsTheCall(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		select {
		case <-r.Context().Done():
		case <-time.After(3 * time.Second):
		}
	}))
	defer srv.Close()

	c := &Client{URL: srv.URL}
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()

	start := time.Now()
	_, err := c.Resolve(ctx, "hello", "sess-1")
	elapsed := time.Since(start)

	if err == nil {
		t.Fatal("Resolve: want error, got nil")
	}
	if elapsed >= time.Second {
		t.Errorf("elapsed = %v, want < 1s", elapsed)
	}
}

func TestHookMatchedAndFallsThrough(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(contract))
	}))
	defer srv.Close()

	log := slog.New(slog.NewTextHandler(io.Discard, nil))
	h := Hook{Client: &Client{URL: srv.URL}, Log: log}

	raw, text, ok := h.Resolve(context.Background(), "check ci status", "sess-1")
	if !ok {
		t.Fatal("Resolve: ok = false, want true")
	}
	if string(raw) != contract {
		t.Errorf("raw = %s, want %s", raw, contract)
	}
	if text != "All green." {
		t.Errorf("text = %q, want %q", text, "All green.")
	}

	srv.Close()
	h2 := Hook{Client: &Client{URL: srv.URL}, Log: log}
	_, _, ok2 := h2.Resolve(context.Background(), "check ci status", "sess-1")
	if ok2 {
		t.Error("Resolve on closed server: ok = true, want false")
	}
}
