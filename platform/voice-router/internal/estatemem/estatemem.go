// Package estatemem is the voice's door into unified estate memory: the
// remember/recall/brief tools the agentgateway serves at /estate/mcp, the same
// memory every Otto and every runtime on the operator's Mac reads and writes.
//
// It is switched on by two settings and off without them: ESTATE_MCP_URL (the
// gateway's MCP endpoint) and ESTATE_MCP_KEY_FILE (a file holding its bearer
// key). Every failure is the caller's to ignore: memory grounds an answer, it
// never stands between a question and its answer.
package estatemem

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

const (
	protocolVersion = "2025-03-26"
	runtime         = "fleetview-voice"
	source          = "voice"
	maxGrounding    = 1500 // chars of brief handed to the brain: a spoken answer needs a few facts, not a dossier
	maxRemembered   = 600  // chars of one exchange kept
)

// Client calls the estate memory tools. A nil *Client is valid and does nothing.
type Client struct {
	URL     string
	KeyFile string // re-read on every call, so a rotated secret is picked up without a restart
	HTTP    *http.Client
	Log     *slog.Logger

	mu      sync.Mutex
	session string
	pending chan struct{} // bounds the background remembers in flight
	nextID  int
}

// FromEnv returns a client when ESTATE_MCP_URL and ESTATE_MCP_KEY_FILE are both
// set and the key file is readable and non-empty; otherwise nil (memory off).
func FromEnv(log *slog.Logger) *Client {
	url, file := strings.TrimSpace(os.Getenv("ESTATE_MCP_URL")), strings.TrimSpace(os.Getenv("ESTATE_MCP_KEY_FILE"))
	if url == "" || file == "" {
		return nil
	}
	if b, err := os.ReadFile(file); err != nil || strings.TrimSpace(string(b)) == "" {
		log.Warn("estatemem.off", "reason", "key file unreadable or empty", "key_file", file)
		return nil
	}
	return New(url, file, log)
}

// New returns a client for url, authenticating with the key in keyFile.
func New(url, keyFile string, log *slog.Logger) *Client {
	return &Client{URL: url, KeyFile: keyFile, HTTP: &http.Client{}, Log: log, pending: make(chan struct{}, 4)}
}

// Brief returns what estate memory holds that is relevant to task, as lines
// ready to hand the brain. "" on any failure or when nothing is relevant.
func (c *Client) Brief(ctx context.Context, task string) string {
	if c == nil {
		return ""
	}
	t0 := time.Now()
	text, err := c.call(ctx, "brief", map[string]any{"task": task, "limit": 5})
	if err != nil {
		c.Log.Warn("estatemem.brief", "err", err, "ms", time.Since(t0).Milliseconds())
		return ""
	}
	var out struct {
		Relevant []struct {
			Text string `json:"text"`
		} `json:"relevant"`
	}
	if err := json.Unmarshal([]byte(text), &out); err != nil {
		c.Log.Warn("estatemem.brief", "err", fmt.Errorf("decode: %w", err))
		return ""
	}
	var b strings.Builder
	for _, r := range out.Relevant {
		line := strings.TrimSpace(r.Text)
		if line == "" {
			continue
		}
		if b.Len()+len(line) > maxGrounding {
			break
		}
		b.WriteString("- " + line + "\n")
	}
	c.Log.Info("estatemem.brief", "items", len(out.Relevant), "chars", b.Len(), "ms", time.Since(t0).Milliseconds())
	return strings.TrimSpace(b.String())
}

// Recall returns the raw JSON text of the memories matching query.
func (c *Client) Recall(ctx context.Context, query string, limit int) (string, error) {
	if c == nil {
		return "", errors.New("estate memory is off")
	}
	args := map[string]any{"query": query}
	if limit > 0 {
		args["limit"] = limit
	}
	return c.call(ctx, "recall", args)
}

// Remember stores content in the background, bounded by timeout. It never
// blocks: when too many are already in flight, this one is dropped and logged.
func (c *Client) Remember(content string, timeout time.Duration) {
	if c == nil || strings.TrimSpace(content) == "" {
		return
	}
	if len(content) > maxRemembered {
		content = content[:maxRemembered]
	}
	select {
	case c.pending <- struct{}{}:
	default:
		c.Log.Warn("estatemem.remember", "err", "dropped: too many in flight")
		return
	}
	go func() {
		defer func() { <-c.pending }()
		ctx, cancel := context.WithTimeout(context.Background(), timeout)
		defer cancel()
		if _, err := c.call(ctx, "remember", map[string]any{"content": content, "source": source, "runtime": runtime}); err != nil {
			c.Log.Warn("estatemem.remember", "err", err)
		}
	}()
}

