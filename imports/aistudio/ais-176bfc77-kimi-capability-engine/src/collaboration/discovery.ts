/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * GEMINI — P0 Universal Agent Collaboration Recovery
 * Phase 1: Rapid Discovery & Architectural Reconciliation
 */

import { EstateCapabilityAudit } from './types';

export const ESTATE_CAPABILITY_AUDIT: EstateCapabilityAudit[] = [
  {
    id: 'IDP-7794',
    name: 'Universal Agent Onboarding Contract',
    ref: 'chidionyema/idp#7794',
    status: 'PARTIAL',
    evidence: 'Onboarding schemas exist in idp/agents/onboarding.json but lack provider-agnostic token issuance for sandboxed agents (Z.ai / deepseek). Only native mTLS was provisioned.',
    defectRootCause: 'Assumed all agents have persistent bi-directional gRPC sockets, locking out browser-based and stateless sandboxed LLM agents.',
    smallestSafeIntegrationRepair: 'Add authenticated HTTPS Adapter endpoint accepting scoped Bearer tokens backed by existing IDP IAM service account authority.',
    ownerRepo: 'chidionyema/idp'
  },
  {
    id: 'IDP-7790',
    name: 'Continuity & Agent Takeover Mechanism',
    ref: 'chidionyema/idp#7790',
    status: 'IMPLEMENTED_BUT_UNDEPLOYED',
    evidence: 'Temporal workflow idp/workflows/agent_takeover.py implemented with 600s stall heartbeat, but worker queue lacked active listeners for external provider task slots.',
    defectRootCause: 'Lease takeover was coupled to synchronous founder Slack notifications instead of autonomous fence token lease reclamation.',
    smallestSafeIntegrationRepair: 'Wire 600s timeout directly into Temporal fenced lease manager with auto-recovery to IDP Executor.',
    ownerRepo: 'chidionyema/idp'
  },
  {
    id: 'IDP-7490',
    name: 'Common Communications Envelope',
    ref: 'chidionyema/idp#7490',
    status: 'PARTIAL',
    evidence: 'Initial protobuf schema idp/proto/agent_message.proto defined message_id and payload, but lacked correlation_id, idempotency_key, and lease authority refs.',
    defectRootCause: 'Transports (NATS vs Git peer board) used separate conflicting envelope wrappers, forcing founder to copy-paste payloads.',
    smallestSafeIntegrationRepair: 'Canonicalize UniversalAgentEnvelope v1.0.0 with single message identity and transport-agnostic serialization.',
    ownerRepo: 'chidionyema/idp'
  },
  {
    id: 'IDP-7771',
    name: 'Execution Ownership & Leases',
    ref: 'chidionyema/idp#7771',
    status: 'LIVE',
    evidence: 'Issue #7771 lease broker active in production with CLAIM-7771 mutex locks and 300s-600s TTLs.',
    defectRootCause: 'Functioning correctly for IDP core services, but external agent submissions bypassed the lease broker and ran in disconnected unmanaged child processes.',
    smallestSafeIntegrationRepair: 'Enforce that all patch submissions acquire a fenced authority lease before dispatch to Greenlane.',
    ownerRepo: 'chidionyema/idp'
  },
  {
    id: 'ARGON-PR-40',
    name: 'Argon Peer-Bus Proposal (Closed Unmerged)',
    ref: 'chidionyema/argon#40',
    status: 'ABSENT',
    evidence: 'PR #40 proposed a parallel Redis-based peer bus with custom gossip protocol; closed unmerged to avoid duplicate message brokers.',
    defectRootCause: 'Attempted to invent a new broker instead of using existing NATS JetStream and Git peer boards.',
    smallestSafeIntegrationRepair: 'Respect decision to reject PR #40; strictly route peer messaging over existing NATS JetStream + Git peer board fallback.',
    ownerRepo: 'chidionyema/argon'
  },
  {
    id: 'NATS-JETSTREAM',
    name: 'Existing NATS/JetStream Cluster & Streams',
    ref: 'infra/nats/jetstream-cluster.yaml',
    status: 'LIVE',
    evidence: 'Stream ESTATE_COLLABORATION active on nats://nats.idp.internal:4222 with memory/file storage and durable consumer offsets.',
    defectRootCause: 'Consumer lag was unmonitored for external agents, and NAKs lacked bounded exponential backoff resulting in retry storms.',
    smallestSafeIntegrationRepair: 'Configure max_deliver: 3, dead-letter stream dlq.estate.collaboration, and explicit ACK handling.',
    ownerRepo: 'chidionyema/idp'
  },
  {
    id: 'TEMPORAL-WORKFLOWS',
    name: 'Temporal Workflows & Custody Ledger',
    ref: 'idp/workflows/custody_ledger.py',
    status: 'LIVE',
    evidence: 'Temporal cluster temporal.idp.internal:7233 runs CustodyLedgerWorkflow tracking mission milestones and checkpoint hashes.',
    defectRootCause: 'Sandboxed agents had no direct ingress to submit checkpoints without gRPC credentials.',
    smallestSafeIntegrationRepair: 'Route HTTPS adapter checkpoint submissions directly into Temporal signal methods via existing gateway.',
    ownerRepo: 'chidionyema/idp'
  },
  {
    id: 'GIT-PEER-BOARD',
    name: 'Git-Backed Peer Board & Discovery Branches',
    ref: 'refs/heads/peer-board/collaboration-v1',
    status: 'PARTIAL',
    evidence: 'Branch refs/heads/peer-board exists with JSON manifests of active agents, but lacked atomic conflict resolution and fallback polling.',
    defectRootCause: 'Only updated manually during agent deployments; agents did not query it during NATS transport interruptions.',
    smallestSafeIntegrationRepair: 'Formalize Git Peer Board as an automated offline fallback with signed digest commits and reconciliation upon reconnect.',
    ownerRepo: 'chidionyema/argon'
  },
  {
    id: 'GREENLANE-REACTION',
    name: 'Greenlane Failure Reaction Workflow & State Ref',
    ref: '.github/workflows/greenlane-common-failure-reaction.yml',
    status: 'PARTIAL',
    evidence: 'Workflow triggers on workflow_run failure and reads refs/greenlane/state, but has NO machine-readable evidence output step. Kimi cannot read failure diagnostics.',
    defectRootCause: 'Workflow ends after updating internal status; missing a sanitized JSON projection step and public/authenticated read endpoint.',
    smallestSafeIntegrationRepair: 'Add versioned sanitized JSON evidence projection step publishing immutable run-specific record + atomic latest pointer.',
    ownerRepo: 'chidionyema/idp'
  },
  {
    id: 'FOUNDER-SURFACE-OTTO',
    name: 'Founder Surface, Otto & Genesis Projections',
    ref: 'argon/ui/founder_surface.tsx',
    status: 'PARTIAL',
    evidence: 'Dashboard shows overall cluster CPU and PR list, but lacks live cross-agent handoff queues, patch custody, and stuck lease alerts.',
    defectRootCause: 'Founder was forced to act as human copy-paste relay because agent handoffs were invisible until PR stage.',
    smallestSafeIntegrationRepair: 'Surface real-time agent connectivity, message custody ledger, Greenlane evidence links, and single-click recovery triggers.',
    ownerRepo: 'chidionyema/argon'
  }
];

export function getAuditSummary() {
  const counts = {
    LIVE: ESTATE_CAPABILITY_AUDIT.filter(a => a.status === 'LIVE').length,
    IMPLEMENTED_BUT_UNDEPLOYED: ESTATE_CAPABILITY_AUDIT.filter(a => a.status === 'IMPLEMENTED_BUT_UNDEPLOYED').length,
    PARTIAL: ESTATE_CAPABILITY_AUDIT.filter(a => a.status === 'PARTIAL').length,
    ABSENT: ESTATE_CAPABILITY_AUDIT.filter(a => a.status === 'ABSENT').length,
    UNKNOWN: ESTATE_CAPABILITY_AUDIT.filter(a => a.status === 'UNKNOWN').length,
  };

  return {
    total: ESTATE_CAPABILITY_AUDIT.length,
    counts,
    operationalHealthScore: Math.round(((counts.LIVE + (counts.PARTIAL * 0.5)) / ESTATE_CAPABILITY_AUDIT.length) * 100)
  };
}
