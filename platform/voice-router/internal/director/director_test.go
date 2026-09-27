package director

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/chidionyema/idp/platform/voice-router/internal/brain"
)

func TestRingDropsOldest(t *testing.T) {
	r := NewRing(3)
	for i := 0; i < 5; i++ {
		r.Push(Event{SessionID: "s" + string(rune('0'+i))})
	}
	got := r.Drain()
	want := []string{"s2", "s3", "s4"}
	if len(got) != len(want) {
		t.Fatalf("len = %d, want %d", len(got), len(want))
	}
	for i, w := range want {
		if got[i].SessionID != w {
			t.Errorf("got[%d] = %s, want %s", i, got[i].SessionID, w)
		}
	}
	if r.Dropped() != 2 {
		t.Errorf("Dropped() = %d, want 2", r.Dropped())
	}
	if second := r.Drain(); len(second) != 0 {
		t.Errorf("second Drain() len = %d, want 0", len(second))
	}
}

func TestRingCapacityConstant(t *testing.T) {
	if Capacity != 1024 {
		t.Fatalf("Capacity = %d, want 1024", Capacity)
	}
	r := NewRing(Capacity)
	for i := 0; i < 1030; i++ {
		r.Push(Event{At: itoa(i)})
	}
	if r.Dropped() != 6 {
		t.Errorf("Dropped() = %d, want 6", r.Dropped())
	}
	got := r.Drain()
	if len(got) != 1024 {
		t.Fatalf("len(Drain()) = %d, want 1024", len(got))
	}
	if got[0].At != itoa(6) {
		t.Errorf("first = %s, want %s (7th pushed)", got[0].At, itoa(6))
	}
}

func itoa(i int) string {
	return time.Unix(int64(i), 0).UTC().String()
}

func TestCoalescePriority(t *testing.T) {
	events := []Event{
		{SessionID: "a", Kind: "tool"},
		{SessionID: "b", Kind: "wait"},
		{SessionID: "a", Kind: "phase"},
		{SessionID: "c", Kind: "steer"},
		{SessionID: "d", Kind: "steer"},
	}
	got := Coalesce(events)
	if got == nil || got.SessionID != "d" {
		t.Fatalf("Coalesce = %+v, want session d", got)
	}

	events2 := []Event{
		{SessionID: "a", Kind: "tool"},
		{SessionID: "a", Kind: "wait"},
		{SessionID: "b", Kind: "phase"},
	}
	got2 := Coalesce(events2)
	if got2 == nil || got2.SessionID != "b" {
		t.Fatalf("Coalesce = %+v, want session b", got2)
	}

	if Coalesce(nil) != nil {
		t.Error("Coalesce(nil) != nil")
	}

	if Coalesce([]Event{{SessionID: "x", Kind: "unknown"}}) != nil {
		t.Error("Coalesce of unknown kind should be nil")
	}
}

func TestShotTable(t *testing.T) {
	cases := []struct {
		kind string
		want Shot
	}{
		{"tool", Shot{ShotMacroDOV, 85, 0.2}},
		{"steer", Shot{ShotOrbitFocus, 50, 0.5}},
		{"phase", Shot{ShotOrbitFocus, 35, 0.4}},
		{"wait", Shot{ShotPanoramicSweep, 24, 0.3}},
		{"done", Shot{ShotPanoramicSweep, 18, 0.6}},
	}
	for _, c := range cases {
		got, ok := ShotFor(c.kind)
		if !ok {
			t.Errorf("ShotFor(%q) ok = false, want true", c.kind)
		}
		if got != c.want {
			t.Errorf("ShotFor(%q) = %+v, want %+v", c.kind, got, c.want)
		}
	}
	if _, ok := ShotFor("x"); ok {
		t.Error("ShotFor(\"x\") ok = true, want false")
	}
}

func TestNewCueJSON(t *testing.T) {
	ev := Event{SessionID: "s-1"}
	s := Shot{ShotOrbitFocus, 50, 0.5}
	now := time.Date(2026, 9, 27, 12, 0, 0, 0, time.UTC)
	cue := NewCue(ev, s, "hello", now)

	b, err := json.Marshal(cue)
	if err != nil {
		t.Fatalf("Marshal: %v", err)
	}
	var m map[string]any
	if err := json.Unmarshal(b, &m); err != nil {
		t.Fatalf("Unmarshal: %v", err)
	}
	for _, key := range []string{"target_id", "shot_type", "monologue", "focal_length", "dolly_speed", "timestamp"} {
		if _, ok := m[key]; !ok {
			t.Errorf("missing key %q in %s", key, b)
		}
	}
	if _, err := time.Parse(time.RFC3339, m["timestamp"].(string)); err != nil {
		t.Errorf("timestamp not RFC3339: %v", err)
	}
}

