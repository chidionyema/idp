// Command bench measures the voice-router engine candidates on this machine:
// streaming ASR real-time factor and finalisation latency, and TTS
// time-to-first-audio. Numbers only count for the hardware they ran on.
package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	sherpa "github.com/k2-fsa/sherpa-onnx-go/sherpa_onnx"
)

var (
	models  = flag.String("models", os.ExpandEnv("$HOME/.cache/estate-tools/sherpa-models"), "model root")
	threads = flag.Int("threads", 2, "onnx threads")
	runs    = flag.Int("runs", 3, "repeats per case")
	ttsOnly = flag.Bool("tts", false, "TTS only")
	cadence = flag.Bool("cadence", false, "print when each streaming ASR partial changes, in audio time, then exit")
	text    = flag.String("text", "All five agents are healthy. The build lane finished two minutes ago, and nothing needs you right now.", "TTS sentence")
)

const chunk = 1600 // 100 ms at 16 kHz

type asrCase struct{ name, dir, enc, dec, join, modelType string }

func main() {
	flag.Parse()
	wavs := flag.Args()
	if len(wavs) == 0 {
		wavs = []string{"/tmp/vbench/q.wav", "/tmp/vbench/long.wav"}
	}
	asr := []asrCase{
		{"kroko-zipformer", "sherpa-onnx-streaming-zipformer-en-kroko-2025-08-06", "encoder.onnx", "decoder.onnx", "joiner.onnx", ""},
		{"nemo-480ms-int8", "sherpa-onnx-nemo-streaming-fast-conformer-transducer-en-480ms-int8", "encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", ""},
		{"nemotron-0.6b-160ms-int8", "sherpa-onnx-nemotron-speech-streaming-en-0.6b-160ms-int8-2026-04-25", "encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", ""},
	}
	fmt.Printf("threads=%d runs=%d\n\n", *threads, *runs)
	if *cadence {
		for _, c := range asr {
			partials(c, wavs)
		}
		return
	}
	if !*ttsOnly {
		for _, c := range asr {
			benchASR(c, wavs)
		}
	}
	benchTTS()
}

func benchASR(c asrCase, wavs []string) {
	d := filepath.Join(*models, c.dir)
	cfg := sherpa.OnlineRecognizerConfig{}
	cfg.FeatConfig = sherpa.FeatureConfig{SampleRate: 16000, FeatureDim: 80}
	cfg.ModelConfig.Transducer = sherpa.OnlineTransducerModelConfig{
		Encoder: filepath.Join(d, c.enc), Decoder: filepath.Join(d, c.dec), Joiner: filepath.Join(d, c.join),
	}
	cfg.ModelConfig.Tokens = filepath.Join(d, "tokens.txt")
	cfg.ModelConfig.NumThreads = *threads
	cfg.ModelConfig.ModelType = c.modelType
	cfg.DecodingMethod = "greedy_search"
	t0 := time.Now()
	rec := sherpa.NewOnlineRecognizer(&cfg)
	if rec == nil {
		fmt.Printf("ASR %-26s LOAD FAILED\n", c.name)
		return
	}
	defer sherpa.DeleteOnlineRecognizer(rec)
	fmt.Printf("ASR %-26s load %.2fs\n", c.name, time.Since(t0).Seconds())
	for _, w := range wavs {
		wave := sherpa.ReadWave(w)
		if wave == nil {
			fmt.Printf("    %s unreadable\n", w)
			continue
		}
		audioSec := float64(len(wave.Samples)) / float64(wave.SampleRate)
		var best struct{ compute, final, worstChunk time.Duration }
		var txt string
		for r := 0; r < *runs; r++ {
			s := sherpa.NewOnlineStream(rec)
			var compute, worst time.Duration
			for i := 0; i < len(wave.Samples); i += chunk {
				end := min(i+chunk, len(wave.Samples))
				t := time.Now()
				s.AcceptWaveform(wave.SampleRate, wave.Samples[i:end])
				for rec.IsReady(s) {
					rec.Decode(s)
				}
				el := time.Since(t)
				compute += el
				worst = max(worst, el)
			}
			// Speech has ended: push tail padding and flush, as the service does
			// once the endpoint fires. This is the wait the listener feels.
			t := time.Now()
			s.AcceptWaveform(wave.SampleRate, make([]float32, wave.SampleRate*6/10))
			s.InputFinished()
			for rec.IsReady(s) {
				rec.Decode(s)
			}
			txt = rec.GetResult(s).Text
			final := time.Since(t)
			sherpa.DeleteOnlineStream(s)
			if r == 0 || compute+final < best.compute+best.final {
				best.compute, best.final, best.worstChunk = compute, final, worst
			}
		}
		fmt.Printf("    %-9s audio %.2fs  rtf %.3f  worst-100ms-chunk %4dms  finalise %4dms  %q\n",
			filepath.Base(w), audioSec, best.compute.Seconds()/audioSec, best.worstChunk.Milliseconds(), best.final.Milliseconds(), strings.TrimSpace(txt))
	}
}

