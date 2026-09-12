// Placement, summarised from the cluster-state receipt's `placement` section. Pure: the hook
// feeds it the receipt, the page draws what it returns, tests prove it on fixtures.
//
// WHY THIS EXISTS. bin/idp-fits-a-node grades placement in CI against a receipt the cluster writes
// every 15 minutes, and until now nothing showed that answer to a person. On 2026-09-12 the
// cluster sat at 96% of CPU REQUESTS while using 39%/85% of ACTUAL CPU, the second catalogue
// replica was Pending, and the only place that fact existed was a CI job's output. A measurement
// nobody reads is not an instrument.
//
// The receipt carries what the grader needs: every pod's request, whether the scheduler refused
// it, and how much room the best OTHER node has. This module turns that into the sentences a
// person reads, and names the three different facts that must not be collapsed into one:
//
//   refused          the scheduler will not place it at all          -> it is not running
//   pinned           it runs, but no other node would take it        -> one eviction from gone
//   fits             it could be placed again                        -> healthy
//
// "Pinned" is the one nobody sees coming: the pod looks fine because it already has its place,
// and it does not come back after a drain. That is the state SigNoz's ClickHouse sat in for eleven
// days.

export type PlacementPod = {
  namespace: string;
  name: string;
  kind?: string;
  cpu_request_m?: number | null;
  memory_request_mi?: number | null;
  unschedulable?: boolean;
  /** How much CPU the best OTHER node has free, when the receipt measured it. */
  best_other_cpu_free_m?: number | null;
  best_other_memory_free_mi?: number | null;
  /** The scheduler's own words when it refused. */
  reason?: string | null;
};

export type Placement = {
  at?: string;
  pods?: PlacementPod[];
  cpu_requested_m?: number | null;
  cpu_used_m?: number | null;
  cpu_allocatable_m?: number | null;
};

export type PlacementState = 'loading' | 'unavailable' | 'ready';

export type PlacementSummary = {
  state: PlacementState;
  summary: string;
  refused: PlacementPod[];
  pinned: PlacementPod[];
  /** Reserved but not used, across the cluster, when the receipt measured both. */
  idleM: number | null;
  requestedM: number | null;
  usedM: number | null;
};

const empty: PlacementSummary = {
  state: 'loading',
  summary: 'Reading placement…',
  refused: [],
  pinned: [],
  idleM: null,
  requestedM: null,
  usedM: null,
};

/** A pod is pinned when it is running but would fit on no other node, so an eviction loses it. */
export function isPinned(pod: PlacementPod): boolean {
  if (pod.unschedulable) return false;
  const need = pod.cpu_request_m ?? 0;
  const free = pod.best_other_cpu_free_m;
  if (free === null || free === undefined) return false;
  return free < need;
}

export function summarisePlacement(
  placement: Placement | null | undefined,
): PlacementSummary {
  if (!placement) return empty;

  const pods = placement.pods ?? [];
  const refused = pods.filter(p => p.unschedulable);
  const pinned = pods.filter(isPinned);

  const requestedM = placement.cpu_requested_m ?? null;
  const usedM = placement.cpu_used_m ?? null;
  const idleM =
    requestedM !== null && usedM !== null ? Math.max(0, requestedM - usedM) : null;

  const parts: string[] = [];
  if (refused.length) {
    // First, because a refused pod is a workload that is NOT running. Everything else is a risk;
    // this is an outage.
    parts.push(
      `${refused.length} pod${refused.length === 1 ? '' : 's'} the scheduler refused`,
    );
  }
  if (pinned.length) {
    parts.push(
      `${pinned.length} pinned (running, but no other node would take ${
        pinned.length === 1 ? 'it' : 'them'
      })`,
    );
  }
  if (idleM !== null && requestedM) {
    // The sentence that explains why a cluster can be full and idle at once: requests are
    // reservations, and a reservation nobody uses is a place no pod can have.
    const pct = Math.round((idleM / requestedM) * 100);
    parts.push(`${idleM}m reserved but idle (${pct}% of all requests)`);
  }
  if (!parts.length) {
    parts.push('every workload could be placed again');
  }

  return {
    state: 'ready',
    summary: parts.join(' · '),
    refused,
    pinned,
    idleM,
    requestedM,
    usedM,
  };
}

/** One row's request, as a cell. Null means the receipt did not say, which is not zero. */
export function requestLabel(pod: PlacementPod): string {
  if (pod.cpu_request_m === null || pod.cpu_request_m === undefined) return '—';
  return `${pod.cpu_request_m}m`;
}

/** How much room the best other node has. Null means not measured. */
export function headroomLabel(pod: PlacementPod): string {
  const free = pod.best_other_cpu_free_m;
  if (free === null || free === undefined) return '—';
  return `${free}m`;
}

/** Whether a pod's placement is a problem, and which one. */
export function placementState(pod: PlacementPod): 'refused' | 'pinned' | 'fits' {
  if (pod.unschedulable) return 'refused';
  return isPinned(pod) ? 'pinned' : 'fits';
}
