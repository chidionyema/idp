package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"time"

	"github.com/nats-io/nats.go/jetstream"

	"github.com/chidionyema/idp/platform/messaging/subject"
)

var slackExported = subject.MustParse("epistemic.event.slack.exported.v1")

type slackMessage struct {
	Type string `json:"type"`
	User string `json:"user"`
	Text string `json:"text"`
	TS   string `json:"ts"`
}

type slackHistoryResponse struct {
	OK       bool           `json:"ok"`
	Error    string         `json:"error"`
	Messages []slackMessage `json:"messages"`
}

// runSlack polls one channel's conversations.history (the Slack export the
// spec names) and publishes every message newer than the last one seen.
// Cursor is in-memory: a pod restart re-reads from `oldest` (env, if the
// founder sets one) or from "now" -- CP1's own acceptance check sends one
// message and expects one message to land, which this satisfies without a
// second store to hold a cursor (THE HEADLINE: no store this estate did not
// already have).
func runSlack(ctx context.Context, js jetstream.JetStream) error {
	if _, err := ensureStream(ctx, js, slackStream); err != nil {
		return fmt.Errorf("ensure stream %s: %w", slackStream.name, err)
	}
	token, err := secretFromFile("SLACK_BOT_TOKEN_FILE")
	if err != nil {
		return err
	}
	channel := os.Getenv("SLACK_CHANNEL_ID")
	if channel == "" {
		return fmt.Errorf("SLACK_CHANNEL_ID not set: FOUNDER ACTION -- which channel to import is a founder decision, not a default")
	}
	client := &http.Client{Timeout: 15 * time.Second}
	oldest := os.Getenv("SLACK_OLDEST_TS")
	if oldest == "" {
		oldest = fmt.Sprintf("%d.000000", time.Now().Unix())
	}
	touchReady()
	return runLoop(ctx, pollInterval(), func(ctx context.Context) error {
		next, err := pollSlackOnce(ctx, client, token, channel, oldest, js)
		if err != nil {
			return err
		}
		if next != "" {
			oldest = next
		}
		return nil
	})
}

func pollSlackOnce(ctx context.Context, client *http.Client, token, channel, oldest string, js jetstream.JetStream) (string, error) {
	q := url.Values{"channel": {channel}, "oldest": {oldest}, "inclusive": {"false"}, "limit": {"200"}}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		slackAPIBase+"/conversations.history?"+q.Encode(), nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("conversations.history: %w", err)
	}
	defer resp.Body.Close()
	var hist slackHistoryResponse
	if err := json.NewDecoder(resp.Body).Decode(&hist); err != nil {
		return "", fmt.Errorf("decode conversations.history: %w", err)
	}
	if !hist.OK {
		return "", fmt.Errorf("conversations.history: slack error %q", hist.Error)
	}
	latest := oldest
	// Slack returns newest-first; publish oldest-first so a stream read in
	// order reads like the conversation did.
	for i := len(hist.Messages) - 1; i >= 0; i-- {
		m := hist.Messages[i]
		body, err := json.Marshal(m)
		if err != nil {
			return latest, err
		}
		if _, err := publish(ctx, js, slackStream.wireSubject, slackExported,
			"/epistemic-ingest/slack/"+channel, m.TS, body); err != nil {
			return latest, err
		}
		if m.TS > latest {
			latest = m.TS
		}
	}
	return latest, nil
}
