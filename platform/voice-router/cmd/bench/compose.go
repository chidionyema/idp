package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"

	sherpa "github.com/k2-fsa/sherpa-onnx-go/sherpa_onnx"

	"github.com/chidionyema/idp/platform/voice-router/internal/engine"
)

// The sentences the round trip speaks: the kind of thing the estate says aloud.
var sentences = []string{
	"all five agents are healthy",
	"the build lane finished two minutes ago",
	"nothing needs you right now",
	"three pull requests are waiting for review",
	"the deploy is green and the cluster is steady",
	"one agent is stuck on a failing test",
	"i stopped the job and saved its logs",
	"memory use is under half on every node",
}

type result struct {
	asr, tts          string
	silence           float64
	humanWER, loopWER float64
	endpointMS, ttsMS int64 // endpoint: audio time after speech; tts: wall time to first audio (p50)
	finaliseMS        int64 // wall time of the ASR work at the endpoint frame (p50)
	gate              string
}

// wait is what the listener sits through before any sound, minus the brain:
// the endpointer's silence, the ASR's last decode, the voice's first audio.
func (r result) wait() int64 { return r.endpointMS + r.finaliseMS + r.ttsMS }

// compose runs every cached streaming ASR against every cached voice, at each
// endpoint silence, and ranks the pairs. Hard gates first, then listener wait.
// No weighted score: it would hide which axis won.
func compose(silences []float64) {
	asrs, _ := filepath.Glob(filepath.Join(*models, "sherpa-onnx-*streaming*"))
	voices, _ := filepath.Glob(filepath.Join(*models, "vits-piper-*"))
	if len(asrs) == 0 || len(voices) == 0 {
		fmt.Fprintf(os.Stderr, "compose needs at least one streaming ASR and one piper voice under %s\n", *models)
		os.Exit(1)
	}
	var all []result
	for _, ad := range asrs {
		for _, sil := range silences {
			asr, err := engine.NewASR(ad, *threads, float32(sil))
			if err != nil {
				fmt.Println(err)
				continue
			}
			human, endpoint, finalise := humanWER(asr, ad)
			for _, vd := range voices {
				tts, err := engine.NewPiperTTS(vd, *threads, 1, 1)
				if err != nil {
					fmt.Println(err)
					continue
				}
				loop, ttsMS := loopWER(asr, tts)
				r := result{asr: short(ad), tts: short(vd), silence: sil, humanWER: human, loopWER: loop,
					endpointMS: endpoint, finaliseMS: finalise, ttsMS: ttsMS}
				switch {
				case researchOnly(r.tts) != "":
					r.gate = researchOnly(r.tts)
				case human < 0:
					r.gate = "no human test audio"
				case human > 0.10:
					r.gate = "human WER > 10%"
				case loop > 0.20:
					r.gate = "round-trip WER > 20%"
				}
				all = append(all, r)
				fmt.Fprintf(os.Stderr, "measured %s + %s @ %.1fs\n", r.asr, r.tts, sil)
			}
		}
	}
	slices.SortStableFunc(all, func(a, b result) int {
		if (a.gate == "") != (b.gate == "") {
			if a.gate == "" {
				return -1
			}
			return 1
		}
		if d := a.wait() - b.wait(); d != 0 {
			return int(d)
		}
		switch {
		case a.loopWER < b.loopWER:
			return -1
		case a.loopWER > b.loopWER:
			return 1
		}
		return 0
	})
	fmt.Printf("threads=%d reps=%d  (wait = endpoint + finalise + tts first audio; the brain is not in it)\n\n", *threads, *runs)
	fmt.Println("| rank | ASR | voice | silence | wait ms | endpoint ms | finalise ms | tts first ms | human WER | round-trip WER | gate |")
	fmt.Println("|---|---|---|---|---|---|---|---|---|---|---|")
	for i, r := range all {
		g := r.gate
		if g == "" {
			g = "pass"
		}
		fmt.Printf("| %d | %s | %s | %.1fs | %d | %d | %d | %d | %.1f%% | %.1f%% | %s |\n", i+1, r.asr, r.tts, r.silence,
			r.wait(), r.endpointMS, r.finaliseMS, r.ttsMS, 100*r.humanWER, 100*r.loopWER, g)
	}
}

