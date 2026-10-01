package newsroom

// crew#987 CP6 phase 1b: flux/deploy on the newsroom, and its freshness SLO.
//
// The ImageUpdateAutomation `deploy` (platform/image-automation/deploy.yaml) rebuilds
// flux/deploy from main plus the current image tags. Two facts about it go on the board:
//
//   flux.pushed  every time it writes flux/deploy (status.lastPushCommit moves).
//   flux.stale   the SLO breach: main's head, as the idp-writer GitRepository sees it, has not
//                been built by the automation (status.observedSourceRevision) within StaleAfter.
//                A stale flux/deploy means main is not deploying. flux.fresh closes it.
//
// StaleAfter defaults to 10m, measured 2026-09-30: GitHub delivered 100 of 100 webhook pushes
// with p99 1.31s, and 1514 automation reconciles since 2026-09-26 took p50 <=40s with 89% <=60s
// (controller_runtime_reconcile_time_seconds). A missed webhook falls back to the automation's
// 5m interval plus one run, about 7m; past 10m both the webhook and the backstop have failed.

import (
	"context"
	"encoding/json"
	"strings"
	"sync"
	"time"
)

const (
	ImageUpdateAutomationsPath = "/apis/image.toolkit.fluxcd.io/v1/imageupdateautomations"
	GitRepositoriesPath        = "/apis/source.toolkit.fluxcd.io/v1/gitrepositories"
)

// DeployBranch holds the two revisions the SLO compares. Both watches write it; Check reads it.
type DeployBranch struct {
	Automation string        // ImageUpdateAutomation name, "deploy"
	Source     string        // GitRepository tracking main, "idp-writer"
	Namespace  string        // "flux-system"
	StaleAfter time.Duration // the SLO

	mu       sync.Mutex
	main     string    // main's head sha, from Source
	mainAt   time.Time // when that head was first seen
	built    string    // the main sha the automation last built from
	stale    bool
	lastPush string
}

// sha takes "main@sha1:<hex>" (Flux's revision format) or a bare sha to the bare sha.
func sha(rev string) string {
	if i := strings.LastIndex(rev, ":"); i >= 0 {
		return rev[i+1:]
	}
	return rev
}

func short(s string) string {
	if len(s) > 7 {
		return s[:7]
	}
	return s
}

type objMeta struct {
	Name      string `json:"name"`
	Namespace string `json:"namespace"`
}

// automationMapper watches ImageUpdateAutomations and reports each new push of the one it owns.
type automationMapper struct {
	d     *DeployBranch
	since time.Duration
}

func (m *automationMapper) seen(obj json.RawMessage, src source, now time.Time) (Raw, bool) {
	var a struct {
		Metadata objMeta `json:"metadata"`
		Spec     struct {
			Git struct {
				Push struct {
					Branch string `json:"branch"`
				} `json:"push"`
			} `json:"git"`
		} `json:"spec"`
		Status struct {
			LastPushCommit         string `json:"lastPushCommit"`
			LastPushTime           string `json:"lastPushTime"`
			ObservedSourceRevision string `json:"observedSourceRevision"`
		} `json:"status"`
	}
	if json.Unmarshal(obj, &a) != nil || a.Metadata.Name != m.d.Automation || a.Metadata.Namespace != m.d.Namespace {
		return Raw{}, false
	}
	d := m.d
	d.mu.Lock()
	defer d.mu.Unlock()
	if a.Status.ObservedSourceRevision != "" {
		d.built = sha(a.Status.ObservedSourceRevision)
	}
	commit := a.Status.LastPushCommit
	if commit == "" || commit == d.lastPush {
		return Raw{}, false
	}
	first := d.lastPush == ""
	d.lastPush = commit
	at := now
	if t, err := time.Parse(time.RFC3339, a.Status.LastPushTime); err == nil {
		at = t
	}
	if first && src == firstList && now.Sub(at) > m.since {
		return Raw{}, false
	}
	branch := a.Spec.Git.Push.Branch
	return Raw{
		Source: "flux", Kind: "flux.pushed", Severity: "info",
		Entity: "ImageUpdateAutomation/" + d.Namespace + "/" + d.Automation,
		Name:   d.Automation, Namespace: d.Namespace,
		Reason: short(commit), Message: "pushed " + short(commit) + " to " + branch + " from main " + short(d.built),
		At: at,
	}, true
}

// sourceMapper watches GitRepositories and records main's head from the one it owns.
type sourceMapper struct{ d *DeployBranch }

func (m *sourceMapper) seen(obj json.RawMessage, _ source, now time.Time) (Raw, bool) {
	var g struct {
		Metadata objMeta `json:"metadata"`
		Status   struct {
			Artifact struct {
				Revision       string `json:"revision"`
				LastUpdateTime string `json:"lastUpdateTime"`
			} `json:"artifact"`
		} `json:"status"`
	}
	if json.Unmarshal(obj, &g) != nil || g.Metadata.Name != m.d.Source || g.Metadata.Namespace != m.d.Namespace {
		return Raw{}, false
	}
	rev := sha(g.Status.Artifact.Revision)
	if rev == "" {
		return Raw{}, false
	}
	d := m.d
	d.mu.Lock()
	defer d.mu.Unlock()
	if rev != d.main {
		d.main, d.mainAt = rev, now
		if t, err := time.Parse(time.RFC3339, g.Status.Artifact.LastUpdateTime); err == nil && t.Before(now) {
			d.mainAt = t
		}
	}
	return Raw{}, false
}

// Check applies the SLO at now: a breach opens flux.stale, catching up closes it with flux.fresh.
func (d *DeployBranch) Check(now time.Time) (Raw, bool) {
	d.mu.Lock()
	defer d.mu.Unlock()
	if d.main == "" {
		return Raw{}, false
	}
	entity := "ImageUpdateAutomation/" + d.Namespace + "/" + d.Automation
	behind := d.built != d.main
	if behind && !d.stale && now.Sub(d.mainAt) > d.StaleAfter {
		d.stale = true
		lag := now.Sub(d.mainAt).Round(time.Minute)
		return Raw{
			Source: "flux", Kind: "flux.stale", Severity: "danger",
			Entity: entity, Name: d.Automation, Namespace: d.Namespace,
			Reason:  lag.String(),
			Message: "main " + short(d.main) + " not on flux/deploy after " + lag.String() + " (last built main " + short(d.built) + ")",
			At:      now,
		}, true
	}
	if !behind && d.stale {
		d.stale = false
		return Raw{
			Source: "flux", Kind: "flux.fresh", Severity: "info",
			Entity: entity, Name: d.Automation, Namespace: d.Namespace,
			Reason: short(d.main), Message: "flux/deploy carries main " + short(d.main) + " again",
			At: now,
		}, true
	}
	return Raw{}, false
}

// Run watches both objects and applies the SLO every tick.
func (d *DeployBranch) Run(ctx context.Context, k *Kube, since, tick time.Duration, out chan<- Raw) {
	go k.watch(ctx, ImageUpdateAutomationsPath, &automationMapper{d: d, since: since}, out)
	go k.watch(ctx, GitRepositoriesPath, &sourceMapper{d: d}, out)
	t := time.NewTicker(tick)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			if r, ok := d.Check(k.Now()); ok && !send(ctx, out, r) {
				return
			}
		}
	}
}
