package newsroom

import (
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

func writeTokenFile(t *testing.T) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "token")
	if err := os.WriteFile(path, []byte("tok\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

func isWatch(r *http.Request) bool {
	return r.URL.Query().Get("watch") != ""
}

func drain(t *testing.T, ch <-chan Raw, n int) []Raw {
	t.Helper()
	out := make([]Raw, 0, n)
	timeout := time.After(2 * time.Second)
	for len(out) < n {
		select {
		case r := <-ch:
			out = append(out, r)
		case <-timeout:
			t.Fatalf("timed out waiting for %d events, got %d: %+v", n, len(out), out)
		}
	}
	return out
}

func drainNone(t *testing.T, ch <-chan Raw, d time.Duration) {
	t.Helper()
	select {
	case r := <-ch:
		t.Fatalf("expected no event, got %+v", r)
	case <-time.After(d):
	}
}

func TestKubeReplaysOnlyTheLastHour(t *testing.T) {
	now := time.Date(2026, 9, 27, 12, 0, 0, 0, time.UTC)
	old := now.Add(-2 * time.Hour).Format(time.RFC3339Nano)
	recent := now.Add(-10 * time.Minute).Format(time.RFC3339Nano)

	eventsList := fmt.Sprintf(`{"metadata":{"resourceVersion":"1"},"items":[
		{"type":"Warning","reason":"OldThing","message":"old warning","lastTimestamp":%q,"involvedObject":{"kind":"Pod","namespace":"mcp","name":"old-pod"}},
		{"type":"Warning","reason":"RecentThing","message":"recent warning","lastTimestamp":%q,"involvedObject":{"kind":"Pod","namespace":"mcp","name":"recent-pod"}}
	]}`, old, recent)

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api/v1/events":
			if isWatch(r) {
				<-r.Context().Done()
				return
			}
			w.Write([]byte(eventsList))
		case "/apis/kustomize.toolkit.fluxcd.io/v1/kustomizations":
			if isWatch(r) {
				<-r.Context().Done()
				return
			}
			w.Write([]byte(`{"metadata":{"resourceVersion":"1"},"items":[]}`))
		case "/apis/helm.toolkit.fluxcd.io/v2/helmreleases":
			if isWatch(r) {
				<-r.Context().Done()
				return
			}
			w.Write([]byte(`{"metadata":{"resourceVersion":"1"},"items":[]}`))
		}
	}))
	defer srv.Close()

	k := &Kube{
		Host:      srv.URL,
		TokenFile: writeTokenFile(t),
		HTTP:      srv.Client(),
		Backoff:   10 * time.Millisecond,
		Now:       func() time.Time { return now },
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	out := make(chan Raw, 16)
	go k.Run(ctx, out)

	got := drain(t, out, 1)
	if got[0].Kind != "k8s.warning" || got[0].Name != "recent-pod" {
		t.Fatalf("unexpected event: %+v", got[0])
	}
	drainNone(t, out, 100*time.Millisecond)
}

func TestKubeMapsACrashloop(t *testing.T) {
	now := time.Now()

	watchLine := `{"type":"ADDED","object":{"type":"Warning","reason":"BackOff","message":"Back-off restarting failed container api in pod api-7f","lastTimestamp":"` + now.Format(time.RFC3339Nano) + `","involvedObject":{"kind":"Pod","namespace":"mcp","name":"api-7f"}}}` + "\n"

	var watchServed atomic.Bool

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/api/v1/events":
			if isWatch(r) {
				if watchServed.CompareAndSwap(false, true) {
					w.Write([]byte(watchLine))
					return
				}
				<-r.Context().Done()
				return
			}
			w.Write([]byte(`{"metadata":{"resourceVersion":"1"},"items":[]}`))
		default:
			if isWatch(r) {
				<-r.Context().Done()
				return
			}
			w.Write([]byte(`{"metadata":{"resourceVersion":"1"},"items":[]}`))
		}
	}))
	defer srv.Close()

	k := &Kube{
		Host:      srv.URL,
		TokenFile: writeTokenFile(t),
		HTTP:      srv.Client(),
		Backoff:   10 * time.Millisecond,
		Now:       func() time.Time { return now },
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	out := make(chan Raw, 16)
	go k.Run(ctx, out)

	got := drain(t, out, 1)
	if got[0].Kind != "k8s.crashloop" || got[0].Severity != "danger" || got[0].Entity != "Pod/mcp/api-7f" {
		t.Fatalf("unexpected event: %+v", got[0])
	}
}