// call runs one tool and returns its result text. The MCP session is opened
// once and reused; a gateway that has forgotten it (404) gets a fresh one, once.
func (c *Client) call(ctx context.Context, tool string, args map[string]any) (string, error) {
	key, err := os.ReadFile(c.KeyFile)
	if err != nil {
		return "", fmt.Errorf("key file: %w", err)
	}
	k := strings.TrimSpace(string(key))
	for attempt := 0; ; attempt++ {
		sid, err := c.sessionID(ctx, k)
		if err != nil {
			return "", err
		}
		res, status, _, err := c.rpc(ctx, k, sid, "tools/call", map[string]any{"name": tool, "arguments": args})
		if status == http.StatusNotFound && attempt == 0 {
			c.mu.Lock()
			if c.session == sid {
				c.session = ""
			}
			c.mu.Unlock()
			continue
		}
		if err != nil {
			return "", fmt.Errorf("%s: %w", tool, err)
		}
		var r struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
			IsError bool `json:"isError"`
		}
		if err := json.Unmarshal(res, &r); err != nil {
			return "", fmt.Errorf("%s: decode result: %w", tool, err)
		}
		text := ""
		if len(r.Content) > 0 {
			text = r.Content[0].Text
		}
		if r.IsError {
			return "", fmt.Errorf("%s: tool error: %.200s", tool, text)
		}
		return text, nil
	}
}

func (c *Client) sessionID(ctx context.Context, key string) (string, error) {
	c.mu.Lock()
	sid := c.session
	c.mu.Unlock()
	if sid != "" {
		return sid, nil
	}
	_, _, sid, err := c.rpc(ctx, key, "", "initialize", map[string]any{
		"protocolVersion": protocolVersion,
		"capabilities":    map[string]any{},
		"clientInfo":      map[string]any{"name": runtime, "version": "1"},
	})
	if err != nil {
		return "", fmt.Errorf("initialize: %w", err)
	}
	c.mu.Lock()
	c.session = sid
	c.mu.Unlock()
	return sid, nil
}

// rpc posts one JSON-RPC request and returns its result, the HTTP status and
// the session id the server named. The reply may be plain JSON or an SSE
// stream; for SSE the last data: line is the answer.
func (c *Client) rpc(ctx context.Context, key, sid, method string, params any) (json.RawMessage, int, string, error) {
	c.mu.Lock()
	c.nextID++
	id := c.nextID
	c.mu.Unlock()
	body, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "id": id, "method": method, "params": params})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.URL, bytes.NewReader(body))
	if err != nil {
		return nil, 0, "", err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json, text/event-stream")
	req.Header.Set("Authorization", "Bearer "+key)
	if sid != "" {
		req.Header.Set("Mcp-Session-Id", sid)
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, 0, "", err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return nil, resp.StatusCode, "", err
	}
	if resp.StatusCode != http.StatusOK {
		return nil, resp.StatusCode, "", fmt.Errorf("http %d: %.200s", resp.StatusCode, raw)
	}
	payload := raw
	if strings.HasPrefix(resp.Header.Get("Content-Type"), "text/event-stream") {
		payload = nil
		sc := bufio.NewScanner(bytes.NewReader(raw))
		sc.Buffer(make([]byte, 64*1024), 1<<20)
		for sc.Scan() {
			if d, ok := strings.CutPrefix(sc.Text(), "data:"); ok && strings.TrimSpace(d) != "" {
				payload = []byte(strings.TrimSpace(d))
			}
		}
		if payload == nil {
			return nil, resp.StatusCode, "", errors.New("event stream carried no data")
		}
	}
	var m struct {
		Result json.RawMessage `json:"result"`
		Error  *struct {
			Code    int    `json:"code"`
			Message string `json:"message"`
		} `json:"error"`
	}
	if err := json.Unmarshal(payload, &m); err != nil {
		return nil, resp.StatusCode, "", fmt.Errorf("decode: %w", err)
	}
	if m.Error != nil {
		return nil, resp.StatusCode, "", fmt.Errorf("rpc error %d: %s", m.Error.Code, m.Error.Message)
	}
	return m.Result, resp.StatusCode, resp.Header.Get("Mcp-Session-Id"), nil
}