type fakeBrain struct {
	text  string
	err   error
	block bool
	calls int
}

func (f *fakeBrain) Stream(ctx context.Context, msgs []brain.Message, onDelta func(string)) error {
	f.calls++
	if f.block {
		<-ctx.Done()
		return ctx.Err()
	}
	if f.err != nil {
		return f.err
	}
	onDelta(f.text)
	return nil
}

func TestNarratorUsesLLM(t *testing.T) {
	fb := &fakeBrain{text: "Agent digs into auth."}
	n := &Narrator{Brain: fb, Limiter: NewLimiter()}
	ev := Event{SessionID: "abc-12345678", Runtime: "claude-code", Kind: "tool", Phase: "executing"}
	got, used := n.Line(context.Background(), ev)
	if !used {
		t.Fatal("used = false, want true")
	}
	if got != "Agent digs into auth." {
		t.Errorf("got = %q", got)
	}
}

func TestNarratorFallsBackOnError(t *testing.T) {
	fb := &fakeBrain{err: errBoom}
	n := &Narrator{Brain: fb, Limiter: NewLimiter()}
	ev := Event{SessionID: "abc-12345678", Runtime: "claude-code", Kind: "tool", Phase: "executing"}
	got, used := n.Line(context.Background(), ev)
	if used {
		t.Fatal("used = true, want false")
	}
	want := "claude-code agent 12345678 is tooling."
	if got != want {
		t.Errorf("got = %q, want %q", got, want)
	}
	if Template(ev) != want {
		t.Errorf("Template = %q, want %q", Template(ev), want)
	}
}

var errBoom = &boomErr{}

type boomErr struct{}

func (*boomErr) Error() string { return "boom" }

func TestNarratorFallsBackOnTimeout(t *testing.T) {
	fb := &fakeBrain{block: true}
	n := &Narrator{Brain: fb, Limiter: NewLimiter(), Timeout: 30 * time.Millisecond}
	ev := Event{SessionID: "abc-12345678", Runtime: "claude-code", Kind: "tool", Phase: "executing"}
	start := time.Now()
	_, used := n.Line(context.Background(), ev)
	elapsed := time.Since(start)
	if used {
		t.Error("used = true, want false")
	}
	if elapsed >= 500*time.Millisecond {
		t.Errorf("elapsed = %v, want < 500ms", elapsed)
	}
}

func TestNarratorOnlyOnStateChange(t *testing.T) {
	fb := &fakeBrain{text: "Agent digs into auth."}
	n := &Narrator{Brain: fb, Limiter: NewLimiter()}
	ev := Event{SessionID: "abc-12345678", Runtime: "claude-code", Kind: "tool", Phase: "executing"}
	n.Line(context.Background(), ev)
	n.Line(context.Background(), ev)
	if fb.calls != 1 {
		t.Errorf("calls = %d, want 1", fb.calls)
	}
}

func TestLimiterWithFakeClock(t *testing.T) {
	now := time.Unix(1000, 0)
	fb := &fakeBrain{text: "Agent digs into auth."}
	n := &Narrator{Brain: fb, Limiter: NewLimiter(), Now: func() time.Time { return now }}
	ev := Event{SessionID: "abc-12345678", Runtime: "claude-code", Kind: "tool", Phase: "executing"}

	_, used := n.Line(context.Background(), ev)
	if !used {
		t.Fatal("first call: used = false, want true")
	}

	now = now.Add(1 * time.Second)
	ev.Kind = "phase"
	_, used = n.Line(context.Background(), ev)
	if used {
		t.Error("t+1s: used = true, want false (per-session limit)")
	}

	now = now.Add(10 * time.Second)
	ev.Kind = "tool"
	_, used = n.Line(context.Background(), ev)
	if !used {
		t.Error("t+11s: used = false, want true")
	}

	l := NewLimiter()
	base := time.Unix(2000, 0)
	for i := 0; i < 6; i++ {
		session := "sess" + string(rune('0'+i))
		if !l.Allow(session, base) {
			t.Errorf("session %d at t: Allow = false, want true", i)
		}
	}
	if l.Allow("sess6", base) {
		t.Error("7th session at t: Allow = true, want false")
	}
	later := base.Add(61 * time.Second)
	if !l.Allow("sess6", later) {
		t.Error("7th session at t+61s: Allow = false, want true")
	}
}
