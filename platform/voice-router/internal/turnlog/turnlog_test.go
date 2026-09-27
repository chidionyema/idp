package turnlog

import (
	"testing"
	"time"
)

func TestRingKeepsTheLastNNewestFirst(t *testing.T) {
	r := NewRing(3)
	for i := 1; i <= 5; i++ {
		r.Add(Turn{Words: i, Outcome: "ok"})
	}
	got := r.Recent(10)
	if len(got) != 3 || got[0].Words != 5 || got[2].Words != 3 {
		t.Fatalf("recent %+v", got)
	}
}

func TestSummaryMediansOnlyCompletedTurns(t *testing.T) {
	r := NewRing(10)
	for _, f := range []float64{0.9, 0.3, 0.5} {
		r.Add(Turn{Kind: "ask", Outcome: "ok", FirstAudio: f, ASRS: f})
	}
	r.Add(Turn{Kind: "ask", Outcome: "cancelled", FirstAudio: 9})
	r.Add(Turn{Kind: "say", Outcome: "ok", FirstAudio: 0.4})
	s := r.Summary()
	if s.Turns != 5 || s.Completed != 4 || s.Outcomes["cancelled"] != 1 {
		t.Fatalf("summary %+v", s)
	}
	// first audio over 0.3 0.4 0.5 0.9; asr over the asks only: 0.3 0.5 0.9.
	if s.MedianS["first_audio_s"] != 0.5 || s.MedianS["asr_s"] != 0.5 {
		t.Fatalf("medians %+v", s.MedianS)
	}
}

// A wall clock that steps backwards (NTP) must not reorder turns.
func TestClockStaysOrderedWhenTheWallClockStepsBack(t *testing.T) {
	now := time.UnixMilli(1_000_000)
	c := &Clock{now: func() time.Time { return now }}
	a := c.Stamp()
	now = now.Add(-5 * time.Second)
	b := c.Stamp()
	now = now.Add(10 * time.Second)
	d := c.Stamp()
	if !(a < b && b < d) {
		t.Fatalf("stamps out of order: %s %s %s", a, b, d)
	}
}
