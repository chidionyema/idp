// Package director turns estate.agent events into camera cues for the /fleet live movie. Pure: no NATS import.
package director

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/chidionyema/idp/platform/voice-router/internal/brain"
)

// Event is one row of an agent's live mind (estate.agent.event).
type Event struct {
	SessionID string `json:"session_id"`
	Runtime   string `json:"runtime"`
	Kind      string `json:"kind"`
	Phase     string `json:"phase"`
	At        string `json:"at"`
	Needs     string `json:"needs,omitempty"`
	Tool      *Tool  `json:"tool,omitempty"`
}

// Tool names what a tool event acted on.
type Tool struct {
	Name   string `json:"name"`
	Target string `json:"target"`
}

// Capacity is the fixed ring buffer size.
const Capacity = 1024

// Ring is a fixed-capacity ring buffer of events that overwrites the oldest
// entry once full.
type Ring struct {
	mu      sync.Mutex
	buf     []Event
	head    int
	n       int
	dropped uint64
}

// NewRing creates a Ring with the given capacity (minimum 1).
func NewRing(capacity int) *Ring {
	if capacity < 1 {
		capacity = 1
	}
	return &Ring{buf: make([]Event, capacity)}
}

// Push adds e to the ring, overwriting the oldest entry when full.
func (r *Ring) Push(e Event) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.n == len(r.buf) {
		r.buf[r.head] = e
		r.head = (r.head + 1) % len(r.buf)
		r.dropped++
		return
	}
	r.buf[(r.head+r.n)%len(r.buf)] = e
	r.n++
}

// Drain returns all buffered events oldest-first and empties the ring.
func (r *Ring) Drain() []Event {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.n == 0 {
		return nil
	}
	out := make([]Event, r.n)
	for i := 0; i < r.n; i++ {
		out[i] = r.buf[(r.head+i)%len(r.buf)]
	}
	r.head = 0
	r.n = 0
	return out
}

// Dropped returns the cumulative count of overwritten events.
func (r *Ring) Dropped() uint64 {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.dropped
}

// Shot kinds.
const (
	ShotOrbitFocus     = "ORBIT_FOCUS"
	ShotPanoramicSweep = "PANORAMIC_SWEEP"
	ShotMacroDOV       = "MACRO_DOV"
)

// Shot describes a camera move.
type Shot struct {
	Type        string
	FocalLength float64
	DollySpeed  float64
}

// ShotFor returns the fixed camera shot for an event kind.
func ShotFor(kind string) (Shot, bool) {
	switch kind {
	case "tool":
		return Shot{ShotMacroDOV, 85, 0.2}, true
	case "steer":
		return Shot{ShotOrbitFocus, 50, 0.5}, true
	case "phase":
		return Shot{ShotOrbitFocus, 35, 0.4}, true
	case "wait":
		return Shot{ShotPanoramicSweep, 24, 0.3}, true
	case "done":
		return Shot{ShotPanoramicSweep, 18, 0.6}, true
	default:
		return Shot{}, false
	}
}

func priority(kind string) int {
	switch kind {
	case "steer":
		return 5
	case "tool":
		return 4
	case "phase":
		return 3
	case "done":
		return 2
	case "wait":
		return 1
	default:
		return 0
	}
}

// Coalesce keeps the last event per session and returns the highest-priority
// survivor, ties broken by the most recent original index.
func Coalesce(events []Event) *Event {
	type latest struct {
		ev  Event
		idx int
	}
	bySession := make(map[string]latest)
	for i, e := range events {
		if e.SessionID == "" || priority(e.Kind) == 0 {
			continue
		}
		bySession[e.SessionID] = latest{ev: e, idx: i}
	}
	var best *latest
	for k := range bySession {
		l := bySession[k]
		if best == nil {
			b := l
			best = &b
			continue
		}
		pl, pb := priority(l.ev.Kind), priority(best.ev.Kind)
		if pl > pb || (pl == pb && l.idx > best.idx) {
			b := l
			best = &b
		}
	}
	if best == nil {
		return nil
	}
	out := best.ev
	return &out
}

// Cue is a camera + narration instruction for the live movie.
type Cue struct {
	TargetID    string  `json:"target_id"`
	ShotType    string  `json:"shot_type"`
	Monologue   string  `json:"monologue"`
	FocalLength float64 `json:"focal_length"`
	DollySpeed  float64 `json:"dolly_speed"`
	Timestamp   string  `json:"timestamp"`
}

