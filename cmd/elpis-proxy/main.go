// cmd/elpis-proxy/main.go
// Layer 3: Elpis Cryptographic Signing Sidecar Proxy
// HTTP proxy at 127.0.0.1:8080 that reads Ed25519 key from tmpfs,
// signs outbound requests with canonical envelope, and injects attribution headers.

package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/pem"
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strconv"
	"time"
)

// SigningProxy intercepts outbound HTTP requests, signs them with the agent's
// Ed25519 private key (held in tmpfs), and forwards them to the upstream service.
// All headers are injected so the upstream can cryptographically verify the caller's identity.
type SigningProxy struct {
	privateKey ed25519.PrivateKey
	agentURN   string
	sessionID  string
	reverse    *httputil.ReverseProxy
}

// NewSigningProxy creates a new signing proxy.
func NewSigningProxy(keyPath, agentURN, sessionID, targetHost string) (*SigningProxy, error) {
	keyPEM, err := os.ReadFile(keyPath)
	if err != nil {
		return nil, fmt.Errorf("reading private key from tmpfs mount: %w", err)
	}

	block, _ := pem.Decode(keyPEM)
	if block == nil {
		return nil, fmt.Errorf("failed decoding PEM block from key file")
	}

	parsedKey, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("failed to parse PKCS8 private key: %w", err)
	}

	privKey, ok := parsedKey.(ed25519.PrivateKey)
	if !ok {
		return nil, fmt.Errorf("key in %s is not a valid Ed25519 private key", keyPath)
	}

	target, err := url.Parse(targetHost)
	if err != nil {
		return nil, fmt.Errorf("invalid upstream URL: %w", err)
	}

	p := &SigningProxy{
		privateKey: privKey,
		agentURN:   agentURN,
		sessionID:  sessionID,
	}

	p.reverse = &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			req.URL.Scheme = target.Scheme
			req.URL.Host = target.Host
			req.Host = target.Host
		},
	}

	return p, nil
}

// ServeHTTP handles incoming requests:
// 1. Read body
// 2. Compute SHA-256 of body
// 3. Sign canonical string (Method|URI|Timestamp|BodyHash|AgentURN|SessionID)
// 4. Inject X-Agent-* headers
// 5. Forward to upstream
func (p *SigningProxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	bodyBytes, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, `{"error":"FAILED_READING_PAYLOAD"}`, http.StatusBadRequest)
		return
	}
	r.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

	// Canonical payload digest: SHA-256 of raw request body
	hasher := sha256.New()
	hasher.Write(bodyBytes)
	bodyDigest := hex.EncodeToString(hasher.Sum(nil))

	timestamp := strconv.FormatInt(time.Now().Unix(), 10)

	// Canonical String to Sign (permissive delimiter: 
):
	// Method
URI
Timestamp
BodyHash
AgentURN
SessionID
	// All fields are newline-delimited to prevent injection.
	canonicalString := fmt.Sprintf("%s
%s
%s
%s
%s
%s",
		r.Method,
		r.URL.RequestURI(),
		timestamp,
		bodyDigest,
		p.agentURN,
		p.sessionID,
	)

	signature := ed25519.Sign(p.privateKey, []byte(canonicalString))
	signatureB64 := base64.StdEncoding.EncodeToString(signature)

	// Inject Attribution Envelope headers
	r.Header.Set("X-Agent-Id", p.agentURN)
	r.Header.Set("X-Agent-Session", p.sessionID)
	r.Header.Set("X-Agent-Timestamp", timestamp)
	r.Header.Set("X-Agent-Payload-Digest", bodyDigest)
	r.Header.Set("X-Agent-Signature", signatureB64)

	// Forward through reverse proxy
	p.reverse.ServeHTTP(w, r)
}

func main() {
	keyPath := os.Getenv("AGENT_KEY_PATH")
	if keyPath == "" {
		keyPath = "/run/secrets/agent-identity/ed25519.key"
	}

	agentURN := os.Getenv("AGENT_URN")
	sessionID := os.Getenv("SESSION_ID")
	upstreamURL := os.Getenv("UPSTREAM_URL")
	listenPort := os.Getenv("PROXY_PORT")
	if listenPort == "" {
		listenPort = "8080"
	}

	if agentURN == "" || sessionID == "" || upstreamURL == "" {
		fmt.Fprintf(os.Stderr, "FATAL: AGENT_URN, SESSION_ID, and UPSTREAM_URL must be set
")
		os.Exit(1)
	}

	proxy, err := NewSigningProxy(keyPath, agentURN, sessionID, upstreamURL)
	if err != nil {
		fmt.Fprintf(os.Stderr, "FATAL: Failed initializing signing proxy: %v
", err)
		os.Exit(1)
	}

	server := &http.Server{
		Addr:         ":" + listenPort,
		Handler:      proxy,
		ReadTimeout:  120 * time.Second,
		WriteTimeout: 120 * time.Second,
	}

	fmt.Printf("ELPIS_PROXY_ONLINE: Intercepting on :%s, agent=%s
", listenPort, agentURN)
	if err := server.ListenAndServe(); err != nil {
		fmt.Fprintf(os.Stderr, "FATAL: Server exited: %v
", err)
		os.Exit(1)
	}
}
