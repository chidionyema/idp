package main

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"os/signal"
	"syscall"
	"time"

	"github.com/nats-io/nats.go"

	"github.com/chidionyema/idp/platform/voice-router/internal/brain"
	"github.com/chidionyema/idp/platform/voice-router/internal/director"
)

const (
	cueSubject    = "estate.cinema.cue"
	agentSubjects = "estate.agent.>"
)

func runDirector(log *slog.Logger) int {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	url := env("NATS_URL", "nats://nats.event-bus.svc:4222")
	nc, err := nats.Connect(url, nats.Name("voice-router-director"), nats.MaxReconnects(-1))
	if err != nil {
		log.Error("director.start", "err", err)
		return 1
	}

	js, err := nc.JetStream()
	if err != nil {
		log.Error("director.start", "err", err)
		return 1
	}

	ring := director.NewRing(director.Capacity)
	sub, err := js.Subscribe(agentSubjects, func(m *nats.Msg) {
		var ev director.Event
		if json.Unmarshal(m.Data, &ev) != nil || ev.SessionID == "" {
			return
		}
		ring.Push(ev)
	}, nats.OrderedConsumer(), nats.DeliverNew())
	if err != nil {
		log.Error("director.start", "err", err)
		return 1
	}

	b := brain.FromEnv()
	narrator := &director.Narrator{Brain: b, Limiter: director.NewLimiter(), Now: time.Now}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) { _, _ = w.Write([]byte("ok\n")) })
	srv := &http.Server{Addr: env("VOICE_ADDR", ":8080"), Handler: mux, ReadHeaderTimeout: 10 * time.Second}
	go func() {
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Error("director.listen", "err", err)
			stop()
		}
	}()

	log.Info("director.ready", "nats", url, "addr", srv.Addr, "brain", b.BaseURL, "model", b.Model)

	tick := time.NewTicker(250 * time.Millisecond)
	defer tick.Stop()
	drops := time.NewTicker(10 * time.Second)
	defer drops.Stop()

loop:
	for {
		select {
		case <-ctx.Done():
			break loop
		case <-drops.C:
			if d := ring.Dropped(); d > 0 {
				log.Warn("director.drop", "dropped", d)
			}
		case <-tick.C:
			ev := director.Coalesce(ring.Drain())
			if ev == nil {
				continue
			}
			shot, ok := director.ShotFor(ev.Kind)
			if !ok {
				continue
			}
			t0 := time.Now()
			line, used := narrator.Line(ctx, *ev)
			cue := director.NewCue(*ev, shot, line, time.Now())
			b, _ := json.Marshal(cue)
			if err := nc.Publish(cueSubject, b); err != nil {
				log.Warn("director.publish", "err", err)
				continue
			}
			log.Info("director.cue", "target_id", cue.TargetID, "shot_type", cue.ShotType, "llm", used, "ms", time.Since(t0).Milliseconds())
		}
	}

	_ = sub.Unsubscribe()
	_ = nc.Drain()
	shut, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = srv.Shutdown(shut)
	log.Info("director.stop")
	return 0
}
