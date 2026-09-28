# SPIRE Key Broker — Router Identity Without Standing Credentials
**Date:** 2026-09-24
**Problem:** Founder is the credential. Every session ends with "founder, set the key." SPIRE is deployed. Not wired.
**Goal:** Router fetches provider keys via SVID. No mounted Secret. No ExternalSecret. No Bitwarden-as-source-of-truth-for-humans. No founder.

---

## A. What exists

### SPIRE (deployed, active)
- Namespace: `spire-mgmt`
- HelmRelease: `spire` v0.30.1 (spire-crds v0.6.1), via Flux Kustomization `spire` in `clusters/oke/platform.yaml`
- Server + agent run; CSI driver (`csi.spiffe.io`) mounts the Workload API socket into pods
- Proof: `platform/spire/proof.yaml` — a Job in namespace `backstage` mounts the CSI socket, calls `spire-agent api fetch x509`, prints the SPIFFE ID
- `platform/spire/proof-cronjob.yaml` — automated verification

### Router keys (the problem)
`platform/llm/litellm.yaml` mounts 10 secrets:
```
litellm-db            → LITELLM_DB_PASSWORD   (vault master key, required)
litellm-master-key    → LITELLM_MASTER_KEY   (vault master key)
litellm-langfuse     → Langfuse credentials
litellm-sso          → OIDC client credentials
litellm-cache        → REDIS_PASSWORD
human-minimax        → MINIMAX_API_KEY      (ExternalSecret ← Bitwarden, optional)
human-openrouter     → OPENROUTER_API_KEY   (ExternalSecret ← Bitwarden, optional)
human-gemini         → GEMINI_API_KEY       (ExternalSecret ← Bitwarden, optional)
human-cohere         → COHERE_API_KEY       (ExternalSecret ← Bitwarden, optional)
human-kimi           → MOONSHOT_API_KEY     (ExternalSecret ← Bitwarden, optional)
human-cerebras       → CEREBRAS_API_KEY     (ExternalSecret ← Bitwarden, optional)
human-nvidia         → NVIDIA_API_KEY       (ExternalSecret ← Bitwarden, optional)
human-groq           → GROQ_API_KEY        (ExternalSecret ← Bitwarden, optional)
human-sambanova      → SAMBANOVA_API_KEY    (ExternalSecret ← Bitwarden, optional)
```
Each `human-<vendor>` is an ExternalSecret that syncs from Bitwarden Secrets Manager every 1 minute, owned by the `human-vault-bridge` Flux Kustomization (helm chart rendered from `platform/vendors/consoles.yaml`).

LiteLLM reads keys as `os.environ/MINIMAX_API_KEY` etc.

### The trust chain (the problem, precisely)
```
Founder pastes key into Bitwarden
  → ExternalSecret syncs from Bitwarden every 1 min
    → Kubernetes Secret in namespace llm
      → env var mounted into router pod
        → LiteLLM reads at call time
```
Every link in that chain requires the founder. The founder is the credential.

---

## B. The target

```
Router pod starts
  → SPIRE agent issues SVID (via CSI socket, spiffe://estate/ns/llm/sa/idp-router)
  → Router calls key broker: "I am spiffe://estate/ns/llm/sa/idp-router. Give me the MiniMax key."
  → Broker verifies SVID against SPIRE API
  → Broker fetches from OCI Vault using workload identity (IRSA or OCI native workload identity)
  → Broker returns key
  → Router uses key
  → SVID expires (~1h). Next fetch gets a fresh SVID.
```
No mounted Secret. No ExternalSecret. No Bitwarden. No founder. The router's identity is its SVID.

OCI Vault as source of truth. Provider keys live there, not in Bitwarden.

---

## C. Implementation options

### Option 1: SPIFFE-aware ExternalSecret backend (simplest)
Extend the ExternalSecrets Operator to authenticate to OCI Vault using the pod's SVID instead of a static OCI API key.

