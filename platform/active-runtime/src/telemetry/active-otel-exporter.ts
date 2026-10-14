// src/telemetry/active-otel-exporter.ts
import { metrics, trace, SpanStatusCode, Attributes } from "@opentelemetry/api";
import { AttemptOutcomeStatus, TrustProvenance } from "../types/active-runtime";

export interface TelemetrySnapshot {
  prefetchCount: number;
  lastBriefTokens: number;
  factsPromoted: number;
  factsIgnoredEphemeral: number;
  factsBlockedStaleOrUntrusted: number;
  factsArchived: number;
  attemptsByOutcome: Record<AttemptOutcomeStatus, number>;
  strategyPivots: number;
  circuitBreakerTrips: number;
  approvalEvents: Record<
    "requested" | "approved" | "rejected" | "consumed" | "replay_or_hash_blocked",
    number
  >;
  totalCostUsd: number;
}

export class ActiveRuntimeTelemetry {
  private readonly tracer = trace.getTracer("active-agent-runtime", "1.0.0");
  private readonly meter = metrics.getMeter("active-agent-runtime", "1.0.0");

  // OpenTelemetry Histograms & Counters
  private readonly prefetchDurationHistogram = this.meter.createHistogram(
    "active_memory.prefetch.duration_ms",
    { description: "Latency of 1-hop Graph + Vector associative pre-fetch", unit: "ms" }
  );

  private readonly briefTokenHistogram = this.meter.createHistogram(
    "active_memory.brief.tokens",
    { description: "Token count of injected Active Context Brief", unit: "tokens" }
  );

  private readonly consolidationCounter = this.meter.createCounter(
    "active_memory.facts.consolidated_total",
    { description: "Total memory candidates processed by bi-temporal consolidation gate" }
  );

  private readonly archivedFactsCounter = this.meter.createCounter(
    "active_memory.facts.archived_total",
    { description: "Project-scoped facts retired on ticket completion" }
  );

  private readonly attemptCounter = this.meter.createCounter(
    "active_focus.attempts_total",
    { description: "Total agent tool/reasoning attempts partitioned by strategy class and outcome" }
  );

  private readonly pivotCounter = this.meter.createCounter(
    "active_focus.strategy_pivots_total",
    { description: "Number of times Active Focus locked a failing strategy class and forced a pivot" }
  );

  private readonly circuitBreakerCounter = this.meter.createCounter(
    "active_focus.circuit_breaker_trips_total",
    { description: "Hard halts triggered by budget, wall-clock, or exhausted strategy classes" }
  );

  private readonly approvalGateCounter = this.meter.createCounter(
    "active_focus.approval_gate_events_total",
    { description: "Consequential action gate events (requested, approved, rejected, blocked)" }
  );

  private readonly runCostHistogram = this.meter.createHistogram(
    "active_focus.run.cost_usd",
    { description: "Cumulative USD cost per agent run", unit: "usd" }
  );

  // Deterministic in-process snapshot for health checks & chaos tests
  private readonly state: TelemetrySnapshot = {
    prefetchCount: 0,
    lastBriefTokens: 0,
    factsPromoted: 0,
    factsIgnoredEphemeral: 0,
    factsBlockedStaleOrUntrusted: 0,
    factsArchived: 0,
    attemptsByOutcome: {
      progress: 0,
      blocked: 0,
      failed: 0,
      needs_info: 0,
      done: 0,
    },
    strategyPivots: 0,
    circuitBreakerTrips: 0,
    approvalEvents: {
      requested: 0,
      approved: 0,
      rejected: 0,
      consumed: 0,
      replay_or_hash_blocked: 0,
    },
    totalCostUsd: 0,
  };

  /**
   * Wraps any async runtime phase in an OpenTelemetry span with automatic error recording.
   */
  async withSpan<T>(
    spanName: string,
    attributes: Attributes,
    fn: () => Promise<T>
  ): Promise<T> {
    return this.tracer.startActiveSpan(spanName, { attributes }, async (span) => {
      try {
        const result = await fn();
        span.setStatus({ code: SpanStatusCode.OK });
        return result;
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        span.recordException(err instanceof Error ? err : new Error(message));
        span.setStatus({ code: SpanStatusCode.ERROR, message });
        throw err;
      } finally {
        span.end();
      }
    });
  }

