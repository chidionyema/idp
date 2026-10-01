package main

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"os"
	"time"

	"github.com/nats-io/nats.go"

	"github.com/chidionyema/idp/platform/voice-router/internal/brain"
	"github.com/chidionyema/idp/platform/voice-router/internal/newsroom"
)

const (
	newsStream   = "ESTATE_NEWS"
	newsSubjects = "estate.news.>"
	feedRetry    = 60 * time.Second
)

var epistemicSubjects = []string{newsroom.SubjectCICD, newsroom.SubjectIncidents}

func newsStreamConfig() *nats.StreamConfig {
	return &nats.StreamConfig{
		Name:      newsStream,
		Subjects:  []string{newsSubjects},
		Storage:   nats.FileStorage,
		Retention: nats.LimitsPolicy,
		MaxAge:    24 * time.Hour,
		MaxMsgs:   5000,
		MaxBytes:  10 << 20,
		Replicas:  1,
	}
}

func ensureNewsStream(js nats.JetStreamManager) error {
	cfg := newsStreamConfig()
	_, err := js.AddStream(cfg)
	if errors.Is(err, nats.ErrStreamNameAlreadyInUse) {
		_, err = js.UpdateStream(cfg)
	}
	return err
}

func subscribeRetry(ctx context.Context, log *slog.Logger, js nats.JetStreamContext, subj, absent string, h nats.MsgHandler) {
	for {
		sub, err := js.Subscribe(subj, h, nats.OrderedConsumer(), nats.DeliverNew())
		if err == nil {
			log.Info("director.feed_attached", "subject", subj)
			<-ctx.Done()
			sub.Unsubscribe()
			return
		}
		log.Warn(absent, "subject", subj, "err", err, "retry_s", int(feedRetry.Seconds()))
		select {
		case <-ctx.Done():
			return
		case <-time.After(feedRetry):
		}
	}
}

func runNewsroom(ctx context.Context, log *slog.Logger, nc *nats.Conn, js nats.JetStreamContext) {
	if err := ensureNewsStream(js); err != nil {
		log.Warn("newsroom.stream", "err", err)
	}

	raws := make(chan newsroom.Raw, 256)

	if kube, err := newsroom.InCluster(log); err != nil {
		log.Warn("newsroom.kube_absent", "err", err)
	} else {
		go kube.Run(ctx, raws)
		// crew#987 CP6: flux/deploy's pushes and its freshness SLO (internal/newsroom/deploybranch.go).
		staleAfter, err := time.ParseDuration(env("DEPLOY_STALE_AFTER", "10m"))
		if err != nil {
			staleAfter = 10 * time.Minute
		}
		deploy := &newsroom.DeployBranch{
			Automation: env("DEPLOY_AUTOMATION", "deploy"),
			Source:     env("DEPLOY_MAIN_SOURCE", "idp-writer"),
			Namespace:  "flux-system",
			StaleAfter: staleAfter,
		}
		go deploy.Run(ctx, kube, time.Hour, 30*time.Second, raws)
	}

	for _, subj := range epistemicSubjects {
		s := subj
		go subscribeRetry(ctx, log, js, s, "newsroom.feed_absent", func(m *nats.Msg) {
			r, ok := newsroom.DecodeEpistemic(s, m.Data, time.Now())
			if !ok {
				return
			}
			select {
			case raws <- r:
			default:
				log.Warn("newsroom.drop", "subject", s)
			}
		})
	}

	// Without a router key the router refuses the call, so the anchor desk stays on templates.
	var anchor *newsroom.Anchor
	if os.Getenv("LLM_API_KEY") != "" {
		anchor = &newsroom.Anchor{Brain: brain.NarrateFromEnv()}
	} else {
		log.Info("newsroom.anchor_template_only", "reason", "LLM_API_KEY unset")
	}

	ed := newsroom.NewEditor()
	for {
		select {
		case <-ctx.Done():
			return
		case r := <-raws:
			s, ok := ed.Ingest(r, time.Now())
			if !ok {
				continue
			}
			s, byLLM := anchor.Voice(ctx, s, time.Now())
			b, _ := json.Marshal(s)
			for _, subj := range newsroom.Subjects(s) {
				if err := nc.Publish(subj, b); err != nil {
					log.Warn("newsroom.publish", "subject", subj, "err", err)
				}
			}
			log.Info("news.story", "id", s.ID, "channel", s.Channel, "severity", s.Severity, "state", s.State, "breaking", s.Breaking, "anchor_by", anchorBy(byLLM), "headline", s.Headline)
		}
	}
}

func anchorBy(llm bool) string {
	if llm {
		return "llm"
	}
	return "template"
}
