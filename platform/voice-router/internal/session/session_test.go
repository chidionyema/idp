package session

import (
	"context"
	"encoding/binary"
	"encoding/json"
	"io"
	"log/slog"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/chidionyema/idp/platform/voice-router/internal/brain"
)

// fakeASR returns a scripted partial per Accept call, and an endpoint when the
// script says so.
type fakeASR struct {
	script []step
	i      int
	cur    string
}
type step struct {
	partial  string
	endpoint bool
}

func (a *fakeASR) Accept([]float32) {
	if a.i < len(a.script) {
		a.cur = a.script[a.i].partial
	}
	a.i++
}
func (a *fakeASR) Partial() string { return a.cur }
func (a *fakeASR) Endpoint() bool  { return a.i <= len(a.script) && a.script[a.i-1].endpoint }
func (a *fakeASR) Reset()          { a.cur = "" }

// fakeTTS emits two chunks per phrase from ONE reused buffer, as a real
// synthesiser may, and can be slowed down to leave room for a barge-in.
type fakeTTS struct {
	delay time.Duration
	mu    sync.Mutex // the real engine serialises synthesis the same way
	buf   []float32
}

func (t *fakeTTS) SampleRate() int { return 22050 }
func (t *fakeTTS) Synth(ctx context.Context, text string, emit func([]float32) bool) error {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.buf == nil {
		t.buf = make([]float32, 4)
	}
	for k := 0; k < 2; k++ {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(t.delay):
		}
		for i := range t.buf {
			t.buf[i] = float32(k+1) / 10
		}
		if !emit(t.buf) {
			return nil
		}
	}
	return nil
}

type fakeBrain struct {
	tokens []string
	gap    time.Duration
	mu     sync.Mutex
	calls  [][]brain.Message
}

func (b *fakeBrain) Stream(ctx context.Context, msgs []brain.Message, on func(string)) error {
	b.mu.Lock()
	b.calls = append(b.calls, msgs)
	b.mu.Unlock()
	for _, t := range b.tokens {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(b.gap):
		}
		on(t)
	}
	return nil
}

type rec struct {
	mu     sync.Mutex
	events []Event
	frames [][]byte
}

func (r *rec) JSON(v any) error {
	b, _ := json.Marshal(v)
	var e Event
	_ = json.Unmarshal(b, &e)
	r.mu.Lock()
	r.events = append(r.events, e)
	r.mu.Unlock()
	return nil
}
func (r *rec) Binary(b []byte) error {
	r.mu.Lock()
	r.frames = append(r.frames, b)
	r.mu.Unlock()
	return nil
}
func (r *rec) has(typ string, turn uint32) bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, e := range r.events {
		if e.Type == typ && e.Turn == turn {
			return true
		}
	}
	return false
}
func (r *rec) wait(t *testing.T, typ string, turn uint32) {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for !r.has(typ, turn) {
		if time.Now().After(deadline) {
			t.Fatalf("no %s event for turn %d; got %+v", typ, turn, r.snapshot())
		}
		time.Sleep(5 * time.Millisecond)
	}
}
func (r *rec) snapshot() []Event {
	r.mu.Lock()
	defer r.mu.Unlock()
	return append([]Event(nil), r.events...)
}
func (r *rec) framesFor(turn uint32) int {
	r.mu.Lock()
	defer r.mu.Unlock()
	n := 0
	for _, f := range r.frames {
		if binary.LittleEndian.Uint32(f) == turn {
			n++
		}
	}
	return n
}

var quiet = slog.New(slog.NewTextHandler(io.Discard, nil))
var pcm = make([]byte, 320)

func newSession(a *fakeASR, t *fakeTTS, b Brain) (*Session, *rec) {
	r := &rec{}
	return New(context.Background(), a, t, b, r, "you are the estate", quiet), r
}

func TestUtteranceBecomesSpokenReply(t *testing.T) {
	a := &fakeASR{script: []step{{"how many", false}, {"how many agents", false}, {"how many agents", true}}}
	b := &fakeBrain{tokens: []string{"Five", " agents.", " All", " healthy."}}
	s, r := newSession(a, &fakeTTS{}, b)
	for range a.script {
		s.OnAudio(pcm)
	}
	r.wait(t, "done", 1)

	var phrases []string
	for _, e := range r.snapshot() {
		if e.Type == "phrase" {
			phrases = append(phrases, e.Text)
		}
	}
	if strings.Join(phrases, "|") != "Five agents.|All healthy." {
		t.Fatalf("phrases %q", phrases)
	}
	if got := r.framesFor(1); got != 4 {
		t.Fatalf("audio frames for turn 1 = %d, want 4", got)
	}
	b.mu.Lock()
	msgs := b.calls[0]
	b.mu.Unlock()
	if msgs[0].Role != "system" || msgs[1].Content != "how many agents" {
		t.Fatalf("brain got %+v", msgs)
	}
}

