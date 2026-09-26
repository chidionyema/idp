// Package session runs one voice conversation: audio in, words out, speech
// back, with barge-in. It knows nothing about sherpa, websockets or vendors;
// those arrive as the small interfaces below, which is what makes it testable.
package session

import (
	"context"
	"encoding/binary"
	"log/slog"
	"math"
	"strings"
	"sync"
	"time"
	"unicode"

	"github.com/chidionyema/idp/platform/voice-router/internal/brain"
	"github.com/chidionyema/idp/platform/voice-router/internal/chunk"
)

// ASR is one streaming recognizer stream (16 kHz mono float32 in).
type ASR interface {
	Accept(samples []float32)
	Partial() string
	Endpoint() bool
	Reset()
}

// TTS synthesises a phrase, calling emit with audio as it is produced. emit
// returning false, or ctx ending, stops synthesis.
type TTS interface {
	Synth(ctx context.Context, text string, emit func(samples []float32) bool) error
	SampleRate() int
}

// Brain streams a reply.
type Brain interface {
	Stream(ctx context.Context, msgs []brain.Message, onDelta func(string)) error
}

// Out is the client connection. JSON sends a control event; Binary sends an
// audio frame: 4-byte little-endian turn id, then int16 little-endian PCM.
type Out interface {
	JSON(v any) error
	Binary(b []byte) error
}

// Event is every control message the server sends.
type Event struct {
	Type string `json:"type"`
	Turn uint32 `json:"turn,omitempty"`
	Text string `json:"text,omitempty"`
	Rate int    `json:"rate,omitempty"`
}

const maxHistory = 12

// continueWindow: speech that interrupts a turn this soon after its question
// was heard, before the agent has made a sound, is the same thought after a
// pause, not a new question. The two halves are joined so the brain sees the
// whole sentence. Once the listener has heard the agent, they are replying.
const continueWindow = 3 * time.Second

// fillers are what a recognizer makes of a cough or a breath. They never
// interrupt the agent; only real words do.
var fillers = map[string]bool{"uh": true, "um": true, "hmm": true, "mm": true, "ah": true, "oh": true, "er": true, "huh": true, "mhm": true}

// Session is one connected client.
type Session struct {
	asr   ASR
	tts   TTS
	brain Brain
	out   Out
	log   *slog.Logger
	root  context.Context

	mu      sync.Mutex
	system  string
	history []brain.Message
	turn    uint32
	cancel  context.CancelFunc // non-nil while a turn is live
	done    chan struct{}      // closed when the latest turn has fully finished
	partial string
	spoke   time.Time // last time the partial transcript changed
	barged  bool      // this utterance has already interrupted the agent
	cont    bool      // this utterance continues the last question
	heardAt time.Time // when the last question was heard
	audible bool      // the latest turn has sent audio
}

// New creates a session. ctx ends every turn when the connection closes.
func New(ctx context.Context, asr ASR, tts TTS, b Brain, out Out, system string, log *slog.Logger) *Session {
	return &Session{asr: asr, tts: tts, brain: b, out: out, system: system, log: log, root: ctx}
}

// Hello tells the client the audio formats.
func (s *Session) Hello() error {
	return s.out.JSON(Event{Type: "hello", Rate: s.tts.SampleRate()})
}

// SetSystem replaces the system prompt (the client can send live fleet context).
func (s *Session) SetSystem(p string) {
	s.mu.Lock()
	s.system = p
	s.mu.Unlock()
}

