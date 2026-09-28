package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/nats-io/nats.go/jetstream"

	"github.com/chidionyema/idp/platform/messaging/subject"
)

var incidentLogged = subject.MustParse("epistemic.event.incident.logged.v1")

type issue struct {
	Number    int    `json:"number"`
	Title     string `json:"title"`
	State     string `json:"state"`
	UpdatedAt string `json:"updated_at"`
	HTMLURL   string `json:"html_url"`
}

// runIncidents polls one repo's GitHub Issues, filtered by INCIDENT_LABEL
// (default "incident"), sorted by update time -- the incident log the spec
// names -- and publishes every issue whose updated_at is newer than the last
// one seen. An issue that gets a second comment publishes again, on the same
// number+updated_at pair, so a duplicate poll of an unchanged issue dedups
// (D8) rather than storing the same state twice.
func runIncidents(ctx context.Context, js jetstream.JetStream) error {
	if _, err := ensureStream(ctx, js, incidentsStream); err != nil {
		return fmt.Errorf("ensure stream %s: %w", incidentsStream.name, err)
	}
	token, err := secretFromFile("GITHUB_TOKEN_FILE")
	if err != nil {
		return err
	}
	repo := os.Getenv("GITHUB_REPO")
	if repo == "" {
		return fmt.Errorf("GITHUB_REPO not set (owner/repo): which repository's incidents to tap is a founder decision")
	}
	label := os.Getenv("INCIDENT_LABEL")
	if label == "" {
		label = "incident"
	}
	client := &http.Client{Timeout: 15 * time.Second}
	sinceUpdated := os.Getenv("INCIDENTS_SINCE")
	if sinceUpdated == "" {
		sinceUpdated = time.Now().UTC().Format(time.RFC3339)
	}
	touchReady()
	return runLoop(ctx, pollInterval(), func(ctx context.Context) error {
		next, err := pollIncidentsOnce(ctx, client, token, repo, label, sinceUpdated, js)
		if err != nil {
			return err
		}
		if next != "" {
			sinceUpdated = next
		}
		return nil
	})
}

func pollIncidentsOnce(ctx context.Context, client *http.Client, token, repo, label, since string, js jetstream.JetStream) (string, error) {
	url := githubAPIBase + "/repos/" + repo + "/issues?labels=" + label +
		"&state=all&sort=updated&direction=asc&since=" + since
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return since, err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Accept", "application/vnd.github+json")
	resp, err := client.Do(req)
	if err != nil {
		return since, fmt.Errorf("list issues: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return since, fmt.Errorf("list issues: HTTP %d", resp.StatusCode)
	}
	var issues []issue
	if err := json.NewDecoder(resp.Body).Decode(&issues); err != nil {
		return since, fmt.Errorf("decode issues: %w", err)
	}
	latest := since
	for _, it := range issues {
		body, err := json.Marshal(it)
		if err != nil {
			return latest, err
		}
		externalID := strconv.Itoa(it.Number) + "@" + it.UpdatedAt
		if _, err := publish(ctx, js, incidentsStream.wireSubject, incidentLogged,
			"/epistemic-ingest/incidents/"+repo, externalID, body); err != nil {
			return latest, err
		}
		if it.UpdatedAt > latest {
			latest = it.UpdatedAt
		}
	}
	return latest, nil
}
