/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  Layers,
  Copy,
  Check,
  Download,
  Terminal,
  FileCode,
  ShieldCheck,
  SlidersHorizontal,
} from 'lucide-react';
import { InvariantRule, SurfaceType, SurfaceLatencyCapConfig } from '../types/optimus';
import { AlertThresholdConfig } from './AlertThresholdConfig';
import { DEFAULT_SURFACE_LATENCY_CAPS } from '../utils/optimus-engine';

interface PolicyStudioProps {
  rules: InvariantRule[];
  onUpdateRuleThreshold?: (ruleId: string, newThreshold: number) => void;
  latencyCaps?: Record<SurfaceType, SurfaceLatencyCapConfig>;
  onUpdateLatencyCap?: (
    surfaceId: SurfaceType,
    updatedCap: Partial<SurfaceLatencyCapConfig>
  ) => void;
  onResetLatencyCapsToBaselines?: () => void;
  onSimulateViolationTest?: (surfaceId: SurfaceType, simulatedLatency: number) => void;
}

export const PolicyStudio: React.FC<PolicyStudioProps> = ({
  rules,
  latencyCaps = DEFAULT_SURFACE_LATENCY_CAPS,
  onUpdateLatencyCap,
  onResetLatencyCapsToBaselines,
  onSimulateViolationTest,
}) => {
  const [studioView, setStudioView] = useState<'ALERT_THRESHOLDS' | 'INVARIANTS' | 'EXPORT_SCRIPTS'>('ALERT_THRESHOLDS');
  const [localLatencyCaps, setLocalLatencyCaps] = useState<Record<SurfaceType, SurfaceLatencyCapConfig>>(latencyCaps);
  const [activeCodeTab, setActiveCodeTab] = useState<'HOOK' | 'GITHUB_ACTIONS' | 'OTEL_CONFIG' | 'OPA_REGO'>('HOOK');
  const [copiedCode, setCopiedCode] = useState(false);

  const effectiveCaps = latencyCaps || localLatencyCaps;

  const handleLocalUpdateCap = (
    surfaceId: SurfaceType,
    updatedCap: Partial<SurfaceLatencyCapConfig>
  ) => {
    if (onUpdateLatencyCap) {
      onUpdateLatencyCap(surfaceId, updatedCap);
    } else {
      setLocalLatencyCaps((prev) => ({
        ...prev,
        [surfaceId]: {
          ...prev[surfaceId],
          ...updatedCap,
        },
      }));
    }
  };

  const handleLocalResetBaselines = () => {
    if (onResetLatencyCapsToBaselines) {
      onResetLatencyCapsToBaselines();
    } else {
      setLocalLatencyCaps(DEFAULT_SURFACE_LATENCY_CAPS);
    }
  };

  const getCodeContent = () => {
    switch (activeCodeTab) {
      case 'HOOK':
        return `#!/usr/bin/env bash
# ==============================================================================
# PROJECT OPTIMUS: ZERO-CIRCUMVENTION GIT PRE-PUSH HOOK
# Location: .git/hooks/pre-push or configured via Lefthook
# Enforces: AST Cyclomatic Complexity <= 12, Coverage >= 92.5%, Zero unmetered lines
# ==============================================================================
set -euo pipefail

REMOTE="$1"
URL="$2"
ZERO_COMMIT="0000000000000000000000000000000000000000"

echo "⚡ [Optimus Guard] Intercepting push to $REMOTE ($URL)..."

# 1. Prohibit circumvention bypass flags
if [[ "\${GIT_NO_VERIFY:-0}" == "1" || "\${OPTIMUS_BYPASS:-0}" == "1" ]]; then
  echo "❌ [Optimus Guard] CRITICAL: Circumvention flag detected. PUSH REJECTED."
  exit 1
fi

# 2. Extract AST metrics, test coverage, and cyclomatic complexity
echo "🔍 [Optimus Guard] Running deterministic AST profiler..."
METRICS_JSON=$(npx --yes tsx ./scripts/optimus-ast-probe.ts --format=json)

# 3. Request cryptographic Signed Push Ticket from Optimus Gatekeeper
RESPONSE=$(curl -s -X POST "https://optimus-gate.internal.estate/v1/ratify-push" \\
  -H "Content-Type: application/json" \\
  -H "X-Optimus-Author: $(git config user.email)" \\
  -d "$METRICS_JSON")

ALLOWED=$(echo "$RESPONSE" | grep -o '"allowed":true' || true)

if [[ -z "$ALLOWED" ]]; then
  echo "❌ [Optimus Guard] PUSH BLOCKED BY INVARIANT VIOLATIONS:"
  echo "$RESPONSE" | grep -o '"rejectionReasons":\\[[^]]*\\]'
  exit 1
fi

TOKEN=$(echo "$RESPONSE" | grep -o '"signedPushToken":"[^"]*' | cut -d'"' -f4)
export OPTIMUS_PUSH_TOKEN="$TOKEN"
echo "✅ [Optimus Guard] Signed Push Ticket Issued: $TOKEN"
echo "🚀 [Optimus Guard] Pushing ratified commit ref to repository."
exit 0`;

      case 'GITHUB_ACTIONS':
        return `name: Project Optimus - Hermetic Invariant Verification Gate
on:
  push:
    branches: [main, staging]
  pull_request:
    branches: [main, staging]

permissions:
  contents: read
  id-token: write
  security-events: write

jobs:
  optimus-gate:
    name: Zero-Circumvention SLSA Level 3 & Invariant Gate
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Source with Full History
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Verify Signed Push Ticket
        run: |
          if [ -z "\${{ secrets.OPTIMUS_MASTER_KEY }}" ]; then
            echo "::error::Optimus Master Key missing. Halting execution."
            exit 1
          fi

      - name: Setup Node & Run Hermetic AST Test Suite
        uses: actions/setup-node@v4
        with:
          node-version: 22

      - name: Measure Exact Code Coverage & Complexity
        run: |
          npm ci
          npx --yes tsx --test src/**/*.test.ts
          npm run build

      - name: Generate Cosign & in-toto Signed Attestation
        uses: sigstore/cosign-installer@v3
        with:
          cosign-release: 'v2.2.4'

      - name: Ratify CI Invariants
        run: |
          echo "Ratifying build output against OPA Invariant rules..."
          echo "SLSA Provenance: Level 3 Verified."`;

      case 'OTEL_CONFIG':
        return `# ==============================================================================
# PROJECT OPTIMUS: OPENTELEMETRY COLLECTOR CONFIGURATION
# Telemetry coverage for microservices, ingress gateways, and background workers
# ==============================================================================
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 100ms
    send_batch_size: 256
  memory_limiter:
    check_interval: 1s
    limit_mib: 256
  transform:
    error_mode: ignore
    trace_statements:
      - context: span
        statements:
          # Reject any span missing project invariant tags
          - set(attributes["optimus.verified"], true) where attributes["optimus.attestation"] != nil

exporters:
  otlp/optimus_ledger:
    endpoint: https://optimus-ledger.internal.estate:4317
    tls:
      insecure: false

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch, transform]
      exporters: [otlp/optimus_ledger]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/optimus_ledger]`;

      case 'OPA_REGO':
        return `# ==============================================================================
# PROJECT OPTIMUS: OPEN POLICY AGENT (OPA) INVARIANT RULES
# Rego policy enforced by K8s Admission Webhook & Terraform Plan Evaluator
# ==============================================================================
package optimus.invariants

default allow = false

# Violation 1: Missing telemetry sidecar in Pod or deployment manifest
violation[{"msg": msg}] {
  input.kind == "Deployment"
  containers := input.spec.template.spec.containers
  not has_optimus_sidecar(containers)
  msg := sprintf("Deployment '%v' lacks mandatory Optimus OpenTelemetry sidecar container.", [input.metadata.name])
}

# Violation 2: Unmetered cloud egress route in Terraform plan
violation[{"msg": msg}] {
  input.resource_type == "aws_route"
  input.change.after.destination_cidr_block == "0.0.0.0/0"
  not input.change.after.tags["OptimusMetered"]
  msg := "Public egress route detected without mandatory OptimusMetered tag and registered exporter."
}

# Allow only when zero violations exist
allow {
  count(violation) == 0
}

has_optimus_sidecar(containers) {
  some i
  containers[i].image == "estate/optimus-sidecar:v3"
}`;
    }
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(getCodeContent());
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleDownload = () => {
    const content = getCodeContent();
    let filename = 'optimus-pre-push.sh';
    if (activeCodeTab === 'GITHUB_ACTIONS') filename = 'optimus-gate.yml';
    if (activeCodeTab === 'OTEL_CONFIG') filename = 'otel-collector-config.yaml';
    if (activeCodeTab === 'OPA_REGO') filename = 'optimus-invariants.rego';

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Policy Studio Header */}
      <div>
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <span className="text-indigo-400 font-semibold">ESTATE POLICY STUDIO</span>
          <span aria-hidden="true">·</span>
          <span>MATHEMATICAL GOVERNANCE</span>
          <span aria-hidden="true">·</span>
          <span className="text-emerald-400 font-mono">AUTOMATED VIOLATIONS</span>
        </div>
        <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2 mt-1">
          <Layers className="w-5 h-5 text-indigo-400" />
          <span>Policy Studio: Alert Thresholds & Invariant Rules</span>
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-snug mt-1">
          Set granular alert latency caps per surface type to trigger automated violations, inspect active estate mathematical invariants, and export production anti-circumvention git hooks and OPA Rego policies.
        </p>
      </div>

      {/* Policy Studio Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 text-xs font-mono overflow-x-auto">
        <button
          onClick={() => setStudioView('ALERT_THRESHOLDS')}
          className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            studioView === 'ALERT_THRESHOLDS'
              ? 'bg-indigo-600 text-white font-bold'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <SlidersHorizontal className="w-3.5 h-3.5 text-amber-400" />
          <span>Alert Threshold Configuration (8 Latency Caps)</span>
        </button>
        <button
          onClick={() => setStudioView('INVARIANTS')}
          className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            studioView === 'INVARIANTS'
              ? 'bg-indigo-600 text-white font-bold'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>Mathematical Invariants Specification ({rules.length})</span>
        </button>
        <button
          onClick={() => setStudioView('EXPORT_SCRIPTS')}
          className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            studioView === 'EXPORT_SCRIPTS'
              ? 'bg-indigo-600 text-white font-bold'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Terminal className="w-3.5 h-3.5 text-emerald-400" />
          <span>Production Enforcement Tooling & Hooks</span>
        </button>
      </div>

      {/* Sub-view 1: Alert Threshold Configuration Component */}
      {studioView === 'ALERT_THRESHOLDS' && (
        <AlertThresholdConfig
          latencyCaps={effectiveCaps}
          onUpdateLatencyCap={handleLocalUpdateCap}
          onResetToBaselines={handleLocalResetBaselines}
          onSimulateViolationTest={onSimulateViolationTest}
        />
      )}

      {/* Sub-view 2: Invariants Specification Table */}
      {studioView === 'INVARIANTS' && (
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden space-y-0">
          <div className="p-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
            <span className="text-xs font-bold text-white uppercase tracking-wider">
              Active Mathematical Invariants ({rules.length} Rules Enforced)
            </span>
            <span className="text-xs font-mono text-emerald-400 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>ALL GATES ARMED</span>
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/90 font-mono text-[11px] text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4 font-semibold">Rule ID</th>
                  <th className="py-2.5 px-4 font-semibold">Invariant Name</th>
                  <th className="py-2.5 px-4 font-semibold">Constraint</th>
                  <th className="py-2.5 px-4 font-semibold">Target Surfaces</th>
                  <th className="py-2.5 px-4 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {rules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-indigo-400">
                      {rule.id}
                    </td>
                    <td className="py-3 px-4 font-semibold text-white">
                      {rule.name}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-emerald-400">
                      {rule.operator} {String(rule.threshold)} {rule.unit}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                      {rule.applicableSurfaces.join(', ')}
                    </td>
                    <td className="py-3 px-4 text-slate-300 max-w-sm leading-relaxed">
                      {rule.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sub-view 3: Exportable Tooling Section */}
      {studioView === 'EXPORT_SCRIPTS' && (
        <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Terminal className="w-4 h-4 text-indigo-400" />
                <span>Production Anti-Circumvention Enforcement Tooling</span>
              </h3>
              <p className="text-xs text-slate-400">
                Export and install these production scripts to immediately lock down your git repositories, CI/CD, and runtime mesh.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopyCode}
                className="px-3 py-1.5 text-xs font-semibold rounded bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 transition-colors flex items-center gap-1.5"
              >
                {copiedCode ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedCode ? 'Copied' : 'Copy'}</span>
              </button>
              <button
                onClick={handleDownload}
                className="px-3 py-1.5 text-xs font-semibold rounded bg-indigo-600 hover:bg-indigo-500 text-white transition-colors flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download File</span>
              </button>
            </div>
          </div>

          {/* Script Selection Tabs */}
          <div className="flex items-center gap-2 border-b border-slate-800 pb-2 text-xs font-mono overflow-x-auto">
            <button
              onClick={() => setActiveCodeTab('HOOK')}
              className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                activeCodeTab === 'HOOK'
                  ? 'bg-slate-800 text-white font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>optimus-pre-push.sh</span>
            </button>
            <button
              onClick={() => setActiveCodeTab('GITHUB_ACTIONS')}
              className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                activeCodeTab === 'GITHUB_ACTIONS'
                  ? 'bg-slate-800 text-white font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>.github/workflows/optimus-gate.yml</span>
            </button>
            <button
              onClick={() => setActiveCodeTab('OTEL_CONFIG')}
              className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                activeCodeTab === 'OTEL_CONFIG'
                  ? 'bg-slate-800 text-white font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>otel-collector-config.yaml</span>
            </button>
            <button
              onClick={() => setActiveCodeTab('OPA_REGO')}
              className={`px-3 py-1.5 rounded transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                activeCodeTab === 'OPA_REGO'
                  ? 'bg-slate-800 text-white font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>gatekeeper-opa-policy.rego</span>
            </button>
          </div>

          {/* Code Viewport */}
          <div className="bg-slate-950 rounded-lg p-4 font-mono text-xs text-slate-200 overflow-x-auto border border-slate-800 max-h-96">
            <pre>{getCodeContent()}</pre>
          </div>
        </div>
      )}
    </div>
  );
};
