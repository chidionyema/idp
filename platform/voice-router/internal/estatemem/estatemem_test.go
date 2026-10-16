package estatemem

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

var quiet = slog.New(slog.NewTextHandler(io.Discard, nil))

// gateway is a fake /estate/mcp: it checks the key and the session, and
// answers each tool from tools, as plain JSON or, with sse set, an event stream.
type gateway struct {
	t     *testing.T
	sse   bool
	delay time.Duration
	tools map[string]string // tool -> result text
	isErr bool

	mu    sync.Mutex
	inits int
	calls []map[string]any // tools/call params, in order
	drop  bool             // forget the session once: the next tools/call gets 404
}

func (g *gateway) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Header.Get("Authorization") != "Bearer k3y" {
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return
	}
	var req struct {
		ID     int             `json:"id"`
		Method string          `json:"method"`
		Params json.RawMessage `json:"params"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		g.t.Errorf("decode: %v", err)
	}
	time.Sleep(g.delay)
	var result any
	g.mu.Lock()
	switch req.Method {
	case "initialize":
		g.inits++
		w.Header().Set("Mcp-Session-Id", fmt.Sprintf("s%d", g.inits))
		result = map[string]any{"protocolVersion": protocolVersion}
	case "tools/call":
		if r.Header.Get("Mcp-Session-Id") != fmt.Sprintf("s%d", g.inits) || g.drop {
			g.drop = false
			g.mu.Unlock()
			http.Error(w, "unknown session", http.StatusNotFound)
			return
		}
		var p map[string]any
		_ = json.Unmarshal(req.Params, &p)
		g.calls = append(g.calls, p)
		result = map[string]any{"content": []map[string]any{{"type": "text", "text": g.tools[p["name"].(string)]}}, "isError": g.isErr}
	}
	g.mu.Unlock()
	body, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "id": req.ID, "result": result})
	if g.sse {
		w.Header().Set("Content-Type", "text/event-stream")
		fmt.Fprintf(w, "event: message\ndata: %s\n\n", body)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write(body)
}

func keyFile(t *testing.T, key string) string {
	f := filepath.Join(t.TempDir(), "ESTATE_MCP_KEY")
	if err := os.WriteFile(f, []byte(key+"\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	return f
}

const briefText = `{"relevant":[{"text":"the estate runs three nodes","metadata":{}},{"text":"voice lives on :8091","metadata":{}}],"recent":[],"namespace":"estate"}`

func TestDisabledWithoutBothSettings(t *testing.T) {
	f := keyFile(t, "k3y")
	for _, c := range []struct{ url, file string }{{"", f}, {"http://x", ""}, {"http://x", filepath.Join(t.TempDir(), "missing")}, {"http://x", keyFile(t, " ")}} {
		t.Setenv("ESTATE_MCP_URL", c.url)
		t.Setenv("ESTATE_MCP_KEY_FILE", c.file)
		if got := FromEnv(quiet); got != nil {
			t.Fatalf("url=%q file=%q: memory on, want off", c.url, c.file)
		}
	}
	var off *Client // what main holds when memory is off: every call is a harmless no-op
	if off.Brief(context.Background(), "x") != "" {
		t.Fatal("nil client briefed")
	}
	off.Remember("x", time.Second)
	t.Setenv("ESTATE_MCP_URL", "http://x")
	t.Setenv("ESTATE_MCP_KEY_FILE", f)
	if FromEnv(quiet) == nil {
		t.Fatal("both set and key readable: memory off, want on")
	}
}

func TestBriefPlainAndEventStream(t *testing.T) {
	for _, sse := range []bool{false, true} {
		g := &gateway{t: t, sse: sse, tools: map[string]string{"brief": briefText}}
		srv := httptest.NewServer(g)
		c := New(srv.URL, keyFile(t, "k3y"), quiet)
		got := c.Brief(context.Background(), "how many nodes")
		if got != "- the estate runs three nodes\n- voice lives on :8091" {
			t.Fatalf("sse=%v: brief %q", sse, got)
		}
		c.Brief(context.Background(), "again") // the session is reused, not reopened
		if g.inits != 1 || g.calls[0]["arguments"].(map[string]any)["task"] != "how many nodes" {
			t.Fatalf("sse=%v: inits=%d calls=%v", sse, g.inits, g.calls)
		}
		srv.Close()
	}
}

func TestSlowGatewayIsCutOffByTheCaller(t *testing.T) {
	g := &gateway{t: t, delay: 2 * time.Second, tools: map[string]string{"brief": briefText}}
	srv := httptest.NewServer(g)
	defer srv.Close()
	c := New(srv.URL, keyFile(t, "k3y"), quiet)
	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()
	t0 := time.Now()
	if got := c.Brief(ctx, "x"); got != "" {
		t.Fatalf("brief %q from a gateway past its deadline", got)
	}
	if d := time.Since(t0); d > time.Second {
		t.Fatalf("brief waited %v, past its 100ms budget", d)
	}
}

func TestFailuresAreQuiet(t *testing.T) {
	g := &gateway{t: t, isErr: true, tools: map[string]string{"brief": "boom", "recall": "boom"}}
	srv := httptest.NewServer(g)
	c := New(srv.URL, keyFile(t, "k3y"), quiet)
	if got := c.Brief(context.Background(), "x"); got != "" {
		t.Fatalf("tool error briefed %q", got)
	}
	if _, err := c.Recall(context.Background(), "x", 3); err == nil || !strings.Contains(err.Error(), "tool error") {
		t.Fatalf("recall err %v", err)
	}
	bad := New(srv.URL, keyFile(t, "wrong"), quiet)
	if _, err := bad.Recall(context.Background(), "x", 0); err == nil || !strings.Contains(err.Error(), "401") {
		t.Fatalf("wrong key: err %v", err)
	}
	srv.Close()
	if got := c.Brief(context.Background(), "x"); got != "" { // gateway gone
		t.Fatalf("dead gateway briefed %q", got)
	}
}

func TestForgottenSessionIsReopenedOnce(t *testing.T) {
	g := &gateway{t: t, tools: map[string]string{"recall": `{"memories":[]}`}}
	srv := httptest.NewServer(g)
	defer srv.Close()
	c := New(srv.URL, keyFile(t, "k3y"), quiet)
	if _, err := c.Recall(context.Background(), "x", 0); err != nil {
		t.Fatal(err)
	}
	g.mu.Lock()
	g.drop = true
	g.mu.Unlock()
	if _, err := c.Recall(context.Background(), "x", 0); err != nil {
		t.Fatalf("after the gateway forgot the session: %v", err)
	}
}

func TestRememberRunsInTheBackgroundWithItsTags(t *testing.T) {
	g := &gateway{t: t, tools: map[string]string{"remember": `{"ok":true}`}}
	srv := httptest.NewServer(g)
	defer srv.Close()
	c := New(srv.URL, keyFile(t, "k3y"), quiet)
	c.Remember("Asked by voice: how many nodes\nAnswered: three", time.Second)
	deadline := time.Now().Add(2 * time.Second)
	for {
		g.mu.Lock()
		n := len(g.calls)
		g.mu.Unlock()
		if n == 1 {
			break
		}
		if time.Now().After(deadline) {
			t.Fatal("remember never reached the gateway")
		}
		time.Sleep(5 * time.Millisecond)
	}
	a := g.calls[0]["arguments"].(map[string]any)
	if g.calls[0]["name"] != "remember" || a["runtime"] != "fleetview-voice" || a["source"] != "voice" || !strings.Contains(a["content"].(string), "three") {
		t.Fatalf("remember sent %v", g.calls[0])
	}
}
