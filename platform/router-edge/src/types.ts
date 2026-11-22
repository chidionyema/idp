export interface Env {
  BUDGET_LEDGER: DurableObjectNamespace;
  ROUTING_STATE: DurableObjectNamespace;
  COMMIT_SHA: string;
  DEPLOYMENT_ZONE: string;
  DEFAULT_OUTPUT_FLOOR: string;
  UPSTREAM_TIMEOUT_MS: string;
  RESERVATION_TTL_MS: string;
  // Secrets (set via `wrangler secret put`)
  MERIDIAN_CLIENT_KEY: string;
  MERIDIAN_ADMIN_KEY: string;
  // Vendor / Lane-2 secrets resolved dynamically by backend.apiKeySecretName
  [secretName: string]: unknown;
}

export type LaneKind = "edge-direct" | "oci-pennyd";

export interface BackendCandidate {
  id: string;
  vendor: string;
  lane: LaneKind;
  baseUrl: string;              // e.g. "https://api.groq.com/openai/v1/chat/completions"
  apiKeySecretName: string;     // env binding name, never literal key
  upstreamModel: string;        // vendor model id
  maxContextTokens: number;     // hard prompt + output ceiling
  maxOutputTokens: number;      // hard output token ceiling
  supportsTools: boolean;
  priority: number;             // lower runs first
  costPer1kInputUsd: number;
  costPer1kOutputUsd: number;
  enabled: boolean;
}

export interface RolePool {
  role: string;                 // e.g. "role:coder", "role:architect", "role:verifier"
  minOutputFloor: number;       // >= 2048 unless explicitly lowered
  candidates: BackendCandidate[];
}

export interface CircuitRecord {
  failures: number;
  openUntilMs: number;
  learnedMaxContextTokens?: number;
  learnedMaxExpiresMs?: number;
  lastErrorCode?: number;
  lastErrorAtMs?: number;
}

export interface PlanRequest {
  role: string;
  estimatedInputTokens: number;
  requestedOutputTokens: number;
  requiresTools: boolean;
  excludeBackendIds?: string[];
}

export interface RejectedCandidate {
  id: string;
  reason: string;
}

export interface PlanResponse {
  role: string;
  effectiveOutputTokens: number;
  eligible: BackendCandidate[];
  rejected: RejectedCandidate[];
}

export interface ReserveRequest {
  reservationId: string;
  role: string;
  estimatedUsd: number;
  ttlMs: number;
}

export interface ReserveResponse {
  ok: boolean;
  code: "RESERVED" | "BUDGET_EXHAUSTED";
  remainingUsd: number;
  dailyLimitUsd: number;
  spentUsd: number;
  reservedUsd: number;
}

export interface SettleRequest {
  reservationId: string;
  actualUsd: number;
}

export interface ChatCompletionRequest {
  model: string;
  messages: Array<{ role: string; content: unknown; [k: string]: unknown }>;
  tools?: unknown[];
  tool_choice?: unknown;
  max_tokens?: number;
  max_completion_tokens?: number;
  stream?: boolean;
  [k: string]: unknown;
}