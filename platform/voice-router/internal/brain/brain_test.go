package brain

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
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

// A reasoning lane can finish with no words (seen on /fleet 2026-09-27: turn 2 fell silent).
// One empty draw is asked again; two are ErrEmpty, carrying the finish reason.
func TestEmptyReplyIsAskedOnceMoreThenReported(t *testing.T) {
	calls, answerOn := 0, 2
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		if calls == answerOn {
			sse(w, "Three sessions.")
			return
		}
		fmt.Fprint(w, "data: {\"choices\":[{\"delta\":{\"content\":\"\\n \"}}]}\n\n")
		fmt.Fprint(w, "data: {\"choices\":[{\"delta\":{},\"finish_reason\":\"length\"}]}\n\ndata: [DONE]\n\n")
	}))
	defer srv.Close()
	c := &Client{BaseURL: srv.URL, HTTP: srv.Client()}

	var b strings.Builder
	if err := c.Stream(context.Background(), nil, func(d string) { b.WriteString(d) }); err != nil || b.String() != "Three sessions." || calls != 2 {
		t.Fatalf("retry: err=%v said=%q calls=%d", err, b.String(), calls)
	}

	calls, answerOn = 0, 99
	err := c.Stream(context.Background(), nil, func(string) {})
	if !errors.Is(err, ErrEmpty) || !strings.Contains(err.Error(), `"length"`) || calls != 2 {
		t.Fatalf("two empties: err=%v calls=%d", err, calls)
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

// A pooled connection the router resets after reading the next request must not fail the turn:
// the request is replayed on a fresh connection (2026-09-27, "connection reset by peer").
func TestStreamSurvivesResetOfPooledConnection(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	answer := func(c net.Conn, r *bufio.Reader) bool {
		req, err := http.ReadRequest(r)
		if err != nil {
			return false
		}
		_, _ = io.Copy(io.Discard, req.Body)
		body := "data: {\"choices\":[{\"delta\":{\"content\":\"ok\"}}]}\n\ndata: [DONE]\n\n"
		fmt.Fprintf(c, "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nContent-Length: %d\r\n\r\n%s", len(body), body)
		return true
	}
	go func() {
		first := true
		for {
			c, err := ln.Accept()
			if err != nil {
				return
			}
			r := bufio.NewReader(c)
			if first {
				first = false
				answer(c, r)
				_, _ = http.ReadRequest(r) // the next turn arrives on the pooled connection ...
				c.(*net.TCPConn).SetLinger(0)
				c.Close() // ... and is reset unanswered
				continue
			}
			go func() {
				defer c.Close()
				for answer(c, r) {
				}
			}()
		}
	}()
	c := &Client{BaseURL: "http://" + ln.Addr().String(), HTTP: &http.Client{Timeout: 5 * time.Second}}
	for i := range 2 {
		var b strings.Builder
		if err := c.Stream(context.Background(), []Message{{"user", "hi"}}, func(d string) { b.WriteString(d) }); err != nil {
			t.Fatalf("turn %d: %v", i+1, err)
		}
		if b.String() != "ok" {
			t.Fatalf("turn %d: got %q", i+1, b.String())
		}
	}
}

// 2026-09-27 the laptop router was re-rendered without the `voice` lane. voice-router's
// /healthz kept answering ok while every spoken turn got "the brain did not answer" for two
// hours. Ready asks the lane itself, so a lane the router cannot serve is not ready.
func TestReadyIsTheLaneAnsweringNotTheProcessUp(t *testing.T) {
	var got map[string]any
	status, body := http.StatusOK, `{"choices":[{"message":{"content":"ok"}}]}`
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewDecoder(r.Body).Decode(&got)
		w.WriteHeader(status)
		_, _ = io.WriteString(w, body)
	}))
	defer srv.Close()
	c := &Client{BaseURL: srv.URL + "/v1", Model: "voice", HTTP: srv.Client()}
	if err := c.Ready(context.Background()); err != nil {
		t.Fatalf("a lane that answers is ready: %v", err)
	}
	if got["model"] != "voice" || got["stream"] == true {
		t.Fatalf("readiness asks the configured lane, unstreamed: %v", got)
	}

	status = http.StatusBadRequest
	body = `{"error":{"message":"litellm.BadRequestError: You passed in model=voice. There are no healthy deployments for this model"}}`
	err := c.Ready(context.Background())
	if err == nil || !strings.Contains(err.Error(), "no healthy deployments") || !strings.Contains(err.Error(), "voice") {
		t.Fatalf("a lane the router cannot serve is not ready, and says why: %v", err)
	}
}