  recordPrefetch(params: {
    tenantId: string;
    projectId?: string;
    durationMs: number;
    estimatedTokens: number;
  }): void {
    const attrs: Attributes = {
      tenant_id: params.tenantId,
      project_id: params.projectId ?? "global",
    };
    this.prefetchDurationHistogram.record(params.durationMs, attrs);
    this.briefTokenHistogram.record(params.estimatedTokens, attrs);
    this.state.prefetchCount += 1;
    this.state.lastBriefTokens = params.estimatedTokens;
  }

  recordConsolidation(params: {
    tenantId: string;
    provenance: TrustProvenance;
    promoted: number;
    ignoredEphemeral: number;
    blockedStaleOrUntrusted: number;
  }): void {
    const baseAttrs: Attributes = {
      tenant_id: params.tenantId,
      provenance: params.provenance,
    };

    if (params.promoted > 0) {
      this.consolidationCounter.add(params.promoted, {
        ...baseAttrs,
        resolution: "promoted",
      });
      this.state.factsPromoted += params.promoted;
    }

    if (params.ignoredEphemeral > 0) {
      this.consolidationCounter.add(params.ignoredEphemeral, {
        ...baseAttrs,
        resolution: "ignored_ephemeral",
      });
      this.state.factsIgnoredEphemeral += params.ignoredEphemeral;
    }

    if (params.blockedStaleOrUntrusted > 0) {
      this.consolidationCounter.add(params.blockedStaleOrUntrusted, {
        ...baseAttrs,
        resolution: "blocked_stale_or_untrusted",
      });
      this.state.factsBlockedStaleOrUntrusted += params.blockedStaleOrUntrusted;
    }
  }

  recordProjectArchival(tenantId: string, projectId: string, archivedCount: number): void {
    this.archivedFactsCounter.add(archivedCount, {
      tenant_id: tenantId,
      project_id: projectId,
    });
    this.state.factsArchived += archivedCount;
  }

  recordAttempt(params: {
    agentId: string;
    toolName: string;
    strategyClass: string;
    outcome: AttemptOutcomeStatus;
    costUsd: number;
  }): void {
    this.attemptCounter.add(1, {
      agent_id: params.agentId,
      tool_name: params.toolName,
      strategy_class: params.strategyClass,
      outcome: params.outcome,
    });
    this.state.attemptsByOutcome[params.outcome] += 1;
    this.state.totalCostUsd += params.costUsd;
  }

  recordStrategyPivot(params: {
    agentId: string;
    lockedStrategyClass: string;
    remainingClassesCount: number;
  }): void {
    this.pivotCounter.add(1, {
      agent_id: params.agentId,
      locked_strategy_class: params.lockedStrategyClass,
      remaining_classes: params.remainingClassesCount,
    });
    this.state.strategyPivots += 1;
  }

  recordCircuitBreakerTrip(params: { agentId: string; reason: string; totalRunCostUsd: number }): void {
    this.circuitBreakerCounter.add(1, {
      agent_id: params.agentId,
      reason: params.reason.slice(0, 120),
    });
    this.runCostHistogram.record(params.totalRunCostUsd, {
      agent_id: params.agentId,
      terminal_status: "circuit_breaker_halt",
    });
    this.state.circuitBreakerTrips += 1;
  }

  recordApprovalEvent(params: {
    agentId: string;
    toolName: string;
    event: "requested" | "approved" | "rejected" | "consumed" | "replay_or_hash_blocked";
  }): void {
    this.approvalGateCounter.add(1, {
      agent_id: params.agentId,
      tool_name: params.toolName,
      event: params.event,
    });
    this.state.approvalEvents[params.event] += 1;
  }

  getSnapshot(): TelemetrySnapshot {
    return JSON.parse(JSON.stringify(this.state)) as TelemetrySnapshot;
  }
}
