package engine

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	sherpa "github.com/k2-fsa/sherpa-onnx-go/sherpa_onnx"
)

// These run the real models. VOICE_MODELS points at the model root (the image
// build runs them against /models, on each arch it ships).
func models(t *testing.T) string {
	d := os.Getenv("VOICE_MODELS")
	if d == "" {
		d = os.ExpandEnv("$HOME/.cache/estate-tools/sherpa-models")
	}
	if _, err := os.Stat(d); err != nil {
		t.Skip("no models at " + d)
	}
	return d
}

// A human speaker, not a synthesiser: the recording and its transcript ship in
// the model release (LibriSpeech), so this needs nothing from the machine.
func TestASRTranscribesAndEndpoints(t *testing.T) {
	dir := filepath.Join(models(t), asrModel, "test_wavs")
	w := sherpa.ReadWave(filepath.Join(dir, "0.wav"))
	trans, err := os.ReadFile(filepath.Join(dir, "trans.txt"))
	if w == nil || err != nil {
		t.Fatalf("the ASR release's test recording is missing from %s", dir)
	}
	var want []string
	for _, line := range strings.Split(string(trans), "\n") {
		if f := strings.Fields(strings.ToLower(line)); len(f) > 1 && f[0] == "0.wav" {
			want = f[1:]
		}
	}
	first, _ := transcribe(t, newASR(t, models(t)), w.Samples)
	got := strings.Fields(first) // the whole sentence, at one endpoint
	wer := float64(distance(want, got)) / float64(len(want))
	t.Logf("heard %q: word error rate %.1f%%", strings.Join(got, " "), 100*wer)
	if wer > 0.10 {
		t.Fatalf("word error rate %.1f%% is above 10%%; want %q", 100*wer, strings.Join(want, " "))
	}
}

const asrModel = "sherpa-onnx-nemo-streaming-fast-conformer-transducer-en-480ms-int8"

// voice is the TTS under test: the service default unless VOICE_TTS names another.
func voice() string {
	if v := os.Getenv("VOICE_TTS"); v != "" {
		return v
	}
	return "vits-piper-en_US-ljspeech-medium"
}

func newASR(t *testing.T, root string) *ASR {
	a, err := NewASR(filepath.Join(root, asrModel), 2, 0.5)
	if err != nil {
		t.Fatal(err)
	}
	return a
}

// transcribe streams 16 kHz audio in 20 ms frames, as the service does. first
// is the text at the first endpoint -- the utterance the service would act on;
// all is every word heard to the end of the audio, across endpoints.
func transcribe(t *testing.T, a *ASR, samples []float32) (first, all string) {
	s := a.NewStream()
	defer s.Close()
	audio := append(append(make([]float32, 16000), samples...), make([]float32, 2*16000)...)
	var heard []string
	for i := 0; i < len(audio); i += 320 {
		s.Accept(audio[i:min(i+320, len(audio))])
		if s.Endpoint() {
			if p := strings.ToLower(strings.TrimSpace(s.Partial())); p != "" {
				heard = append(heard, p)
			}
			s.Reset()
		}
	}
	if len(heard) == 0 {
		t.Fatal("no endpoint")
	}
	return heard[0], strings.Join(heard, " ")
}

// TestVoiceIsIntelligible feeds the voice's own speech back through the ASR.
// A voice the recognizer cannot follow word for word is one a listener will
// strain at; this is the objective half of "does it sound right".
//
// The synthesiser samples noise, so one pass of these 57 words scored anywhere
// from 3.5% to 12.3% on ljspeech (six processes, 2026-09-26); each sentence is
// spoken three times to steady the number. The bar is for a BROKEN voice -- a
// wrong model, rate or format scores far above it -- not a ranking of voices.
func TestVoiceIsIntelligible(t *testing.T) {
	root := models(t)
	tts, err := NewPiperTTS(filepath.Join(root, voice()), 2, 1, 1)
	if err != nil {
		t.Fatal(err)
	}
	a := newASR(t, root)
	var errs, words int
	for _, want := range []string{
		"all five agents are healthy",
		"the build lane finished two minutes ago",
		"nothing needs you right now",
		"three pull requests are waiting for review",
		"the deploy is green and the cluster is steady",
		"one agent is stuck on a failing test",
		"i stopped the job and saved its logs",
		"memory use is under half on every node",
	} {
		for rep := 0; rep < 3; rep++ {
			var pcm []float32
			if err := tts.Synth(context.Background(), want+".", func(s []float32) bool { pcm = append(pcm, s...); return true }); err != nil {
				t.Fatal(err)
			}
			// Every word, not just those before the first endpoint: a pause in the
			// voice is the endpointer's business, not a word the listener lost.
			_, got := transcribe(t, a, resample(pcm, tts.SampleRate(), 16000))
			e := distance(strings.Fields(want), strings.Fields(got))
			errs, words = errs+e, words+len(strings.Fields(want))
			if e > 0 {
				t.Logf("spoke %q, heard %q", want, got)
			}
		}
	}
	wer := float64(errs) / float64(words)
	t.Logf("%s: word error rate %.1f%% (%d/%d)", voice(), 100*wer, errs, words)
	if wer > 0.20 {
		t.Fatalf("word error rate %.1f%% is above 20%%", 100*wer)
	}
}

// distance is the word-level edit distance.
func distance(a, b []string) int {
	prev := make([]int, len(b)+1)
	for j := range prev {
		prev[j] = j
	}
	for i := 1; i <= len(a); i++ {
		cur := make([]int, len(b)+1)
		cur[0] = i
		for j := 1; j <= len(b); j++ {
			sub := prev[j-1]
			if a[i-1] != b[j-1] {
				sub++
			}
			cur[j] = min(sub, prev[j]+1, cur[j-1]+1)
		}
		prev = cur
	}
	return prev[len(b)]
}

// resample is linear interpolation: crude, but enough for speech recognition.
func resample(in []float32, from, to int) []float32 {
	out := make([]float32, len(in)*to/from)
	for i := range out {
		p := float64(i) * float64(from) / float64(to)
		j := int(p)
		if j+1 >= len(in) {
			out[i] = in[len(in)-1]
			continue
		}
		f := float32(p - float64(j))
		out[i] = in[j]*(1-f) + in[j+1]*f
	}
	return out
}

func TestTTSSynthesisesAndCancels(t *testing.T) {
	root := models(t)
	tts, err := NewPiperTTS(filepath.Join(root, "vits-piper-en_US-ljspeech-medium"), 2, 1, 1)
	if err != nil {
		t.Fatal(err)
	}
	n := 0
	if err := tts.Synth(context.Background(), "Five agents are on duty.", func(s []float32) bool { n += len(s); return true }); err != nil {
		t.Fatal(err)
	}
	if secs := float64(n) / float64(tts.SampleRate()); secs < 0.8 || secs > 4 {
		t.Fatalf("got %.2fs of audio for a short sentence", secs)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	start := time.Now()
	if err := tts.Synth(ctx, "This should never be spoken.", func([]float32) bool { t.Error("emitted after cancel"); return true }); err == nil {
		t.Fatal("cancelled synthesis returned nil")
	}
	if time.Since(start) > 100*time.Millisecond {
		t.Fatal("cancelled synthesis still ran")
	}
}
