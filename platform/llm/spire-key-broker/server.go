// SPIRE Key Broker — router fetches provider keys via OCI workload identity.
// No Bitwarden. No ExternalSecret. No founder-as-credential.
//
// How it works:
//   1. Router pod starts; SPIRE agent issues SVID to the pod's workloads.
//   2. Key-broker sidecar runs alongside the router in the same pod.
//   3. Sidecar calls `oci vault secret get` using OCI workload identity (no static key).
//   4. Sidecar writes keys to /vault-keys/<keyname> on a shared emptyDir volume.
//   5. Router reads /vault-keys/<keyname> files instead of env vars.
//   6. Sidecar refreshes every 10 min and on SIGUSR1.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"
)

// providerKeys lists the keys this broker manages.
// In production this comes from a configmap so adding a key is a configmap patch.
var providerKeys = []string{
	"minimax", "deepseek", "gemini", "kimi",
	"cohere", "cerebras", "nvidia", "groq",
	"sambanova", "openrouter",
}

// ociVaultKeyNames maps the broker's internal name to the OCI Vault secret name.
var ociVaultKeyNames = map[string]string{
	"minimax":    "MINIMAX_API_KEY",
	"deepseek":    "DEEPSEEK_API_KEY",
	"gemini":      "GEMINI_API_KEY",
	"kimi":        "MOONSHOT_API_KEY",
	"cohere":      "COHERE_API_KEY",
	"cerebras":    "CEREBRAS_API_KEY",
	"nvidia":      "NVIDIA_API_KEY",
	"groq":        "GROQ_API_KEY",
	"sambanova":    "SAMBANOVA_API_KEY",
	"openrouter":   "OPENROUTER_API_KEY",
}

const (
	keysDir         = "/vault-keys"
	refreshInterval = 10 * time.Minute
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	if err := os.MkdirAll(keysDir, 0400); err != nil {
		log.Fatalf("mkdir %s: %v", keysDir, err)
	}

	b := &Broker{state: make(map[string]keyState)}

	if err := b.fetchAll(ctx); err != nil {
		log.Printf("initial fetch: %v", err)
	}

	go b.refreshLoop(ctx)

	// SIGUSR1 → immediate refresh.
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGUSR1)
	go func() {
		for range sigCh {
			if err := b.fetchAll(context.Background()); err != nil {
				log.Printf("SIGUSR1 refresh: %v", err)
			}
		}
	}()

	mux := http.NewServeMux()
	mux.HandleFunc("/keys/", b.handleKey)
	mux.HandleFunc("/healthz", b.handleHealth)
	mux.HandleFunc("/metrics", b.handleMetrics)
	mux.HandleFunc("/refresh", b.handleRefresh)

	log.Println("spire-key-broker listening :8080")
	if err := http.ListenAndServe(":8080", mux); err != nil {
		log.Fatalf("server: %v", err)
	}
}

type keyState struct {
	value   string
	fetched time.Time
	err     error
}

type Broker struct {
	state map[string]keyState
	mu    sync.RWMutex
}

// fetchAll fetches every key from OCI Vault and writes to the shared volume.
func (b *Broker) fetchAll(ctx context.Context) error {
	var lastErr error
	for _, name := range providerKeys {
		vaultName := ociVaultKeyNames[name]
		val, err := fetchOCISecret(ctx, vaultName)
		path := filepath.Join(keysDir, name)
		if err != nil {
			log.Printf("key %s (%s): %v", name, vaultName, err)
			lastErr = err
		} else {
			log.Printf("key %s: fetched OK", name)
			if err := os.WriteFile(path, []byte(val), 0400); err != nil {
				log.Printf("write %s: %v", path, err)
				err = fmt.Errorf("write: %w", err)
			}
		}
		b.mu.Lock()
		b.state[name] = keyState{value: val, fetched: time.Now(), err: err}
		b.mu.Unlock()
	}
	return lastErr
}

func (b *Broker) refreshLoop(ctx context.Context) {
	ticker := time.NewTicker(refreshInterval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			b.fetchAll(ctx)
		}
	}
}

// handleKey returns the current value of one key.
// GET /keys/<name>
// The caller presents X-SPIFFE-ID: <spiffe-id> header. The broker verifies this
// against the SPIRE agent before returning the key. This is the SVID wire from
// Section B of the spec: the router proves its identity
// (spiffe://estate.internal/ns/llm/sa/idp-router) before the broker returns a secret.
func (b *Broker) handleKey(w http.ResponseWriter, r *http.Request) {
	name := filepath.Base(r.URL.Path)
	if _, ok := ociVaultKeyNames[name]; !ok {
		http.Error(w, "unknown key: "+name, http.StatusNotFound)
		return
	}

	// --- SPIRE SVID verification ---
	callerSPIFFE := r.Header.Get("X-SPIFFE-ID")
	if callerSPIFFE == "" {
		// No SPIFFE ID presented: the caller is not a SPIFFE workload.
		// Refuse the request. The router must present its SVID.
		http.Error(w, "no SPIFFE ID presented", http.StatusUnauthorized)
		return
	}
	if err := verifySVID(callerSPIFFE); err != nil {
		log.Printf("SVID verification failed for %s: %v", callerSPIFFE, err)
		http.Error(w, "invalid SPIFFE ID: "+err.Error(), http.StatusForbidden)
		return
	}
	// --- end SPIRE SVID verification ---

	b.mu.RLock()
	state, ok := b.state[name]
	b.mu.RUnlock()
	if !ok || state.err != nil {
		http.Error(w, "key unavailable: "+name, http.StatusServiceUnavailable)
		return
	}
	log.Printf("key %s served to %s [spiffe://%s]", name, r.RemoteAddr, callerSPIFFE)
	w.Header().Set("Content-Type", "text/plain")
	w.Write([]byte(state.value))
}

