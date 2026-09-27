package newsroom

import (
	"testing"
	"time"
)

func TestDecodeCICDFailure(t *testing.T) {
	data := []byte(`{"id":123,"name":"build-multiarch","status":"completed","conclusion":"failure","updated_at":"2026-09-27T08:05:07Z","head_branch":"main","html_url":"https://github.com/chidionyema/idp/actions/runs/123"}`)
	now := time.Now()
	r, ok := DecodeEpistemic(SubjectCICD, data, now)
	if !ok {
		t.Fatal("expected ok")
	}
	if r.Kind != "cicd.failed" {
		t.Errorf("Kind = %q, want cicd.failed", r.Kind)
	}
	if r.Entity != "workflow/build-multiarch/main" {
		t.Errorf("Entity = %q, want workflow/build-multiarch/main", r.Entity)
	}
	if r.Reason != "main" {
		t.Errorf("Reason = %q, want main", r.Reason)
	}
	wantAt, _ := time.Parse(time.RFC3339, "2026-09-27T08:05:07Z")
	if !r.At.Equal(wantAt) {
		t.Errorf("At = %v, want %v", r.At, wantAt)
	}

	editor := NewEditor()
	story, ok := editor.Ingest(r, now)
	if !ok {
		t.Fatal("expected ingest ok")
	}
	if story.Headline != "CI RED: build-multiarch on main" {
		t.Errorf("Headline = %q, want CI RED: build-multiarch on main", story.Headline)
	}
	if story.Channel != "deploys" {
		t.Errorf("Channel = %q, want deploys", story.Channel)
	}
}

func TestDecodeCICDIgnoresInProgress(t *testing.T) {
	now := time.Now()
	inProgress := []byte(`{"id":1,"name":"build","status":"in_progress","conclusion":"","updated_at":"2026-09-27T08:00:00Z","head_branch":"main","html_url":""}`)
	if _, ok := DecodeEpistemic(SubjectCICD, inProgress, now); ok {
		t.Error("expected false for in_progress status")
	}

	cancelled := []byte(`{"id":2,"name":"build","status":"completed","conclusion":"cancelled","updated_at":"2026-09-27T08:00:00Z","head_branch":"main","html_url":""}`)
	if _, ok := DecodeEpistemic(SubjectCICD, cancelled, now); ok {
		t.Error("expected false for cancelled conclusion")
	}
}

func TestDecodeIncident(t *testing.T) {
	now := time.Now()
	open := []byte(`{"number":42,"title":"router 502s","state":"open","updated_at":"2026-09-27T08:00:00Z","html_url":"https://github.com/chidionyema/idp/issues/42"}`)
	r, ok := DecodeEpistemic(SubjectIncidents, open, now)
	if !ok {
		t.Fatal("expected ok")
	}
	if r.Kind != "incident.open" || r.Severity != "danger" {
		t.Errorf("Kind/Severity = %q/%q, want incident.open/danger", r.Kind, r.Severity)
	}

	editor := NewEditor()
	story, ok := editor.Ingest(r, now)
	if !ok {
		t.Fatal("expected ingest ok")
	}
	if story.Channel != "news" {
		t.Errorf("Channel = %q, want news", story.Channel)
	}
	if !story.Breaking {
		t.Error("expected Breaking true")
	}

	closed := []byte(`{"number":42,"title":"router 502s","state":"closed","updated_at":"2026-09-27T09:00:00Z","html_url":"https://github.com/chidionyema/idp/issues/42"}`)
	r2, ok := DecodeEpistemic(SubjectIncidents, closed, now)
	if !ok {
		t.Fatal("expected ok")
	}
	if r2.Kind != "incident.closed" || r2.Severity != "info" {
		t.Errorf("Kind/Severity = %q/%q, want incident.closed/info", r2.Kind, r2.Severity)
	}

	story2, ok := editor.Ingest(r2, now)
	if !ok {
		t.Fatal("expected ingest ok")
	}
	if story2.State != StateCorrected {
		t.Errorf("State = %q, want %q", story2.State, StateCorrected)
	}
	if story2.Headline != "RECOVERED: router 502s" {
		t.Errorf("Headline = %q, want RECOVERED: router 502s", story2.Headline)
	}
}

func TestDecodeUnknownSubject(t *testing.T) {
	if _, ok := DecodeEpistemic("epistemic.other", []byte(`{}`), time.Now()); ok {
		t.Error("expected false for unknown subject")
	}
}
