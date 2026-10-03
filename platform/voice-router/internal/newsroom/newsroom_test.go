package newsroom

import (
	"encoding/json"
	"testing"
	"time"
)

var t0 = time.Date(2026, 9, 27, 8, 0, 0, 0, time.UTC)

func TestClassify(t *testing.T) {
	cases := []struct {
		source string
		want   string
	}{
		{"flux", "deploys"},
		{"k8s", "cluster"},
		{"cicd", "deploys"},
		{"incidents", "news"},
		{"agent", "agents"},
		{"unknown", "news"},
	}
	for _, c := range cases {
		got := Classify(Raw{Source: c.source})
		if got != c.want {
			t.Errorf("Classify(%q) = %q, want %q", c.source, got, c.want)
		}
	}
}

func TestEditorDedupesWithinTheWindow(t *testing.T) {
	e := NewEditor()
	s1, ok := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", At: t0}, t0)
	if !ok {
		t.Fatal("expected ok")
	}
	s2, ok := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", At: t0.Add(5 * time.Minute)}, t0.Add(5*time.Minute))
	if !ok {
		t.Fatal("expected ok")
	}
	if s1.ID != s2.ID {
		t.Fatalf("expected same ID, got %q and %q", s1.ID, s2.ID)
	}
	if s2.Count != 2 {
		t.Fatalf("expected Count 2, got %d", s2.Count)
	}
	s3, ok := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", At: t0.Add(45 * time.Minute)}, t0.Add(45*time.Minute))
	if !ok {
		t.Fatal("expected ok")
	}
	if s3.ID == s1.ID {
		t.Fatalf("expected new ID, got same %q", s3.ID)
	}
	if s3.Count != 1 {
		t.Fatalf("expected Count 1, got %d", s3.Count)
	}
}

// A repeat updates the story but must announce nothing. One warning re-emitted in a burst
// became a published story and a log line per repeat, and the director was OOMKilled at its
// 128Mi limit (exit=137, measured on OKE 2026-10-03). The map was always deduped; the
// announcement was not, which is the whole bug.
func TestEditorMarksARepeatSoItIsNotAnnouncedAgain(t *testing.T) {
	e := NewEditor()
	s1, ok := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", At: t0}, t0)
	if !ok || s1.Repeat {
		t.Fatalf("first sighting: ok=%v Repeat=%v, want true/false", ok, s1.Repeat)
	}

	s2, ok := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", At: t0.Add(time.Second)}, t0.Add(time.Second))
	if !ok {
		t.Fatal("a repeat must still return the story")
	}
	if !s2.Repeat {
		t.Fatal("a repeat inside the window must be marked Repeat, or it publishes a second time")
	}
	if s2.ID != s1.ID || s2.Count != 2 {
		t.Fatalf("a repeat must fold into the story: id=%q count=%d want %q/2", s2.ID, s2.Count, s1.ID)
	}

	// Past the window it is news again, not a repeat.
	s3, _ := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", At: t0.Add(45 * time.Minute)}, t0.Add(45*time.Minute))
	if s3.Repeat {
		t.Fatal("a story past the dedupe window is a new sighting and must be announced")
	}
}

// The flood itself, as it was seen in production: the same warning many times in the same
// instant. Every repeat must be muted, so the count of announcements stays 1 no matter how
// many raw events arrive. This is the assertion that would have failed before the fix.
func TestABurstOfTheSameWarningIsAnnouncedOnce(t *testing.T) {
	e := NewEditor()
	announced := 0
	for i := 0; i < 500; i++ {
		at := t0.Add(time.Duration(i) * time.Microsecond)
		s, ok := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "Pod/default/probe-bad", Name: "probe-bad", At: at}, at)
		if ok && !s.Repeat {
			announced++
		}
	}
	if announced != 1 {
		t.Fatalf("500 repeats announced %d times, want 1 -- the flood is back", announced)
	}
}

func TestEditorFoldsTheSchedulerRetryCadence(t *testing.T) {
	e := NewEditor()
	var first Story
	for i := 0; i < 6; i++ {
		at := t0.Add(time.Duration(i) * (10*time.Minute + 11*time.Second))
		s, _ := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "coroot/pod", Name: "pod", Severity: "warn", At: at}, at)
		if i == 0 {
			first = s
		}
		if s.ID != first.ID {
			t.Fatalf("retry %d opened a new story %q, want %q", i, s.ID, first.ID)
		}
		if s.Count != i+1 {
			t.Fatalf("retry %d count = %d, want %d", i, s.Count, i+1)
		}
	}
}

func TestEditorSeverityOnlyEscalates(t *testing.T) {
	e := NewEditor()
	s1, _ := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", Severity: "warn", At: t0}, t0)
	s2, _ := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", Severity: "danger", At: t0.Add(1 * time.Minute)}, t0.Add(1*time.Minute))
	s3, _ := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", Severity: "info", At: t0.Add(2 * time.Minute)}, t0.Add(2*time.Minute))
	if s1.Severity != "warn" {
		t.Errorf("s1.Severity = %q, want warn", s1.Severity)
	}
	if s2.Severity != "danger" {
		t.Errorf("s2.Severity = %q, want danger", s2.Severity)
	}
	if s3.Severity != "danger" {
		t.Errorf("s3.Severity = %q, want danger", s3.Severity)
	}
}

