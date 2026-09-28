// Command negative-constraints-proxy is Primitive A of the via-negativa engine
// (docs/specs/2026-09-13-via-negativa-engine.md): a reverse proxy in front of
// the LLM gateway that pre-flight rejects tool calls matching a known-bad
// signature, instead of letting the model burn a turn on a failure it has
// already made before.
//
// Contract proved by tests/test_via_negativa_engine.py:
//   - go build -o <bin> . must succeed with zero external modules (no network
//     access assumed at build time in CI), so the Redis client here is a
//     ~40-line hand-rolled RESP client, not a fetched dependency.
//   - a tool_call whose name matches a banned signature gets HTTP 422 and
//     never reaches the upstream.
//   - REDIS_URL unreachable must fail OPEN: the proxy keeps serving using
//     whatever pattern set it last had (built-ins at minimum), it never
//     blocks the whole pipeline because the ledger is down.
package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

// builtinSignatures are the deterministic, non-negotiable bans (Primitive B):
// no RCA run has to teach the proxy these, they ship with it.
var builtinSignatures = []string{
	"rm_rf",
	"rm -rf /",
	"drop table",
	"drop database",
	":(){ :|:& };:",
	"git push --force origin main",
	"git reset --hard",
}

// normalizeRe strips dynamic args (paths, timestamps, UUIDs, hex ids) before
// matching, per the spec's "regex normalization" edge case -- otherwise every
// distinct tmp path or timestamp mints a "new" signature that never repeats.
var normalizeRe = []*regexp.Regexp{
	regexp.MustCompile(`[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}`), // uuid
	regexp.MustCompile(`\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?`),         // timestamp
	regexp.MustCompile(`/[\w./-]+`),            // paths
	regexp.MustCompile(`\b[0-9a-fA-F]{12,}\b`), // long hex ids
	regexp.MustCompile(`\s+`),                  // collapse whitespace
}

func normalize(s string) string {
	s = strings.ToLower(s)
	for _, re := range normalizeRe {
		s = re.ReplaceAllString(s, " ")
	}
	return strings.TrimSpace(s)
}

// patternStore holds the live banned-signature set (Primitive A/B) and the
// top-N negative-constraint summaries the RCA worker (Primitive D) has
// ranked by failure_count (Primitive C, injected into the outbound prompt
// below). Reads never block on Redis -- refresh() is best-effort per field
// and a failure on either just keeps that field's old value.
type patternStore struct {
	mu          sync.RWMutex
	patterns    []string
	constraints []string
}

func newPatternStore() *patternStore {
	return &patternStore{patterns: append([]string(nil), builtinSignatures...)}
}

func (p *patternStore) match(s string) (bool, string) {
	norm := normalize(s)
	p.mu.RLock()
	defer p.mu.RUnlock()
	for _, sig := range p.patterns {
		if sig != "" && strings.Contains(norm, normalize(sig)) {
			return true, sig
		}
	}
	return false, ""
}

func (p *patternStore) topConstraints() []string {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return append([]string(nil), p.constraints...)
}

func (p *patternStore) refresh(redisURL, redisKey, constraintsKey string, topN int, timeout time.Duration) {
	learned, err := redisSMembers(redisURL, redisKey, timeout)
	if err != nil {
		log.Printf("fail-open: redis refresh skipped (%v) -- serving %d cached signatures", err, len(p.patterns))
	} else {
		merged := append([]string(nil), builtinSignatures...)
		merged = append(merged, learned...)
		p.mu.Lock()
		p.patterns = merged
		p.mu.Unlock()
		log.Printf("refreshed pattern set: %d built-in + %d learned", len(builtinSignatures), len(learned))
	}

	constraints, err := redisZRevRange(redisURL, constraintsKey, topN, timeout)
	if err != nil {
		log.Printf("fail-open: constraint refresh skipped (%v) -- serving %d cached constraints", err, len(p.constraints))
		return
	}
	p.mu.Lock()
	p.constraints = constraints
	p.mu.Unlock()
}

