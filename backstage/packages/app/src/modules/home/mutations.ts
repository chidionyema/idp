// The "Pending mutations" tile's data (docs/tickets/2026-09-15-typed-multidomain-mutation-ledger.md,
// "The door"). Pure: no fetch here, see useMutations.ts. Read from
// `GET /api/proxy/fleetview/mutations` (backstage/plugins/fleetview-backend/src/mutations.py),
// which lists every ledger `propose_mutation` opened and not yet admitted or rejected.
export type Domain = 'code' | 'manifest' | 'sql';

export type PendingMutation = {
  ledger_id: string;
  claim: string;
  domains: Domain[];
  status: 'pending_verification' | 'verified';
  per_domain: Record<string, string>;
};

export type MutationsData = {
  mutations: PendingMutation[];
};

export const parseMutations = (raw: unknown): MutationsData => {
  const o = (raw ?? {}) as Partial<MutationsData>;
  if (!Array.isArray(o.mutations))
    throw new Error('/fleetview/mutations answered a shape mutations.py does not write');
  return { mutations: o.mutations as PendingMutation[] };
};

export const mutationsSentence = (d: MutationsData) =>
  d.mutations.length === 0
    ? 'No mutation ledger is waiting on you.'
    : `${d.mutations.length} mutation ledger${
        d.mutations.length === 1 ? '' : 's'
      } waiting on you.`;

// Never a Backstage-side approve label until the ledger has actually passed the gauntlet --
// a pending_verification ledger has no per-domain verdict yet, so its only honest action is
// reject (withdraw) or wait.
export const canApprove = (m: PendingMutation) => m.status === 'verified';