func TestEditorScoreDecays(t *testing.T) {
	e := NewEditor()
	s1, _ := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", Severity: "warn", At: t0}, t0)
	if s1.Score != 6 {
		t.Errorf("s1.Score = %v, want 6", s1.Score)
	}
	s2, _ := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", Severity: "warn", At: t0.Add(10 * time.Minute)}, t0.Add(10*time.Minute))
	if s2.Score != 1.5 {
		t.Errorf("s2.Score = %v, want 1.5", s2.Score)
	}
	if got := Score("danger", 0, 1); got != 18 {
		t.Errorf("Score(danger,0,1) = %v, want 18", got)
	}
}

func TestEditorBreaking(t *testing.T) {
	e := NewEditor()
	s1, _ := e.Ingest(Raw{Source: "k8s", Kind: "k8s.crashloop", Entity: "e1", Name: "n1", Severity: "danger", At: t0}, t0)
	if !s1.Breaking {
		t.Error("expected danger story to be breaking")
	}

	e2 := NewEditor()
	s2, _ := e2.Ingest(Raw{Source: "cicd", Kind: "cicd.failed", Entity: "e2", Name: "n2", Reason: "main", Severity: "warn", At: t0}, t0)
	if s2.Breaking {
		t.Error("expected count 1 cicd.failed not breaking")
	}
	s3, _ := e2.Ingest(Raw{Source: "cicd", Kind: "cicd.failed", Entity: "e2", Name: "n2", Reason: "main", Severity: "warn", At: t0.Add(1 * time.Minute)}, t0.Add(1*time.Minute))
	if s3.Breaking {
		t.Error("expected count 2 cicd.failed not breaking")
	}
	s4, _ := e2.Ingest(Raw{Source: "cicd", Kind: "cicd.failed", Entity: "e2", Name: "n2", Reason: "main", Severity: "warn", At: t0.Add(2 * time.Minute)}, t0.Add(2*time.Minute))
	if !s4.Breaking {
		t.Error("expected count 3 cicd.failed breaking")
	}
}

func TestEditorCorrectsARecoveredFailure(t *testing.T) {
	e := NewEditor()
	a, _ := e.Ingest(Raw{Source: "flux", Kind: "flux.failed", Entity: "ns-fences", Name: "ns-fences", Reason: "timeout", At: t0}, t0)

	b, _ := e.Ingest(Raw{Source: "flux", Kind: "flux.deployed", Entity: "ns-fences", Name: "ns-fences", Reason: "main@sha1:abc", At: t0.Add(2 * time.Minute)}, t0.Add(2*time.Minute))
	if b.ID == a.ID {
		t.Fatal("expected new ID for correction")
	}
	if b.Supersedes != a.ID {
		t.Errorf("Supersedes = %q, want %q", b.Supersedes, a.ID)
	}
	if b.State != StateCorrected {
		t.Errorf("State = %q, want %q", b.State, StateCorrected)
	}
	if b.Severity != "info" {
		t.Errorf("Severity = %q, want info", b.Severity)
	}
	if b.Headline != "RECOVERED: ns-fences" {
		t.Errorf("Headline = %q, want %q", b.Headline, "RECOVERED: ns-fences")
	}

	c, _ := e.Ingest(Raw{Source: "flux", Kind: "flux.deployed", Entity: "ns-fences", Name: "ns-fences", Reason: "main@sha1:def", At: t0.Add(30 * time.Minute)}, t0.Add(30*time.Minute))
	if c.State != StateConfirmed {
		t.Errorf("State = %q, want %q", c.State, StateConfirmed)
	}
	if c.Supersedes != "" {
		t.Errorf("Supersedes = %q, want empty", c.Supersedes)
	}
}

func TestEditorConfirmsAFluxDeploy(t *testing.T) {
	e := NewEditor()
	s1, _ := e.Ingest(Raw{Source: "flux", Kind: "flux.deployed", Entity: "e1", Name: "n1", Reason: "main@sha1:abc", At: t0}, t0)
	if s1.State != StateConfirmed {
		t.Errorf("State = %q, want %q", s1.State, StateConfirmed)
	}
	s2, _ := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e2", Name: "n2", Reason: "OOMKilled", At: t0}, t0)
	if s2.State != StateReported {
		t.Errorf("State = %q, want %q", s2.State, StateReported)
	}
}

func TestEditorEvidenceCapsAtFive(t *testing.T) {
	e := NewEditor()
	var last Story
	for i := 1; i <= 7; i++ {
		msg := "msg" + string(rune('0'+i))
		s, _ := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", Message: msg, At: t0.Add(time.Duration(i) * time.Minute)}, t0.Add(time.Duration(i)*time.Minute))
		last = s
	}
	if len(last.Evidence) != 5 {
		t.Fatalf("len(Evidence) = %d, want 5", len(last.Evidence))
	}
	if last.Evidence[len(last.Evidence)-1] != "msg7" {
		t.Errorf("last evidence = %q, want msg7", last.Evidence[len(last.Evidence)-1])
	}
}