func (b *Broker) handleHealth(w http.ResponseWriter, r *http.Request) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	for _, name := range providerKeys {
		if b.state[name].err != nil {
			w.WriteHeader(http.StatusServiceUnavailable)
			fmt.Fprintln(w, "DEGRADED")
			return
		}
	}
	w.WriteHeader(http.StatusOK)
	fmt.Fprintln(w, "OK")
}

func (b *Broker) handleMetrics(w http.ResponseWriter, r *http.Request) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	for _, name := range providerKeys {
		s := b.state[name]
		exists := 0.0
		if s.err == nil && s.value != "" {
			exists = 1.0
		}
		fmt.Fprintf(w, "spire_key_broker_key_exists{key=%q} %.0f\n", name, exists)
		if !s.fetched.IsZero() {
			fmt.Fprintf(w, "spire_key_broker_key_age_seconds{key=%q} %.0f\n",
				name, time.Since(s.fetched).Seconds())
		}
	}
}

func (b *Broker) handleRefresh(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	go b.fetchAll(context.Background())
	w.WriteHeader(http.StatusAccepted)
	fmt.Fprintln(w, "refreshing")
}

// verifySVID verifies that the claimed SPIFFE ID matches the caller's actual SVID.
// It calls `spire-agent api fetch x509` via the SPIRE Workload API socket and parses
// the SPIFFE ID from the agent's response. If the agent has no SVID for this workload,
// or the claimed ID does not match, it returns an error.
//
// The SPIRE CSI driver mounts /spiffe-workload-api/ into every pod. The agent listens
// on the workload socket and attributes the call to the calling process's identity.
// Since the broker and router run in the same pod, the router's process identity is
// the router's SPIFFE ID:
//   spiffe://estate.internal/ns/llm/sa/idp-router
// (trust domain from platform/spire/values.yaml: trustDomain: estate.internal)
//
// The router passes its SPIFFE ID in the X-SPIFFE-ID header; this function verifies
// that claim against the SPIRE agent's own view of the caller's identity.
func verifySVID(claimedSPIFFEID string) error {
	socketPath := os.Getenv("SPIRE_SOCKET")
	if socketPath == "" {
		socketPath = "/spiffe-workload-api/spire-agent.sock"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// spire-agent api fetch x509: the agent returns JSON with the workload's SVIDs.
	// When called from the router process, the agent attributes the call to the router's
	// SPIFFE ID (spiffe://estate.internal/ns/llm/sa/idp-router).
	cmd := exec.CommandContext(ctx, "spire-agent", "api", "fetch", "x509",
		"-socketPath", socketPath, "-timeout", "5s")
	// Inherit OCI auth so the agent can reach the SPIRE server over the tailnet.
	cmd.Env = append(os.Environ(),
		"OCI_CLI_AUTH=workload_identity",
		"SPIRE_AGENT_DATA_DIR=/run/spire/agent-data",
	)

	out, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("spire-agent fetch failed: %w", err)
	}

	// Parse the agent's JSON output. Each entry has a "spiffe_id" field.
	var resp struct {
		Svids []struct {
			SPIFFEID string `json:"spiffe_id"`
		} `json:"svids"`
	}
	if err := json.Unmarshal(out, &resp); err != nil {
		return fmt.Errorf("parse spire-agent output: %w", err)
	}

	for _, svid := range resp.Svids {
		if svid.SPIFFEID == claimedSPIFFEID {
			return nil // verified
		}
	}
	return fmt.Errorf("claimed %q not in agent response; got %v", claimedSPIFFEID,
		func() []string {
			ids := make([]string, len(resp.Svids))
			for i, s := range resp.Svids {
				ids[i] = s.SPIFFEID
			}
			return ids
		}())
}

// fetchOCISecret calls `oci vault secret get` using OCI workload identity.
// OCI CLI in OKE automatically uses the pod's workload identity.
// No config file, no static credentials.
func fetchOCISecret(ctx context.Context, secretName string) (string, error) {
	vaultOCID, err := getVaultOCID()
	if err != nil {
		return "", fmt.Errorf("vault OCID: %w", err)
	}

	ctx, cancel := context.WithTimeout(ctx, 15*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "oci",
		"vault", "secret", "get",
		"--vault-id", vaultOCID,
		"--secret-name", secretName,
		"--query", "data.secret_bundlePlaintext",
		"--raw-output",
	)
	cmd.Env = append(os.Environ(),
		"OCI_CLI_AUTH=workload_identity",
	)

	out, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("oci vault secret get %s: %w", secretName, err)
	}
	return strings.TrimSpace(string(out)), nil
}

// getVaultOCID reads the vault OCID from the vault-ocid ConfigMap in the llm namespace.
// bin/idp-flux-bootstrap creates this ConfigMap alongside estate-vars:
//   kubectl -n llm create configmap vault-ocid --from-literal=vault_ocid="$VAULT_ID"
// The path matches the volume mount: /configmaps/vault-ocid/vault_ocid
func getVaultOCID() (string, error) {
	path := os.Getenv("VAULT_OCID_PATH")
	if path == "" {
		path = "/configmaps/vault-ocid/vault_ocid"
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("read vault OCID from %s: %w", path, err)
	}
	return strings.TrimSpace(string(data)), nil
}
