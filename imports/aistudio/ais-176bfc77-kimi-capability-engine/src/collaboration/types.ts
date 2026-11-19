/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * GEMINI — P0 Universal Agent Collaboration Recovery
 * Types & Canonical Message Contract
 * Reconciles IDP #7794, #7790, #7490, #7771, Argon PR #40
 */

export type DiscoveryStatus = 
  | 'LIVE' 
  | 'IMPLEMENTED_BUT_UNDEPLOYED' 
  | 'PARTIAL' 
  | 'ABSENT' 
  | 'UNKNOWN';

export type AgentProvider = 'gemini' | 'kimi' | 'zai' | 'deepseek' | 'otto' | 'system_executor';

export type AgentConnectivity = 'CONNECTED' | 'DISCONNECTED' | 'READ_ONLY_SANDBOX' | 'UNKNOWN';

export interface EstateCapabilityAudit {
  id: string;
  name: string;
  ref: string;
  status: DiscoveryStatus;
  evidence: string;
  defectRootCause: string;
  smallestSafeIntegrationRepair: string;
  ownerRepo: 'chidionyema/idp' | 'chidionyema/argon' | 'shared';
}

export type UniversalMessageType = 
  | 'instruction' 
  | 'request' 
  | 'response' 
  | 'patch_submission' 
  | 'evidence' 
  | 'checkpoint' 
  | 'completion' 
  | 'failure' 
  | 'recovery';

export interface AgentIdentity {
  agent_id: string;
  provider: AgentProvider;
  authenticated: boolean;
  role: string;
  public_key?: string;
  signature?: string;
}

export interface AuthorityLeaseRef {
  lease_id: string;
  fenced_token: number;
  owner: string;
  acquired_at: string;
  expires_at: string;
  heartbeat_interval_seconds: number;
}

export interface ArtifactRef {
  id: string;
  filename: string;
  uri: string;
  sha256: string;
  mime_type: string;
  size_bytes: number;
}

/**
 * Phase 2: One Universal Agent Envelope
 * One message identity across all transports (NATS, HTTPS, Git peer board)
 */
export interface UniversalAgentEnvelope<T = any> {
  // Identity & Versioning
  message_id: string;
  schema_version: '1.0.0';
  correlation_id: string;

  // Mission & Instruction Hierarchy
  mission_id: string;
  instruction_id: string;
  attempt_id: number;

  // Authentication & Addressing
  sender: AgentIdentity;
  recipient: {
    agent_id: string;
    provider: AgentProvider | 'any';
    role: string;
  };

  // Semantics & Timing
  message_type: UniversalMessageType;
  timestamp: string;
  expiry: string;

  // Authority & Custody
  authority_lease_ref?: AuthorityLeaseRef;

  // Integrity & Content Digests
  context_digest: string;
  artifact_refs: ArtifactRef[];

  // Ordering & Deduplication
  idempotency_key: string;
  sequence: number;

  // Causal Chains
  acknowledgement_refs: string[];
  result_refs: string[];

  // Typed Payload
  payload: T;
}

export interface PatchSubmissionPayload {
  patch_id: string;
  repo: string;
  base_sha: string;
  target_branch: string;
  commit_message: string;
  unified_diff: string;
  files_changed: string[];
  lines_added: number;
  lines_deleted: number;
  verification_commands: string[];
}

export interface EvidencePayload {
  run_id: string;
  workflow_name: string;
  commit_sha: string;
  overall_status: 'SUCCESS' | 'FAILURE' | 'DEGRADED';
  failure_class?: string;
  diagnostics: Array<{
    code: string;
    file: string;
    line?: number;
    message: string;
    actionable_remediation?: string;
  }>;
  independent_verifier: string;
  evidence_sha256: string;
}

export interface CheckpointPayload {
  checkpoint_id: string;
  stage: string;
  state_snapshot: Record<string, any>;
  provenance_chain: string[];
  work_completed_ratio: number;
}

export interface StructuredFailurePayload {
  error_code: string;
  error_class: string;
  detail: string;
  can_retry: boolean;
  retry_count: number;
  max_retries: number;
  recoverable_next_action: string;
  incident_id?: string;
}

export interface GreenlaneEvidenceRecord {
  run_id: string;
  created_at: string;
  workflow_run_url: string;
  commit_sha: string;
  ref: string;
  sanitized: boolean;
  payload: EvidencePayload;
  immutable_digest: string;
  read_endpoint: string;
}

export interface AgentSessionInfo {
  agent_id: string;
  provider: AgentProvider;
  name: string;
  role: string;
  connectivity: AgentConnectivity;
  last_heartbeat: string;
  supported_transports: ('NATS' | 'HTTPS_ADAPTER' | 'GIT_PEER_BOARD')[];
  assigned_missions_count: number;
  unacknowledged_messages: number;
  credentials_type: 'AUTHENTICATED_MUTUAL_TLS' | 'BEARER_TOKEN' | 'READ_ONLY_ANONYMOUS';
}

export interface MissionCustodyRecord {
  mission_id: string;
  instruction_id: string;
  title: string;
  owner_agent: string;
  current_executor: string;
  status: 'PENDING_HANDOFF' | 'IN_EXECUTION' | 'COMPLETED' | 'STALLED_RECOVERED' | 'FAILED';
  fenced_token: number;
  last_checkpoint?: string;
  patch_id?: string;
  patch_pr_url?: string;
  greenlane_run_id?: string;
  greenlane_status?: 'PASSING' | 'FAILING' | 'PENDING' | 'REVERTED';
  started_at: string;
  updated_at: string;
  elapsed_seconds: number;
  recovery_trigger_seconds: number; // 600s
}

export interface AcceptanceScenarioResult {
  scenario_id: number;
  title: string;
  participating_agents: string[];
  transport_used: 'NATS' | 'HTTPS_ADAPTER' | 'GIT_PEER_BOARD';
  status: 'PASS' | 'PENDING' | 'FAIL';
  operational_evidence: string;
  verification_receipt_hash: string;
  duration_ms: number;
  notes: string;
}
