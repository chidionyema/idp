#!/usr/bin/env python3
"""Meridian recovery decision model v0.1 (synthetic, offline, standard-library only).

This is a *falsifiable model*, not a live fleet operator or a policy grant.
All probabilities and topology in example_config.json are HYPOTHETICAL.
Actions require the actual estate's independent authority, budget and verifier gates.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
import json
import math
import sys
from typing import Mapping


@dataclass(frozen=True)
class Capability:
    name: str
    requires: frozenset[str]
    weight: float


def closure(seed: set[str], rules: list[Capability]) -> set[str]:
    """Least fixed point: only enabled nodes with all preconditions satisfied activate."""
    active = set(seed)
    for _ in range(len(rules) + 1):
        nxt = active | {r.name for r in rules if r.requires <= active}
        if nxt == active:
            return active
        active = nxt
    raise AssertionError('Closure failed to converge in the finite capability graph')


def unlocked(seed: set[str], actions: set[str], rules: list[Capability]) -> dict:
    before = closure(seed, rules)
    after = closure(seed | actions, rules)
    weights = {r.name: r.weight for r in rules}
    gained = (after - before) & set(weights)  # Count derived capabilities, not raw repaired inputs.
    return {'gained': sorted(gained), 'newly_feasible_weight_under_assumptions': sum(weights.get(n, 0.0) for n in gained)}


def validate_model(m: dict) -> None:
    fault = m['fault_priors']
    if len(fault) < 2 or any(not isinstance(p, (int, float)) or not math.isfinite(p) or p < 0 for p in fault.values()):
        raise ValueError('Prior distribution must have >=2 hypotheses, finite nonnegative masses')
    if abs(sum(fault.values()) - 1.0) > 1e-9:
        raise ValueError('Priors must sum to one')
    for a, cost in m['repair_costs'].items():
        if a not in fault or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
            raise ValueError('Each fault needs a finite nonnegative repair cost')
    if set(fault) != set(m['repair_costs']):
        raise ValueError('One repair must be modelled for each fault')
    for x in ('successful_recovery_value', 'probe_cost'):
        v = m[x]
        if not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f'{x} must be finite and nonnegative')
    q = m['probe_accuracy']
    if not isinstance(q, (float, int)) or not math.isfinite(q) or not 0.0 <= q <= 1.0:
        raise ValueError('Probe accuracy must be in [0,1]')
    if len(fault) > 2 and q < 1 / len(fault):
        raise ValueError('Probe accuracy must be at least chance in this symmetric-noise model')


def probe_likelihood(label: str, fault: str, accuracy: float, n: int) -> float:
    return accuracy if label == fault else (1.0 - accuracy) / (n - 1)


def best_direct_repair(priors: Mapping[str, float], costs: Mapping[str, float], success_value: float) -> dict:
    choices = {name: priors[name] * success_value - costs[name] for name in priors}
    # The no-action option is mandatory: uncertainty cannot force a speculative repair.
    choices['DEFER'] = 0.0
    best = max(choices, key=lambda n: (choices[n], n))
    return {'repair': best, 'expected_net': choices[best], 'alternatives': choices}


def evaluate_probe(m: dict) -> dict:
    """Exact one-step EVSI; no entropy proxy and no invented utility weights."""
    validate_model(m)
    priors = m['fault_priors']
    costs = m['repair_costs']
    value = m['successful_recovery_value']
    acc = m['probe_accuracy']
    faults = sorted(priors)
    n = len(faults)
    direct = best_direct_repair(priors, costs, value)
    observations = []
    after = 0.0
    for label in faults:
        mass = sum(priors[f] * probe_likelihood(label, f, acc, n) for f in faults)
        if mass <= 0.0:
            continue
        posterior = {f: priors[f] * probe_likelihood(label, f, acc, n) / mass for f in faults}
        optimal = best_direct_repair(posterior, costs, value)
        after += mass * optimal['expected_net']
        observations.append({'observation': label, 'probability': mass, 'posterior': posterior,
                             'repair_after_observation': optimal['repair'],
                             'conditional_expected_net': optimal['expected_net']})
    net = after - m['probe_cost']
    result = {'direct': direct, 'probe': {'net_expected_value': net, 'expected_value_of_sample_information': after - direct['expected_net'],
                                       'net_value_of_sample_information': net - direct['expected_net'],
                                       'cost': m['probe_cost'], 'observations': observations},
              'choice': 'PROBE' if net > direct['expected_net'] else ('ABSTAIN' if direct['repair'] == 'DEFER' else 'DIRECT_REPAIR')}
    return result


def feasibility(action: dict) -> tuple[bool, list[str]]:
    """A diagnostic/selection gate, NOT an authorization to execute effects."""
    missing = []
    for key in ('authority_receipt', 'budget_receipt'):
        if not action.get(key):
            missing.append(key)
    if action.get('effects') and not action.get('independent_evidence_receipt'):
        missing.append('independent_evidence_receipt')
    if action.get('worker_required') and not action.get('worker_verified'):
        missing.append('worker_verified')
    return not missing, missing


def custody_transition(state: dict, event: str) -> dict:
    """Toy safety automaton: an accepted obligation is never erased by worker loss.

    It is NOT a distributed-storage guarantee. It demonstrates a local model invariant.
    """
    nxt = dict(state)
    if event == 'WORKER_LOST':
        nxt['workers'] = 0
    elif event == 'WORKER_RETURNED':
        nxt['workers'] += 1
    elif event == 'CHECKPOINT':
        if nxt['workers'] == 0:
            raise ValueError('Cannot execute model-dependent checkpoint with zero workers')
        nxt['checkpoint_epoch'] += 1
    elif event == 'VERIFY_AND_SETTLE':
        if not nxt.get('independent_receipt'):
            raise ValueError('Settlement needs independent receipt')
        nxt['open_obligations'] = max(0, nxt['open_obligations'] - 1)
    else:
        raise ValueError('Unknown event')
    if nxt['open_obligations'] < 0:
        raise AssertionError('Debt cannot go negative')
    return nxt


def run_model(config: dict) -> dict:
    m = config['decision']
    r = evaluate_probe(m)
    rules = [Capability(x['name'], frozenset(x['requires']), float(x['weight']))
             for x in config['capability_graph']['rules']]
    seed = set(config['capability_graph']['verified_seed'])
    r['capability_effect'] = {
        'repair_intake': unlocked(seed, {'intake'}, rules),
        'repair_intake_but_no_git_authority': unlocked(seed - {'git_authority'}, {'intake'}, rules),
    }
    actions = config['candidate_actions']
    r['claimed_evidence_screen_NOT_AUTHORITY'] = {a['name']: dict(zip(('input_claims_complete', 'missing_claims'), feasibility(a))) for a in actions}
    initial = {'workers': 1, 'open_obligations': 2, 'checkpoint_epoch': 0, 'independent_receipt': False}
    lost = custody_transition(initial, 'WORKER_LOST')
    returned = custody_transition(lost, 'WORKER_RETURNED')
    r['zero_worker_safety_simulation'] = {'before': initial, 'after_worker_loss': lost,
                              'after_worker_return': returned, 'obligations_survived': returned['open_obligations'] == initial['open_obligations']}
    return r


def main() -> int:
    if len(sys.argv) != 2:
        print(f'usage: {sys.argv[0]} example_config.json', file=sys.stderr)
        return 2
    with open(sys.argv[1], encoding='utf-8') as f:
        config = json.load(f)
    print(json.dumps(run_model(config), sort_keys=True, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())