// OnAudio takes int16 little-endian PCM at 16 kHz.
func (s *Session) OnAudio(pcm []byte) {
	samples := make([]float32, len(pcm)/2)
	for i := range samples {
		samples[i] = float32(int16(binary.LittleEndian.Uint16(pcm[2*i:]))) / 32768
	}
	s.asr.Accept(samples)
	p := strings.TrimSpace(s.asr.Partial())

	s.mu.Lock()
	changed := p != s.partial
	if changed {
		s.partial = p
		s.spoke = time.Now()
	}
	interrupt := changed && !s.barged && hasWords(p)
	if interrupt {
		s.barged = true
		s.cont = s.turn > 0 && !s.audible && time.Since(s.heardAt) < continueWindow
	}
	s.mu.Unlock()

	if changed && p != "" {
		_ = s.out.JSON(Event{Type: "partial", Text: p})
	}
	// Real words stop the agent even after its turn has finished generating:
	// the client may still be playing buffered audio for it.
	if interrupt {
		s.Barge()
	}
	if s.asr.Endpoint() {
		s.asr.Reset()
		s.mu.Lock()
		text, spoke, cont := s.partial, s.spoke, s.cont
		s.partial, s.barged, s.cont = "", false, false
		s.mu.Unlock()
		if hasWords(text) {
			s.log.Info("voice.heard", "endpoint_wait_ms", time.Since(spoke).Milliseconds(), "chars", len(text), "continues", cont)
			s.ask(text, cont)
		}
	}
}

// Barge stops the latest turn and tells the client to stop playing it.
func (s *Session) Barge() { s.stop(true) }

// stop cancels the live turn. The client is told when a turn was cancelled,
// or always when announce is set, so buffered playback stops too.
func (s *Session) stop(announce bool) {
	s.mu.Lock()
	cancel, id := s.cancel, s.turn
	s.cancel = nil
	s.mu.Unlock()
	if cancel != nil {
		cancel()
	}
	if id > 0 && (cancel != nil || announce) {
		_ = s.out.JSON(Event{Type: "barge", Turn: id})
		s.log.Info("voice.barge", "turn", id, "was_generating", cancel != nil)
	}
}

// Ask starts a new turn for text, ending any turn still speaking.
func (s *Session) Ask(text string) { s.ask(text, false) }

// Say speaks text as it is, with no brain, ending any turn still speaking.
// It is how the client reads out words that came from elsewhere -- an agent's
// reply on /fleet -- in the same voice, with the same barge-in. What was said
// joins the history, so a follow-up question has it in context.
func (s *Session) Say(text string) {
	id, ctx, done := s.begin()
	s.heardAt = time.Time{} // nothing was asked: speech before its audio is a new question
	s.mu.Unlock()
	go s.run(ctx, id, func(_ context.Context, on func(string)) error { on(text); return nil }, done)
}

// begin ends the live turn and starts the next one. It returns holding s.mu.
func (s *Session) begin() (uint32, context.Context, chan struct{}) {
	s.stop(false)
	// Let the previous turn record what it already said, so the brain sees
	// the interrupted reply. Bounded: a stuck synthesiser never blocks a turn.
	s.mu.Lock()
	prev := s.done
	s.mu.Unlock()
	if prev != nil {
		select {
		case <-prev:
		case <-time.After(3 * time.Second):
		}
	}
	s.mu.Lock()
	s.turn++
	ctx, cancel := context.WithCancel(s.root)
	s.cancel = cancel
	s.done = make(chan struct{})
	s.audible = false
	return s.turn, ctx, s.done
}

func (s *Session) ask(text string, cont bool) {
	id, ctx, done := s.begin()
	if cont {
		// Replace the cut-off question (and any partial answer) with the whole one.
		for i := len(s.history) - 1; i >= 0; i-- {
			if s.history[i].Role == "user" {
				text = s.history[i].Content + " " + text
				s.history = s.history[:i]
				break
			}
		}
	}
	s.heardAt = time.Now()
	s.history = append(s.history, brain.Message{Role: "user", Content: text})
	if len(s.history) > maxHistory {
		s.history = s.history[len(s.history)-maxHistory:]
	}
	msgs := make([]brain.Message, 0, len(s.history)+1)
	if s.system != "" {
		msgs = append(msgs, brain.Message{Role: "system", Content: s.system})
	}
	msgs = append(msgs, s.history...)
	s.mu.Unlock()

	_ = s.out.JSON(Event{Type: "final", Turn: id, Text: text})
	go s.run(ctx, id, func(ctx context.Context, on func(string)) error { return s.brain.Stream(ctx, msgs, on) }, done)
}