// redisCommand issues one raw RESP command over a short-timeout TCP
// connection and reads back an array-of-bulk-strings reply. No external
// module: this whole proxy is stdlib-only so `go build .` never touches the
// network.
//
// THE BUG THIS FIXES (measured 2026-09-19). resolveRedisURL folds the mounted
// password into REDIS_URL as url.UserPassword, and that URL is what gets logged
// at startup -- so the line reads `redis://:<pass>@host:6379` and looks correct.
// But this function only ever parsed `u.Host` and dialed it. The userinfo was
// never turned into an AUTH command, so every call below sent SMEMBERS straight
// out and Redis answered `-NOAUTH Authentication required.` The proxy then took
// its own fail-open path and served a frozen cache: 7 built-in signatures and
// zero constraints, every 10 seconds, for four days. The log said `fail-open`
// and named Redis, which read as a Redis-side outage; Redis was healthy the
// whole time and the missing byte was on this side.
//
// A password in a URL is not authentication. It is a string that looks like it.
func redisAuth(conn net.Conn, u *url.URL) error {
	if u.User == nil {
		return nil
	}
	pass, hasPass := u.User.Password()
	if !hasPass {
		return nil
	}
	user := u.User.Username()
	// Redis 6+ wants AUTH <user> <pass>; a URL with no username is the classic
	// AUTH <pass> form and sending an empty first field would be a syntax error.
	args := []string{"AUTH"}
	if user != "" {
		args = append(args, user)
	}
	args = append(args, pass)
	var cmd strings.Builder
	fmt.Fprintf(&cmd, "*%d\r\n", len(args))
	for _, a := range args {
		fmt.Fprintf(&cmd, "$%d\r\n%s\r\n", len(a), a)
	}
	if _, err := conn.Write([]byte(cmd.String())); err != nil {
		return fmt.Errorf("auth write: %w", err)
	}
	r := bufio.NewReader(conn)
	line, err := r.ReadString('\n')
	if err != nil {
		return fmt.Errorf("auth read: %w", err)
	}
	line = strings.TrimRight(line, "\r\n")
	if !strings.HasPrefix(line, "+OK") {
		// Deliberately not fatal to the caller: this proxy's posture is
		// fail-open, and a wrong password should degrade to the frozen
		// cache with a line naming AUTH, not to refusing traffic.
		return fmt.Errorf("AUTH rejected: %q", line)
	}
	return nil
}

func redisCommand(redisURL string, args []string, timeout time.Duration) ([]string, error) {
	u, err := url.Parse(redisURL)
	if err != nil {
		return nil, fmt.Errorf("parse REDIS_URL: %w", err)
	}
	addr := u.Host
	if addr == "" {
		addr = redisURL
	}
	conn, err := net.DialTimeout("tcp", addr, timeout)
	if err != nil {
		return nil, fmt.Errorf("dial: %w", err)
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))

	if err := redisAuth(conn, u); err != nil {
		return nil, err
	}

	var cmd strings.Builder
	fmt.Fprintf(&cmd, "*%d\r\n", len(args))
	for _, a := range args {
		fmt.Fprintf(&cmd, "$%d\r\n%s\r\n", len(a), a)
	}
	if _, err := conn.Write([]byte(cmd.String())); err != nil {
		return nil, fmt.Errorf("write: %w", err)
	}

	r := bufio.NewReader(conn)
	line, err := r.ReadString('\n')
	if err != nil {
		return nil, fmt.Errorf("read reply header: %w", err)
	}
	line = strings.TrimRight(line, "\r\n")
	if len(line) == 0 || line[0] != '*' {
		return nil, fmt.Errorf("unexpected reply: %q", line)
	}
	var n int
	if _, err := fmt.Sscanf(line, "*%d", &n); err != nil {
		return nil, fmt.Errorf("parse array len: %w", err)
	}
	out := make([]string, 0, n)
	for i := 0; i < n; i++ {
		bulkHeader, err := r.ReadString('\n')
		if err != nil {
			return nil, fmt.Errorf("read bulk header: %w", err)
		}
		bulkHeader = strings.TrimRight(bulkHeader, "\r\n")
		var blen int
		if _, err := fmt.Sscanf(bulkHeader, "$%d", &blen); err != nil {
			return nil, fmt.Errorf("parse bulk len: %w", err)
		}
		if blen < 0 {
			continue
		}
		buf := make([]byte, blen+2) // payload + CRLF
		if _, err := io.ReadFull(r, buf); err != nil {
			return nil, fmt.Errorf("read bulk body: %w", err)
		}
		out = append(out, string(buf[:blen]))
	}
	return out, nil
}

