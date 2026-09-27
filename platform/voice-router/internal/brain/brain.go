// Package brain streams a chat completion from any OpenAI-compatible
// endpoint. In the estate that endpoint is the litellm router, so the model
// behind the voice is a router alias, never a vendor wired into this code.
package brain

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
)

// Message is one chat turn.
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// Client talks to an OpenAI-compatible /chat/completions endpoint.
type Client struct {
	BaseURL   string
	Model     string
	APIKey    string
	MaxTokens int
	HTTP      *http.Client
}

// FromEnv reads LLM_BASE_URL, LLM_MODEL and LLM_API_KEY. The defaults point at
// the local estate router and its fast lane.
func FromEnv() *Client {
	c := &Client{
		BaseURL: env("LLM_BASE_URL", "http://127.0.0.1:4000/v1"),
		Model:   env("LLM_MODEL", "fast"),
		APIKey:  os.Getenv("LLM_API_KEY"),
		// Headroom for reasoning lanes: the router's fast lane (gpt-oss) streams
		// ~200-300 hidden reasoning chunks first; at 300 the answer came back
		// empty (measured 2026-09-26). The system prompt bounds spoken length.
		MaxTokens: 1024,
		HTTP:      &http.Client{},
	}
	c.BaseURL = strings.TrimRight(c.BaseURL, "/")
	return c
}

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

// ErrEmpty is a completed reply with no words in it. A reasoning lane does this when its hidden
// reasoning spends the token budget (finish_reason "length"), or now and then for no stated reason.
var ErrEmpty = errors.New("brain: empty reply")

// Stream sends msgs and calls onDelta with each content fragment as it
// arrives. Cancelling ctx drops the connection, which stops generation.
//
// An empty reply is asked once more: the person is waiting in silence, and the second draw
// usually answers. A second empty reply is returned as ErrEmpty with the finish reason.
func (c *Client) Stream(ctx context.Context, msgs []Message, onDelta func(string)) error {
	var err error
	for range 2 {
		got := false
		var finish string
		// Whitespace is not an answer (/fleet measured a 0.48 s reply of nothing but blanks), so
		// leading blanks are dropped and do not count as a reply.
		err = c.stream(ctx, msgs, func(d string) {
			if !got && strings.TrimSpace(d) == "" {
				return
			}
			got = true
			onDelta(d)
		}, &finish)
		if err != nil || got {
			return err
		}
		err = fmt.Errorf("%w (finish_reason=%q)", ErrEmpty, finish)
	}
	return err
}

// Ready asks the lane for one token. The process being up says nothing about voice: on
// 2026-09-27 the router lost the `voice` lane and every turn failed while /healthz said ok.
func (c *Client) Ready(ctx context.Context) error {
	body, err := json.Marshal(map[string]any{
		"model": c.Model, "messages": []Message{{"user", "ok"}}, "max_tokens": 1,
	})
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	if c.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.APIKey)
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return fmt.Errorf("brain %s: %w", c.Model, err)
	}
	defer resp.Body.Close()
	b, _ := io.ReadAll(io.LimitReader(resp.Body, 512))
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("brain %s: %s: %s", c.Model, resp.Status, strings.TrimSpace(string(b)))
	}
	return nil
}

func (c *Client) stream(ctx context.Context, msgs []Message, onDelta func(string), finish *string) error {
	body, err := json.Marshal(map[string]any{
		"model": c.Model, "messages": msgs, "stream": true, "max_tokens": c.MaxTokens,
	})
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "text/event-stream")
	if c.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.APIKey)
	}
	// Marks the POST replayable without sending the header (net/http: a nil value), so a pooled
	// connection the router closed while idle is retried on a fresh one instead of failing the
	// turn. 2026-09-27 a gate turn went silent on "connection reset by peer" 63 ms after the final.
	req.Header["X-Idempotency-Key"] = nil
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(io.LimitReader(resp.Body, 512))
		return fmt.Errorf("brain: %s: %s", resp.Status, strings.TrimSpace(string(b)))
	}
	sc := bufio.NewScanner(resp.Body)
	sc.Buffer(make([]byte, 64*1024), 1<<20)
	for sc.Scan() {
		line := sc.Text()
		if !strings.HasPrefix(line, "data:") {
			continue
		}
		data := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
		if data == "[DONE]" {
			return nil
		}
		var chunk struct {
			Choices []struct {
				Delta struct {
					Content string `json:"content"`
				} `json:"delta"`
				FinishReason string `json:"finish_reason"`
			} `json:"choices"`
			Error *struct {
				Message string `json:"message"`
			} `json:"error"`
		}
		if err := json.Unmarshal([]byte(data), &chunk); err != nil {
			continue
		}
		if chunk.Error != nil {
			return fmt.Errorf("brain: %s", chunk.Error.Message)
		}
		if len(chunk.Choices) > 0 {
			if f := chunk.Choices[0].FinishReason; f != "" {
				*finish = f
			}
			if chunk.Choices[0].Delta.Content != "" {
				onDelta(chunk.Choices[0].Delta.Content)
			}
		}
	}
	if err := sc.Err(); err != nil {
		return err
	}
	return ctx.Err()
}
