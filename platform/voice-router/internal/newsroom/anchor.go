package newsroom

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/chidionyema/idp/platform/voice-router/internal/brain"
)

// The anchor desk (crew#974 P3): a BREAKING story's anchor sentence is rewritten by the
// router's cheap lane so the founder hears a newsreader, not a template. Everything else
// keeps its deterministic template. Spend is bounded twice: here (breaking only, one rewrite
// per story id, AnchorPerMinute overall) and at the router, which caps the key's daily
// budget (bin/idp-router-key, estate-defaults llm.virtual_key_daily_usd).
const (
	AnchorPerMinute = 6
	AnchorTimeout   = 4 * time.Second
	AnchorMaxRunes  = 240
	anchorMemory    = 256
)

// Streamer streams a chat completion. *brain.Client satisfies it.
type Streamer interface {
	Stream(ctx context.Context, msgs []brain.Message, onDelta func(string)) error
}

type Anchor struct {
	Brain   Streamer
	Timeout time.Duration

	window  []time.Time
	written map[string]string
	order   []string
}

const anchorSystem = "You are the anchor of a live TV news channel about a software estate, " +
	"reading one breaking bulletin aloud. Write ONE spoken sentence under 25 words: say what is " +
	"happening and what it means, plainly, the way a newsreader would. Use only the facts given: " +
	"never add a number, name, cause or fix that is not in them. Never read out field names, " +
	"severity words or log text verbatim. End with the attribution (\"according to ...\"). " +
	"No markdown, no quotes, no symbols."

// Voice returns s with its anchor rewritten by the LLM when s is breaking, and whether the
// LLM wrote it. A story id is rewritten once; its later updates reuse that sentence. Any
// failure, timeout, cap or empty reply keeps the template.
func (a *Anchor) Voice(ctx context.Context, s Story, now time.Time) (Story, bool) {
	if !s.Breaking || a == nil || a.Brain == nil {
		return s, false
	}
	if line, ok := a.written[s.ID]; ok {
		s.Anchor = line
		return s, true
	}
	if !a.allow(now) {
		return s, false
	}
	timeout := a.Timeout
	if timeout == 0 {
		timeout = AnchorTimeout
	}
	cctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	msgs := []brain.Message{
		{Role: "system", Content: anchorSystem},
		{Role: "user", Content: fmt.Sprintf("Headline: %s\nWire copy: %s\nSeen %d times. Raw signal: %s",
			s.Headline, s.Anchor, s.Count, strings.Join(s.Evidence, " | "))},
	}
	var sb strings.Builder
	err := a.Brain.Stream(cctx, msgs, func(d string) { sb.WriteString(d) })
	if err != nil || cctx.Err() != nil {
		return s, false
	}
	line := strings.TrimSpace(sb.String())
	if i := strings.IndexByte(line, '\n'); i >= 0 {
		line = strings.TrimSpace(line[:i])
	}
	line = strings.Trim(line, "\"'` ")
	if line == "" {
		return s, false
	}
	if r := []rune(line); len(r) > AnchorMaxRunes {
		line = string(r[:AnchorMaxRunes])
	}
	a.remember(s.ID, line)
	s.Anchor = line
	return s, true
}

func (a *Anchor) allow(now time.Time) bool {
	kept := a.window[:0]
	for _, t := range a.window {
		if now.Sub(t) < time.Minute {
			kept = append(kept, t)
		}
	}
	a.window = kept
	if len(a.window) >= AnchorPerMinute {
		return false
	}
	a.window = append(a.window, now)
	return true
}

func (a *Anchor) remember(id, line string) {
	if a.written == nil {
		a.written = make(map[string]string)
	}
	a.written[id] = line
	a.order = append(a.order, id)
	if len(a.order) > anchorMemory {
		delete(a.written, a.order[0])
		a.order = a.order[1:]
	}
}
