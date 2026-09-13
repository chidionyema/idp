// The compiled estate, summarised from the document `bin/idp-compile-helm` writes. Pure: the hook
// feeds it the document, the page draws what it returns, tests prove it on fixtures.
//
// WHY. On 2026-09-12 a right-sizing that had been merged for five days was not in the cluster. The
// pull request changed a COMMENT claiming "cpu 500m" and left the VALUE at 1000m; CI was green
// because the YAML was valid; the cluster kept running 1000m. The only way to see it was to render
// the chart by hand.
//
// This module turns the compiled document into the sentence a person reads. It has no opinion: the
// number it shows is always the one the chart RENDERS, because that is the one the cluster runs. A
// comment, a values file, and a postRenderer patch are all claims, and a claim is not a
// measurement.

export type CompiledContainer = {
  name?: string;
  requests?: Record<string, string> | null;
  limits?: Record<string, string> | null;
};

export type CompiledObject = {
  apiVersion?: string;
  kind?: string;
  namespace?: string;
  name?: string;
  resources?: CompiledContainer[];
};

export type CompiledRelease = {
  namespace: string;
  name: string;
  file?: string;
  chart?: string | null;
  version?: string | null;
  repository?: string;
  values_sources?: string[];
  objects?: CompiledObject[];
  error?: string | null;
};

export type CompiledDoc = {
  releases?: CompiledRelease[];
  summary?: { total?: number; rendered?: number; failed?: number; objects?: number };
};

export type CompiledState = 'loading' | 'unavailable' | 'ready';

export type CompiledSummary = {
  state: CompiledState;
  summary: string;
  /** Releases whose chart could not be rendered. Their numbers are unknown, never assumed. */
  unrendered: CompiledRelease[];
  /** Every workload the estate renders, with the resources the CHART decided. */
  workloads: {
    release: string;
    namespace: string;
    kind: string;
    name: string;
    containers: CompiledContainer[];
  }[];
};

const empty: CompiledSummary = {
  state: 'loading',
  summary: 'Compiling the estate…',
  unrendered: [],
  workloads: [],
};

/** `500m` -> 500, `1` -> 1000. Kubernetes CPU quantities. */
export function millicores(cpu: string | undefined | null): number | null {
  if (!cpu) return null;
  if (cpu.endsWith('m')) return Number(cpu.slice(0, -1));
  const n = Number(cpu);
  return Number.isFinite(n) ? n * 1000 : null;
}

export function summariseCompiled(doc: CompiledDoc | null | undefined): CompiledSummary {
  if (!doc) return empty;

  const releases = doc.releases ?? [];
  if (!releases.length) {
    return {
      state: 'unavailable',
      summary: 'The estate compiled no Helm releases, which cannot be right: it has thirty-one.',
      unrendered: [],
      workloads: [],
    };
  }

  const unrendered = releases.filter(r => r.error);
  const workloads: CompiledSummary['workloads'] = [];
  for (const r of releases) {
    for (const o of r.objects ?? []) {
      if (!o.resources?.length) continue;
      workloads.push({
        release: r.name,
        namespace: o.namespace ?? r.namespace,
        kind: o.kind ?? '?',
        name: o.name ?? '?',
        containers: o.resources,
      });
    }
  }

  const total = doc.summary?.total ?? releases.length;
  const rendered = doc.summary?.rendered ?? total - unrendered.length;
  const parts = [`${rendered} of ${total} charts render`];
  if (workloads.length) {
    // Workloads, not objects: the count a person can act on is how many things will run.
    parts.push(`${workloads.length} workload${workloads.length === 1 ? '' : 's'}`);
  }
  if (unrendered.length) {
    // Named, never counted silently. An unrendered chart is a workload whose numbers nobody knows,
    // so it must appear even when every other release is fine.
    parts.push(
      `${unrendered.length} could NOT be rendered: ${unrendered
        .map(r => `${r.namespace}/${r.name}`)
        .join(', ')}`,
    );
  }

  return {
    state: unrendered.length ? 'unavailable' : 'ready',
    summary: parts.join(' · '),
    unrendered,
    workloads,
  };
}

/** A container's rendered cpu, as a cell. Null is a dash: the chart did not set one, which is not
 *  the same as setting zero. */
export function cpuLabel(c: CompiledContainer): string {
  return c.requests?.cpu ?? '—';
}

/** Whether a container's rendered request equals its rendered limit, which is what makes the pod
 *  Guaranteed and therefore evicted last. `require-priority-class` refuses a split on the
 *  radio-room set, so a split here is a change that would be rejected at admission. */
export function guaranteed(c: CompiledContainer): boolean {
  const req = c.requests?.cpu;
  const lim = c.limits?.cpu;
  return Boolean(req) && req === lim;
}