// redisSMembers reads the banned-signature set the RCA worker's _persist()
// writes to (Primitive B: SADD of a deterministic signature_regex).
func redisSMembers(redisURL, key string, timeout time.Duration) ([]string, error) {
	return redisCommand(redisURL, []string{"SMEMBERS", key}, timeout)
}

// redisZRevRange reads the top-N constraint summaries by failure_count the
// RCA worker's _persist() ZINCRBYs on every repeat failure (Primitive C).
func redisZRevRange(redisURL, key string, topN int, timeout time.Duration) ([]string, error) {
	if topN < 1 {
		return nil, nil
	}
	return redisCommand(redisURL, []string{"ZREVRANGE", key, "0", strconv.Itoa(topN - 1)}, timeout)
}

// sessionRejectionTracker implements the spec's deadlock-breaker edge case:
// three CONSECUTIVE rejections for the same session/step must force a
// clarification instead of letting the agent keep retrying variations of a
// tool call this proxy has already told it is banned. In-memory and
// per-replica by design -- a session pinned to one pod (the common case
// behind a sticky-session LB) sees it exactly; unpinned traffic sees a
// slightly higher threshold in effect, which is the safe direction to be
// wrong in (a missed break, never a false one) given this pass does not add
// a second shared store for one counter (THE HEADLINE).
type sessionRejectionTracker struct {
	mu     sync.Mutex
	counts map[string]int
}

func newSessionRejectionTracker() *sessionRejectionTracker {
	return &sessionRejectionTracker{counts: make(map[string]int)}
}

const deadlockBreakerThreshold = 3

// recordRejection returns the new consecutive-rejection count for session.
func (t *sessionRejectionTracker) recordRejection(session string) int {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.counts[session]++
	n := t.counts[session]
	if n >= deadlockBreakerThreshold {
		delete(t.counts, session) // the break resets the loop; don't fire again next call
	}
	return n
}

// recordSuccess clears a session's streak: only CONSECUTIVE rejections count.
func (t *sessionRejectionTracker) recordSuccess(session string) {
	t.mu.Lock()
	defer t.mu.Unlock()
	delete(t.counts, session)
}

// sessionKey identifies the caller for the deadlock breaker: an explicit
// header first (what a well-behaved agent harness sets), then the OpenAI
// wire convention's top-level "user" field, then the TCP peer as an honest
// last resort (LAW 46: no silent literal, this is a real fallback and it is
// named as one in the log line that would explain a surprising break).
func sessionKey(r *http.Request, body []byte) string {
	if h := r.Header.Get("X-Via-Negativa-Session"); h != "" {
		return h
	}
	var payload struct {
		User string `json:"user"`
	}
	if json.Unmarshal(body, &payload) == nil && payload.User != "" {
		return payload.User
	}
	return "addr:" + r.RemoteAddr
}