- ESO already supports multiple backends (AWS Secrets Manager, GCP, Azure, HashiCorp, OCI Vault)
- OCI Vault backend uses an OCI API key as the authentication credential
- Replace the static OCI API key with a SPIFFE-authenticated call: ESO pod mounts the SPIRE CSI socket, uses its SVID to call OCI Vault
- Provider keys move from Bitwarden to OCI Vault
- ExternalSecret still creates mounted Kubernetes Secrets → env vars → LiteLLM
- Founder removed from chain. OCI Vault is the source. SPIRE is the authn.
- Limitation: ESO pod's SVID, not individual pod SVIDs. All ESO-fetched secrets share the ESO's identity.

### Option 2: Sidecar → shared volume (built)
The broker runs as a sidecar in the router pod, not as a separate service.
- Broker calls `oci vault secret get` using the pod's OCI workload identity
- Broker writes keys to `/vault-keys/<provider>` on a shared emptyDir volume
- Router reads `/vault-keys/<provider>` at startup and exports as env vars
- No static API key anywhere. No Bitwarden. Founder removed from the chain.

### Option 3: Router-side SVID → OCI Vault directly
LiteLLM extended with a custom key provider that:
1. Calls `spire-agent api fetch x509` via the local socket
2. Uses the SVID to authenticate to OCI Vault
3. Returns the key to LiteLLM at call time
- Most direct. Requires a LiteLLM patch or a key-provider sidecar.

---

## D. What was built

The broker sidecar writes to a shared emptyDir; the router reads at startup.

```
Router pod
  ├── litellm (router container)
  │     ├── startup: read /vault-keys/<provider> files
  │     ├── export as MINIMAX_API_KEY, DEEPSEEK_API_KEY, ...
  │     └── exec litellm --config /etc/litellm/config.yaml
  └── broker (sidecar container)
        ├── read vault-ocid ConfigMap (llm namespace)
        ├── oci vault secret get --secret-name MINIMAX_API_KEY
        │     └── uses OCI workload identity (pod annotation)
        ├── write to /vault-keys/minimax
        └── refresh every 10 min + on SIGUSR1
```

**Files:**
- `platform/llm/spire-key-broker/server.go`     — broker HTTP service + OCI Vault fetch
- `platform/llm/spire-key-broker/Dockerfile`    — OCI CLI image + Go binary
- `platform/llm/router-sa.yaml`                — ServiceAccount with OCI workload identity annotation
- `platform/llm/litellm.yaml`                  — sidecar container, vault-keys volume, startup reads /vault-keys/
- `platform/llm/kustomization.yaml`            — includes router-sa.yaml
- `deploy/helm/spire-key-broker/`               — Helm chart (standalone dev; sidecar is the normal deployment)
- `bin/idp-flux-bootstrap`                      — creates vault-ocid ConfigMap in llm namespace

**OCI Vault names:** MINIMAX_API_KEY, DEEPSEEK_API_KEY, GEMINI_API_KEY, MOONSHOT_API_KEY,
COHERE_API_KEY, CEREBRAS_API_KEY, NVIDIA_API_KEY, GROQ_API_KEY, SAMBANOVA_API_KEY,
OPENROUTER_API_KEY — one vault entry per key, written by `bin/idp-vault-put`.

**OCI Vault discovery:** vault OCID read from `vault-ocid` ConfigMap (llm namespace),
created by `bin/idp-flux-bootstrap` from tofu output. Broker reads `/configmaps/vault-ocid/vault_ocid`.

---

## E. Vault-seed bootstrap (founder action once)

Run after `bin/idp-flux-bootstrap` creates the vault-ocid ConfigMap. One-time migration
from Bitwarden to OCI Vault:

