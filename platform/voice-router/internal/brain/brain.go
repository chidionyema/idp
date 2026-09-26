// Package brain streams a chat completion from any OpenAI-compatible
// endpoint. In the estate that endpoint is the litellm router, so the model
// behind the voice is a router alias, never a vendor wired into this code.
package brain

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
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

// Stream sends msgs and calls onDelta with each content fragment as it
// arrives. Cancelling ctx drops the connection, which stops generation.
func (c *Client) Stream(ctx context.Context, msgs []Message, onDelta func(string)) error {
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
		if len(chunk.Choices) > 0 && chunk.Choices[0].Delta.Content != "" {
			onDelta(chunk.Choices[0].Delta.Content)
		}
	}
	if err := sc.Err(); err != nil {
		return err
	}
	return ctx.Err()
}