func TestFluxEmitsOnlyOnTransitions(t *testing.T) {
	now := time.Date(2026, 9, 27, 12, 0, 0, 0, time.UTC)
	oldTransition := now.Add(-3 * time.Hour).Format(time.RFC3339Nano)

	kustList := fmt.Sprintf(`{"metadata":{"resourceVersion":"1"},"items":[
		{"metadata":{"name":"ns-fences","namespace":"flux-system"},"status":{"lastAppliedRevision":"A","conditions":[{"type":"Ready","status":"True","lastTransitionTime":%q}]}}
	]}`, oldTransition)

	lines := []string{
		fmt.Sprintf(`{"type":"MODIFIED","object":{"metadata":{"name":"ns-fences","namespace":"flux-system"},"status":{"lastAppliedRevision":"A","conditions":[{"type":"Ready","status":"True","lastTransitionTime":%q}]}}}`, now.Format(time.RFC3339Nano)),
		fmt.Sprintf(`{"type":"MODIFIED","object":{"metadata":{"name":"ns-fences","namespace":"flux-system"},"status":{"lastAppliedRevision":"B","conditions":[{"type":"Ready","status":"True","lastTransitionTime":%q}]}}}`, now.Format(time.RFC3339Nano)),
		fmt.Sprintf(`{"type":"MODIFIED","object":{"metadata":{"name":"ns-fences","namespace":"flux-system"},"status":{"lastAppliedRevision":"B","conditions":[{"type":"Ready","status":"False","reason":"BuildFailed","message":"build failed","lastTransitionTime":%q}]}}}`, now.Format(time.RFC3339Nano)),
	}
	watchBody := strings.Join(lines, "\n") + "\n"

	var watchServed atomic.Bool

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/apis/kustomize.toolkit.fluxcd.io/v1/kustomizations":
			if isWatch(r) {
				if watchServed.CompareAndSwap(false, true) {
					w.Write([]byte(watchBody))
					return
				}
				<-r.Context().Done()
				return
			}
			w.Write([]byte(kustList))
		default:
			if isWatch(r) {
				<-r.Context().Done()
				return
			}
			w.Write([]byte(`{"metadata":{"resourceVersion":"1"},"items":[]}`))
		}
	}))
	defer srv.Close()

	k := &Kube{
		Host:      srv.URL,
		TokenFile: writeTokenFile(t),
		HTTP:      srv.Client(),
		Backoff:   10 * time.Millisecond,
		Now:       func() time.Time { return now },
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	out := make(chan Raw, 16)
	go k.Run(ctx, out)

	got := drain(t, out, 2)
	if got[0].Kind != "flux.deployed" || got[0].Reason != "B" {
		t.Fatalf("unexpected first event: %+v", got[0])
	}
	if got[1].Kind != "flux.failed" || got[1].Reason != "BuildFailed" {
		t.Fatalf("unexpected second event: %+v", got[1])
	}
}

func TestKubeRelistsOnGone(t *testing.T) {
	var kustListCount atomic.Int64

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/apis/kustomize.toolkit.fluxcd.io/v1/kustomizations":
			if isWatch(r) {
				w.WriteHeader(http.StatusGone)
				return
			}
			kustListCount.Add(1)
			w.Write([]byte(`{"metadata":{"resourceVersion":"1"},"items":[]}`))
		default:
			if isWatch(r) {
				<-r.Context().Done()
				return
			}
			w.Write([]byte(`{"metadata":{"resourceVersion":"1"},"items":[]}`))
		}
	}))
	defer srv.Close()

	k := &Kube{
		Host:      srv.URL,
		TokenFile: writeTokenFile(t),
		HTTP:      srv.Client(),
		Backoff:   10 * time.Millisecond,
		Now:       time.Now,
	}

	ctx, cancel := context.WithCancel(context.Background())
	out := make(chan Raw, 16)
	go k.Run(ctx, out)

	deadline := time.After(2 * time.Second)
	for {
		if kustListCount.Load() >= 2 {
			break
		}
		select {
		case <-deadline:
			t.Fatalf("expected list to be hit at least twice, got %d", kustListCount.Load())
		case <-time.After(10 * time.Millisecond):
		}
	}
	cancel()
}

func TestKubeSendsTheToken(t *testing.T) {
	var gotAuth atomic.Value
	gotAuth.Store("")

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotAuth.Store(r.Header.Get("Authorization"))
		if isWatch(r) {
			<-r.Context().Done()
			return
		}
		w.Write([]byte(`{"metadata":{"resourceVersion":"1"},"items":[]}`))
	}))
	defer srv.Close()

	k := &Kube{
		Host:      srv.URL,
		TokenFile: writeTokenFile(t),
		HTTP:      srv.Client(),
		Backoff:   10 * time.Millisecond,
		Now:       time.Now,
	}

	ctx, cancel := context.WithCancel(context.Background())
	out := make(chan Raw, 16)
	go k.Run(ctx, out)

	deadline := time.After(2 * time.Second)
	for {
		if v := gotAuth.Load().(string); v != "" {
			if v != "Bearer tok" {
				t.Fatalf("unexpected auth header: %q", v)
			}
			break
		}
		select {
		case <-deadline:
			t.Fatal("timed out waiting for request")
		case <-time.After(10 * time.Millisecond):
		}
	}
	cancel()
}

func TestEveryRunOfACronJobIsOneEntity(t *testing.T) {
	for _, c := range []struct{ kind, name, wantKind, wantName string }{
		{"Job", "front-door-heartbeat-29841635", "CronJob", "front-door-heartbeat"},
		{"Pod", "spiffe-proof-29841645-zjz42", "CronJob", "spiffe-proof"},
		{"Pod", "coroot-549554db7f-pd45b", "Pod", "coroot-549554db7f-pd45b"},
		{"HelmRelease", "dagster", "HelmRelease", "dagster"},
	} {
		k, n := owner(c.kind, c.name)
		if k != c.wantKind || n != c.wantName {
			t.Errorf("owner(%s, %s) = %s/%s, want %s/%s", c.kind, c.name, k, n, c.wantKind, c.wantName)
		}
	}
}
