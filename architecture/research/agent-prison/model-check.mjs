/**
 * Bounded falsifier for the IDP instruction-to-yield causal-ledger hypothesis.
 * This models a trusted finality sink. It does NOT claim that IDP currently implements it.
 * No trusted global wall-clock ordering; authority decisions require a protected epoch.
 * Run: node architecture/research/agent-prison/model-check.mjs
 */
import assert from 'node:assert/strict';

// Parent relationships define the causal partial order, rather than arrival timestamps.
// "x" and "y" deliberately conflict without causal order (two concurrent status writes).
const E = [
  { id: 'g', type: 'grant', parents: [] },
  { id: 'p', type: 'candidate', parents: ['g'] },
  { id: 'a', type: 'authorization', parents: ['p'], policyEpoch: 1, allowed: true, actDigest: 'act-v1' },
  { id: 'f', type: 'finality', parents: ['p', 'a'], policyEpoch: 1, sinkSequence: 10, actDigest: 'act-v1' },
  { id: 'w', type: 'witness', parents: ['f'], resultDigest: 'result-v1' },
  { id: 'c', type: 'claim', parents: ['w'], resultDigest: 'result-v1' },
  { id: 't', type: 'terminated', parents: ['f'] },
  { id: 'd', type: 'completed', parents: ['t'] },
  { id: 'r', type: 'revoke', parents: ['g'], policyEpoch: 2, sinkSequence: 9 },
  { id: 'z', type: 'revoke', parents: ['f'], policyEpoch: 2, sinkSequence: 11 },
  { id: 'x', type: 'status', parents: [], value: 'running' },
  { id: 'y', type: 'status', parents: [], value: 'paused' },
];
const ID = Object.fromEntries(E.map((e, i) => [e.id, i]));
const byId = Object.fromEntries(E.map(e => [e.id, e]));
const bit = id => 1 << ID[id];
const has = (mask, id) => Boolean(mask & bit(id));
const masks = 1 << E.length;
function closed(mask) {
  return E.every(e => !has(mask, e.id) || e.parents.every(p => has(mask, p)));
}
const totalSeen = mask => E.filter(e => has(mask, e.id));