// NewCue builds a Cue from an event, its shot, and a narration line.
func NewCue(ev Event, s Shot, line string, now time.Time) Cue {
	return Cue{
		TargetID:    ev.SessionID,
		ShotType:    s.Type,
		Monologue:   line,
		FocalLength: s.FocalLength,
		DollySpeed:  s.DollySpeed,
		Timestamp:   now.UTC().Format(time.RFC3339),
	}
}

// Limiter rate-limits narration per session and across all sessions.
// Not safe for concurrent use; used from the tick goroutine only.
type Limiter struct {
	PerSession time.Duration
	PerMinute  int
	last       map[string]time.Time
	window     []time.Time
}

// NewLimiter returns a Limiter with the default estate cadence: 10s per
// session, 6 lines per minute overall.
func NewLimiter() *Limiter {
	return &Limiter{
		PerSession: 10 * time.Second,
		PerMinute:  6,
		last:       make(map[string]time.Time),
	}
}

// Allow reports whether a narration line for session may fire now, and
// records it if so.
func (l *Limiter) Allow(session string, now time.Time) bool {
	pruned := l.window[:0]
	for _, t := range l.window {
		if now.Sub(t) < time.Minute {
			pruned = append(pruned, t)
		}
	}
	l.window = pruned

	for s, t := range l.last {
		if now.Sub(t) >= l.PerSession {
			delete(l.last, s)
		}
	}

	if _, ok := l.last[session]; ok {
		return false
	}
	if len(l.window) >= l.PerMinute {
		return false
	}
	l.last[session] = now
	l.window = append(l.window, now)
	return true
}

// Streamer streams a chat completion. *brain.Client satisfies it.
type Streamer interface {
	Stream(ctx context.Context, msgs []brain.Message, onDelta func(string)) error
}

// DefaultTimeout bounds how long the narrator waits for the LLM.
const DefaultTimeout = 800 * time.Millisecond

// Narrator turns events into spoken narration lines, falling back to a
// template when the LLM is unavailable, rate-limited, or too slow.
type Narrator struct {
	Brain   Streamer
	Limiter *Limiter
	Now     func() time.Time
	Timeout time.Duration
	seen    map[string]string
}

// ShortID returns the last 8 characters of id (or the whole id if shorter).
func ShortID(id string) string {
	if len(id) <= 8 {
		return id
	}
	return id[len(id)-8:]
}

// Template is the deterministic fallback narration line.
func Template(ev Event) string {
	return fmt.Sprintf("%s agent %s is %sing.", ev.Runtime, ShortID(ev.SessionID), ev.Kind)
}

// Line returns a narration line for ev, and whether it came from the LLM.
func (n *Narrator) Line(ctx context.Context, ev Event) (string, bool) {
	if n.seen == nil {
		n.seen = make(map[string]string)
	}
	state := ev.Kind + "/" + ev.Phase
	changed := n.seen[ev.SessionID] != state
	n.seen[ev.SessionID] = state

	now := time.Now
	if n.Now != nil {
		now = n.Now
	}

	if !changed || n.Brain == nil || n.Limiter == nil || !n.Limiter.Allow(ev.SessionID, now()) {
		return Template(ev), false
	}

	timeout := n.Timeout
	if timeout == 0 {
		timeout = DefaultTimeout
	}
	cctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	toolText := ""
	if ev.Tool != nil {
		toolText = ev.Tool.Name + " " + ev.Tool.Target
	}
	msgs := []brain.Message{
		{Role: "system", Content: "You narrate a live film of AI agents at work. Reply with one short spoken sentence under 15 words. No markdown, no symbols."},
		{Role: "user", Content: fmt.Sprintf("runtime=%s session=%s kind=%s phase=%s tool=%s needs=%s", ev.Runtime, ShortID(ev.SessionID), ev.Kind, ev.Phase, toolText, ev.Needs)},
	}

	var sb strings.Builder
	err := n.Brain.Stream(cctx, msgs, func(delta string) {
		sb.WriteString(delta)
	})
	if err != nil || cctx.Err() != nil {
		return Template(ev), false
	}

	text := strings.TrimSpace(sb.String())
	if idx := strings.IndexByte(text, '\n'); idx >= 0 {
		text = text[:idx]
	}
	if text == "" {
		return Template(ev), false
	}
	runes := []rune(text)
	if len(runes) > 200 {
		text = string(runes[:200])
	}
	return text, true
}