// run speaks one turn: stream yields the words, which are chunked into
// phrases and synthesised as they arrive.
func (s *Session) run(ctx context.Context, id uint32, stream func(context.Context, func(string)) error, done chan struct{}) {
	defer close(done)
	t0 := time.Now()
	var firstPhrase, firstAudio time.Duration
	phrases := make(chan string, 32)
	errc := make(chan error, 1)

	go func() {
		defer close(phrases)
		c := chunk.Chunker{First: true}
		send := func(p string) {
			select {
			case phrases <- p:
			case <-ctx.Done():
			}
		}
		err := stream(ctx, func(d string) {
			for _, p := range c.Push(d) {
				send(p)
			}
		})
		if rest := c.Flush(); rest != "" && ctx.Err() == nil {
			send(rest)
		}
		errc <- err
	}()

	var said []string
	for p := range phrases {
		if ctx.Err() != nil {
			break
		}
		if firstPhrase == 0 {
			firstPhrase = time.Since(t0)
		}
		if s.send(ctx, Event{Type: "phrase", Turn: id, Text: p}) != nil {
			break
		}
		err := s.tts.Synth(ctx, p, func(samples []float32) bool {
			if ctx.Err() != nil {
				return false
			}
			if firstAudio == 0 {
				firstAudio = time.Since(t0)
				s.mu.Lock()
				if s.turn == id {
					s.audible = true
				}
				s.mu.Unlock()
			}
			return s.out.Binary(Frame(id, samples)) == nil
		})
		if err != nil && ctx.Err() == nil {
			s.log.Error("voice.tts", "turn", id, "err", err)
		}
		said = append(said, p)
	}
	for range phrases { // let the brain goroutine finish if we stopped early
	}
	err := <-errc

	cancelled := ctx.Err() != nil
	s.mu.Lock()
	if len(said) > 0 {
		m := brain.Message{Role: "assistant", Content: strings.Join(said, " ")}
		if s.turn == id || len(s.history) == 0 {
			s.history = append(s.history, m)
		} else { // interrupted: what was said belongs before the question that cut it off
			n := len(s.history) - 1
			s.history = append(s.history[:n], m, s.history[n])
		}
	}
	if s.turn == id && s.cancel != nil {
		s.cancel()
		s.cancel = nil
	}
	s.mu.Unlock()

	switch {
	case cancelled:
	case err == nil && len(said) == 0:
		s.log.Error("voice.brain", "turn", id, "err", "empty reply")
		_ = s.out.JSON(Event{Type: "error", Turn: id, Text: "the brain gave an empty reply"})
	case err != nil:
		s.log.Error("voice.brain", "turn", id, "err", err)
		_ = s.out.JSON(Event{Type: "error", Turn: id, Text: "the brain did not answer"})
	default:
		_ = s.out.JSON(Event{Type: "done", Turn: id})
	}
	s.log.Info("voice.turn", "turn", id, "first_phrase_ms", firstPhrase.Milliseconds(),
		"first_audio_ms", firstAudio.Milliseconds(), "total_ms", time.Since(t0).Milliseconds(),
		"phrases", len(said), "cancelled", cancelled)
}

// send drops events for a turn that has already been cancelled.
func (s *Session) send(ctx context.Context, e Event) error {
	if ctx.Err() != nil {
		return ctx.Err()
	}
	return s.out.JSON(e)
}

// Frame encodes one audio frame into a fresh buffer: turn id then int16 PCM.
// Fresh every call, because the synthesiser may reuse its sample slice.
func Frame(turn uint32, samples []float32) []byte {
	b := make([]byte, 4+2*len(samples))
	binary.LittleEndian.PutUint32(b, turn)
	for i, v := range samples {
		v = float32(math.Max(-1, math.Min(1, float64(v))))
		binary.LittleEndian.PutUint16(b[4+2*i:], uint16(int16(v*32767)))
	}
	return b
}

func hasWords(p string) bool {
	for _, w := range strings.FieldsFunc(strings.ToLower(p), func(r rune) bool { return !unicode.IsLetter(r) && r != '\'' }) {
		if len(w) >= 2 && !fillers[w] {
			return true
		}
	}
	return false
}
