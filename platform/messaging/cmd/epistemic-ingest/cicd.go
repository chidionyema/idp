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

var cicdReported = subject.MustParse("epistemic.event.cicd.reported.v1")

type workflowRun struct {
	ID         int64  `json:"id"`
	Name       string `json:"name"`
	Status     string `json:"status"`
	Conclusion string `json:"conclusion"`
	UpdatedAt  string `json:"updated_at"`
	HeadBranch string `json:"head_branch"`
	HTMLURL    string `json:"html_url"`
}

type workflowRunsResponse struct {
	WorkflowRuns []workflowRun `json:"workflow_runs"`
}

// runCICD polls one repo's GitHub Actions run list -- the CI/CD telemetry the
// spec names -- and publishes every run whose id is newer than the highest one
// already seen.
func runCICD(ctx context.Context, js jetstream.JetStream) error {
	if _, err := ensureStream(ctx, js, cicdStream); err != nil {
		return fmt.Errorf("ensure stream %s: %w", cicdStream.name, err)
	}
	token, err := secretFromFile("GITHUB_TOKEN_FILE")
	if err != nil {
		return err
	}
	repo := os.Getenv("GITHUB_REPO")
	if repo == "" {
		return fmt.Errorf("GITHUB_REPO not set (owner/repo): which repository's CI to tap is a founder decision")
	}
	client := &http.Client{Timeout: 15 * time.Second}
	var sinceID int64
	if v := os.Getenv("CICD_SINCE_RUN_ID"); v != "" {
		sinceID, _ = strconv.ParseInt(v, 10, 64)
	}
	touchReady()
	return runLoop(ctx, pollInterval(), func(ctx context.Context) error {
		next, err := pollCICDOnce(ctx, client, token, repo, sinceID, js)
		if err != nil {
			return err
		}
		if next > sinceID {
			sinceID = next
		}
		return nil
	})
}

func pollCICDOnce(ctx context.Context, client *http.Client, token, repo string, sinceID int64, js jetstream.JetStream) (int64, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		githubAPIBase+"/repos/"+repo+"/actions/runs?per_page=30", nil)
	if err != nil {
		return sinceID, err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Accept", "application/vnd.github+json")
	resp, err := client.Do(req)
	if err != nil {
		return sinceID, fmt.Errorf("list workflow runs: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return sinceID, fmt.Errorf("list workflow runs: HTTP %d", resp.StatusCode)
	}
	var runs workflowRunsResponse
	if err := json.NewDecoder(resp.Body).Decode(&runs); err != nil {
		return sinceID, fmt.Errorf("decode workflow runs: %w", err)
	}
	max := sinceID
	for i := len(runs.WorkflowRuns) - 1; i >= 0; i-- {
		r := runs.WorkflowRuns[i]
		if r.ID <= sinceID {
			continue
		}
		body, err := json.Marshal(r)
		if err != nil {
			return max, err
		}
		if _, err := publish(ctx, js, cicdStream.wireSubject, cicdReported,
			"/epistemic-ingest/cicd/"+repo, strconv.FormatInt(r.ID, 10), body); err != nil {
			return max, err
		}
		if r.ID > max {
			max = r.ID
		}
	}
	return max, nil
}
