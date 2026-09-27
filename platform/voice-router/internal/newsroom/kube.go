package newsroom

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

const (
	EventsPath         = "/api/v1/events?fieldSelector=type%3DWarning"
	KustomizationsPath = "/apis/kustomize.toolkit.fluxcd.io/v1/kustomizations"
	HelmReleasesPath   = "/apis/helm.toolkit.fluxcd.io/v2/helmreleases"
	saDir              = "/var/run/secrets/kubernetes.io/serviceaccount"
	maxWatchBackoff    = 30 * time.Second
)

type Kube struct {
	Host      string
	TokenFile string
	HTTP      *http.Client
	Log       *slog.Logger
	Since     time.Duration
	Backoff   time.Duration
	Now       func() time.Time
}

func InCluster(log *slog.Logger) (*Kube, error) {
	host, port := os.Getenv("KUBERNETES_SERVICE_HOST"), os.Getenv("KUBERNETES_SERVICE_PORT")
	if host == "" || port == "" {
		return nil, fmt.Errorf("newsroom: KUBERNETES_SERVICE_HOST/PORT not set")
	}
	ca, err := os.ReadFile(saDir + "/ca.crt")
	if err != nil {
		return nil, fmt.Errorf("newsroom: read ca.crt: %w", err)
	}
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(ca) {
		return nil, fmt.Errorf("newsroom: parse ca.crt: no certificates found")
	}
	tr := &http.Transport{TLSClientConfig: &tls.Config{RootCAs: pool, MinVersion: tls.VersionTLS12}}
	return &Kube{Host: "https://" + net.JoinHostPort(host, port), HTTP: &http.Client{Transport: tr}, Log: log, TokenFile: saDir + "/token"}, nil
}

func (k *Kube) Run(ctx context.Context, out chan<- Raw) {
	if k.Since == 0 {
		k.Since = time.Hour
	}
	if k.Backoff == 0 {
		k.Backoff = time.Second
	}
	if k.Now == nil {
		k.Now = time.Now
	}
	if k.HTTP == nil {
		k.HTTP = http.DefaultClient
	}
	if k.Log == nil {
		k.Log = slog.Default()
	}
	go k.watch(ctx, EventsPath, &eventMapper{since: k.Since}, out)
	go k.watch(ctx, KustomizationsPath, &fluxMapper{kind: "Kustomization", since: k.Since, state: map[string]fluxState{}}, out)
	go k.watch(ctx, HelmReleasesPath, &fluxMapper{kind: "HelmRelease", since: k.Since, state: map[string]fluxState{}}, out)
	<-ctx.Done()
}

type source int

const (
	firstList source = iota
	relist
	watched
)

type mapper interface {
	seen(obj json.RawMessage, src source, now time.Time) (Raw, bool)
}

