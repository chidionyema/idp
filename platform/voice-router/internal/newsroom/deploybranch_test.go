package newsroom

import (
	"encoding/json"
	"testing"
	"time"
)

func newDeploy() *DeployBranch {
	return &DeployBranch{Automation: "deploy", Source: "idp-writer", Namespace: "flux-system", StaleAfter: 10 * time.Minute}
}

func automation(name, commit, observed string, pushed time.Time) json.RawMessage {
	b, _ := json.Marshal(map[string]any{
		"metadata": map[string]any{"name": name, "namespace": "flux-system"},
		"spec":     map[string]any{"git": map[string]any{"push": map[string]any{"branch": "flux/deploy"}}},
		"status": map[string]any{
			"lastPushCommit":         commit,
			"lastPushTime":           pushed.Format(time.RFC3339),
			"observedSourceRevision": "main@sha1:" + observed,
		},
	})
	return b
}

func gitRepo(name, rev string, at time.Time) json.RawMessage {
	b, _ := json.Marshal(map[string]any{
		"metadata": map[string]any{"name": name, "namespace": "flux-system"},
		"status": map[string]any{"artifact": map[string]any{
			"revision": "main@sha1:" + rev, "lastUpdateTime": at.Format(time.RFC3339),
		}},
	})
	return b
}

func TestEveryPushToFluxDeployIsAStory(t *testing.T) {
	d := newDeploy()
	m := &automationMapper{d: d, since: time.Hour}
	now := time.Date(2026, 9, 30, 17, 0, 0, 0, time.UTC)

	r, ok := m.seen(automation("deploy", "aaaaaaaaaa", "1111111111", now), watched, now)
	if !ok || r.Kind != "flux.pushed" || r.Reason != "aaaaaaa" || r.Entity != "ImageUpdateAutomation/flux-system/deploy" {
		t.Fatalf("first push: got %+v ok=%v", r, ok)
	}
	if _, ok := m.seen(automation("deploy", "aaaaaaaaaa", "1111111111", now), watched, now); ok {
		t.Fatal("the same push reported twice")
	}
	if _, ok := m.seen(automation("backstage", "bbbbbbbbbb", "1111111111", now), watched, now); ok {
		t.Fatal("another automation's push reported as flux/deploy")
	}
	if r, ok := m.seen(automation("deploy", "cccccccccc", "2222222222", now), watched, now); !ok || r.Reason != "ccccccc" {
		t.Fatalf("second push: got %+v ok=%v", r, ok)
	}
}

func TestAnOldPushAtStartupIsNotNews(t *testing.T) {
	m := &automationMapper{d: newDeploy(), since: time.Hour}
	now := time.Date(2026, 9, 30, 17, 0, 0, 0, time.UTC)
	if _, ok := m.seen(automation("deploy", "aaaaaaaaaa", "1", now.Add(-2*time.Hour)), firstList, now); ok {
		t.Fatal("a two-hour-old push was reported at startup")
	}
}

func TestMainNotOnFluxDeployWithinTheSLOIsABreach(t *testing.T) {
	d := newDeploy()
	t0 := time.Date(2026, 9, 30, 17, 0, 0, 0, time.UTC)
	(&automationMapper{d: d, since: time.Hour}).seen(automation("deploy", "p1", "old", t0), watched, t0)
	(&sourceMapper{d: d}).seen(gitRepo("idp-writer", "new", t0), watched, t0)

	if _, ok := d.Check(t0.Add(9 * time.Minute)); ok {
		t.Fatal("breach reported inside the 10m SLO")
	}
	r, ok := d.Check(t0.Add(11 * time.Minute))
	if !ok || r.Kind != "flux.stale" || r.Severity != "danger" {
		t.Fatalf("no breach at 11m: got %+v ok=%v", r, ok)
	}
	if _, ok := d.Check(t0.Add(12 * time.Minute)); ok {
		t.Fatal("one breach reported twice")
	}

	(&automationMapper{d: d, since: time.Hour}).seen(automation("deploy", "p2", "new", t0), watched, t0.Add(13*time.Minute))
	r, ok = d.Check(t0.Add(13 * time.Minute))
	if !ok || r.Kind != "flux.fresh" {
		t.Fatalf("no recovery once main was built: got %+v ok=%v", r, ok)
	}
}

func TestACurrentFluxDeployNeverBreaches(t *testing.T) {
	d := newDeploy()
	t0 := time.Date(2026, 9, 30, 17, 0, 0, 0, time.UTC)
	(&sourceMapper{d: d}).seen(gitRepo("idp-writer", "same", t0), watched, t0)
	(&automationMapper{d: d, since: time.Hour}).seen(automation("deploy", "p1", "same", t0), watched, t0)
	if r, ok := d.Check(t0.Add(time.Hour)); ok {
		t.Fatalf("breach on a current flux/deploy: %+v", r)
	}
	if _, ok := (&sourceMapper{d: d}).seen(gitRepo("other", "x", t0), watched, t0); ok || d.main != "same" {
		t.Fatal("another GitRepository moved main's head")
	}
}

func TestABreachIsBreakingNewsAndItsRecoveryCorrectsIt(t *testing.T) {
	e := NewEditor()
	now := time.Date(2026, 9, 30, 17, 11, 0, 0, time.UTC)
	stale := Raw{Source: "flux", Kind: "flux.stale", Severity: "danger", Entity: "ImageUpdateAutomation/flux-system/deploy",
		Name: "deploy", Namespace: "flux-system", Reason: "11m0s", At: now}
	s, ok := e.Ingest(stale, now)
	if !ok || !s.Breaking || s.Channel != "deploys" {
		t.Fatalf("breach story: %+v", s)
	}
	subj := Subjects(s)
	if len(subj) != 2 || subj[0] != "estate.news.story.deploys" || subj[1] != "estate.news.story.news" {
		t.Fatalf("breach not on the news channel: %v", subj)
	}
	if s.Headline != "DEPLOY STALLED: main not on flux/deploy after 11m0s" {
		t.Fatalf("headline: %q", s.Headline)
	}
	fresh := stale
	fresh.Kind, fresh.Severity, fresh.At = "flux.fresh", "info", now.Add(2*time.Minute)
	c, ok := e.Ingest(fresh, now.Add(2*time.Minute))
	if !ok || c.State != StateCorrected || c.Supersedes != s.ID {
		t.Fatalf("recovery did not correct the breach: %+v", c)
	}
}
