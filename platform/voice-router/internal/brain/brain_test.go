package brain

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func sse(w http.ResponseWriter, parts ...string) {
	w.Header().Set("Content-Type", "text/event-stream")
	for _, p := range parts {
		b, _ := json.Marshal(map[string]any{"choices": []any{map[string]any{"delta": map[string]string{"content": p}}}})
		fmt.Fprintf(w, "data: %s\n\n", b)
		w.(http.Flusher).Flush()
	}
	fmt.Fprint(w, "data: [DONE]\n\n")
}

func TestStreamDeltasInOrderAndRequestShape(t *testing.T) {
	var got map[string]any
	var auth string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/chat/completions" {
			t.Errorf("path %s", r.URL.Path)
		}
		auth = r.Header.Get("Authorization")
		_ = json.NewDecoder(r.Body).Decode(&got)
		sse(w, "All five", " agents", " are healthy.")
	}))
	defer srv.Close()
	c := &Client{BaseURL: srv.URL + "/v1", Model: "fast", HTTP: srv.Client()}
	var b strings.Builder
	if err := c.Stream(context.Background(), []Message{{"user", "hi"}}, func(d string) { b.WriteString(d) }); err != nil {
		t.Fatal(err)
	}
	if b.String() != "All five agents are healthy." {
		t.Fatalf("got %q", b.String())
	}
	if got["model"] != "fast" || got["stream"] != true {
		t.Fatalf("request %v", got)
	}
	if auth != "" {
		t.Fatalf("sent an Authorization header with no key configured: %q", auth)
	}
}

func TestStreamReportsHTTPErrors(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, `{"error":"no such model"}`, http.StatusBadRequest)
	}))
	defer srv.Close()
	c := &Client{BaseURL: srv.URL, Model: "x", HTTP: srv.Client()}
	err := c.Stream(context.Background(), nil, func(string) {})
	if err == nil || !strings.Contains(err.Error(), "400") || !strings.Contains(err.Error(), "no such model") {
		t.Fatalf("err = %v", err)
	}
}

func TestStreamReportsInBandErrors(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, "data: {\"error\":{\"message\":\"rate limited\"}}\n\n")
	}))
	defer srv.Close()
	c := &Client{BaseURL: srv.URL, HTTP: srv.Client()}
	if err := c.Stream(context.Background(), nil, func(string) {}); err == nil || !strings.Contains(err.Error(), "rate limited") {
		t.Fatalf("err = %v", err)
	}
}

// Barge-in depends on this: cancelling the context must end the stream
// promptly even while the server is still sending.
func TestCancelStopsStream(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		for i := 0; ; i++ {
			select {
			case <-r.Context().Done():
				return
			case <-time.After(10 * time.Millisecond):
			}
			fmt.Fprintf(w, "data: {\"choices\":[{\"delta\":{\"content\":\"w%d \"}}]}\n\n", i)
			w.(http.Flusher).Flush()
		}
	}))
	defer srv.Close()
	ctx, cancel := context.WithCancel(context.Background())
	c := &Client{BaseURL: srv.URL, HTTP: srv.Client()}
	n := 0
	done := make(chan error, 1)
	go func() {
		done <- c.Stream(ctx, nil, func(string) {
			n++
			if n == 3 {
				cancel()
			}
		})
	}()
	select {
	case err := <-done:
		if err == nil {
			t.Fatal("cancelled stream returned nil")
		}
	case <-time.After(2 * time.Second):
		t.Fatal("stream did not stop after cancel")
	}
}
