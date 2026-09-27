// Command voice-router is the estate's self-hosted streaming voice service.
//
// One WebSocket per conversation at /voice/ws:
//
//	client -> server  binary: int16 LE PCM, 16 kHz mono (any frame size)
//	client -> server  text:   {"type":"system","text":...} | {"type":"ask","text":...} | {"type":"say","text":...} | {"type":"stop"}
//	server -> client  text:   hello{rate} partial{text} final{turn,text} phrase{turn,text} intent_result{turn,intent} barge{turn} done{turn} error{turn,text}
//	server -> client  binary: uint32 LE turn id, then int16 LE PCM at hello.rate
//
// The client drops audio for any turn at or below the last barge.
//
// VOICE_INTENT_URL (the FleetView backend's POST /voice/intent; empty = off): an utterance that names a
// committed, arg-free estate intent runs it; intent_result carries the result contract and its text is spoken.
//
// GET /voice/turns: the last turns (voice_turns fields) and their medians.
//
// VOICE_MODE=director runs the /fleet cinema director instead (director.go); no models load.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/coder/websocket"

	"github.com/chidionyema/idp/platform/voice-router/internal/brain"
	"github.com/chidionyema/idp/platform/voice-router/internal/engine"
	"github.com/chidionyema/idp/platform/voice-router/internal/intent"
	"github.com/chidionyema/idp/platform/voice-router/internal/session"
	"github.com/chidionyema/idp/platform/voice-router/internal/turnlog"
)

const defaultSystem = "You are the estate's voice. Open with a short sentence of under six words, " +
	"then at most two more short sentences. No markdown, no lists, no symbols; plain words that sound natural aloud."

func main() {
	log := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	if os.Getenv("VOICE_MODE") == "director" {
		os.Exit(runDirector(log))
	}
	models := env("VOICE_MODELS", "/models")
	threads := envInt("VOICE_THREADS", 2)

	t0 := time.Now()
	asr, err := engine.NewASR(filepath.Join(models, env("VOICE_ASR", "sherpa-onnx-nemo-streaming-fast-conformer-transducer-en-480ms-int8")),
		threads, float32(envFloat("VOICE_ENDPOINT_SILENCE", 0.5)))
	if err != nil {
		log.Error("voice.start", "err", err)
		os.Exit(1)
	}
	voice := env("VOICE_TTS", "vits-piper-en_US-ljspeech-medium")
	tts, err := engine.NewPiperTTS(filepath.Join(models, voice),
		threads, envInt("VOICE_TTS_POOL", 1), float32(envFloat("VOICE_SPEED", 1.0)))
	if err != nil {
		log.Error("voice.start", "err", err)
		os.Exit(1)
	}
	b := brain.FromEnv()
	origins := strings.Split(env("VOICE_ALLOWED_ORIGINS", "localhost:3100,127.0.0.1:3100"), ",")
	system := env("VOICE_SYSTEM_PROMPT", defaultSystem)
	var intents session.Intents
	if u := env("VOICE_INTENT_URL", ""); u != "" {
		intents = intent.Hook{Client: &intent.Client{URL: u}, Log: log}
	}
	log.Info("voice.ready", "load_ms", time.Since(t0).Milliseconds(), "brain", b.BaseURL, "model", b.Model, "origins", origins, "tts_rate", tts.SampleRate(), "intent_url", env("VOICE_INTENT_URL", ""))

	turns, clock := turnlog.NewRing(envInt("VOICE_TURNS_KEPT", 200)), turnlog.NewClock()
	var conns atomic.Uint64
	mux := http.NewServeMux()
	mux.HandleFunc("GET /voice/turns", func(w http.ResponseWriter, r *http.Request) {
		// The same allow-list as the socket: a page that may talk may also read its own metrics.
		if o := r.Header.Get("Origin"); allowedOrigin(origins, o) {
			w.Header().Set("Access-Control-Allow-Origin", o)
			w.Header().Set("Vary", "Origin")
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{"summary": turns.Summary(), "recent": turns.Recent(50)})
	})
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) { _, _ = w.Write([]byte("ok\n")) })
	mux.HandleFunc("GET /voice/ws", func(w http.ResponseWriter, r *http.Request) {
		c, err := websocket.Accept(w, r, &websocket.AcceptOptions{OriginPatterns: origins})
		if err != nil {
			log.Warn("voice.reject", "origin", r.Header.Get("Origin"), "err", err)
			return
		}
		id := strconv.FormatInt(t0.Unix(), 36) + "-" + strconv.FormatUint(conns.Add(1), 10)
		serve(r.Context(), c, asr, tts, b, system, log.With("session_id", id), func(s *session.Session) {
			s.Record(turns, clock, id, "piper", voice)
			if intents != nil {
				s.SetIntents(intents)
			}
		})
	})

	srv := &http.Server{Addr: env("VOICE_ADDR", ":8080"), Handler: mux, ReadHeaderTimeout: 10 * time.Second}
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	go func() {
		<-ctx.Done()
		shut, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = srv.Shutdown(shut)
	}()
	log.Info("voice.listen", "addr", srv.Addr)
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Error("voice.listen", "err", err)
		os.Exit(1)
	}
}

type wsOut struct {
	ctx context.Context
	c   *websocket.Conn
}

func (o wsOut) JSON(v any) error {
	b, err := json.Marshal(v)
	if err != nil {
		return err
	}
	return o.c.Write(o.ctx, websocket.MessageText, b)
}

func (o wsOut) Binary(b []byte) error { return o.c.Write(o.ctx, websocket.MessageBinary, b) }

func serve(parent context.Context, c *websocket.Conn, asr *engine.ASR, tts *engine.TTS, b *brain.Client, system string, log *slog.Logger, setup func(*session.Session)) {
	ctx, cancel := context.WithCancel(parent)
	defer cancel()
	defer c.CloseNow()
	c.SetReadLimit(1 << 20)
	stream := asr.NewStream()
	defer stream.Close()
	s := session.New(ctx, stream, tts, b, wsOut{ctx, c}, system, log)
	setup(s)
	if err := s.Hello(); err != nil {
		return
	}
	log.Info("voice.connect")
	defer log.Info("voice.disconnect")
	for {
		typ, data, err := c.Read(ctx)
		if err != nil {
			return
		}
		if typ == websocket.MessageBinary {
			s.OnAudio(data)
			continue
		}
		var m struct{ Type, Text string }
		if json.Unmarshal(data, &m) != nil {
			continue
		}
		switch m.Type {
		case "system":
			s.SetSystem(m.Text)
		case "ask":
			if t := strings.TrimSpace(m.Text); t != "" {
				s.Ask(t)
			}
		case "say":
			if t := strings.TrimSpace(m.Text); t != "" {
				s.Say(t)
			}
		case "stop":
			s.Barge()
		}
	}
}

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func envInt(k string, def int) int {
	if n, err := strconv.Atoi(os.Getenv(k)); err == nil {
		return n
	}
	return def
}

func envFloat(k string, def float64) float64 {
	if f, err := strconv.ParseFloat(os.Getenv(k), 64); err == nil {
		return f
	}
	return def
}

// allowedOrigin matches an Origin header's host against the allow-list patterns the way the
// WebSocket accept does (path.Match on the host, case-insensitive).
func allowedOrigin(patterns []string, origin string) bool {
	u, err := url.Parse(origin)
	if origin == "" || err != nil || u.Host == "" {
		return false
	}
	for _, p := range patterns {
		if ok, _ := path.Match(strings.ToLower(strings.TrimSpace(p)), strings.ToLower(u.Host)); ok {
			return true
		}
	}
	return false
}
