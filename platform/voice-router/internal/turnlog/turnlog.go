// Package turnlog records every voice turn, timed, in one row.
//
// The fields and their names are sovereign/voice/turnlog.py's voice_turns
// columns, so a turn from this service and a turn from the Python engine are
// the same record and the bench reads the same numbers production does. Each
// turn is logged as one structured line (the evidence a production claim needs)
// and kept in a bounded ring, whose medians GET /voice/turns serves.
package turnlog

import (
	"fmt"
	"slices"
	"sync"
	"time"
)

// Turn is one voice turn. Durations are seconds, as in voice_turns.
type Turn struct {
	SessionID string    `json:"session_id"`
	HLC       string    `json:"hlc"`      // orders turns across surfaces without trusting their clocks
	HeardAt   time.Time `json:"heard_at"` // when the utterance ended (or the say arrived)
	Kind      string    `json:"kind"`     // ask | say
	// ASRS is the endpointer's wait: from the last change in the words to the
	// end of the utterance. Streaming ASR has already transcribed by then, so
	// this is the whole of "time to transcribe" the listener sits through.
	ASRS       float64 `json:"asr_s"`
	LLMFirstS  float64 `json:"llm_first_s"`   // to the first phrase ready to speak
	LLMTotalS  float64 `json:"llm_total_s"`   // to the last phrase
	TTSS       float64 `json:"tts_s"`         // synthesis summed across phrases
	FirstAudio float64 `json:"first_audio_s"` // to the first sound: the number a person feels
	Words      int     `json:"words"`
	Clauses    int     `json:"clauses"`
	Engine     string  `json:"engine"`
	Voice      string  `json:"voice"`
	Outcome    string  `json:"outcome"` // ok | empty | error | cancelled
	Detail     string  `json:"detail,omitempty"`
}

// Ring keeps the last n turns.
type Ring struct {
	mu    sync.Mutex
	n     int
	turns []Turn
}

func NewRing(n int) *Ring { return &Ring{n: n} }

func (r *Ring) Add(t Turn) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.turns = append(r.turns, t)
	if len(r.turns) > r.n {
		r.turns = r.turns[len(r.turns)-r.n:]
	}
}

// Recent returns up to limit turns, newest first.
func (r *Ring) Recent(limit int) []Turn {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]Turn, 0, min(limit, len(r.turns)))
	for i := len(r.turns) - 1; i >= 0 && len(out) < limit; i-- {
		out = append(out, r.turns[i])
	}
	return out
}

// Summary is turnlog.summary's shape: counts by outcome and the median of each
// timing over the turns that completed. Cancelled turns are counted but not
// timed: a barge-in cut them short, so their timings measure the person.
type Summary struct {
	Turns     int                `json:"turns"`
	Outcomes  map[string]int     `json:"outcomes"`
	MedianS   map[string]float64 `json:"median_s"`
	Completed int                `json:"completed"`
}

func (r *Ring) Summary() Summary {
	r.mu.Lock()
	defer r.mu.Unlock()
	s := Summary{Turns: len(r.turns), Outcomes: map[string]int{}, MedianS: map[string]float64{}}
	cols := map[string][]float64{}
	for _, t := range r.turns {
		s.Outcomes[t.Outcome]++
		if t.Outcome != "ok" {
			continue
		}
		s.Completed++
		if t.Kind == "ask" {
			cols["asr_s"] = append(cols["asr_s"], t.ASRS)
		}
		cols["llm_first_s"] = append(cols["llm_first_s"], t.LLMFirstS)
		cols["llm_total_s"] = append(cols["llm_total_s"], t.LLMTotalS)
		cols["tts_s"] = append(cols["tts_s"], t.TTSS)
		cols["first_audio_s"] = append(cols["first_audio_s"], t.FirstAudio)
	}
	for k, v := range cols {
		slices.Sort(v)
		s.MedianS[k] = v[len(v)/2]
	}
	return s
}

// Clock is a hybrid logical clock: wall milliseconds, plus a counter that
// breaks ties and carries order through a clock that steps backwards.
type Clock struct {
	mu      sync.Mutex
	wall    int64
	logical int64
	now     func() time.Time
}

func NewClock() *Clock { return &Clock{now: time.Now} }

// Tick returns the next stamp. Stamps from one clock strictly increase.
func (c *Clock) Tick() (wall, logical int64) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if pt := c.now().UnixMilli(); pt > c.wall {
		c.wall, c.logical = pt, 0
	} else {
		c.logical++
	}
	return c.wall, c.logical
}

// Stamp is Tick as a string that sorts in the same order: "<wall ms>.<counter>".
func (c *Clock) Stamp() string {
	w, l := c.Tick()
	return fmt.Sprintf("%013d.%06d", w, l)
}