// The pasted design sent buffer[:n] from one reused buffer, so every frame
// already queued was overwritten by the next read. Frames must be independent.
func TestFramesDoNotShareTheSynthBuffer(t *testing.T) {
	a := &fakeASR{script: []step{{"status please", true}}}
	s, r := newSession(a, &fakeTTS{}, &fakeBrain{tokens: []string{"Fine."}})
	s.OnAudio(pcm)
	r.wait(t, "done", 1)
	r.mu.Lock()
	defer r.mu.Unlock()
	if len(r.frames) != 2 {
		t.Fatalf("frames %d", len(r.frames))
	}
	v0 := int16(binary.LittleEndian.Uint16(r.frames[0][4:]))
	v1 := int16(binary.LittleEndian.Uint16(r.frames[1][4:]))
	if v0 == v1 {
		t.Fatalf("frame 0 was overwritten by frame 1 (both %d)", v0)
	}
}

func TestRealWordsBargeIn(t *testing.T) {
	a := &fakeASR{script: []step{{"tell me everything", true}, {"stop", false}, {"stop now", true}}}
	b := &fakeBrain{tokens: []string{"One.", " Two.", " Three.", " Four.", " Five."}, gap: 30 * time.Millisecond}
	s, r := newSession(a, &fakeTTS{delay: 20 * time.Millisecond}, b)
	s.OnAudio(pcm)
	r.waitAudio(t, 1)
	s.OnAudio(pcm) // "stop": real word while turn 1 is audibly speaking
	r.wait(t, "barge", 1)
	before := r.framesFor(1)
	s.OnAudio(pcm) // endpoint: turn 2
	r.wait(t, "done", 2)
	if r.has("done", 1) {
		t.Fatal("interrupted turn 1 still reported done")
	}
	if after := r.framesFor(1); after != before {
		t.Fatalf("turn 1 kept sending audio after barge-in: %d -> %d frames", before, after)
	}
	// Turn 2 sees what turn 1 managed to say, before the interrupting question.
	b.mu.Lock()
	last := b.calls[1]
	b.mu.Unlock()
	if last[len(last)-1].Content != "stop now" || last[len(last)-2].Role != "assistant" {
		t.Fatalf("history for turn 2: %+v", last)
	}
}

// The looping bug on /fleet: any sound cancelled the reply. Coughs, breaths
// and fillers must never interrupt.
func TestNoiseAndFillersDoNotBargeIn(t *testing.T) {
	a := &fakeASR{script: []step{{"what's running", true}, {"", false}, {"uh", false}, {"hmm", false}, {"", true}}}
	b := &fakeBrain{tokens: []string{"Three.", " Builds."}, gap: 20 * time.Millisecond}
	s, r := newSession(a, &fakeTTS{delay: 10 * time.Millisecond}, b)
	s.OnAudio(pcm)
	r.wait(t, "phrase", 1)
	for i := 1; i < len(a.script); i++ {
		s.OnAudio(pcm)
	}
	r.wait(t, "done", 1)
	if r.has("barge", 1) {
		t.Fatal("noise interrupted the agent")
	}
	if r.has("final", 2) {
		t.Fatal("noise became a turn")
	}
}

// After the server finishes generating, the browser is still playing. Speech
// then must still tell the client to stop, and only once per utterance.
func TestBargeAfterGenerationStillStopsPlayback(t *testing.T) {
	a := &fakeASR{script: []step{{"hi there", true}, {"wait", false}, {"wait what", false}}}
	s, r := newSession(a, &fakeTTS{}, &fakeBrain{tokens: []string{"Hello."}})
	s.OnAudio(pcm)
	r.wait(t, "done", 1)
	s.OnAudio(pcm)
	s.OnAudio(pcm)
	n := 0
	for _, e := range r.snapshot() {
		if e.Type == "barge" {
			n++
		}
	}
	if n != 1 {
		t.Fatalf("barge events = %d, want exactly 1", n)
	}
}

func TestBrainFailureIsReported(t *testing.T) {
	a := &fakeASR{script: []step{{"status please", true}}}
	s, r := newSession(a, &fakeTTS{}, failing{})
	s.OnAudio(pcm)
	r.wait(t, "error", 1)
}

type failing struct{}

func (failing) Stream(context.Context, []brain.Message, func(string)) error {
	return io.ErrUnexpectedEOF
}

func TestHasWords(t *testing.T) {
	for in, want := range map[string]bool{"": false, "uh": false, "um hmm": false, "a": false, "no": true, "stop": true, "uh wait": true, "I'm": true} {
		if hasWords(in) != want {
			t.Errorf("hasWords(%q) != %v", in, want)
		}
	}
}

func TestEmptyReplyIsAnError(t *testing.T) {
	a := &fakeASR{script: []step{{"status please", true}}}
	s, r := newSession(a, &fakeTTS{}, &fakeBrain{})
	s.OnAudio(pcm)
	r.wait(t, "error", 1)
	if r.has("done", 1) {
		t.Fatal("an empty reply was reported as done")
	}
}

