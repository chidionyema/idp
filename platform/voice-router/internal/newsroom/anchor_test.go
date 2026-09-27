package newsroom

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/chidionyema/idp/platform/voice-router/internal/brain"
)

type fakeBrain struct {
	reply string
	err   error
	delay time.Duration
	calls int
	last  []brain.Message
}

func (f *fakeBrain) Stream(ctx context.Context, msgs []brain.Message, onDelta func(string)) error {
	f.calls++
	f.last = msgs
	if f.delay > 0 {
		select {
		case <-time.After(f.delay):
		case <-ctx.Done():
			return ctx.Err()
		}
	}
	if f.err != nil {
		return f.err
	}
	for _, w := range strings.SplitAfter(f.reply, " ") {
		onDelta(w)
	}
	return nil
}

func breakingStory(id string) Story {
	return Story{ID: id, Breaking: true, Severity: "danger", Count: 3,
		Headline: "CRASHLOOP: spiffe-proof in identity",
		Anchor:   "spiffe-proof keeps restarting, so what it serves is down or degraded, according to Kubernetes.",
		Evidence: []string{"BackOff: Back-off restarting failed container"}}
}

func TestAnchorRewritesABreakingStory(t *testing.T) {
	b := &fakeBrain{reply: "\"Breaking: spiffe-proof is crash-looping in identity, according to Kubernetes.\"\nextra"}
	a := &Anchor{Brain: b}
	s, llm := a.Voice(context.Background(), breakingStory("x1"), t0)
	if !llm || s.Anchor != "Breaking: spiffe-proof is crash-looping in identity, according to Kubernetes." {
		t.Fatalf("got %v %q", llm, s.Anchor)
	}
	if !strings.Contains(b.last[1].Content, "CRASHLOOP: spiffe-proof in identity") ||
		!strings.Contains(b.last[1].Content, "BackOff") {
		t.Fatalf("facts not sent: %q", b.last[1].Content)
	}
}

func TestAnchorNeverSpendsOnAnOrdinaryStory(t *testing.T) {
	b := &fakeBrain{reply: "no"}
	a := &Anchor{Brain: b}
	s := breakingStory("x1")
	s.Breaking = false
	got, llm := a.Voice(context.Background(), s, t0)
	if llm || b.calls != 0 || got.Anchor != s.Anchor {
		t.Fatalf("ordinary story reached the LLM: calls=%d", b.calls)
	}
}

func TestAnchorRewritesAStoryIDOnce(t *testing.T) {
	b := &fakeBrain{reply: "Spiffe-proof is down, according to Kubernetes."}
	a := &Anchor{Brain: b}
	a.Voice(context.Background(), breakingStory("x1"), t0)
	s, llm := a.Voice(context.Background(), breakingStory("x1"), t0.Add(5*time.Minute))
	if b.calls != 1 || !llm || s.Anchor != "Spiffe-proof is down, according to Kubernetes." {
		t.Fatalf("calls=%d llm=%v anchor=%q", b.calls, llm, s.Anchor)
	}
}

func TestAnchorCapsCallsPerMinute(t *testing.T) {
	b := &fakeBrain{reply: "ok, according to Kubernetes."}
	a := &Anchor{Brain: b}
	for i := 0; i < AnchorPerMinute+3; i++ {
		a.Voice(context.Background(), breakingStory(string(rune('a'+i))), t0.Add(time.Duration(i)*time.Second))
	}
	if b.calls != AnchorPerMinute {
		t.Fatalf("calls=%d want %d", b.calls, AnchorPerMinute)
	}
	a.Voice(context.Background(), breakingStory("later"), t0.Add(2*time.Minute))
	if b.calls != AnchorPerMinute+1 {
		t.Fatalf("window never reopened: calls=%d", b.calls)
	}
}

func TestAnchorFallsBackToTheTemplate(t *testing.T) {
	want := breakingStory("x1").Anchor
	for name, b := range map[string]*fakeBrain{
		"error":   {err: errors.New("401")},
		"empty":   {reply: "   "},
		"timeout": {reply: "late", delay: 50 * time.Millisecond},
	} {
		a := &Anchor{Brain: b, Timeout: 10 * time.Millisecond}
		s, llm := a.Voice(context.Background(), breakingStory("x1"), t0)
		if llm || s.Anchor != want {
			t.Errorf("%s: llm=%v anchor=%q", name, llm, s.Anchor)
		}
	}
	var none *Anchor
	if _, llm := none.Voice(context.Background(), breakingStory("x1"), t0); llm {
		t.Error("nil anchor spoke")
	}
}

func TestAnchorBoundsTheSentence(t *testing.T) {
	a := &Anchor{Brain: &fakeBrain{reply: strings.Repeat("word ", 200)}}
	s, _ := a.Voice(context.Background(), breakingStory("x1"), t0)
	if n := len([]rune(s.Anchor)); n > AnchorMaxRunes {
		t.Fatalf("anchor %d runes", n)
	}
}
