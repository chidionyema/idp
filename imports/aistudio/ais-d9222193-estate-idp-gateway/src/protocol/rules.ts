/**
 * Estate Governance Rules & Pinned Hash Reference
 *
 * ARCHITECTURAL CLARIFICATION & BOUNDARY:
 *   IDP server.py provides MCP context tool dispatch. Neither server.py nor local
 *   JSON paths establish an authorized administrative execution connection.
 *   Privileged mutations across the estate must execute via the canonical action-door
 *   broker under valid leases, not through simulated client shortcuts.
 *
 * ROLE OF THIS MODULE:
 *   CONSULT Observability & Candidate Invariant Harness.
 *   This client validates consensus rules hash binding (18e3ccdaee...) and candidate allowlists.
 */

import { ActionType, GovernanceClause, CANONICAL_OFFLINE_ALLOWLIST } from './types';

// The canonical cryptographically pinned governance rules hash from estate consensus
export const PINNED_RULES_HASH = '18e3ccdaee2a0cceff3ad85c777ddfe7b33255694844b6925a4d331b29a9f3dd';

// Candidate offline safe action allowlist for disconnected client testing (launch, back, home, wait)
// Unallowlisted mutations are refused offline without lease
export const CANONICAL_OFFLINE_ACTIONS = new Set<string>(CANONICAL_OFFLINE_ALLOWLIST);

// Registry of known declared canonical capabilities
export const KNOWN_CAPABILITIES = new Set([
  'git.fetch',
  'git.diff',
  'git.pr_sync',
  'contract.load',
  'contract.verify',
  'ci.triage',
  'ci.verdict',
  'linear.evidence',
  'linear.staleness',
  'linear.refresh',
  'receipt.query',
  'launch',
  'back',
  'home',
  'wait',
  'cluster.deploy',
  'cluster.cron_evaluate',
]);

export const GOVERNANCE_CLAUSES: GovernanceClause[] = [
  {
    clauseNumber: 1,
    name: 'One discovery pass',
    decidableByMachine: 'Partly',
    enforcementMode: 'linted',
    details: 'Batch reads, cap output near 10k tokens. Never repeat checks unless evidence digest changes.',
    requiredDeclaration: 'Task scope, output byte caps, evidence digest predicate',
  },
  {
    clauseNumber: 2,
    name: 'One plan, one execution cycle',
    decidableByMachine: 'Partly',
    enforcementMode: 'linted',
    details: 'Count micro-edits, path re-reads, and narration. Requires emitted artifact to distinguish plan vs execution.',
    requiredDeclaration: 'Plan artifact declaration, file edit quota',
  },
  {
    clauseNumber: 3,
    name: 'Medium reasoning; escalate for irreversible',
    decidableByMachine: 'No',
    enforcementMode: 'advice',
    details: 'Classification assigned by agent. Require cryptographic authority token for declared destructive ops.',
    requiredDeclaration: 'Irreversible action classes, authority tokens',
  },
  {
    clauseNumber: 4,
    name: 'Short-loop detection',
    decidableByMachine: 'Yes',
    enforcementMode: 'enforced',
    details: 'Fingerprints target, action, and evidence digest. Folder-agnostic normalization. Fails loud on corrupt state.',
    requiredDeclaration: 'Executable shortLoop validator with state fail-loud check',
  },
  {
    clauseNumber: 5,
    name: 'No speculative sweeps',
    decidableByMachine: 'No',
    enforcementMode: 'advice',
    details: 'Intent-based. Enforced by positive directory and dependency scope bounds rather than brittle denylists.',
    requiredDeclaration: 'Declared task boundary / allowed directories',
  },
  {
    clauseNumber: 6,
    name: 'Verification before reporting',
    decidableByMachine: 'Partly',
    enforcementMode: 'enforced',
    details: 'Canonical gateway guarantees receipt presence; reports must cite a valid receipt ID from data/receipts.',
    requiredDeclaration: 'Runtime issued receipts, receipt presence validation',
  },
  {
    clauseNumber: 7,
    name: 'Minimal communication',
    decidableByMachine: 'Mostly',
    enforcementMode: 'linted',
    details: 'Count messages per action and narration density. Volume throttling on agent turns.',
    requiredDeclaration: 'Message-to-state-change quota',
  },
  {
    clauseNumber: 8,
    name: 'Rough token allocation (10/60/20/10)',
    decidableByMachine: 'Measure only',
    enforcementMode: 'advice',
    details: 'Dashboard telemetry metric; hard gating would contradict simple tasks skipping phases.',
    requiredDeclaration: 'Telemetry phase labels (discovery, plan, impl, verify)',
  },
  {
    clauseNumber: 9,
    name: 'Automatic stop conditions',
    decidableByMachine: 'Yes',
    enforcementMode: 'enforced',
    details: 'Halt on repeated failure loop, missing lease/authority token, or active governance freeze order.',
    requiredDeclaration: 'Authority lease, repeat counter, freeze flags',
  },
];

/**
 * Validates that an envelope is bound to the exact canonical pinned rule hash.
 */
export function validateRulesHash(hash?: string): boolean {
  return hash === PINNED_RULES_HASH;
}

/**
 * Verifies if an action is within the canonical offline allowlist
 * per node_protocol.json:19 (launch, back, home, wait).
 */
export function isCanonicalOfflineSafeAction(action: string): boolean {
  return CANONICAL_OFFLINE_ACTIONS.has(action);
}

/**
 * Checks if a capability is known in the canonical estate registry.
 * If unknown, protocol mandates fallback to READ-ONLY.
 */
export function isKnownCapability(capability: string): boolean {
  return KNOWN_CAPABILITIES.has(capability);
}

/**
 * Determines whether the requested action is permitted under the rule state.
 * Unknown rules become read-only: any mutation ('mutation', 'safe_mutation', 'unsafe_mutation')
 * must be refused, while 'read' is allowed.
 */
export function checkActionPermissionForRule(
  capability: string,
  actionType: ActionType
): { allowed: boolean; readOnlyDowngrade: boolean } {
  const isKnown = isKnownCapability(capability);
  if (!isKnown) {
    if (actionType !== 'read') {
      return { allowed: false, readOnlyDowngrade: true };
    }
    return { allowed: true, readOnlyDowngrade: true };
  }
  return { allowed: true, readOnlyDowngrade: false };
}