```bash
# 1. Get each key value from Bitwarden Secrets Manager.
# 2. Write to OCI Vault:
bin/idp-vault-put MINIMAX_API_KEY MINIMAX_API_KEY=<value from Bitwarden>
bin/idp-vault-put DEEPSEEK_API_KEY DEEPSEEK_API_KEY=<value>
bin/idp-vault-put GEMINI_API_KEY GEMINI_API_KEY=<value>
bin/idp-vault-put MOONSHOT_API_KEY MOONSHOT_API_KEY=<value>
bin/idp-vault-put COHERE_API_KEY COHERE_API_KEY=<value>
bin/idp-vault-put CEREBRAS_API_KEY CEREBRAS_API_KEY=<value>
bin/idp-vault-put NVIDIA_API_KEY NVIDIA_API_KEY=<value>
bin/idp-vault-put GROQ_API_KEY GROQ_API_KEY=<value>
bin/idp-vault-put SAMBANOVA_API_KEY SAMBANOVA_API_KEY=<value>
bin/idp-vault-put OPENROUTER_API_KEY OPENROUTER_API_KEY=<value>

# Verify:
bin/idp-cloud secret get MINIMAX_API_KEY   # should return the value
```

This is the **founder's one action**. After this, the vault is the source of truth.
The ESO bridge (human-vault-bridge) still syncs Bitwarden → `human-*` Secrets for
otto-gateway and consoles.yaml pool deployments — that is a separate path and does not
need to be retired to call this work done.

---

## F. Migration status

**Phase 1 ✅ (done):**
- Broker sidecar built and wired into litellm.yaml
- vault-ocid ConfigMap created by bin/idp-flux-bootstrap
- OCI workload identity via pod annotation `oci.oraclecloud.com/principal: workload`
- SPIRE CSI socket (csi.spiffe.io) mounted to broker sidecar
- Broker has spire-agent binary: SVID verification is wired, not stubbed
  - handleKey requires X-SPIFFE-ID header from caller
  - broker calls `spire-agent api fetch x509` to verify claimed ID matches agent response
  - Logs SPIFFE ID + key name + timestamp per request (audit trail)
- Router reads /vault-keys/<provider> at startup; broker writes every 10 min
- human-* volume mounts removed from router; ESO bridge still runs (otto-gateway uses it)

**Phase 0 🔜 (needed before traffic flows):**
- Founder runs `bin/idp-vault-put` for each provider key (Bitwarden → OCI Vault)
- Until keys are in the vault, the router starts without provider keys (broker writes nothing)

**Phase 2 (this week):**
- All provider keys in OCI Vault
- Retire Bitwarden as source-of-truth for llm namespace keys
- Optionally remove human-* ESO entries for llm namespace (keep for otto-gateway)

**Phase 3 🔜 (next):**
- Router calls broker with SVID: router mounts SPIRE socket, fetches its SVID,
  calls broker HTTP endpoint with X-SPIFFE-ID header
- Broker verifies X-SPIFFE-ID against spire-agent (already wired, see above)
- After this, the spec's Section B chain is fully implemented:
  Router proves identity via SVID → Broker verifies → Broker returns key

---

## G. Verification

```bash
# 1. vault-ocid ConfigMap exists:
kubectl get configmap vault-ocid -n llm -o jsonpath='{.data.vault_ocid}'

# 2. Broker image builds:
docker build -t ghcr.io/earendil-works/idp/spire-key-broker platform/llm/spire-key-broker/

# 3. Router pod has both containers:
kubectl get pod -n llm -l app.kubernetes.io/name=litellm \
  -o jsonpath='{.items[0].spec.containers[*].name}'
# → litellm broker

# 4. OCI workload identity annotation on pod:
kubectl get pod -n llm -l app.kubernetes.io/name=litellm \
  -o jsonpath='{.items[0].metadata.annotations.oci\.oraclecloud\.com/principal}'
# → workload

# 5. Broker writing keys to shared volume (after vault-seed):
kubectl exec -n llm deploy/litellm -c broker -- cat /vault-keys/minimax

# 6. Router exporting the key:
kubectl exec -n llm deploy/litellm -c litellm -- \
  sh -c 'echo $MINIMAX_API_KEY' | head -c 10; echo

# 7. No human-* volume mounts on router:
kubectl get deploy litellm -n llm -o yaml | grep 'human-'
# → (empty)

# 8. Broker health:
kubectl exec -n llm deploy/litellm -c broker -- wget -qO- localhost:8080/healthz
# → OK
```
