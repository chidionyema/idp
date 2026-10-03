// Package newsroom — the estate newsroom (crew#974 P1) turns raw cluster and
// CI facts into scored, deduplicated stories with deterministic headlines and
// no LLM.
package newsroom

import (
	"crypto/sha256"
	"fmt"
	"math"
	"sync"
	"time"
)

const (
	StateReported  = "reported"
	StateConfirmed = "confirmed"
	StateCorrected = "corrected"

	// The scheduler retries an unschedulable pod every ~10m11s (measured on OKE, 2026-09-27);
	// a 10m window split one ongoing failure into a story per retry.
	DedupeWindow = 30 * time.Minute
	EvidenceCap  = 5
)

type Raw struct {
	Source    string
	Kind      string
	Entity    string
	Name      string
	Namespace string
	Severity  string
	Reason    string
	Message   string
	Link      string
	At        time.Time
}

type Story struct {
	ID         string    `json:"id"`
	Supersedes string    `json:"supersedes,omitempty"`
	Channel    string    `json:"channel"`
	Source     string    `json:"source"`
	Severity   string    `json:"severity"`
	State      string    `json:"state"`
	Headline   string    `json:"headline"`
	Anchor     string    `json:"anchor"`
	Entity     string    `json:"entity"`
	Link       string    `json:"link,omitempty"`
	Evidence   []string  `json:"evidence"`
	Score      float64   `json:"score"`
	Count      int       `json:"count"`
	Breaking   bool      `json:"breaking"`
	FirstAt    time.Time `json:"first_at"`
	At         time.Time `json:"at"`

	// Repeat is true when this Ingest folded into a story that already exists inside the
	// dedupe window, rather than opening a new one. It is the answer to "has the estate heard
	// this already?", which Count alone cannot give: a repeat still carries the updated Count
	// and evidence, and the caller must still keep it, but it must not be announced again.
	//
	// This exists because a repeat was being published and logged like a first sighting. One
	// Kyverno warning re-emitted 24 times in 7ms became 24 published stories and 24 log lines,
	// and the director was OOMKilled at its 128Mi limit (measured on OKE, 2026-10-03,
	// exit=137 reason=OOMKilled). Deduping the map is not deduping the announcement.
	Repeat bool `json:"-"`

	raw Raw
}

func Classify(r Raw) string {
	switch r.Source {
	case "flux", "cicd":
		return "deploys"
	case "k8s":
		return "cluster"
	case "agent":
		return "agents"
	default:
		return "news"
	}
}

// Score weighs severity, decays it by age, and doubles a first-ever sighting.
func Score(severity string, age time.Duration, count int) float64 {
	weight := 1.0
	switch severity {
	case "warn":
		weight = 3
	case "danger":
		weight = 9
	}
	if age < 0 {
		age = 0
	}
	score := weight * math.Pow(0.5, age.Minutes()/10)
	if count == 1 {
		score *= 2
	}
	return math.Round(score*100) / 100
}

func Subjects(s Story) []string {
	subjects := []string{"estate.news.story." + s.Channel}
	if s.Channel != "news" && (s.Score >= 3 || s.Breaking) {
		subjects = append(subjects, "estate.news.story.news")
	}
	return subjects
}

func severityRank(sev string) int {
	switch sev {
	case "warn":
		return 1
	case "danger":
		return 2
	default:
		return 0
	}
}

func higherSeverity(a, b string) string {
	if severityRank(b) > severityRank(a) {
		return b
	}
	return a
}

func isHealthyKind(kind string) bool {
	return kind == "flux.deployed" || kind == "cicd.passed" || kind == "incident.closed"
}
func isFailureKind(kind string) bool {
	return kind == "flux.failed" || kind == "cicd.failed" || kind == "k8s.crashloop" || kind == "incident.open"
}

type Editor struct {
	mu      sync.Mutex
	stories map[string]*Story
	failed  map[string]string
	seq     uint64
}

func NewEditor() *Editor {
	return &Editor{
		stories: make(map[string]*Story),
		failed:  make(map[string]string),
	}
}

func (e *Editor) nextID(entity string, t time.Time) string {
	sum := sha256.Sum256([]byte(fmt.Sprintf("%s|%d|%d", entity, t.UnixNano(), e.seq)))
	e.seq++
	return fmt.Sprintf("%x", sum)[:16]
}

func appendEvidence(evidence []string, r Raw) []string {
	line := r.Message
	if line == "" {
		line = r.Reason
	}
	if line == "" {
		return evidence
	}
	evidence = append(evidence, line)
	if len(evidence) > EvidenceCap {
		evidence = evidence[len(evidence)-EvidenceCap:]
	}
	return evidence
}

func copyStory(s *Story) Story {
	out := *s
	out.Evidence = append([]string{}, s.Evidence...)
	return out
}

func (e *Editor) prune(now time.Time) {
	if len(e.stories) <= 2000 {
		return
	}
	cutoff := now.Add(-1 * time.Hour)
	for entity, s := range e.stories {
		if s.At.Before(cutoff) {
			delete(e.stories, entity)
		}
	}
}