func TestHeadlines(t *testing.T) {
	e := NewEditor()
	e.Ingest(Raw{Source: "flux", Kind: "flux.failed", Entity: "ns-fences", Name: "ns-fences", Reason: "timeout", At: t0}, t0)
	e.Ingest(Raw{Source: "flux", Kind: "flux.failed", Entity: "ns-fences", Name: "ns-fences", Reason: "timeout", At: t0.Add(5 * time.Minute)}, t0.Add(5*time.Minute))
	s3, _ := e.Ingest(Raw{Source: "flux", Kind: "flux.failed", Entity: "ns-fences", Name: "ns-fences", Reason: "timeout", At: t0.Add(12 * time.Minute)}, t0.Add(12*time.Minute))
	if s3.Headline != "FAILED: ns-fences, 3rd in 12m" {
		t.Errorf("Headline = %q, want %q", s3.Headline, "FAILED: ns-fences, 3rd in 12m")
	}
	if want := "according to Flux."; !hasSuffix(s3.Anchor, want) {
		t.Errorf("Anchor = %q, want suffix %q", s3.Anchor, want)
	}

	e2 := NewEditor()
	sd, _ := e2.Ingest(Raw{Source: "flux", Kind: "flux.deployed", Entity: "e2", Name: "ns-fences", Reason: "main@sha1:abc", At: t0}, t0)
	if sd.Headline != "DEPLOYED: ns-fences reconciled main@sha1:abc" {
		t.Errorf("Headline = %q, want %q", sd.Headline, "DEPLOYED: ns-fences reconciled main@sha1:abc")
	}
	if want := "according to Flux."; !hasSuffix(sd.Anchor, want) {
		t.Errorf("Anchor = %q, want suffix %q", sd.Anchor, want)
	}

	e3 := NewEditor()
	sc, _ := e3.Ingest(Raw{Source: "cicd", Kind: "cicd.failed", Entity: "e3", Name: "build-multiarch", Reason: "main", At: t0}, t0)
	if sc.Headline != "CI RED: build-multiarch on main" {
		t.Errorf("Headline = %q, want %q", sc.Headline, "CI RED: build-multiarch on main")
	}
	if want := "according to GitHub Actions."; !hasSuffix(sc.Anchor, want) {
		t.Errorf("Anchor = %q, want suffix %q", sc.Anchor, want)
	}

	e4 := NewEditor()
	sk, _ := e4.Ingest(Raw{Source: "k8s", Kind: "k8s.crashloop", Entity: "e4", Name: "api-7f", Namespace: "mcp", At: t0}, t0)
	if sk.Headline != "CRASHLOOP: api-7f in mcp" {
		t.Errorf("Headline = %q, want %q", sk.Headline, "CRASHLOOP: api-7f in mcp")
	}
	if want := "according to Kubernetes."; !hasSuffix(sk.Anchor, want) {
		t.Errorf("Anchor = %q, want suffix %q", sk.Anchor, want)
	}
}

func hasSuffix(s, suffix string) bool {
	if len(s) < len(suffix) {
		return false
	}
	return s[len(s)-len(suffix):] == suffix
}

func TestSubjects(t *testing.T) {
	s1 := Story{Channel: "deploys", Score: 6}
	got1 := Subjects(s1)
	want1 := []string{"estate.news.story.deploys", "estate.news.story.news"}
	if !equalSlices(got1, want1) {
		t.Errorf("Subjects = %v, want %v", got1, want1)
	}

	s2 := Story{Channel: "deploys", Score: 2, Breaking: false}
	got2 := Subjects(s2)
	want2 := []string{"estate.news.story.deploys"}
	if !equalSlices(got2, want2) {
		t.Errorf("Subjects = %v, want %v", got2, want2)
	}

	s3 := Story{Channel: "news", Score: 6}
	got3 := Subjects(s3)
	want3 := []string{"estate.news.story.news"}
	if !equalSlices(got3, want3) {
		t.Errorf("Subjects = %v, want %v", got3, want3)
	}
}

func equalSlices(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func TestStoryJSON(t *testing.T) {
	e := NewEditor()
	s, _ := e.Ingest(Raw{Source: "k8s", Kind: "k8s.warning", Entity: "e1", Name: "n1", Reason: "OOMKilled", At: t0}, t0)

	b, err := json.Marshal(s)
	if err != nil {
		t.Fatalf("Marshal error: %v", err)
	}
	var m map[string]interface{}
	if err := json.Unmarshal(b, &m); err != nil {
		t.Fatalf("Unmarshal error: %v", err)
	}
	if _, ok := m["first_at"]; !ok {
		t.Error("expected first_at key")
	}
	if _, ok := m["evidence"]; !ok {
		t.Error("expected evidence key")
	}
	if _, ok := m["supersedes"]; ok {
		t.Error("expected no supersedes key for non-correction story")
	}
}
