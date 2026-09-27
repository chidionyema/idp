// Package intent asks the FleetView backend whether an utterance names a committed estate intent (POST /voice/intent). 204 = no; the brain answers.
package intent

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"time"
)

// Visual is the on-screen cue a matched intent asks the client to render.
type Visual struct {
	Cue      string `json:"cue"`
	Target   string `json:"target"`
	Severity string `json:"severity"`
}

// Result is what the backend returns when text names a committed intent.
type Result struct {
	Kind   string          `json:"kind"`
	Intent string          `json:"intent"`
	Status string          `json:"status"`
	Text   string          `json:"text"`
	Visual Visual          `json:"visual"`
	Ticket *string         `json:"ticket"`
	Raw    json.RawMessage `json:"-"`
}

// DefaultTimeout covers a matched intent's whole run (the backend allows 120s). Barge-in cancels it earlier through ctx.
const DefaultTimeout = 125 * time.Second

// Client calls the FleetView backend's /voice/intent endpoint.
type Client struct {
	URL  string // full endpoint, e.g. http://127.0.0.1:7007/voice/intent
	HTTP *http.Client
}

// Resolve asks whether text names a committed estate intent for sessionID.
func (c *Client) Resolve(ctx context.Context, text, sessionID string) (*Result, error) {
	body, err := json.Marshal(map[string]string{"text": text, "session_id": sessionID})
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.URL, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	hc := c.HTTP
	if hc == nil {
		hc = &http.Client{Timeout: DefaultTimeout}
	}
	resp, err := hc.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNoContent {
		return nil, nil
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("intent: status %d", resp.StatusCode)
	}

	b, err := io.ReadAll(io.LimitReader(resp.Body, 64<<10))
	if err != nil {
		return nil, err
	}
	var r Result
	if err := json.Unmarshal(b, &r); err != nil {
		return nil, err
	}
	if r.Kind != "intent_result" || r.Intent == "" || r.Text == "" {
		return nil, errors.New("intent: not an intent_result")
	}
	r.Raw = b
	return &r, nil
}

// Hook adapts Client to session.Intents. On any error it reports not matched, so the brain answers.
type Hook struct {
	Client *Client
	Log    *slog.Logger
}

// Resolve implements session.Intents.
func (h Hook) Resolve(ctx context.Context, text, sessionID string) (json.RawMessage, string, bool) {
	r, err := h.Client.Resolve(ctx, text, sessionID)
	if err != nil {
		if h.Log != nil && ctx.Err() == nil {
			h.Log.Warn("voice.intent", "err", err)
		}
		return nil, "", false
	}
	if r == nil {
		return nil, "", false
	}
	return r.Raw, r.Text, true
}