// researchOnly names the licence that keeps a voice out of the product, or ""
// (docs/tickets/2026-09-26-voice-router-self-hosted.md, licence table). A voice
// that cannot ship is still measured -- it is the research baseline -- but it
// never ranks above one that can.
func researchOnly(voice string) string {
	switch {
	case strings.Contains(voice, "lessac"):
		return "licence: Blizzard 2013, research only"
	case strings.Contains(voice, "libritts_r"):
		return "licence: fine-tuned from lessac"
	}
	return ""
}

func short(dir string) string {
	s := filepath.Base(dir)
	s = strings.TrimPrefix(s, "sherpa-onnx-")
	return strings.TrimPrefix(s, "vits-piper-")
}

// humanWER scores the ASR on the recording its release ships (a human voice),
// and times the endpoint: how much audio after the speech it took, and the wall
// time of the decode on that frame. -1 when the release has no test audio.
func humanWER(asr *engine.ASR, dir string) (wer float64, endpointMS, finaliseMS int64) {
	tw := filepath.Join(dir, "test_wavs")
	w := sherpa.ReadWave(filepath.Join(tw, "0.wav"))
	trans, err := os.ReadFile(filepath.Join(tw, "trans.txt"))
	if w == nil || err != nil {
		return -1, 0, 0
	}
	var want []string
	for _, line := range strings.Split(string(trans), "\n") {
		if f := strings.Fields(strings.ToLower(line)); len(f) > 1 && f[0] == "0.wav" {
			want = f[1:]
		}
	}
	var eps, fins []int64
	var got string
	for r := 0; r < *runs; r++ {
		text, ep, fin := streamAll(asr, w.Samples)
		got = text
		eps, fins = append(eps, ep), append(fins, fin)
	}
	return float64(distance(want, strings.Fields(got))) / float64(len(want)), p50(eps), p50(fins)
}

// loopWER speaks each sentence runs times through the voice and hears it back.
// It also returns the voice's median wall time to first audio.
func loopWER(asr *engine.ASR, tts *engine.TTS) (float64, int64) {
	var errs, words int
	var firsts []int64
	for _, want := range sentences {
		for r := 0; r < *runs; r++ {
			var pcm []float32
			var first time.Duration
			t := time.Now()
			if err := tts.Synth(context.Background(), want+".", func(s []float32) bool {
				if first == 0 {
					first = time.Since(t)
				}
				pcm = append(pcm, s...)
				return true
			}); err != nil {
				return 1, 0
			}
			firsts = append(firsts, first.Milliseconds())
			got, _, _ := streamAll(asr, resample(pcm, tts.SampleRate(), 16000))
			errs += distance(strings.Fields(want), strings.Fields(got))
			words += len(strings.Fields(want))
		}
	}
	return float64(errs) / float64(words), p50(firsts)
}

// streamAll feeds 1s of silence, the audio, then 3s of silence in 20 ms frames,
// as the service does. It returns every word heard across endpoints, how much
// audio past the end of speech the first endpoint fired at, and the wall time
// of that frame.
func streamAll(asr *engine.ASR, samples []float32) (all string, endpointMS, finaliseMS int64) {
	s := asr.NewStream()
	defer s.Close()
	lead := 16000
	audio := append(append(make([]float32, lead), samples...), make([]float32, 3*16000)...)
	// Speech ends at the last audible sample, not the end of the file: recordings
	// carry trailing silence, and an endpoint inside it is still an endpoint.
	end := lead + len(samples)
	for end > lead && audio[end-1] < 0.02 && audio[end-1] > -0.02 {
		end--
	}
	var heard []string
	first := true
	for i := 0; i < len(audio); i += 320 {
		t := time.Now()
		s.Accept(audio[i:min(i+320, len(audio))])
		if s.Endpoint() {
			if p := strings.ToLower(strings.TrimSpace(s.Partial())); p != "" {
				heard = append(heard, p)
			}
			if first && i+320 >= end {
				endpointMS = int64(i+320-end) * 1000 / 16000
				finaliseMS = time.Since(t).Milliseconds()
				first = false
			}
			s.Reset()
		}
	}
	return strings.Join(heard, " "), endpointMS, finaliseMS
}

func p50(v []int64) int64 {
	if len(v) == 0 {
		return 0
	}
	s := slices.Clone(v)
	slices.Sort(s)
	return s[len(s)/2]
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
