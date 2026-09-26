// Package engine adapts sherpa-onnx to the session interfaces: streaming ASR
// (a streaming transducer, nemo fast-conformer by default) and TTS (piper VITS voices), both in-process.
package engine

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	sherpa "github.com/k2-fsa/sherpa-onnx-go/sherpa_onnx"
)

const asrRate = 16000

// ASR is one loaded recognizer shared by every connection. Decoding is
// serialised: at a measured real-time factor of ~0.06 one recognizer keeps up
// with many live streams, and the lock removes any doubt about thread safety.
type ASR struct {
	mu  sync.Mutex
	rec *sherpa.OnlineRecognizer
}

// NewASR loads a streaming transducer from dir (encoder/decoder/joiner +
// tokens.txt). trailingSilence is how long a pause ends an utterance.
func NewASR(dir string, threads int, trailingSilence float32) (*ASR, error) {
	pick := func(names ...string) string {
		for _, n := range names {
			if p := filepath.Join(dir, n); exists(p) {
				return p
			}
		}
		return filepath.Join(dir, names[0])
	}
	cfg := sherpa.OnlineRecognizerConfig{}
	cfg.FeatConfig = sherpa.FeatureConfig{SampleRate: asrRate, FeatureDim: 80}
	cfg.ModelConfig.Transducer = sherpa.OnlineTransducerModelConfig{
		Encoder: pick("encoder.int8.onnx", "encoder.onnx"),
		Decoder: pick("decoder.int8.onnx", "decoder.onnx"),
		Joiner:  pick("joiner.int8.onnx", "joiner.onnx"),
	}
	cfg.ModelConfig.Tokens = filepath.Join(dir, "tokens.txt")
	cfg.ModelConfig.NumThreads = threads
	cfg.DecodingMethod = "greedy_search"
	cfg.EnableEndpoint = 1
	cfg.Rule1MinTrailingSilence = 2.4 // nothing said yet
	cfg.Rule2MinTrailingSilence = trailingSilence
	cfg.Rule3MinUtteranceLength = 20
	rec := sherpa.NewOnlineRecognizer(&cfg)
	if rec == nil {
		return nil, fmt.Errorf("engine: could not load ASR from %s", dir)
	}
	return &ASR{rec: rec}, nil
}

// Stream is one connection's recognizer stream.
type Stream struct {
	a *ASR
	s *sherpa.OnlineStream
}

// NewStream opens a stream; Close it when the connection ends.
func (a *ASR) NewStream() *Stream { return &Stream{a: a, s: sherpa.NewOnlineStream(a.rec)} }

func (s *Stream) Accept(samples []float32) {
	s.a.mu.Lock()
	defer s.a.mu.Unlock()
	s.s.AcceptWaveform(asrRate, samples)
	for s.a.rec.IsReady(s.s) {
		s.a.rec.Decode(s.s)
	}
}

func (s *Stream) Partial() string {
	s.a.mu.Lock()
	defer s.a.mu.Unlock()
	return s.a.rec.GetResult(s.s).Text
}

func (s *Stream) Endpoint() bool {
	s.a.mu.Lock()
	defer s.a.mu.Unlock()
	return s.a.rec.IsEndpoint(s.s)
}

func (s *Stream) Reset() {
	s.a.mu.Lock()
	defer s.a.mu.Unlock()
	s.a.rec.Reset(s.s)
}

func (s *Stream) Close() { sherpa.DeleteOnlineStream(s.s) }

// TTS is a pool of loaded voices; each synthesis holds one instance.
type TTS struct {
	pool  chan *sherpa.OfflineTts
	rate  int
	speed float32
}

// NewPiperTTS loads a piper VITS voice from dir (<name>.onnx, tokens.txt,
// espeak-ng-data) size times.
func NewPiperTTS(dir string, threads, size int, speed float32) (*TTS, error) {
	models, _ := filepath.Glob(filepath.Join(dir, "*.onnx"))
	if len(models) == 0 {
		return nil, fmt.Errorf("engine: no .onnx voice in %s", dir)
	}
	t := &TTS{pool: make(chan *sherpa.OfflineTts, size), speed: speed}
	for i := 0; i < size; i++ {
		cfg := sherpa.OfflineTtsConfig{MaxNumSentences: 1}
		cfg.Model.Vits = sherpa.OfflineTtsVitsModelConfig{
			Model: models[0], Tokens: filepath.Join(dir, "tokens.txt"), DataDir: filepath.Join(dir, "espeak-ng-data"),
			NoiseScale: 0.667, NoiseScaleW: 0.8, LengthScale: 1,
		}
		cfg.Model.NumThreads = threads
		tts := sherpa.NewOfflineTts(&cfg)
		if tts == nil {
			return nil, fmt.Errorf("engine: could not load TTS from %s", dir)
		}
		t.rate = tts.SampleRate()
		t.pool <- tts
	}
	return t, nil
}

func (t *TTS) SampleRate() int { return t.rate }

// Synth generates text, handing audio to emit as the engine produces it.
// Cancelling ctx stops at the next callback.
func (t *TTS) Synth(ctx context.Context, text string, emit func([]float32) bool) error {
	var tts *sherpa.OfflineTts
	select {
	case tts = <-t.pool:
	case <-ctx.Done():
		return ctx.Err()
	}
	defer func() { t.pool <- tts }()
	if err := ctx.Err(); err != nil { // select picks at random when both are ready
		return err
	}
	a := tts.GenerateWithCallback(text, 0, t.speed, func(samples []float32) bool {
		return ctx.Err() == nil && emit(samples)
	})
	if a == nil {
		return fmt.Errorf("engine: synthesis failed")
	}
	return ctx.Err()
}

func exists(p string) bool { _, err := os.Stat(p); return err == nil }