func deadlockBreakerResponse(w http.ResponseWriter, session string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusConflict)
	_ = json.NewEncoder(w).Encode(map[string]string{
		"error": "via_negativa_deadlock_breaker",
		"detail": fmt.Sprintf(
			"%d consecutive tool calls in this session were rejected for known-bad signatures; "+
				"stop retrying variations of the same blocked action and ask the user for "+
				"clarification instead of looping", deadlockBreakerThreshold,
		),
	})
}

// chatMessage is deliberately narrow: only the two fields injectConstraints
// needs to touch. Every other field on the request round-trips untouched
// because injectConstraints edits the "messages" array in place inside a
// map[string]json.RawMessage, never a typed struct of the whole request.
type chatMessage struct {
	Role    string          `json:"role"`
	Content json.RawMessage `json:"content"`
}

// injectConstraints is Primitive C: it prepends (or appends to an existing
// system message) the ranked negative constraints the RCA worker has
// learned, so the model sees "don't do X again" before it ever proposes X.
// Fails open to the original, unmodified body on anything it doesn't
// recognize (no constraints yet, unparseable JSON, or a system message whose
// content isn't a plain string, e.g. multimodal parts) -- Primitive A's own
// ban check still runs regardless, so a skipped injection never widens what
// gets through, it only loses the softer nudge.
func injectConstraints(body []byte, constraints []string) []byte {
	if len(constraints) == 0 {
		return body
	}
	var payload map[string]json.RawMessage
	if json.Unmarshal(body, &payload) != nil {
		return body
	}
	rawMessages, ok := payload["messages"]
	if !ok {
		return body
	}
	var messages []chatMessage
	if json.Unmarshal(rawMessages, &messages) != nil {
		return body
	}

	var addendum strings.Builder
	addendum.WriteString("Known failure patterns to avoid (learned from prior sessions):\n")
	for _, c := range constraints {
		addendum.WriteString("- ")
		addendum.WriteString(c)
		addendum.WriteString("\n")
	}

	if len(messages) > 0 && messages[0].Role == "system" {
		var text string
		if json.Unmarshal(messages[0].Content, &text) != nil {
			return body // non-string system content -- fail open, skip injection
		}
		encoded, err := json.Marshal(text + "\n\n" + addendum.String())
		if err != nil {
			return body
		}
		messages[0].Content = encoded
	} else {
		encoded, err := json.Marshal(addendum.String())
		if err != nil {
			return body
		}
		messages = append([]chatMessage{{Role: "system", Content: encoded}}, messages...)
	}

	newMessages, err := json.Marshal(messages)
	if err != nil {
		return body
	}
	payload["messages"] = newMessages
	out, err := json.Marshal(payload)
	if err != nil {
		return body
	}
	return out
}

// toolCallNames extracts every tool/function name a chat-completions style
// request is proposing to call, so it can be checked against the ban list
// before a single token reaches the model or a shell.
func toolCallNames(body []byte) []string {
	var payload struct {
		Tools []struct {
			Function struct {
				Name string `json:"name"`
			} `json:"function"`
		} `json:"tools"`
		Messages []struct {
			ToolCalls []struct {
				Function struct {
					Name      string `json:"name"`
					Arguments string `json:"arguments"`
				} `json:"function"`
			} `json:"tool_calls"`
		} `json:"messages"`
	}
	if err := json.Unmarshal(body, &payload); err != nil {
		return nil
	}
	var names []string
	for _, t := range payload.Tools {
		if t.Function.Name != "" {
			names = append(names, t.Function.Name)
		}
	}
	for _, m := range payload.Messages {
		for _, tc := range m.ToolCalls {
			if tc.Function.Name != "" {
				names = append(names, tc.Function.Name)
				names = append(names, tc.Function.Arguments)
			}
		}
	}
	return names
}

func rejectResponse(w http.ResponseWriter, signature string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusUnprocessableEntity)
	_ = json.NewEncoder(w).Encode(map[string]string{
		"error":     "via_negativa_rejected",
		"signature": signature,
		"detail":    "this tool call matches a known-bad signature and was blocked before reaching the model",
	})
}

