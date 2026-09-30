// cmd/identity-bootstrapper/main.go
// Layer 1: Cryptographic Bootstrapper
// Init container: fetches JWT-SVID from SPIRE, exchanges for OCI IAM token via
// RFC 8693, retrieves/generates Ed25519 key from OCI Vault, writes to tmpfs.
//
// Uses OCI CLI (like platform/llm/spire-key-broker) for OCI Vault access.
// Ed25519 key generation uses Go standard library (crypto/ed25519).

package main

import (
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// OCI auth: workload identity (OKE pod's service account token).
// OCI CLI auto-detects this when OCI_CLI_AUTH=workload_identity.

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()

	// --- Configuration from env ---
	spireSocketPath := os.Getenv("SPIRE_AGENT_SOCKET")
	if spireSocketPath == "" {
		spireSocketPath = "unix:///run/spire/sockets/agent.sock"
	}

	ociTokenURL := os.Getenv("OCI_IAM_TOKEN_ENDPOINT")
	ociScope := os.Getenv("OCI_IAM_SCOPE")
	vaultOCID := os.Getenv("OCI_VAULT_OCID")
	compartmentOCID := os.Getenv("OCI_COMPARTMENT_OCID")
	agentURN := os.Getenv("AGENT_URN")
	outputKeyPath := "/run/secrets/agent-identity/ed25519.key"

	if ociTokenURL == "" || vaultOCID == "" || agentURN == "" {
		fmt.Fprintf(os.Stderr, "FATAL: OCI_IAM_TOKEN_ENDPOINT, OCI_VAULT_OCID, and AGENT_URN must be defined\n")
		os.Exit(1)
	}

	// --- Step 1: Acquire JWT-SVID from SPIRE Workload API ---
	fmt.Println("INFO: Fetching JWT-SVID from SPIRE...")
	svidJSON, err := fetchJWTSVID(ctx, spireSocketPath, ociTokenURL)
	if err != nil {
		fmt.Fprintf(os.Stderr, "FATAL: Failed to fetch JWT-SVID: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("INFO: JWT-SVID acquired")

	// --- Step 2: RFC 8693 Token Exchange against OCI IAM ---
	fmt.Println("INFO: Exchanging JWT-SVID for OCI IAM access token (RFC 8693)...")
	accessToken, err := tokenExchange(ctx, ociTokenURL, svidJSON, ociScope)
	if err != nil {
		fmt.Fprintf(os.Stderr, "FATAL: OCI IAM token exchange failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("INFO: OCI IAM access token acquired")

	// --- Step 3: Retrieve or generate Ed25519 key from OCI Vault ---
	// Derive a deterministic secret name from the agent URN (SHA-256, hex truncated).
	h := sha256.New()
	h.Write([]byte(agentURN))
	secretName := fmt.Sprintf("aid-key-%s", hex.EncodeToString(h.Sum(nil))[:32])

	fmt.Printf("INFO: Looking for existing key '%s' in vault...\n", secretName)
	keyPEM, err := getVaultSecret(ctx, vaultOCID, secretName, accessToken)
	if err == nil {
		fmt.Println("INFO: Existing key retrieved from OCI Vault")
	} else {
		// Genesis: generate new Ed25519 keypair and store in OCI Vault.
		fmt.Println("INFO: No existing key found. Generating new Ed25519 keypair (genesis)...")
		pubKey, privKey, err := ed25519.GenerateKey(rand.Reader)
		if err != nil {
			fmt.Fprintf(os.Stderr, "FATAL: Keypair generation failed: %v\n", err)
			os.Exit(1)
		}

		// Serialize to PKCS8 PEM.
		pkcs8Bytes, err := x509.MarshalPKCS8PrivateKey(privKey)
		if err != nil {
			fmt.Fprintf(os.Stderr, "FATAL: PKCS8 marshaling failed: %v\n", err)
			os.Exit(1)
		}
		pemBlock := &pem.Block{Type: "PRIVATE KEY", Bytes: pkcs8Bytes}
		keyPEM = pem.EncodeToMemory(pemBlock)
		_ = pubKey // Public key persists via DB registration (Layer 2)

		fmt.Println("INFO: Storing new key in OCI Vault...")
		if err := createVaultSecret(ctx, vaultOCID, compartmentOCID, secretName, keyPEM, accessToken); err != nil {
			fmt.Fprintf(os.Stderr, "FATAL: Failed to store key in OCI Vault: %v\n", err)
			os.Exit(1)
		}
		fmt.Println("INFO: Genesis complete — Ed25519 keypair stored in OCI Vault")
	}

	// --- Step 4: Write key to tmpfs with strict permissions (mode 0400) ---
	if err := os.MkdirAll(filepath.Dir(outputKeyPath), 0700); err != nil {
		fmt.Fprintf(os.Stderr, "FATAL: Creating secrets directory: %v\n", err)
		os.Exit(1)
	}
	if err := os.WriteFile(outputKeyPath, keyPEM, 0400); err != nil {
		fmt.Fprintf(os.Stderr, "FATAL: Writing key to tmpfs: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("BOOTSTRAP_COMPLETE: Identity %s authenticated and hydrated into %s\n", agentURN, outputKeyPath)
}

// fetchJWTSVID calls `spire-agent api fetch jwt` via the Workload API socket.
func fetchJWTSVID(ctx context.Context, socketPath, audience string) (string, error) {
	socketURL := strings.TrimPrefix(socketPath, "unix://")

	args := []string{
		"api", "fetch", "jwt",
		"-socketPath", socketURL,
		"-audience", audience,
		"-timeout", "30s",
	}

	cmd := exec.CommandContext(ctx, "spire-agent", args...)
	cmd.Env = append(os.Environ(),
		"SPIRE_AGENT_DATA_DIR=/run/spire/agent-data",
	)

	out, err := cmd.Output()
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			return "", fmt.Errorf("spire-agent: %s", string(exitErr.Stderr))
		}
		return "", fmt.Errorf("spire-agent: %w", err)
	}

	// Parse JSON: {"spiffe_jwt":"<token>"}
	var resp struct {
		SPIFFEJWT string `json:"spiffe_jwt"`
	}
	if err := json.Unmarshal(out, &resp); err != nil {
		return "", fmt.Errorf("parse spire-agent JWT response: %w", err)
	}
	return resp.SPIFFEJWT, nil
}

// tokenExchange performs RFC 8693 OAuth 2.0 Token Exchange against OCI IAM.
func tokenExchange(ctx context.Context, tokenURL, subjectToken, scope string) (string, error) {
	data := url.Values{}
	data.Set("grant_type", "urn:ietf:params:oauth:grant-type:token-exchange")
	data.Set("subject_token", subjectToken)
	data.Set("subject_token_type", "urn:ietf:params:oauth:token-type:jwt")
	data.Set("requested_token_type", "urn:ietf:params:oauth:token-type:access_token")
	data.Set("scope", scope)

	req, err := http.NewRequestWithContext(ctx, "POST", tokenURL, strings.NewReader(data.Encode()))
	if err != nil {
		return "", fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("HTTP request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("OCI IAM rejected (status=%d): %s", resp.StatusCode, string(body))
	}

	var tokenResp struct {
		AccessToken string `json:"access_token"`
		ExpiresIn  int    `json:"expires_in"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&tokenResp); err != nil {
		return "", fmt.Errorf("parse token response: %w", err)
	}
	return tokenResp.AccessToken, nil
}

// getVaultSecret retrieves a base64-encoded PEM secret from OCI Vault using the CLI.
func getVaultSecret(ctx context.Context, vaultOCID, secretName, accessToken string) ([]byte, error) {
	args := []string{
		"vault", "secret", "get",
		"--vault-id", vaultOCID,
		"--secret-name", secretName,
		"--query", "data.secret_bundlePlaintext",
		"--raw-output",
	}

	cmd := exec.CommandContext(ctx, "oci", args...)
	cmd.Env = append(os.Environ(),
		"OCI_CLI_AUTH=workload_identity",
		"OCI_ACCESS_TOKEN="+accessToken,
	)

	out, err := cmd.Output()
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			return nil, fmt.Errorf("oci vault secret get: %s", strings.TrimSpace(string(exitErr.Stderr)))
		}
		return nil, fmt.Errorf("oci vault secret get: %w", err)
	}

	// Response is base64-encoded PEM. Decode to raw PEM bytes.
	return base64.StdEncoding.DecodeString(strings.TrimSpace(string(out)))
}

// createVaultSecret creates a new secret in OCI Vault using the CLI.
func createVaultSecret(ctx context.Context, vaultOCID, compartmentOCID, secretName string, pemData []byte, accessToken string) error {
	// Encode PEM as base64 for OCI Vault (expects base64 content).
	b64Content := base64.StdEncoding.EncodeToString(pemData)

	// Write base64 content to a temp file to avoid shell escaping issues.
	tmpFile := "/tmp/secret-content.b64"
	if err := os.WriteFile(tmpFile, []byte(b64Content), 0600); err != nil {
		return fmt.Errorf("write temp file: %w", err)
	}
	defer os.Remove(tmpFile)

	args := []string{
		"vault", "secret", "create",
		"--vault-id", vaultOCID,
		"--compartment-id", compartmentOCID,
		"--secret-name", secretName,
		"--secret-content", "@"+tmpFile,
		"--description", fmt.Sprintf("Ed25519 persistent key for agent (DROS Layer 1)"),
	}

	cmd := exec.CommandContext(ctx, "oci", args...)
	cmd.Env = append(os.Environ(),
		"OCI_CLI_AUTH=workload_identity",
		"OCI_ACCESS_TOKEN="+accessToken,
	)

	out, err := cmd.Output()
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			return fmt.Errorf("oci vault secret create: %s", strings.TrimSpace(string(exitErr.Stderr)))
		}
		return fmt.Errorf("oci vault secret create: %w", err)
	}

	// Parse response to confirm creation.
	var resp struct {
		Data struct {
			SecretId string `json:"id"`
		} `json:"data"`
	}
	if err := json.Unmarshal(out, &resp); err != nil {
		return fmt.Errorf("parse create response: %w", err)
	}
	if resp.Data.SecretId == "" {
		return fmt.Errorf("secret creation: no secret ID in response")
	}
	return nil
}
