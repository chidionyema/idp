// The estate graph, as one section on /ops (estate-twin, 2026-09-12).
//
// WHAT THIS ADDS. /ops already reads the cluster live -- nodes, pods, Kustomizations -- and
// that is a probe: it sees what a request to the API returns right now. The estate's graph
// is the other thing: what the estate has already recorded about ITSELF, including the half
// no probe can reach. A branch carrying 94,093 files that exist on no commit of main is not
// a cluster object; it is in the graph and nowhere else.
//
// The distinction the page must make, in the founder's own words: a probe tells you what is
// answering, the graph tells you what is true. Both are shown, and neither is allowed to
// read as the other.

/** One domain's state and the age of the reading that produced it. */
export type Domain = {
  domain: string;
  state: 'MEASURED_OK' | 'MEASURED_FAIL' | 'UNKNOWN';
  nodes: number;
  not_serving?: number;
  age_s: number | null;
  window_s: number;
};

/** One thing that is not serving, with only the fields that make it actionable. */
export type NotServing = {
  id: string;
  status: string;
  detail: Record<string, string | number>;
};

export type Evidence = { type: string; n: number };

export type EstateGraph = {
  read_at: string;
  domains: Domain[];
  counts: { domain: string; type: string; status: string; n: number }[];
  not_serving_total: number;
  not_serving: NotServing[];
  evidence: Evidence[];
  truncated: boolean;
  note?: string;
  why?: string;
};

export type Loaded =
  | { state: 'loading' }
  | { state: 'error'; error: string }
  | { state: 'ready'; graph: EstateGraph };

/**
 * Seconds as a person reads them. The graph's ages run from seconds to weeks, and "3153s"
 * is a number nobody converts in their head.
 */
export const ago = (seconds: number | null): string => {
  if (seconds === null || seconds === undefined) return 'never';
  if (seconds < 90) return `${seconds}s ago`;
  if (seconds < 5400) return `${Math.round(seconds / 60)}m ago`;
  if (seconds < 172800) return `${Math.round(seconds / 3600)}h ago`;
  return `${Math.round(seconds / 86400)}d ago`;
};

/**
 * The one sentence the section says.
 *
 * It leads with UNKNOWN when any domain is unknown, because a graph that has not been read
 * inside its window cannot be summarised as healthy -- that is the estate's own three-state
 * rule, and a page that buried it would be the failure the rule exists to prevent.
 */
export const graphSentence = (graph: EstateGraph): string => {
  if (graph.why) return graph.why;
  const unknown = graph.domains.filter(d => d.state === 'UNKNOWN');
  if (unknown.length) {
    return `${unknown.map(d => d.domain).join(' and ')} could not be trusted: the graph was last read ${ago(
      unknown[0].age_s,
    )} and the window is ${unknown[0].window_s}s. Everything below is a memory, not a reading.`;
  }
  const failing = graph.domains.filter(d => d.state === 'MEASURED_FAIL');
  if (!failing.length) {
    return `Nothing in the estate is unserved. ${graph.domains.reduce(
      (n, d) => n + d.nodes,
      0,
    )} things recorded, read ${ago(graph.domains[0]?.age_s ?? null)}.`;
  }
  const parts = failing.map(d => `${d.not_serving ?? 0} in ${d.domain}`);
  return `${parts.join(', ')} not serving, out of ${graph.not_serving_total} recorded across both domains. Read ${ago(
    failing[0].age_s,
  )}.`;
};

/** The domains as terse rows: state, name, what is wrong, and how old the reading is. */
export const domainRows = (graph: EstateGraph) =>
  graph.domains.map(d => ({
    domain: d.domain,
    state: d.state,
    detail:
      d.state === 'UNKNOWN'
        ? `last read ${ago(d.age_s)}, window ${d.window_s}s`
        : `${d.not_serving ?? 0} of ${d.nodes} not serving`,
    age: ago(d.age_s),
  }));

/** The worst offenders, already ordered by the tool: workloads before pods. */
export const worst = (graph: EstateGraph, n = 8) => graph.not_serving.slice(0, n);