// resolveRedisURL reads REDIS_URL as-is, unless REDIS_PASSWORD_FILE names a mounted secret
// file (Kyverno secrets-not-from-env-vars: the password never rides a pod env var, and the
// distroless image this binary ships in has no shell to compose the URL before exec, so the
// binary does it itself). A missing or unreadable file is logged and the URL is left
// unauthenticated -- consistent with this proxy's existing fail-open posture: a store refresh
// that then fails to authenticate degrades to an empty pattern set, never to refusing traffic.
func resolveRedisURL(raw string) string {
	path := getenv("REDIS_PASSWORD_FILE", "")
	if path == "" {
		return raw
	}
	password, err := os.ReadFile(path)
	if err != nil {
		log.Printf("REDIS_PASSWORD_FILE %q: %v (continuing without auth)", path, err)
		return raw
	}
	u, err := url.Parse(raw)
	if err != nil {
		log.Printf("REDIS_URL %q: %v (continuing without auth)", raw, err)
		return raw
	}
	u.User = url.UserPassword("", strings.TrimSpace(string(password)))
	return u.String()
}

func main() {
	listenAddr := getenv("LISTEN_ADDR", ":8080")
	upstreamURL := getenv("UPSTREAM_URL", "http://litellm.llm.svc.cluster.local:4000")
	redisURL := resolveRedisURL(getenv("REDIS_URL", "redis://127.0.0.1:6379"))
	redisKey := getenv("REDIS_KEY", "via_negativa:banned_signatures")
	constraintsKey := getenv("TOP_CONSTRAINTS_KEY", "via_negativa:top_constraints")
	topN, err := strconv.Atoi(getenv("TOP_CONSTRAINTS_N", "5"))
	if err != nil || topN < 0 {
		topN = 5
	}
	refreshEvery := 10 * time.Second
	redisTimeout := 500 * time.Millisecond

	upstream, err := url.Parse(upstreamURL)
	if err != nil {
		log.Fatalf("invalid UPSTREAM_URL %q: %v", upstreamURL, err)
	}
	rp := httputil.NewSingleHostReverseProxy(upstream)

	store := newPatternStore()
	store.refresh(redisURL, redisKey, constraintsKey, topN, redisTimeout) // best-effort, fail-open
	go func() {
		for range time.Tick(refreshEvery) {
			store.refresh(redisURL, redisKey, constraintsKey, topN, redisTimeout)
		}
	}()

	tracker := newSessionRejectionTracker()

	mux := http.NewServeMux()
	mux.HandleFunc("/v1/chat/completions", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			rp.ServeHTTP(w, r)
			return
		}
		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "read body", http.StatusBadRequest)
			return
		}
		session := sessionKey(r, body)

		for _, name := range toolCallNames(body) {
			if banned, sig := store.match(name); banned {
				log.Printf("blocked path=%s signature=%q session=%q", r.URL.Path, sig, session)
				if n := tracker.recordRejection(session); n >= deadlockBreakerThreshold {
					log.Printf("deadlock breaker tripped session=%q after %d consecutive rejections", session, n)
					deadlockBreakerResponse(w, session)
					return
				}
				rejectResponse(w, sig)
				return
			}
		}
		tracker.recordSuccess(session)

		body = injectConstraints(body, store.topConstraints())
		r.Body = io.NopCloser(bytes.NewReader(body))
		r.ContentLength = int64(len(body))
		r.Header.Set("Content-Length", strconv.Itoa(len(body)))
		rp.ServeHTTP(w, r)
	})
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		rp.ServeHTTP(w, r)
	})

	log.Printf("via-negativa proxy listening on %s -> %s (redis=%s)", listenAddr, upstreamURL, redisURL)
	if err := http.ListenAndServe(listenAddr, mux); err != nil {
		log.Fatal(err)
	}
}

func getenv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
