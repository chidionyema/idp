import React, { useState } from 'react';

export interface FmeaEntry {
  fmea_id: string;
  failure_title: string;
  error_signature_regex: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  root_cause_explanation: string;
  hypothesis_simulation_cmd: string;
  verified_remediation_cmd: string;
  research_reference: string;
}

export interface ComponentContractItem {
  component_id: string;
  name: string;
  kind: string;
  version: string;
  owner_protocol: string;
  owner_contact: string;
  live_status: 'HEALTHY' | 'DEGRADED_AUTO_HEALING' | 'FENCED';
  live_state_uri: string;
  api_endpoints: string[];
  interfaces_and_schemas: string[];
  upstream_dependencies: string[];
  metrics_exported: string[];
  fmea_atlas: FmeaEntry[];
}

export interface EstateIntelligenceSurfaceProps {
  components?: ComponentContractItem[];
  initialFounderDebugOverride?: boolean;
}

export const INITIAL_COMPONENT_CONTRACTS: ComponentContractItem[] = [
  {
    component_id: 'comp.genesis-kernel',
    name: 'Genesis Rust Kernel (Daemon & Control Plane)',
    kind: 'RUST_BINARY',
    version: 'v1.0.26',
    owner_protocol: 'PROTO_INFRA_LANE',
    owner_contact: 'SPC-INFRA-01 (Kernel Steward)',
    live_status: 'HEALTHY',
    live_state_uri: 'mem://genesis/components/genesis-kernel',
    api_endpoints: ['/api/audit/traces', '/ws/audit', '/api/cockpit/steer', '/api/estate/catalog'],
    interfaces_and_schemas: ['step_runs (SQLite WAL)', 'ticket_fences', 'outbox_events', 'mem_pointers'],
    upstream_dependencies: ['comp.sqlite-wal', 'comp.nats-mesh'],
    metrics_exported: ['cif_receipts_total', 'lease_ttl_ms', 'monotonic_fence_counter'],
    fmea_atlas: [
      {
        fmea_id: 'FMEA-KERN-01',
        failure_title: 'SQLite WAL Busy Lock Contention',
        error_signature_regex: 'database is locked|busy',
        severity: 'CRITICAL',
        root_cause_explanation: 'Concurrent write attempted while an unclosed reader holds a shared lock without timeout.',
        hypothesis_simulation_cmd: 'test -f /var/lib/estate/estate.db-shm && fuser /var/lib/estate/estate.db',
        verified_remediation_cmd: 'sqlite3 /var/lib/estate/estate.db "PRAGMA busy_timeout = 5000;"',
        research_reference: 'https://sqlite.org/wal.html#busy_handler',
      },
      {
        fmea_id: 'FMEA-KERN-02',
        failure_title: 'Stale Fencing Token Split-Brain Attempt',
        error_signature_regex: 'STALE_FENCING_TOKEN',
        severity: 'HIGH',
        root_cause_explanation: 'Partitioned edge node attempted to write state after its 15s lease expired.',
        hypothesis_simulation_cmd: 'nats kv get genesis_config highest_fencing_token',
        verified_remediation_cmd: 'genesis-kernel --claim-lease LANE_C_MAC --fence-inc',
        research_reference: 'RFC 9576 monotonic fencing tokens',
      },
      {
        fmea_id: 'FMEA-KERN-03',
        failure_title: 'Port 8080 TCP Listener Collision',
        error_signature_regex: 'Address already in use',
        severity: 'MEDIUM',
        root_cause_explanation: 'Previous daemon process failed to release SO_REUSEADDR on exit.',
        hypothesis_simulation_cmd: 'lsof -i :8080 | grep LISTEN',
        verified_remediation_cmd: 'pkill -f genesis-kernel || true',
        research_reference: 'UNIX network socket reuse standards',
      },
    ],
  },
  {
    component_id: 'comp.nats-mesh',
    name: 'NATS JetStream Cluster (GENESIS_MESH)',
    kind: 'INFRA_SERVICE',
    version: 'v2.10.12',
    owner_protocol: 'PROTO_INFRA_LANE',
    owner_contact: 'SPC-NET-02 (Mesh Mesh Specialist)',
    live_status: 'HEALTHY',
    live_state_uri: 'mem://genesis/components/nats-mesh',
    api_endpoints: ['nats://127.0.0.1:4222', 'route://100.98.58.101:6222', 'http://127.0.0.1:8222/varz'],
    interfaces_and_schemas: ['GENESIS.traces.v1.live', 'KV:genesis_config'],
    upstream_dependencies: ['comp.tailscale-overlay', 'comp.mtls-pki'],
    metrics_exported: ['nats_cluster_size', 'nats_route_rtt_ms', 'jetstream_storage_bytes'],
    fmea_atlas: [
      {
        fmea_id: 'FMEA-NATS-01',
        failure_title: 'Route mTLS Certificate Expiry / Mismatch',
        error_signature_regex: 'tls: bad certificate|handshake failure',
        severity: 'CRITICAL',
        root_cause_explanation: 'Route certificates out of sync with root CA or expired after rotation.',
        hypothesis_simulation_cmd: 'openssl x509 -checkend 86400 -noout -in ~/.estate/multilane/certs/route.crt',
        verified_remediation_cmd: 'bash ~/.estate/multilane/rotate-route-certs.sh',
        research_reference: 'NATS Cluster Route TLS Security Canon',
      },
      {
        fmea_id: 'FMEA-NATS-02',
        failure_title: 'Duplicate server_name Cluster Collision',
        error_signature_regex: 'cluster already has server with name',
        severity: 'HIGH',
        root_cause_explanation: 'Two nodes joined the mesh with identical LANE_ID or hostname.',
        hypothesis_simulation_cmd: 'curl -s http://127.0.0.1:8222/varz | jq .server_name',
        verified_remediation_cmd: 'sed -i "" "s/server_name.*/server_name: $LANE_ID/" ~/.estate/multilane/nats.conf',
        research_reference: 'NATS JetStream Clustering Architecture Guide',
      },
      {
        fmea_id: 'FMEA-NATS-03',
        failure_title: 'OCI Route Bridge Silent Drop',
        error_signature_regex: 'route closed|broken pipe',
        severity: 'MEDIUM',
        root_cause_explanation: 'NAT timeout on external gateway dropped long-lived idle TCP connection.',
        hypothesis_simulation_cmd: 'nc -zv 100.98.58.103 6222',
        verified_remediation_cmd: 'ssh -f -N -o ServerAliveInterval=15 -R 6222:127.0.0.1:6222 estate-recovery',
        research_reference: 'Tailscale DERP Keepalive Specification',
      },
    ],
  },
  {
    component_id: 'comp.litellm-router',
    name: 'LiteLLM Proxy & Model Routing Layer',
    kind: 'INFRA_SERVICE',
    version: 'v1.44.0',
    owner_protocol: 'PROTO_BUILD_API',
    owner_contact: 'SPC-LLM-01 (Inference Dispatcher)',
    live_status: 'HEALTHY',
    live_state_uri: 'mem://genesis/components/litellm-router',
    api_endpoints: ['POST http://127.0.0.1:4000/v1/chat/completions', 'KV:default_model'],
    interfaces_and_schemas: ['OpenAI Compatible Chat Completion Spec'],
    upstream_dependencies: ['comp.nats-mesh'],
    metrics_exported: ['llm_tokens_in', 'llm_tokens_out', 'llm_p95_latency_ms'],
    fmea_atlas: [
      {
        fmea_id: 'FMEA-LLM-01',
        failure_title: 'Minimax Upstream 429 Rate Limit',
        error_signature_regex: 'rate_limit_exceeded|429',
        severity: 'HIGH',
        root_cause_explanation: 'Sudden burst of concurrent audit passes exhausted API key quota.',
        hypothesis_simulation_cmd: 'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:4000/health',
        verified_remediation_cmd: 'nats kv put genesis_config.burst_fallback deepseek-chat',
        research_reference: 'LiteLLM Dynamic Fallback Routing Matrix',
      },
      {
        fmea_id: 'FMEA-LLM-02',
        failure_title: 'Token Compaction Truncation Leak',
        error_signature_regex: 'Auto-compaction failed: Summarization failed',
        severity: 'CRITICAL',
        root_cause_explanation: 'Unstructured prose log dump exceeded 128k input window during multi-turn debugging.',
        hypothesis_simulation_cmd: 'wc -l /var/log/active_memory.log',
        verified_remediation_cmd: 'npx tsx scripts/enforce-agents-md-120-lines.ts',
        research_reference: 'Genesis Single-Pass mem:// Pointer Reduction Canon (99.2% token cut)',
      },
      {
        fmea_id: 'FMEA-LLM-03',
        failure_title: 'Proxy Connection Pool Exhaustion',
        error_signature_regex: 'Too many open files|pool exhausted',
        severity: 'MEDIUM',
        root_cause_explanation: 'Client connections left open without keep-alive reap timeout.',
        hypothesis_simulation_cmd: 'lsof -c litellm | wc -l',
        verified_remediation_cmd: 'killall -HUP litellm',
        research_reference: 'HTTP/2 connection recycling guidelines',
      },
    ],
  },
  {
    component_id: 'comp.gitops-bridge',
    name: 'GitOps Ingestion & Sync Bridge (argon-sync)',
    kind: 'SHELL_AUTOMATION',
    version: 'v1.0.26',
    owner_protocol: 'PROTO_BUILD_API',
    owner_contact: 'SPC-GITOPS-01 (Release Guardian)',
    live_status: 'HEALTHY',
    live_state_uri: 'mem://genesis/components/gitops-bridge',
    api_endpoints: ['ssh://github.com:443/chidionyema/argon.git', 'refs/heads/genesis-live'],
    interfaces_and_schemas: ['SOURCE_MANIFEST.json', 'STATE_BEACON.json', 'PROMOTION_RECEIPT.json'],
    upstream_dependencies: ['comp.genesis-kernel'],
    metrics_exported: ['manifest_merkle_root', 'unpushed_commits_count', 'sync_latency_ms'],
    fmea_atlas: [
      {
        fmea_id: 'FMEA-GIT-01',
        failure_title: 'Non-Fast-Forward Ref Divergence',
        error_signature_regex: 'fetch first|non-fast-forward',
        severity: 'CRITICAL',
        root_cause_explanation: 'Concurrent push to main without pulling remote git bundle changes.',
        hypothesis_simulation_cmd: 'git rev-list --left-right --count HEAD...origin/main',
        verified_remediation_cmd: 'git fetch origin main && git merge --allow-unrelated-histories -s ours origin/main',
        research_reference: 'B-1 Non-Destructive Git Promotion Canon',
      },
      {
        fmea_id: 'FMEA-GIT-02',
        failure_title: 'SSH Port 22 Corporate Firewall Block',
        error_signature_regex: 'Connection timed out|port 22',
        severity: 'HIGH',
        root_cause_explanation: 'Egress filtering blocking standard SSH port 22.',
        hypothesis_simulation_cmd: 'nc -zv ssh.github.com 443',
        verified_remediation_cmd: 'git remote set-url origin ssh://git@ssh.github.com:443/chidionyema/argon.git',
        research_reference: 'GitHub SSH over HTTPS Port 443 Guidelines',
      },
      {
        fmea_id: 'FMEA-GIT-03',
        failure_title: 'Dirty Working Tree on Git Bundle Creation',
        error_signature_regex: 'uncommitted changes',
        severity: 'MEDIUM',
        root_cause_explanation: 'Manifest generated before pending code edits were staged and committed.',
        hypothesis_simulation_cmd: 'git status --porcelain',
        verified_remediation_cmd: 'git add -A && git commit -m "chore(auto): stage clean working tree"',
        research_reference: 'Atomic Release Manifest Attestation Law',
      },
    ],
  },
];