func (k *Kube) get(ctx context.Context, u string) (*http.Response, error) {
	tok, err := os.ReadFile(k.TokenFile)
	if err != nil {
		return nil, fmt.Errorf("newsroom: read token: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+strings.TrimSpace(string(tok)))
	req.Header.Set("Accept", "application/json")
	return k.HTTP.Do(req)
}

func (k *Kube) list(ctx context.Context, path string) (string, []json.RawMessage, error) {
	resp, err := k.get(ctx, k.Host+path)
	if err != nil {
		return "", nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", nil, fmt.Errorf("list %s: HTTP %d", path, resp.StatusCode)
	}
	var body struct {
		Metadata struct {
			ResourceVersion string `json:"resourceVersion"`
		} `json:"metadata"`
		Items []json.RawMessage `json:"items"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		return "", nil, err
	}
	return body.Metadata.ResourceVersion, body.Items, nil
}

func resourceVersion(obj json.RawMessage) (string, error) {
	var meta struct {
		Metadata struct {
			ResourceVersion string `json:"resourceVersion"`
		} `json:"metadata"`
	}
	err := json.Unmarshal(obj, &meta)
	return meta.Metadata.ResourceVersion, err
}

func (k *Kube) watchOnce(ctx context.Context, path, rv string, m mapper, out chan<- Raw) (string, bool, error) {
	sep := "?"
	if strings.Contains(path, "?") {
		sep = "&"
	}
	u := k.Host + path + sep + "watch=1&allowWatchBookmarks=true&timeoutSeconds=300&resourceVersion=" + url.QueryEscape(rv)
	resp, err := k.get(ctx, u)
	if err != nil {
		return rv, false, err
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusGone {
		return rv, true, nil
	}
	if resp.StatusCode != http.StatusOK {
		return rv, false, fmt.Errorf("watch %s: HTTP %d", path, resp.StatusCode)
	}

	dec := json.NewDecoder(resp.Body)
	for {
		var ev struct {
			Type   string          `json:"type"`
			Object json.RawMessage `json:"object"`
		}
		if err := dec.Decode(&ev); err != nil {
			if err == io.EOF {
				return rv, false, nil
			}
			return rv, false, err
		}
		if ev.Type == "ERROR" {
			var errObj struct {
				Code int `json:"code"`
			}
			if err := json.Unmarshal(ev.Object, &errObj); err != nil {
				return rv, false, err
			}
			if errObj.Code == http.StatusGone {
				return rv, true, nil
			}
			return rv, false, fmt.Errorf("watch %s: error code %d", path, errObj.Code)
		}
		newRV, err := resourceVersion(ev.Object)
		if err != nil {
			return rv, false, err
		}
		rv = newRV
		if ev.Type != "ADDED" && ev.Type != "MODIFIED" {
			continue
		}
		if r, ok := m.seen(ev.Object, watched, k.Now()); ok && !send(ctx, out, r) {
			return rv, false, nil
		}
	}
}

func send(ctx context.Context, out chan<- Raw, r Raw) bool {
	select {
	case out <- r:
		return true
	case <-ctx.Done():
		return false
	}
}

// backoffSleep sleeps for *delay, doubling it up to maxWatchBackoff, and reports whether ctx is still live.
func backoffSleep(ctx context.Context, delay *time.Duration) bool {
	t := time.NewTimer(*delay)
	defer t.Stop()
	select {
	case <-t.C:
	case <-ctx.Done():
		return false
	}
	*delay *= 2
	if *delay > maxWatchBackoff {
		*delay = maxWatchBackoff
	}
	return true
}

func (k *Kube) watch(ctx context.Context, path string, m mapper, out chan<- Raw) {
	delay := k.Backoff
	first := true
	for ctx.Err() == nil {
		rv, items, err := k.list(ctx, path)
		if err != nil {
			k.Log.Warn("newsroom.kube_error", "path", path, "err", err)
			if !backoffSleep(ctx, &delay) {
				return
			}
			continue
		}
		delay = k.Backoff
		src := relist
		if first {
			src = firstList
		}
		first = false
		now := k.Now()
		for _, item := range items {
			if r, ok := m.seen(item, src, now); ok && !send(ctx, out, r) {
				return
			}
		}
		for ctx.Err() == nil {
			newRV, gone, err := k.watchOnce(ctx, path, rv, m, out)
			rv = newRV
			if ctx.Err() != nil {
				return
			}
			if gone {
				break
			}
			if err != nil {
				k.Log.Warn("newsroom.kube_error", "path", path, "err", err)
				if !backoffSleep(ctx, &delay) {
					return
				}
				continue
			}
			delay = k.Backoff
		}
	}
}

type eventMapper struct{ since time.Duration }

func (e *eventMapper) seen(obj json.RawMessage, src source, now time.Time) (Raw, bool) {
	var ev struct {
		Type          string `json:"type"`
		Reason        string `json:"reason"`
		Message       string `json:"message"`
		LastTimestamp string `json:"lastTimestamp"`
		EventTime     string `json:"eventTime"`
		Metadata      struct {
			Namespace         string `json:"namespace"`
			CreationTimestamp string `json:"creationTimestamp"`
		} `json:"metadata"`
		InvolvedObject struct {
			Kind      string `json:"kind"`
			Namespace string `json:"namespace"`
			Name      string `json:"name"`
		} `json:"involvedObject"`
	}
	if err := json.Unmarshal(obj, &ev); err != nil || ev.Type != "Warning" {
		return Raw{}, false
	}

	at := now
	for _, ts := range []string{ev.LastTimestamp, ev.EventTime, ev.Metadata.CreationTimestamp} {
		if ts == "" {
			continue
		}
		if parsed, err := time.Parse(time.RFC3339Nano, ts); err == nil {
			at = parsed
			break
		}
	}
	if src == relist || (src == firstList && now.Sub(at) > e.since) {
		return Raw{}, false
	}

	ns := ev.InvolvedObject.Namespace
	if ns == "" {
		ns = ev.Metadata.Namespace
	}
	kind, severity := "k8s.warning", "warn"
	if ev.Reason == "BackOff" && strings.Contains(ev.Message, "restarting failed container") {
		kind, severity = "k8s.crashloop", "danger"
	}
	return Raw{
		Source: "k8s", Kind: kind, Severity: severity,
		Entity: ev.InvolvedObject.Kind + "/" + ns + "/" + ev.InvolvedObject.Name,
		Name:   ev.InvolvedObject.Name, Namespace: ns,
		Reason: ev.Reason, Message: ev.Message, At: at,
	}, true
}

type fluxState struct{ ready, rev string }

type fluxMapper struct {
	kind  string
	since time.Duration
	state map[string]fluxState
}

type fluxCondition struct {
	Type               string `json:"type"`
	Status             string `json:"status"`
	Reason             string `json:"reason"`
	Message            string `json:"message"`
	LastTransitionTime string `json:"lastTransitionTime"`
}

func (f *fluxMapper) seen(obj json.RawMessage, src source, now time.Time) (Raw, bool) {
	var res struct {
		Metadata struct {
			Name      string `json:"name"`
			Namespace string `json:"namespace"`
		} `json:"metadata"`
		Status struct {
			LastAppliedRevision   string          `json:"lastAppliedRevision"`
			LastAttemptedRevision string          `json:"lastAttemptedRevision"`
			Conditions            []fluxCondition `json:"conditions"`
		} `json:"status"`
	}
	if err := json.Unmarshal(obj, &res); err != nil {
		return Raw{}, false
	}

	var cond *fluxCondition
	for i := range res.Status.Conditions {
		if res.Status.Conditions[i].Type == "Ready" {
			cond = &res.Status.Conditions[i]
			break
		}
	}
	if cond == nil || (cond.Status != "True" && cond.Status != "False") {
		return Raw{}, false
	}

	rev := res.Status.LastAppliedRevision
	if rev == "" {
		rev = res.Status.LastAttemptedRevision
	}
	ns, name := res.Metadata.Namespace, res.Metadata.Name
	key := ns + "/" + name

	at := now
	if parsed, err := time.Parse(time.RFC3339Nano, cond.LastTransitionTime); err == nil {
		at = parsed
	}

	prev, had := f.state[key]
	f.state[key] = fluxState{ready: cond.Status, rev: rev}
	if !had {
		if src == firstList && now.Sub(at) > f.since {
			return Raw{}, false
		}
	} else if (cond.Status == "True" && prev.ready == "True" && prev.rev == rev) ||
		(cond.Status == "False" && prev.ready == "False") {
		return Raw{}, false
	}

	r := Raw{Source: "flux", Entity: f.kind + "/" + ns + "/" + name, Name: name, Namespace: ns, At: at}
	if cond.Status == "True" {
		r.Kind, r.Severity, r.Reason, r.Message = "flux.deployed", "info", rev, cond.Message
	} else {
		r.Kind, r.Severity, r.Reason, r.Message = "flux.failed", "warn", cond.Reason, cond.Message
	}
	return r, true
}