func benchTTS() {
	root := *models
	type ttsCase struct {
		name string
		cfg  sherpa.OfflineTtsModelConfig
	}
	vits := filepath.Join(root, "vits-piper-en_US-lessac-medium-int8")
	kit := filepath.Join(root, "kitten-nano-en-v0_8-int8")
	kok := filepath.Join(root, "kokoro-int8-en-v0_19")
	cases := []ttsCase{
		{"piper-lessac-medium-int8", sherpa.OfflineTtsModelConfig{Vits: sherpa.OfflineTtsVitsModelConfig{
			Model: filepath.Join(vits, "en_US-lessac-medium.onnx"), Tokens: filepath.Join(vits, "tokens.txt"), DataDir: filepath.Join(vits, "espeak-ng-data"),
			NoiseScale: 0.667, NoiseScaleW: 0.8, LengthScale: 1}}},
		{"kitten-nano-int8", sherpa.OfflineTtsModelConfig{Kitten: sherpa.OfflineTtsKittenModelConfig{
			Model: filepath.Join(kit, "model.int8.onnx"), Voices: filepath.Join(kit, "voices.bin"), Tokens: filepath.Join(kit, "tokens.txt"),
			DataDir: filepath.Join(kit, "espeak-ng-data"), LengthScale: 1}}},
		{"kokoro-int8", sherpa.OfflineTtsModelConfig{Kokoro: sherpa.OfflineTtsKokoroModelConfig{
			Model: filepath.Join(kok, "model.int8.onnx"), Voices: filepath.Join(kok, "voices.bin"), Tokens: filepath.Join(kok, "tokens.txt"),
			DataDir: filepath.Join(kok, "espeak-ng-data"), LengthScale: 1}}},
	}
	if dirs, _ := filepath.Glob(filepath.Join(root, "vits-piper-*")); len(dirs) > 0 {
		for _, d := range dirs {
			m, _ := filepath.Glob(filepath.Join(d, "*.onnx"))
			if len(m) == 0 {
				continue
			}
			cases = append(cases, ttsCase{filepath.Base(d)[len("vits-"):], sherpa.OfflineTtsModelConfig{Vits: sherpa.OfflineTtsVitsModelConfig{
				Model: m[0], Tokens: filepath.Join(d, "tokens.txt"), DataDir: filepath.Join(d, "espeak-ng-data"),
				NoiseScale: 0.667, NoiseScaleW: 0.8, LengthScale: 1}}})
		}
	}
	first := strings.SplitAfter(*text, ".")[0]
	fmt.Printf("\nTTS first phrase: %q\n", first)
	for _, c := range cases {
		c.cfg.NumThreads = *threads
		t0 := time.Now()
		tts := sherpa.NewOfflineTts(&sherpa.OfflineTtsConfig{Model: c.cfg, MaxNumSentences: 1})
		if tts == nil {
			fmt.Printf("TTS %-26s LOAD FAILED\n", c.name)
			continue
		}
		load := time.Since(t0)
		var bestFirst, bestTotal time.Duration
		var audioSec float64
		for r := 0; r < *runs; r++ {
			var firstAt time.Duration
			t := time.Now()
			a := tts.GenerateWithCallback(first, 0, 1.0, func(s []float32) bool {
				if firstAt == 0 {
					firstAt = time.Since(t)
				}
				return true
			})
			total := time.Since(t)
			audioSec = float64(len(a.Samples)) / float64(a.SampleRate)
			if r == 0 || firstAt < bestFirst {
				bestFirst, bestTotal = firstAt, total
			}
		}
		fmt.Printf("TTS %-26s load %.2fs  first-audio %4dms  total %4dms  audio %.2fs  rtf %.3f  rate %dHz\n",
			c.name, load.Seconds(), bestFirst.Milliseconds(), bestTotal.Milliseconds(), audioSec, bestTotal.Seconds()/audioSec, tts.SampleRate())
		sherpa.DeleteOfflineTts(tts)
	}
}

// partials feeds 20 ms frames plus 3 s of silence and prints the audio time at
// which the transcript changes. Audio time, not wall time: this is the model's
// own cadence, independent of machine load.
func partials(c asrCase, wavs []string) {
	d := filepath.Join(*models, c.dir)
	cfg := sherpa.OnlineRecognizerConfig{}
	cfg.FeatConfig = sherpa.FeatureConfig{SampleRate: 16000, FeatureDim: 80}
	cfg.ModelConfig.Transducer = sherpa.OnlineTransducerModelConfig{
		Encoder: filepath.Join(d, c.enc), Decoder: filepath.Join(d, c.dec), Joiner: filepath.Join(d, c.join),
	}
	cfg.ModelConfig.Tokens = filepath.Join(d, "tokens.txt")
	cfg.ModelConfig.NumThreads = *threads
	cfg.DecodingMethod = "greedy_search"
	cfg.EnableEndpoint = 1
	cfg.Rule1MinTrailingSilence = 2.4
	cfg.Rule2MinTrailingSilence = 0.5
	cfg.Rule3MinUtteranceLength = 20
	rec := sherpa.NewOnlineRecognizer(&cfg)
	defer sherpa.DeleteOnlineRecognizer(rec)
	for _, w := range wavs {
		wave := sherpa.ReadWave(w)
		samples := append(append([]float32{}, wave.Samples...), make([]float32, 3*16000)...)
		s := sherpa.NewOnlineStream(rec)
		fmt.Printf("%s %s (%.2fs audio then silence)\n", c.name, filepath.Base(w), float64(len(wave.Samples))/16000)
		last := ""
		for i := 0; i < len(samples); i += 320 {
			s.AcceptWaveform(16000, samples[i:min(i+320, len(samples))])
			for rec.IsReady(s) {
				rec.Decode(s)
			}
			at := float64(i+320) / 16000
			if t := rec.GetResult(s).Text; t != last {
				fmt.Printf("   %5.2fs  %q\n", at, t)
				last = t
			}
			if rec.IsEndpoint(s) {
				fmt.Printf("   %5.2fs  ENDPOINT\n", at)
				break
			}
		}
		sherpa.DeleteOnlineStream(s)
	}
}