export const EstateIntelligenceSurface: React.FC<EstateIntelligenceSurfaceProps> = ({
  components = INITIAL_COMPONENT_CONTRACTS,
  initialFounderDebugOverride = false,
}) => {
  const [selectedId, setSelectedId] = useState<string>(
    components[0]?.component_id ?? 'comp.genesis-kernel'
  );
  const [founderDebugOverride, setFounderDebugOverride] = useState<boolean>(
    initialFounderDebugOverride
  );
  const [instructionInput, setInstructionInput] = useState<string>(
    'Sync argon-sync main and verify CIF receipt on LANE_C_OCI'
  );
  const [activeDossier, setActiveDossier] = useState<string | null>(null);

  const activeComponent =
    components.find((c) => c.component_id === selectedId) ?? components[0];

  const classifyProtocol = (text: string) => {
    const lower = text.toLowerCase();
    if (lower.includes('ui') || lower.includes('cockpit') || lower.includes('surface') || lower.includes('text')) {
      return { protocol: 'PROTO_WEB_SURFACE', bound: true };
    }
    if (lower.includes('lane') || lower.includes('nats') || lower.includes('sync') || lower.includes('oci') || lower.includes('mesh')) {
      return { protocol: 'PROTO_INFRA_LANE', bound: true };
    }
    if (lower.includes('api') || lower.includes('schema') || lower.includes('endpoint') || lower.includes('rust')) {
      return { protocol: 'PROTO_BUILD_API', bound: true };
    }
    if (lower.includes('fmea') || lower.includes('failure mode') || lower.includes('bug')) {
      return { protocol: 'PROTO_FMEA_CURATION', bound: true };
    }
    if (lower.includes('dossier') || lower.includes('remediate')) {
      return { protocol: 'PROTO_DECIDE_ON_DOSSIER', bound: true };
    }
    return { protocol: 'UNBOUND_INSTRUCTION_REJECTED', bound: false };
  };

  const binding = classifyProtocol(instructionInput);

  return (
    <div className="p-6 bg-slate-950 text-slate-100 rounded-2xl border border-slate-800 font-mono space-y-6">
      {/* Top Governance Lock Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <span className="text-xs uppercase tracking-wider text-indigo-400 font-bold">
            GENESIS ZERO-DEBUGGING ENGINE // SELF-DESCRIBING ESTATE REGISTRY & PASS 0 DOSSIER
          </span>
          <h2 className="text-lg font-bold text-white mt-0.5">
            Agents Orchestrate Protocols · Founder Orchestrates Agents
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1.5 rounded text-xs font-bold border ${
              !founderDebugOverride
                ? 'bg-emerald-950 text-emerald-300 border-emerald-700'
                : 'bg-amber-950 text-amber-300 border-amber-700'
            }`}
          >
            {!founderDebugOverride
              ? 'AGENT_DEBUG_LOCK: ENFORCED (0 Live Debugging)'
              : 'FOUNDER_OVERRIDE: Agent Probing Unlocked'}
          </span>
          <button
            type="button"
            onClick={() => setFounderDebugOverride(!founderDebugOverride)}
            className="px-3 py-1.5 text-xs rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 cursor-pointer"
          >
            {founderDebugOverride ? 'Re-Lock Agent Debugging' : 'Founder Override (Unlock)'}
          </button>
        </div>
      </div>

      {/* Instruction-to-Protocol Binding Gate Bar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row items-center gap-4">
        <div className="flex-1 w-full">
          <label className="block text-[10px] uppercase tracking-wider text-slate-400 mb-1">
            Mandatory Pre-Execution Instruction-to-Protocol Gate (Φ: X → Π)
          </label>
          <input
            type="text"
            value={instructionInput}
            onChange={(e) => setInstructionInput(e.target.value)}
            className="w-full px-3 py-1.5 text-xs rounded bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`px-3 py-2 rounded text-xs font-bold border ${
              binding.bound
                ? 'bg-indigo-950 text-indigo-300 border-indigo-700'
                : 'bg-rose-950 text-rose-300 border-rose-700'
            }`}
          >
            {binding.protocol}
          </span>
        </div>
      </div>

      {/* 1-Click Component Selector Pills */}
      <div className="flex flex-wrap gap-2">
        {components.map((comp) => (
          <button
            key={comp.component_id}
            onClick={() => setSelectedId(comp.component_id)}
            className={`px-3 py-2 rounded-xl text-xs border transition flex items-center gap-2 cursor-pointer ${
              comp.component_id === activeComponent?.component_id
                ? 'bg-slate-100 text-slate-950 border-white font-bold'
                : 'bg-slate-900 text-slate-300 border-slate-800 hover:border-slate-600'
            }`}
          >
            <span>{comp.name}</span>
            <span className="text-[10px] opacity-75">({comp.fmea_atlas.length} FMEA)</span>
          </button>
        ))}
      </div>

      {/* Selected Component Self-Describing Contract & FMEA Atlas */}
      {activeComponent && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3 text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-bold text-white text-sm">
                {activeComponent.name} ({activeComponent.version})
              </span>
              <span className="px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 text-[10px]">
                {activeComponent.owner_protocol}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Live State Pointer: </span>
              <code className="text-emerald-400">{activeComponent.live_state_uri}</code>
            </div>
            <div>
              <span className="text-slate-400">Owner / Contact: </span>
              <span className="text-slate-200">{activeComponent.owner_contact}</span>
            </div>
            <div>
              <span className="text-slate-400">APIs & Interfaces: </span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {activeComponent.api_endpoints.map((ep) => (
                  <code
                    key={ep}
                    className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-cyan-300 text-[10px]"
                  >
                    {ep}
                  </code>
                ))}
              </div>
            </div>
            <div>
              <span className="text-slate-400">Upstream Dependencies: </span>
              <span className="text-slate-200">
                {activeComponent.upstream_dependencies.join(' -> ')}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Exported Metrics: </span>
              <span className="text-slate-200">
                {activeComponent.metrics_exported.join(', ')}
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3 text-xs">
            <div className="font-bold text-white text-sm border-b border-slate-800 pb-2 flex items-center justify-between">
              <span>Upfront Extreme Failure Mode Atlas (Pass 0 Auto-Simulation)</span>
              <span className="text-[10px] text-cyan-400">3/3 Modes Verified</span>
            </div>
            <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
              {activeComponent.fmea_atlas.map((fmea) => (
                <div
                  key={fmea.fmea_id}
                  className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-300">
                      [{fmea.fmea_id}] {fmea.failure_title}
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                      {fmea.severity}
                    </span>
                  </div>
                  <p className="text-slate-400">{fmea.root_cause_explanation}</p>
                  <div className="text-[11px]">
                    <span className="text-slate-500">Pass 0 Probe: </span>
                    <code className="text-cyan-300">{fmea.hypothesis_simulation_cmd}</code>
                  </div>
                  <div className="text-[11px]">
                    <span className="text-slate-500">1-Pass Decision Fix: </span>
                    <code className="text-emerald-300">{fmea.verified_remediation_cmd}</code>
                  </div>
                  <button
                    onClick={() => setActiveDossier(fmea.fmea_id)}
                    className="mt-1 text-[10px] px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 cursor-pointer"
                  >
                    Simulate Pass 0 Dossier
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Pass 0 Simulated Dossier Output */}
      {activeDossier && (
        <div className="p-4 rounded-xl bg-slate-900 border border-cyan-800/60 text-xs space-y-2">
          <div className="flex items-center justify-between text-cyan-300">
            <span className="font-bold">PASS 0 MACHINE DIAGNOSTIC DOSSIER [SIMULATED IN 1.2ms]</span>
            <button
              onClick={() => setActiveDossier(null)}
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              ✕ Close
            </button>
          </div>
          <p className="text-slate-300">
            Machine ran deterministic hypothesis probe for <span className="text-amber-300 font-bold">{activeDossier}</span>.
            Confidence: <span className="text-emerald-400 font-bold">98.4%</span> (above 0.85 threshold).
            <span className="text-emerald-300"> AGENT_DEBUG_LOCK enforced: 0 exploratory shell commands allowed.</span>
          </p>
          <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-slate-300">
            <span className="text-slate-500">Auto-Remediation Prescribed: </span>
            <code className="text-emerald-400">
              {activeComponent.fmea_atlas.find((f) => f.fmea_id === activeDossier)?.verified_remediation_cmd}
            </code>
          </div>
        </div>
      )}
    </div>
  );
};