// A pause mid-sentence longer than the endpoint splits one thought in two.
// The second half interrupts the first turn and the brain gets the whole
// sentence, once.
func TestPauseMidSentenceIsJoined(t *testing.T) {
	a := &fakeASR{script: []step{{"how many", true}, {"agents are working", false}, {"agents are working", true}}}
	b := &fakeBrain{tokens: []string{"Five.", " Agents."}, gap: 300 * time.Millisecond}
	s, r := newSession(a, &fakeTTS{delay: 20 * time.Millisecond}, b)
	s.OnAudio(pcm)
	r.wait(t, "final", 1)
	s.OnAudio(pcm)
	s.OnAudio(pcm)
	r.wait(t, "done", 2)
	var finals []string
	for _, e := range r.snapshot() {
		if e.Type == "final" {
			finals = append(finals, e.Text)
		}
	}
	if finals[len(finals)-1] != "how many agents are working" {
		t.Fatalf("finals %q", finals)
	}
	b.mu.Lock()
	last := b.calls[len(b.calls)-1]
	b.mu.Unlock()
	users := 0
	for _, m := range last {
		if m.Role == "user" {
			users++
		}
	}
	if users != 1 {
		t.Fatalf("brain saw the split question twice: %+v", last)
	}
}

// A new question well after the last one is a new question.
func TestLaterQuestionIsNotJoined(t *testing.T) {
	a := &fakeASR{script: []step{{"hello there", true}, {"what next", true}}}
	s, r := newSession(a, &fakeTTS{}, &fakeBrain{tokens: []string{"Hi."}})
	s.OnAudio(pcm)
	r.wait(t, "done", 1)
	s.mu.Lock()
	s.heardAt = time.Now().Add(-continueWindow - time.Second)
	s.mu.Unlock()
	s.OnAudio(pcm)
	r.wait(t, "done", 2)
	if !r.hasText("final", 2, "what next") {
		t.Fatalf("got %+v", r.snapshot())
	}
}

func (r *rec) hasText(typ string, turn uint32, text string) bool {
	for _, e := range r.snapshot() {
		if e.Type == typ && e.Turn == turn && e.Text == text {
			return true
		}
	}
	return false
}

func (r *rec) waitAudio(t *testing.T, turn uint32) {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for r.framesFor(turn) == 0 {
		if time.Now().After(deadline) {
			t.Fatalf("no audio for turn %d", turn)
		}
		time.Sleep(5 * time.Millisecond)
	}
}

// /fleet reads an agent's reply aloud. It must be spoken as given -- never sent
// to the brain, which would answer it instead -- and the next question must
// see it, since the listener heard it.
func TestSayReadsTextAloudWithoutTheBrain(t *testing.T) {
	a := &fakeASR{script: []step{{"why", false}, {"why did it fail", true}}}
	b := &fakeBrain{tokens: []string{"Tests."}}
	s, r := newSession(a, &fakeTTS{}, b)
	s.Say("The build failed. Two tests are red.")
	r.wait(t, "done", 1)
	b.mu.Lock()
	calls := len(b.calls)
	b.mu.Unlock()
	if calls != 0 {
		t.Fatalf("say went to the brain %d times", calls)
	}
	if r.has("final", 1) {
		t.Fatal("say reported a final transcript, as if the listener had said it")
	}
	var phrases []string
	for _, e := range r.snapshot() {
		if e.Type == "phrase" && e.Turn == 1 {
			phrases = append(phrases, e.Text)
		}
	}
	if strings.Join(phrases, "|") != "The build failed.|Two tests are red." {
		t.Fatalf("phrases %q", phrases)
	}
	if got := r.framesFor(1); got != 4 {
		t.Fatalf("audio frames for turn 1 = %d, want 4", got)
	}
	for range a.script {
		s.OnAudio(pcm)
	}
	r.wait(t, "done", 2)
	b.mu.Lock()
	msgs := b.calls[0]
	b.mu.Unlock()
	if n := len(msgs); msgs[n-2].Role != "assistant" || msgs[n-2].Content != "The build failed. Two tests are red." || msgs[n-1].Content != "why did it fail" {
		t.Fatalf("history after say: %+v", msgs)
	}
}

// Speech during a say, before any audio, is a new question -- not the rest of
// an earlier one, which is what the continue window would make of it.
func TestSpeechInterruptsSayAsANewQuestion(t *testing.T) {
	a := &fakeASR{script: []step{{"first question", true}, {"stop", false}, {"stop that", true}}}
	b := &fakeBrain{tokens: []string{"Ok."}}
	s, r := newSession(a, &fakeTTS{delay: 50 * time.Millisecond}, b)
	s.OnAudio(pcm)
	r.wait(t, "done", 1)
	s.Say("A long reply from the agent.")
	r.wait(t, "phrase", 2)
	s.OnAudio(pcm) // "stop" before the say has made a sound
	r.wait(t, "barge", 2)
	s.OnAudio(pcm)
	r.wait(t, "done", 3)
	for _, e := range r.snapshot() {
		if e.Type == "final" && e.Turn == 3 && e.Text != "stop that" {
			t.Fatalf("interrupting a say was joined onto the earlier question: %q", e.Text)
		}
	}
}