// Deterministic domain resolution is ESSENTIAL: signed append-only history alone
// does not imply convergence. A concurrent last-arrival-wins register diverges.
function project(mask, order = totalSeen(mask)) {
  const events = order.filter(e => has(mask, e.id));
  const statuses = events.filter(e => e.type === 'status');
  const status = statuses.length ? statuses.reduce((a, b) => a.id > b.id ? a : b).value : null;
  return {
    status, granted: has(mask, 'g'), revoked: has(mask, 'r'),
    prepared: has(mask, 'p'), authorized: has(mask, 'a'),
    effected: has(mask, 'f'), witnessed: has(mask, 'w'),
    claimed: has(mask, 'c'), terminated: has(mask, 't'),
    completed: has(mask, 'd'),
  };
}
function finality(mask, { policyEpoch = 1, actDigest = 'act-v1' } = {}) {
  if (!closed(mask) || !has(mask, 'g') || !has(mask, 'p') || !has(mask, 'a')) return 'INSUFFICIENT_EVIDENCE';
  const a = byId.a;
  // Both revocations are attested by the protected sink, not by replica clocks.
  if (has(mask, 'r') || has(mask, 'z') || policyEpoch !== a.policyEpoch) return 'DENY_REVOKED';
  if (!a.allowed || a.actDigest !== actDigest) return 'DENY_MISMATCH';
  return 'AUTHORIZED';
}
function claim(mask, { resultDigest = 'result-v1' } = {}) {
  if (!closed(mask) || !has(mask, 'w')) return 'INSUFFICIENT_EVIDENCE';
  return byId.w.resultDigest === resultDigest ? 'PROVEN' : 'FALSE';
}
function validate(mask) {
  if (!closed(mask)) return 'CAUSAL_GAP';
  // Replay preserves an effect already finalized before a subsequent revoke.
  // Admission and historical validity are DIFFERENT predicates: a revocation
  // blocks NEW finality but must not erase acknowledged historical evidence.
  if (has(mask, 'f') && (byId.f.actDigest !== byId.a.actDigest ||
      byId.f.policyEpoch !== byId.a.policyEpoch || !byId.a.allowed ||
      (has(mask, 'r') && byId.r.sinkSequence <= byId.f.sinkSequence)))
    return 'UNAUTHORIZED_EFFECT';
  if (has(mask, 'c') && claim(mask) !== 'PROVEN') return 'UNPROVEN_CLAIM';
  if (has(mask, 'd') && !has(mask, 't')) return 'UNTERMINATED_COMPLETION';
  return 'VALID';
}
function naiveArrivalRegister(order) {
  return order.filter(e => e.type === 'status').at(-1)?.value ?? null;
}
function verify() {
  let closedSets = 0, validSets = 0, partitionsChecked = 0, rejected = 0;
  const examples = {};
  for (let mask = 0; mask < masks; mask++) {
    if (!closed(mask)) { rejected++; continue; }
    closedSets++;
    let verdict = validate(mask);
    if (verdict !== 'VALID') { rejected++; examples[verdict] ??= totalSeen(mask).map(e => e.id); continue; }
    validSets++;
    const normal = project(mask);
    assert.deepEqual(project(mask, totalSeen(mask).reverse()), normal, 'same causal set must converge irrespective of order');
    // Exhaust all 3^n assignments among three replicas, not two.
    // During a partition replicas can have incomplete causal histories, so
    // only causally closed local views are replayable; after sync all converge.
    const bits = totalSeen(mask).map(e => bit(e.id));
    for (let assignment = 0; assignment < 3 ** bits.length; assignment++) {
      let left = 0, middle = 0, right = 0, n = assignment;
      for (const b of bits) {
        const target = n % 3; n = Math.floor(n / 3);
        if (target === 0) left |= b;
        else if (target === 1) middle |= b;
        else right |= b;
      }
      if (!closed(left) || !closed(middle) || !closed(right)) continue;
      const healed = left | middle | right;
      assert.equal(healed, mask);
      assert.deepEqual(project(healed), normal);
      partitionsChecked++;
    }
  }
  // Minimal, structurally meaningful counterexamples against the unguarded alternatives.
  assert.notEqual(naiveArrivalRegister([byId.x, byId.y]), naiveArrivalRegister([byId.y, byId.x]));
  assert.equal(finality(bit('g') | bit('p')), 'INSUFFICIENT_EVIDENCE');
  assert.equal(finality(bit('g') | bit('p') | bit('a') | bit('r')), 'DENY_REVOKED');
  assert.equal(finality(bit('g') | bit('p') | bit('a'), { actDigest: 'substituted' }), 'DENY_MISMATCH');
  assert.equal(claim(0), 'INSUFFICIENT_EVIDENCE');
  assert.equal(claim(bit('g') | bit('p') | bit('a') | bit('f') | bit('w'), { resultDigest: 'forged' }), 'FALSE');
  assert.equal(validate(bit('d')), 'CAUSAL_GAP');
  assert.equal(validate(bit('g') | bit('p') | bit('a') | bit('f') | bit('r')), 'UNAUTHORIZED_EFFECT',
    'the sink must refuse effects ordered after revocation');
  assert.equal(validate(bit('g') | bit('p') | bit('a') | bit('f') | bit('z')), 'VALID',
    'revocation after finality must retain historical effects');
  assert.equal(validate(bit('g') | bit('p') | bit('a') | bit('f') | bit('t') | bit('d')), 'VALID');
  const report = {
    schema: 'estate.agent-prison.model-evidence.v1',
    model: 'causal-set+trusted-policy-epoch+deterministic-conflict-resolution',
    event_types: E.length, total_subsets: masks, causal_closed_sets: closedSets,
    valid_sets: validSets, rejected_sets: rejected, partition_reconciliations: partitionsChecked,
    counterexamples: {
      arrival_order_diverges: ['x:running', 'y:paused'],
      effect_without_authorization: 'INSUFFICIENT_EVIDENCE',
      revoke_before_finality: 'DENY_REVOKED',
      post_approval_substitution: 'DENY_MISMATCH',
      unsupported_claim: 'INSUFFICIENT_EVIDENCE',
      forged_result: 'FALSE',
      completion_without_termination: 'CAUSAL_GAP',
      ...examples,
    },
    caveat: 'Finite-state exploration of an abstract specification, not a production proof; liveness, key compromise, witness trust and external effects require distinct verification.',
  };
  console.log(JSON.stringify(report, null, 2));
}
verify();
