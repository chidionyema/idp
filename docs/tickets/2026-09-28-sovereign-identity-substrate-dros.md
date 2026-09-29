# Ticket: Quad-Layer Sovereign Identity & Execution Substrate (DROS)

**Created:** 2026-09-28
**Status:** OPEN
**Priority:** P1
**Owner:** agent-trunk
**Labels:** sovereign-identity, dros, spire, eBPF, kernel, production

## Overview

Implement the Quad-Layer Sovereign Identity & Execution Substrate (DROS): a kernel-enforced
agent identity system where untrusted cognitive agents (Claude Code, Pi, etc.) execute in
isolated pods but can only egress through a cryptographic signing proxy backed by an Ed25519
key that lives in kernel-isolated memory (tmpfs), never in the agent's filesystem.

## Architecture

Five layers, each independently verifiable:

### Layer 1: Cryptographic Bootstrapper
**`cmd/identity-bootstrapper/`** — Go init container
- Mount SPIRE Workload API UNIX Domain Socket
- Fetch JWT-SVID via `workloadapi.FetchJWTSVID()`
- Perform RFC 8693 OAuth 2.0 Token Exchange against OCI IAM
- Authenticate to OCI Vault using federated token
- Retrieve/generate Ed25519 key, write to `tmpfs` at `/run/secrets/agent-identity/ed25519.key` (mode 0400)
- Exit cleanly; agent container never sees the key material

### Layer 2: Persistent Agent Registry
**`schema/identity0_registry.sql`** — PostgreSQL DDL
- `agents` table: agent_id (URN), canonical_name, public_key, key_fingerprint, lineage_parent, authority_scope, operator_id, status
- `sessions` table: session_id, agent_id, spiffe_id, harness, model
- `agent_actions` table: intent_name, args_hash, result_hash, signature, merkle_root
- `merkle_anchors` table: root_hash, leaf_count, oci_object_uri
- Indexes on key_fingerprint, agent_session, signature

### Layer 3: Elpis Signing Sidecar Proxy
**`cmd/elpis-proxy/`** — Go HTTP sidecar at `127.0.0.1:8080`
- Agent sets `HTTP_PROXY=http://127.0.0.1:8080`
- Proxy reads Ed25519 key from tmpfs
- Signs requests with canonical envelope: Method + URI + Timestamp + BodyHash + AgentURN + SessionID
- Injects headers: X-Agent-Id, X-Agent-Session, X-Agent-Timestamp, X-Agent-Payload-Digest, X-Agent-Signature
- Reverse-proxies to upstream (e.g., litellm-gateway)

### Layer 4: DROS eBPF Enforcement Engine
**`bpf/dros_enforce.bpf.c`** — BPF LSM hook
- Hooks `security_socket_connect` / `sys_enter_connect`
- Maintains `agent_process_status` hash map: PID → {Active=1, Revoked=2}
- LPM trie `allowed_ipv4_subnets`: permits registered egress subnets
- Exceptions: loopback (127.0.0.1:8080 signing proxy), SPIRE agent socket
- Immediate `-EPERM` for unauthorized direct egress or revoked PIDs

**`cmd/dros-daemon/`** — User-space daemon
- Loads BPF bytecode via cilium/ebpf
- Attaches to LSM hook
- Exposes Unix socket `/var/run/dros/control.sock`
- Endpoints: `POST /register?pid=X`, `POST /revoke?pid=X`
- On revoke: kernel atomically marks PID=2 in map → next syscall returns -EPERM

### Layer 5: OKE Deployment Manifest
**`deploy/production-agent-pod.yaml`** — Kubernetes Deployment
- ServiceAccount `research-agent-sa` with SPIRE entry annotation
- Init container: `ghcr.io/chidionyema/idp/identity-bootstrapper`
- Agent container: untrusted, `HTTP_PROXY=http://127.0.0.1:8080`
- Sidecar: `ghcr.io/chidionyema/idp/elpis-proxy`
- DROS Daemon: `ghcr.io/chidionyema/idp/dros-daemon` (privileged, BPF-capable)
- Volumes: `identity-tmpfs` (Memory medium), `spire-agent-socket` (hostPath)
- Security: non-root, readOnlyRootFilesystem, drop ALL capabilities

## Prerequisites (must exist before DROS deploys)

1. **SPIRE Server** — already running (`platform/spire/`)
2. **OCI IAM Federation** — OCI Workload Identity configured for SPIFFE trust
3. **OCI Vault** — secret compartment with DROS key vault
4. **Autonomous DB (ATP)** — PostgreSQL-compatible, TLS connection string
5. **OKE Cluster** — kernel CONFIG_BPF_LSM enabled on all agent nodes

## Implementation Order

1. [ ] Layer 2: Deploy `schema/identity0_registry.sql` to ATP
2. [ ] Layer 1: Implement `cmd/identity-bootstrapper` + Docker image build
3. [ ] Layer 3: Implement `cmd/elpis-proxy` + Docker image build
4. [ ] Layer 4: Implement `bpf/` + `cmd/dros-daemon/` + Docker image build
5. [ ] Layer 5: Compose `deploy/production-agent-pod.yaml`
6. [ ] Validation: Run the Step-by-Step Execution Pipeline
7. [ ] shadow-verify: Prove it on a throwaway cluster before production

## Verification

See the Step-by-Step Validation & Execution Pipeline in the architectural spec.
Every step checks cryptographic proofs without trusting local logs.

## Related Work

- `fix/spire-proof-run` — SPIRE proof cronjob fix
- `fix/spire-key-broker-image` — SPIRE key broker image fix
- `fix/spire-mgmt-kubelet-egress` — SPIRE mgmt kubelet egress fix
- `platform/spire/` — existing SPIRE HelmRelease + proof jobs
- `platform/identity/` — existing identity HTTPRoute + OAuth2 proxy

## Definition of Done

- [ ] All 5 layers implemented and building
- [ ] Docker images built and tagged (`ghcr.io/chidionyema/idp/identity-bootstrapper`, `elpis-proxy`, `dros-daemon`)
- [ ] Schema deployed to ATP
- [ ] shadow-verify passes on throwaway k3d cluster
- [ ] Agent pod starts, bootstraps identity, signs requests, enforces kernel-level revocation
- [ ] Documentation: architectural decision recorded in `docs/specs/`