func (e *Editor) Ingest(r Raw, now time.Time) (Story, bool) {
	if r.Entity == "" || r.Kind == "" {
		return Story{}, false
	}
	t := r.At
	if t.IsZero() {
		t = now
	}

	e.mu.Lock()
	defer e.mu.Unlock()

	if isHealthyKind(r.Kind) {
		if supersedes, ok := e.failed[r.Entity]; ok {
			s := e.newStory(r, t, e.nextID(r.Entity, t))
			s.Supersedes = supersedes
			s.Severity = "info"
			s.State = StateCorrected
			finalize(s, now)
			delete(e.failed, r.Entity)
			e.stories[r.Entity] = s
			e.prune(now)
			return copyStory(s), true
		}
	}

	// a deploy of a new revision is its own story, never a repeat of the last one
	newRevision := r.Kind == "flux.deployed" && r.Reason != ""
	if prev, ok := e.stories[r.Entity]; ok && prev.raw.Kind == r.Kind && t.Sub(prev.At) <= DedupeWindow &&
		!(newRevision && prev.raw.Reason != r.Reason) {
		prev.Count++
		prev.Severity = higherSeverity(prev.Severity, r.Severity)
		if t.After(prev.At) {
			prev.At = t
		}
		prev.Evidence = appendEvidence(prev.Evidence, r)
		prev.raw = r
		prev.Link = r.Link
		finalize(prev, now)
		e.prune(now)
		out := copyStory(prev)
		out.Repeat = true
		return out, true
	}

	id := e.nextID(r.Entity, t)
	s := e.newStory(r, t, id)
	if r.Kind == "flux.deployed" {
		s.State = StateConfirmed
	}
	finalize(s, now)
	if isFailureKind(r.Kind) {
		e.failed[r.Entity] = id
	}
	e.stories[r.Entity] = s
	e.prune(now)
	return copyStory(s), true
}

func (e *Editor) newStory(r Raw, t time.Time, id string) *Story {
	severity := r.Severity
	if severity == "" {
		severity = "info"
	}
	return &Story{
		ID:       id,
		Channel:  Classify(r),
		Source:   r.Source,
		Entity:   r.Entity,
		Link:     r.Link,
		Severity: severity,
		State:    StateReported,
		Count:    1,
		FirstAt:  t,
		At:       t,
		Evidence: appendEvidence(nil, r),
		raw:      r,
	}
}

func finalize(s *Story, now time.Time) {
	render(s)
	s.Score = Score(s.Severity, now.Sub(s.FirstAt), s.Count)
	s.Breaking = s.Severity == "danger" || (s.raw.Kind == "cicd.failed" && s.Count >= 3)
}

func ord(n int) string {
	suffix := "th"
	if n%100 < 11 || n%100 > 13 {
		switch n % 10 {
		case 1:
			suffix = "st"
		case 2:
			suffix = "nd"
		case 3:
			suffix = "rd"
		}
	}
	return fmt.Sprintf("%d%s", n, suffix)
}

func attr(source string) string {
	switch source {
	case "flux":
		return "Flux"
	case "k8s":
		return "Kubernetes"
	case "cicd":
		return "GitHub Actions"
	case "incidents":
		return "GitHub Issues"
	case "agent":
		return "the agent feed"
	default:
		return source
	}
}

func render(s *Story) {
	r := s.raw
	n, rs, ns := r.Name, r.Reason, r.Namespace
	m := int(math.Ceil(s.At.Sub(s.FirstAt).Minutes()))
	if m < 1 {
		m = 1
	}

	if s.State == StateCorrected {
		s.Headline = "RECOVERED: " + n
		if r.Source == "cicd" {
			s.Headline = "RECOVERED: " + n + " on " + rs
		}
		s.Anchor = n + " is healthy again after the failure reported earlier, according to " + attr(r.Source) + "."
		return
	}

	switch r.Kind {
	case "flux.deployed":
		s.Headline = "DEPLOYED: " + n + " reconciled " + rs
		s.Anchor = n + " is now running " + rs + ", according to Flux."
	case "flux.failed":
		if s.Count == 1 {
			s.Headline = "FAILED: " + n
		} else {
			s.Headline = fmt.Sprintf("FAILED: %s, %s in %dm", n, ord(s.Count), m)
		}
		s.Anchor = n + " is not reconciling (" + rs + "), so its changes are not reaching the cluster, according to Flux."
	case "k8s.crashloop":
		s.Headline = "CRASHLOOP: " + n + " in " + ns
		s.Anchor = n + " keeps restarting, so what it serves is down or degraded, according to Kubernetes."
	case "k8s.warning":
		s.Headline = "WARNING: " + rs + " on " + n + " in " + ns
		s.Anchor = n + " reported " + rs + ", which can stop it running as intended, according to Kubernetes."
	case "cicd.failed":
		if s.Count == 1 {
			s.Headline = "CI RED: " + n + " on " + rs
		} else {
			s.Headline = fmt.Sprintf("CI RED: %s on %s, %s in %dm", n, rs, ord(s.Count), m)
		}
		s.Anchor = n + " failed on " + rs + ", so that change cannot ship until it is fixed, according to GitHub Actions."
	case "cicd.passed":
		s.Headline = "CI GREEN: " + n + " on " + rs
		s.Anchor = n + " passed on " + rs + ", so that change can ship, according to GitHub Actions."
	case "incident.open":
		s.Headline = "INCIDENT: " + n
		s.Anchor = "An incident is open and needs an owner, according to GitHub Issues."
	case "incident.closed":
		s.Headline = "INCIDENT CLOSED: " + n
		s.Anchor = "The incident is closed, according to GitHub Issues."
	default:
		s.Headline = "UPDATE: " + n
		s.Anchor = n + " changed, according to " + attr(r.Source) + "."
	}
}
