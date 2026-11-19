/**
 * Greenlane Failure Class Telemetry & Ranking
 * Sourced from IDP Greenlane workflow runs, landing history, and agent sandbox logs.
 */

import { GreenlaneFailureClass } from './types';

export const GREENLANE_FAILURE_CLASSES: GreenlaneFailureClass[] = [
  {
    id: 'GL-FAIL-042',
    canonicalName: 'Staged-Patch Working Tree Drift & Pre-Commit Formatting Desync',
    subsystem: 'PRE_COMMIT',
    rootCause:
      'Autonomous agents in sandbox stage partial file changes, leaving local linter/formatter (Ruff/Black/Prettier) fixes uncommitted. Remote Greenlane CI runner detects formatting drift or worktree mismatch, failing the build after 22 minutes.',
    baselineMetrics: {
      failureSharePercent: 41.2,
      failedRunCount: 48,
      wastedCiMinutes: 1056,
      averageRetriesPerBranch: 3.4,
      blockedDeliveriesCount: 32,
      estimatedCostUsd: 15840
    },
    recurrenceRisk: 'CRITICAL',
    remedyStrategy:
      'Staged-patch isolated worktree compilation + bounded 1-pass auto-stage safe repair + actionable line diagnostics.',
    preventionBoundary: 'PRE_COMMIT'
  },
  {
    id: 'GL-FAIL-019',
    canonicalName: 'Flaky Integration Test Dynamic Port Collision',
    subsystem: 'INTEGRATION_TEST',
    rootCause:
      'Concurrent CI runners in staging k8s cluster bind to hardcoded Redis/Postgres test ports (5432, 6379), causing intermittent socket bind failures during peak branch landing hours.',
    baselineMetrics: {
      failureSharePercent: 18.4,
      failedRunCount: 21,
      wastedCiMinutes: 441,
      averageRetriesPerBranch: 1.8,
      blockedDeliveriesCount: 14,
      estimatedCostUsd: 6615
    },
    recurrenceRisk: 'HIGH',
    remedyStrategy: 'Ephemeral port allocation with random socket fallback and mutex lock.',
    preventionBoundary: 'CI_GATE'
  },
  {
    id: 'GL-FAIL-007',
    canonicalName: 'Stale FLOW Task Claim Lease Lock Expiration',
    subsystem: 'AGENT_SANDBOX',
    rootCause:
      'Heavy integration runs exceeding 300s TTL cause Issue #7771 exclusive claim lock to expire before completion, triggering concurrent agent takeover and duplicate PR submissions.',
    baselineMetrics: {
      failureSharePercent: 14.1,
      failedRunCount: 16,
      wastedCiMinutes: 320,
      averageRetriesPerBranch: 1.2,
      blockedDeliveriesCount: 11,
      estimatedCostUsd: 4800
    },
    recurrenceRisk: 'MEDIUM',
    remedyStrategy: 'Heartbeat lease auto-extension in Genesis FLOW runner while process is active.',
    preventionBoundary: 'AGENT_SANDBOX_EXIT'
  },
  {
    id: 'GL-FAIL-033',
    canonicalName: 'Docker Multi-Architecture Build Cache Miss Timeout',
    subsystem: 'CONTAINER_BUILD',
    rootCause:
      'AMD64/ARM64 buildx cache eviction on ephemeral CI runners triggers 15+ minute cold re-compilation of C-extensions, exceeding the 20m runner step timeout.',
    baselineMetrics: {
      failureSharePercent: 12.3,
      failedRunCount: 14,
      wastedCiMinutes: 280,
      averageRetriesPerBranch: 1.1,
      blockedDeliveriesCount: 9,
      estimatedCostUsd: 4200
    },
    recurrenceRisk: 'MEDIUM',
    remedyStrategy: 'Distributed registry build cache (ghcr.io/cache-to=type=registry).',
    preventionBoundary: 'CI_GATE'
  },
  {
    id: 'GL-FAIL-011',
    canonicalName: 'Semantic Dependency Version Lockfile Pinning Drift',
    subsystem: 'CI_RUNNER',
    rootCause:
      'Agent edits package.json or pyproject.toml without updating bun.lock / poetry.lock, failing Greenlane frozen lockfile assertion in CI.',
    baselineMetrics: {
      failureSharePercent: 14.0,
      failedRunCount: 16,
      wastedCiMinutes: 304,
      averageRetriesPerBranch: 1.5,
      blockedDeliveriesCount: 12,
      estimatedCostUsd: 4560
    },
    recurrenceRisk: 'MEDIUM',
    remedyStrategy: 'Pre-push lockfile synchronization hook with automatic integrity checksum verify.',
    preventionBoundary: 'PRE_PUSH'
  }
];
