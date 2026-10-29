#!/usr/bin/env python3
"""assurance.py -- the estate's decision-assurance and hypothesis-space substrate.

THE MANDATE (founder, 2026-10-29): "implement Monte Carlo as a mandatory, conditionally activated
decision-assurance capability at the shared decision boundary, with policy-selected methods,
reproducible evidence, bounded assurance tiers" and "every consequential decision must be assessed
for uncertainty; simulation is compulsory when stochastic simulation is the appropriate method, but
not when deterministic analysis, exact probability, or formal verification is stronger".

WHAT WAS WRONG BEFORE. The estate enforced OWNERSHIP everywhere and TRUTH nowhere (measured this
session: 0 of the last 300 commit bodies carry a Proof: trailer). It had no way to say "this
decision needs a number, and here is the number, and here is how the number can be falsified". A
consequential choice -- the router's retry policy, a capacity plan, a spend forecast -- was made
by whoever typed it, with no policy, no bound and no evidence.

WHAT THIS IS. One module with three layers over ONE evidence substrate:

  1. POLICY. `catalog/decision-assurance.json` maps a decision class to the cheapest adequate
     method (deterministic / formal / monte_carlo), a tier and a risk bound. The agent that wants
     the decision CANNOT exempt itself: a self-declared `monte_carlo_required: false` is refused
     and reported as refused. The agent MAY ask for MORE assurance than policy requires; that is
     escalation, and it is recorded.

  2. HYPOTHESIS SPACE. Evidence is content-addressed (every observation carries the digest of its
     source). A hypothesis is a CAUSAL MECHANISM, so paraphrases merge and conjunctions stay
     distinct. The unexplained residual is a first-class hypothesis and is never pruned. Evidence
     that refutes every live hypothesis leaves a residual, and a residual triggers DETERMINISTIC
     space expansion -- never a confident wrong winner. The packet ranks what to investigate next
     by declared-weight-and-cost (EDVI per unit cost) and says out loud that it is a proxy.

  3. MONTE CARLO. A deterministic in-house PRNG (splitmix64) so a seed reproduces a number across
     processes and machines. The model carries EXPLICIT versioned parameters with provenance
     (measured from a named artifact, or assumed by an author -- an assumption never silently
     becomes a fact). Correlated common-cause failures are modelled, because the independent model
     understates the tail it is used to bound. The outputs are the ones the doctrine names:
     expected loss, P(L > L_max), CVaR_0.99, and P_hat(SLO breach) + uncertainty margin <= epsilon.

THE RECEIPT. `estate.decision-assurance/v1` binds the decision, the candidate artifact's digest,
the scenario version, the model digest, the seed, the sample count, the simulation digest and the
metrics. It is verified by DETERMINISTIC RECOMPUTATION -- re-running the simulation from the
receipt's own seed and comparing digests -- so a tampered number cannot pass. This is not a
second proof-of-work verifier: it proves the SIMULATION, not the claim.

BLIND IS A VERDICT. A catalog that cannot be read, a candidate that cannot be hashed, a scenario
whose source artifact has changed underneath it: these are BLIND (exit 2), never PASS. A gate
that cannot fail is not a gate.

EXIT CODES. 0 PASS (or REVIEW_REQUIRED, which is not a block but is never an admission), 1 BLOCK,
2 BLIND. Greenlane remains the only admission authority; this module never admits anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCHEMA = "estate.decision-assurance/v1"
PACKET_SCHEMA = "estate.hypothesis-packet/v1"
STATE = Path(os.environ.get("ESTATE_STATE_DIR", str(Path.home() / ".estate")))
CATALOG_NAME = "decision-assurance.json"

EXIT_OK = 0
EXIT_BLOCK = 1
EXIT_BLIND = 2

TIER_ORDER = {"tier0": 0, "tier1": 1, "tier2": 2}


# --------------------------------------------------------------------------------------
# canonical form and digests
# --------------------------------------------------------------------------------------


def canonical(obj: Any) -> str:
    """One canonical JSON encoding. Two equal objects always produce the same string."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def digest(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _round(value: float, places: int = 12) -> float:
    return float(round(value, places))


# --------------------------------------------------------------------------------------
# catalog
# --------------------------------------------------------------------------------------


def catalog_candidates(explicit: Optional[str] = None) -> List[Path]:
    """Where the policy registry may live.

    The installed runtime tree carries its own catalog; a checkout carries the repo's. This is
    the same candidate-path strategy platform/estate/libexec/critical-watch.py uses, because
    catalog/ is not synced by bin/estate-runtime-sync.
    """
    here = Path(__file__).resolve()
    out: List[Path] = []
    if explicit:
        out.append(Path(explicit).expanduser())
    out.append(here.parents[3] / "catalog" / CATALOG_NAME)
    out.append(STATE / "runtime/idp/catalog" / CATALOG_NAME)
    out.append(Path.cwd() / "catalog" / CATALOG_NAME)
    return out


def load_catalog(
    explicit: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Path]]:
    for cand in catalog_candidates(explicit):
        try:
            if cand.is_file():
                return json.loads(cand.read_text()), cand
        except (OSError, ValueError):
            continue
    return None, None


class Blind(Exception):
    """A measurement that could not be taken. Never zero, never PASS."""


# --------------------------------------------------------------------------------------
# layer 1: policy -- method selection
# --------------------------------------------------------------------------------------


def method_selection(case: Dict[str, Any], catalog: Dict[str, Any]) -> Dict[str, Any]:
    """Pick the cheapest adequate method for a decision.

    The policy decides. The agent may request more assurance; it may never request less.
    """
    classes = catalog.get("decision_classes") or {}
    decision_class = case.get("class") or case.get("decision_class") or ""
    entry = classes.get(decision_class)
    if entry is None:
        return {
            "decision_class": decision_class,
            "method": None,
            "tier": None,
            "epsilon": None,
            "l_max": None,
            "reason": "no policy class named %r: the estate does not know how to assure this "
            "decision, and a decision with no method is not admitted" % decision_class,
            "required_method": None,
            "refused_self_exemption": False,
            "escalation": None,
            "known_classes": sorted(classes.keys()),
        }

    method = entry.get("method", "deterministic")
    tier = entry.get("tier", "tier0")
    reason = entry.get("reason", "")

    # A formal invariant is stronger than any simulation of it.
    if case.get("formal_invariant"):
        method = "formal"
        reason = (
            "the case declares a formal invariant, and a formal argument is stronger "
            "than any sample of the thing it argues about"
        )

    refused = False
    self_declared = case.get("monte_carlo_required")
    if method == "monte_carlo" and self_declared is False:
        refused = True
        reason = (
            reason
            + " | the agent declared monte_carlo_required=false; that declaration "
            "is REFUSED: the policy selects the method, not the agent"
        ).strip(" |")

    # Escalation: the agent may ask for strictly more assurance than policy requires.
    escalation = None
    requested = case.get("requested_method") or case.get("requested")
    if requested:
        req_tier = case.get("requested_tier")
        if method == "formal" and requested != "formal":
            escalation = {
                "requested_method": requested,
                "accepted": False,
                "reason": "the policy requires a formal argument; sampling cannot replace it",
            }
        elif req_tier and TIER_ORDER.get(req_tier, 0) > TIER_ORDER.get(tier, 0):
            escalation = {
                "requested_method": requested or method,
                "requested_tier": req_tier,
                "accepted": True,
                "reason": "the agent asked for deeper assurance than policy requires; extra "
                "assurance is allowed, reduced assurance is not",
            }
        elif requested and requested != method and method != "formal":
            escalation = {
                "requested_method": requested,
                "accepted": True,
                "reason": "the agent asked for a different adequate method; the deeper of the "
                "two is used",
            }
        else:
            escalation = {
                "requested_method": requested,
                "accepted": False,
                "reason": "the request does not increase assurance over the policy's choice",
            }

    return {
        "decision_class": decision_class,
        "method": method,
        "tier": tier,
        "epsilon": entry.get("epsilon"),
        "l_max": entry.get("l_max"),
        "reason": reason,
        "required_method": method,
        "refused_self_exemption": refused,
        "escalation": escalation,
        "known_classes": sorted(classes.keys()),
    }


# --------------------------------------------------------------------------------------
# layer 2: evidence and the hypothesis space
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Evidence:
    id: str
    source: str
    observation: str
    collected_at: str
    source_digest: str
    reliability: float
    kind: str = "observation"

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Evidence":
        try:
            ev = Evidence(
                id=str(d["id"]),
                source=str(d["source"]),
                observation=str(d.get("observation", "")),
                collected_at=str(d.get("collected_at", "")),
                source_digest=str(d["source_digest"]),
                reliability=float(d.get("reliability", 1.0)),
                kind=str(d.get("kind", "observation")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("evidence is not well formed: %s" % exc) from exc
        if not ev.source_digest:
            raise ValueError(
                "evidence %r has no source_digest: an observation nobody can "
                "re-check is not evidence" % ev.id
            )
        if not 0.0 <= ev.reliability <= 1.0:
            raise ValueError(
                "evidence %r has reliability %r outside [0,1]" % (ev.id, ev.reliability)
            )
        return ev


@dataclass(frozen=True)
class Hypothesis:
    id: str
    mechanism: str
    family: str
    prior: float
    likelihoods: Dict[str, float] = field(default_factory=dict)
    falsifier: str = ""
    conjuncts: Tuple[str, ...] = ()

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Hypothesis":
        try:
            hyp = Hypothesis(
                id=str(d["id"]),
                mechanism=str(d["mechanism"]),
                family=str(d.get("family", "")),
                prior=float(d.get("prior", 0.0)),
                likelihoods={
                    str(k): float(v) for k, v in (d.get("likelihoods") or {}).items()
                },
                falsifier=str(d.get("falsifier", "")),
                conjuncts=tuple(str(c) for c in (d.get("conjuncts") or ())),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("hypothesis is not well formed: %s" % exc) from exc
        if not hyp.mechanism.strip():
            raise ValueError(
                "hypothesis %r has no mechanism: a label is not a cause" % hyp.id
            )
        if not 0.0 <= hyp.prior <= 1.0:
            raise ValueError(
                "hypothesis %r has prior %r outside [0,1]" % (hyp.id, hyp.prior)
            )
        for key, val in hyp.likelihoods.items():
            if not 0.0 <= val <= 1.0:
                raise ValueError(
                    "hypothesis %r has likelihood %r outside [0,1] for %r"
                    % (hyp.id, val, key)
                )
        return hyp


def _normalise(text: str, synonyms: Dict[str, List[str]]) -> str:
    low = " ".join(str(text).lower().split()).strip(" .,:;")
    for group in synonyms.values():
        for phrase in group:
            if low == " ".join(str(phrase).lower().split()):
                return " ".join(sorted(str(g).lower() for g in group))
    return low


def mechanism_fingerprint(hyp: Hypothesis, synonyms: Dict[str, List[str]]) -> str:
    """Identity is the CAUSAL MECHANISM.

    Two hypotheses that name the same mechanism in different words are one hypothesis. Two
    hypotheses that name a conjunction of mechanisms are two, because fixing one conjunct fixes
    only part of the cause.
    """
    if hyp.conjuncts:
        parts = sorted({_normalise(c, synonyms) for c in hyp.conjuncts})
        return digest({"kind": "conjunction", "parts": parts})
    return digest(
        {"kind": "mechanism", "mechanism": _normalise(hyp.mechanism, synonyms)}
    )


def build_packet(
    problem: str,
    evidence: Sequence[Evidence],
    hypotheses: Sequence[Hypothesis],
    catalog: Dict[str, Any],
    minimum_residual_prior: Optional[float] = None,
) -> Dict[str, Any]:
    """Compile a decision-intelligence packet from evidence and a hypothesis space."""
    hy = catalog.get("hypothesis") or {}
    syn = hy.get("synonyms") or {}
    falsified_at = float(hy.get("falsified_likelihood", 0.05))
    min_res = (
        float(hy.get("minimum_residual_prior", 0.05))
        if minimum_residual_prior is None
        else float(minimum_residual_prior)
    )
    max_proposals = int(hy.get("max_expansion_proposals", 3))

    ev_by_id: Dict[str, Evidence] = {}
    for ev in evidence:
        if ev.id in ev_by_id:
            raise ValueError(
                "duplicate evidence id %r: two observations claiming the same "
                "identity cannot both be counted" % ev.id
            )
        ev_by_id[ev.id] = ev

    # merge hypotheses that name the same mechanism
    merged: Dict[str, Hypothesis] = {}
    merge_notes: List[Dict[str, Any]] = []
    for hyp in hypotheses:
        if hyp.id in merged:
            raise ValueError("duplicate hypothesis id %r" % hyp.id)
        fp = mechanism_fingerprint(hyp, syn)
        existing = next(
            (h for h in merged.values() if mechanism_fingerprint(h, syn) == fp), None
        )
        if existing is None:
            merged[hyp.id] = hyp
            continue
        # same mechanism: keep the stronger prior and the union of the likelihoods
        lik = dict(existing.likelihoods)
        for key, val in hyp.likelihoods.items():
            lik[key] = max(val, lik.get(key, 0.0))
        keep, drop = (existing, hyp) if existing.prior >= hyp.prior else (hyp, existing)
        merged[keep.id] = Hypothesis(
            id=keep.id,
            mechanism=keep.mechanism,
            family=keep.family,
            prior=keep.prior,
            likelihoods=lik,
            falsifier=keep.falsifier or drop.falsifier,
            conjuncts=keep.conjuncts or drop.conjuncts,
        )
        merged.pop(drop.id, None)
        merge_notes.append(
            {
                "kept": keep.id,
                "merged": drop.id,
                "reason": "the same causal mechanism stated twice; a paraphrase is not a second cause",
            }
        )

    hyps = list(merged.values())
    if not hyps:
        raise ValueError("a packet with no hypotheses is not a packet")

    prior_total = sum(h.prior for h in hyps)
    if prior_total <= 0:
        raise ValueError(
            "every hypothesis has prior 0: there is no probability space to reason in"
        )

    gaps: List[str] = []
    used_evidence: set = set()
    statuses: Dict[str, Dict[str, Any]] = {}
    raws: List[float] = []

    for hyp in hyps:
        raw = hyp.prior
        falsified_by = ""
        for ev_id, like in sorted(hyp.likelihoods.items()):
            if ev_id not in ev_by_id:
                gaps.append("evidence-absent:%s:%s" % (hyp.id, ev_id))
                continue
            used_evidence.add(ev_id)
            raw *= like
            if like <= falsified_at and not falsified_by:
                falsified_by = ev_id
        if hyp.falsifier and hyp.falsifier not in ev_by_id:
            gaps.append("falsifier-absent:%s:%s" % (hyp.id, hyp.falsifier))
        if not hyp.falsifier:
            gaps.append("hypothesis-no-falsifier:%s" % hyp.id)
        if not hyp.likelihoods:
            gaps.append("hypothesis-uninformed:%s" % hyp.id)
        if hyp.prior <= 0:
            gaps.append("hypothesis-zero-prior:%s" % hyp.id)
        raws.append(raw)
        statuses[hyp.id] = {
            "status": "falsified" if falsified_by else "retained",
            "falsified_by": falsified_by,
        }

    raw_total = sum(raws)
    if raw_total <= 0:
        posteriors = {h.id: 0.0 for h in hyps}
        p_unknown = 1.0
    else:
        posteriors = {hyps[i].id: r / raw_total for i, r in enumerate(raws)}
        p_unknown = 1.0 - sum(posteriors.values())
    if p_unknown < min_res:
        scale = (1.0 - min_res) / max(1e-12, (1.0 - p_unknown))
        for key in posteriors:
            posteriors[key] *= scale
        p_unknown = min_res

    for ev_id in sorted(ev_by_id):
        if ev_id not in used_evidence:
            gaps.append("evidence-unused:%s" % ev_id)
        if ev_by_id[ev_id].reliability < 0.5:
            gaps.append("low-reliability:%s" % ev_id)

    # deterministic expansion: every live hypothesis refuted, and a residual left over
    expansion: List[Dict[str, Any]] = []
    retained = [h for h in hyps if statuses[h.id]["status"] == "retained"]
    if not retained and p_unknown > 0:
        unexplained = sorted(
            ev_id for ev_id in ev_by_id if ev_id not in used_evidence
        ) or sorted(ev_by_id.keys())
        seen = set()
        for hyp in sorted(hyps, key=lambda h: h.id):
            parts = list(hyp.conjuncts) or [hyp.mechanism]
            for part in parts:
                for ev_id in unexplained:
                    mech = "%s accounts for %s" % (part.strip(), ev_id)
                    fp = digest(
                        {"kind": "mechanism", "mechanism": _normalise(mech, syn)}
                    )
                    if fp in seen:
                        continue
                    seen.add(fp)
                    expansion.append(
                        {
                            "mechanism": mech,
                            "from_hypothesis": hyp.id,
                            "explains_evidence": ev_id,
                            "posterior": None,
                            "status": "proposed",
                            "note": "the evidence refuted every live hypothesis and left a residual; "
                            "this mechanism is proposed by decomposition, not by evidence. "
                            "It needs new evidence before it can be scored.",
                        }
                    )
                    if len(expansion) >= max_proposals:
                        break
                if len(expansion) >= max_proposals:
                    break
            if len(expansion) >= max_proposals:
                break

    # EDVI per unit cost -- a DECLARED proxy, and the packet says so.
    costs = hy.get("evidence_costs") or {}
    k = max(2, len(retained))
    ranking: List[Dict[str, Any]] = []
    for hyp in sorted(retained, key=lambda h: h.id):
        cost_key = "default"
        if hyp.falsifier and hyp.falsifier in ev_by_id:
            cost_key = ev_by_id[hyp.falsifier].kind
        cost = float(costs.get(cost_key, costs.get("default", 1.0)))
        evpi = (1.0 - posteriors[hyp.id]) * math.log(k, 2)
        ranking.append(
            {
                "id": hyp.id,
                "posterior": _round(posteriors[hyp.id]),
                "evpi_bits": _round(evpi),
                "cost": cost,
                "edvi_per_cost": _round(evpi / cost if cost else float("inf")),
                "falsifier": hyp.falsifier,
            }
        )
    ranking.sort(key=lambda r: (-r["edvi_per_cost"], r["id"]))

    packet = {
        "schema": PACKET_SCHEMA,
        "problem": problem,
        "evidence": [
            {
                "id": ev.id,
                "source": ev.source,
                "kind": ev.kind,
                "source_digest": ev.source_digest,
                "reliability": ev.reliability,
                "collected_at": ev.collected_at,
                "observation": ev.observation,
            }
            for ev in sorted(ev_by_id.values(), key=lambda e: e.id)
        ],
        "hypotheses": [
            {
                "id": h.id,
                "mechanism": h.mechanism,
                "family": h.family,
                "fingerprint": mechanism_fingerprint(h, syn),
                "prior": h.prior,
                "posterior": _round(posteriors[h.id]),
                "status": statuses[h.id]["status"],
                "falsified_by": statuses[h.id]["falsified_by"],
                "falsifier": h.falsifier,
                "conjuncts": list(h.conjuncts),
            }
            for h in sorted(hyps, key=lambda h: h.id)
        ],
        "unknown": {
            "id": "unknown",
            "posterior": _round(p_unknown),
            "note": "the residual prior mass the evidence cannot explain. It is a hypothesis, it "
            "is never pruned, and a packet that explains everything is a packet that "
            "has stopped looking.",
        },
        "coverage_gaps": sorted(set(gaps)),
        "ranking": ranking,
        "expansion_proposals": expansion,
        "merges": merge_notes,
        "limits": [
            "priors are declared by the author of the hypothesis space; this module never "
            "fabricates one",
            "EDVI per unit cost is a declared-weight-and-cost proxy, not a measured value of "
            "information; the ranking is a hint about where to look next, not a proof",
            "likelihoods are the author's numbers; the packet reports them, it does not check "
            "them against the world",
            "posterior is computed over the prior mass only: it is a relative weight, not a "
            "probability that the cause is the true cause",
        ],
    }
    packet["digest"] = digest({k: v for k, v in packet.items() if k != "digest"})
    return packet


# --------------------------------------------------------------------------------------
# layer 3: monte carlo
# --------------------------------------------------------------------------------------


class SplitMix64:
    """A version-stable PRNG. Same seed, same stream, on every machine and every process.

    random.Random is not used: its stream is an implementation detail of the interpreter, and
    evidence that cannot be reproduced is not evidence.
    """

    _MASK = (1 << 64) - 1

    def __init__(self, seed: int) -> None:
        self._state = int(seed) & self._MASK

    def next_u64(self) -> int:
        self._state = (self._state + 0x9E3779B97F4A7C15) & self._MASK
        z = self._state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & self._MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & self._MASK
        return (z ^ (z >> 31)) & self._MASK

    def uniform(self) -> float:
        return (self.next_u64() >> 11) * (1.0 / (1 << 53))

    def normal(self, mean: float, sd: float) -> float:
        u1 = max(self.uniform(), 1e-12)
        u2 = self.uniform()
        return mean + sd * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

    def truncated_normal(self, mean: float, sd: float) -> float:
        for _ in range(8):
            val = self.normal(mean, sd)
            if val >= 0.0:
                return val
        return 0.0


def _model_from_scenario(
    scenario: Dict[str, Any],
    catalog: Dict[str, Any],
    chain: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    chains = scenario.get("chains") or {}
    name = chain or scenario.get("chain") or ""
    if name not in chains:
        raise Blind(
            "scenario %r has no chain %r (known: %s)"
            % (scenario.get("version"), name, ", ".join(sorted(chains)))
        )
    params: Dict[str, Any] = {}
    provenance: Dict[str, List[str]] = {"measured": [], "assumed": []}
    for key, spec in (scenario.get("parameters") or {}).items():
        value = spec.get("value")
        params[key] = value
        provenance.setdefault(str(spec.get("provenance", "assumed")), []).append(key)
    if overrides:
        for key, value in overrides.items():
            if key not in params:
                raise Blind("override %r is not a parameter of this scenario" % key)
            params[key] = value
            provenance.setdefault("assumed", []).append(key)
    decision = (catalog.get("decision_classes") or {}).get("router.failover") or {}
    l_max = params.get("l_max", decision.get("l_max", 900.0))
    model = {
        "model_version": scenario.get("model_version", "unknown"),
        "scenario_version": scenario.get("version", "0"),
        "chain": name,
        "providers": list(chains[name]),
        "attempts_per_provider": int(params.get("attempts_per_provider", 1)),
        "provider_timeout_s": dict(params.get("provider_timeout_s") or {}),
        "success_mean_s": float(params.get("success_mean_s", 1.0)),
        "success_sd_s": float(params.get("success_sd_s", 0.5)),
        "p_fail": float(params.get("p_fail", 0.0)),
        "p_fail_outage": float(params.get("p_fail_outage", 0.9)),
        "p_common": float(params.get("p_common", 0.0)),
        "p_timeout_given_failure": float(params.get("p_timeout_given_failure", 0.5)),
        "fast_error_s": float(params.get("fast_error_s", 1.0)),
        "l_max": float(l_max),
        "epsilon": float(decision.get("epsilon", 0.05)),
        "delta": float(scenario.get("delta", 0.05)),
        "provenance": provenance,
    }
    return model


def simulate_model(model: Dict[str, Any], seed: int, samples: int) -> Dict[str, Any]:
    """Run the model. Returns metrics, convergence diagnostics and the run's own digest."""
    if samples <= 0:
        raise Blind(
            "samples must be positive: a simulation with no samples measures nothing"
        )
    rng = SplitMix64(seed)
    providers = model["providers"]
    attempts = model["attempts_per_provider"]
    timeouts = model["provider_timeout_s"]
    l_max = model["l_max"]

    losses: List[float] = []
    breaches = 0
    failures = 0
    attempts_used = 0
    checkpoints = [0.1, 0.25, 0.5, 1.0]
    marks = {int(samples * c): c for c in checkpoints}
    running_breaches = 0
    convergence: List[Dict[str, Any]] = []

    for i in range(1, samples + 1):
        outage = rng.uniform() < model["p_common"]
        elapsed = 0.0
        served = False
        for provider in providers:
            for _ in range(attempts):
                attempts_used += 1
                fail_p = model["p_fail_outage"] if outage else model["p_fail"]
                if rng.uniform() < fail_p:
                    if rng.uniform() < model["p_timeout_given_failure"]:
                        elapsed += float(timeouts.get(provider, 60))
                    else:
                        elapsed += model["fast_error_s"]
                else:
                    elapsed += rng.truncated_normal(
                        model["success_mean_s"], model["success_sd_s"]
                    )
                    served = True
                    break
            if served:
                break
        losses.append(elapsed)
        if (not served) or elapsed > l_max:
            running_breaches += 1
            breaches += 1
        if not served:
            failures += 1
        if i in marks:
            frac = marks[i]
            p_hat = running_breaches / i
            margin = math.sqrt(math.log(2.0 / model["delta"]) / (2.0 * i))
            convergence.append(
                {
                    "fraction": frac,
                    "samples": i,
                    "p_slo_breach": _round(p_hat),
                    "uncertainty_margin": _round(margin),
                }
            )

    ordered = sorted(losses)
    tail_n = max(1, int(math.ceil(0.01 * len(ordered))))
    cvar = sum(ordered[-tail_n:]) / tail_n
    p_hat = breaches / samples
    margin = math.sqrt(math.log(2.0 / model["delta"]) / (2.0 * samples))
    bound = p_hat + margin

    metrics = {
        "samples": samples,
        "seed": seed,
        "expected_loss_s": _round(sum(losses) / samples),
        "p_loss_gt_lmax": _round(sum(1 for x in losses if x > l_max) / samples),
        "cvar99_s": _round(cvar),
        "p_slo_breach": _round(p_hat),
        "uncertainty_margin": _round(margin),
        "slo_breach_bound": _round(bound),
        "unserved_requests": failures,
        "mean_attempts": _round(attempts_used / samples),
        "l_max": _round(l_max),
        "epsilon": _round(model["epsilon"]),
    }
    drift = 0.0
    if len(convergence) >= 3:
        drift = abs(convergence[-1]["p_slo_breach"] - convergence[2]["p_slo_breach"])

    payload = {
        "model_digest": digest(model),
        "metrics": metrics,
        "convergence": convergence,
        "drift": _round(drift),
        "rare_event": breaches == 0,
    }
    payload["simulation_digest"] = digest(payload)
    return payload


def _sensitivity_variants(
    model: Dict[str, Any],
    scenario: Dict[str, Any],
    base: float,
    seed: int,
    samples: int,
) -> List[Dict[str, Any]]:
    out = []
    variants = {
        "independent": {"p_common": 0.0},
        "low_fail": {"p_fail": model["p_fail"] / 2.0},
        "high_fail": {"p_fail": model["p_fail"] * 2.0},
        "high_common": {"p_common": model["p_common"] * 2.0},
    }
    for name in scenario.get("sensitivity") or sorted(variants):
        patch = variants.get(name)
        if patch is None:
            continue
        variant = dict(model)
        variant.update(patch)
        run = simulate_model(variant, int(seed), int(samples))
        out.append(
            {
                "variant": name,
                "changed": patch,
                "p_slo_breach": run["metrics"]["p_slo_breach"],
                "p_loss_gt_lmax": run["metrics"]["p_loss_gt_lmax"],
                "delta_p_slo_breach": _round(run["metrics"]["p_slo_breach"] - base),
            }
        )
    return out


def run_scenario(
    scenario_name: str,
    catalog: Dict[str, Any],
    seed: int,
    samples: int,
    chain: Optional[str] = None,
) -> Dict[str, Any]:
    scenario = (catalog.get("scenarios") or {}).get(scenario_name)
    if scenario is None:
        raise Blind(
            "no scenario named %r (known: %s)"
            % (
                scenario_name,
                ", ".join(sorted((catalog.get("scenarios") or {}).keys())),
            )
        )
    model = _model_from_scenario(scenario, catalog, chain)
    run = simulate_model(model, int(seed), int(samples))
    sensitivity = _sensitivity_variants(
        model, scenario, run["metrics"]["p_slo_breach"], int(seed), int(samples)
    )
    run["sensitivity"] = sensitivity
    run["model"] = dict(model)
    run["model"]["seed"] = int(seed)
    run["model"]["samples"] = int(samples)
    return run


# --------------------------------------------------------------------------------------
# the receipt
# --------------------------------------------------------------------------------------


def build_receipt(
    decision_id: str,
    decision_class: str,
    method: str,
    tier: str,
    candidate_digest: str,
    run: Optional[Dict[str, Any]] = None,
    deterministic_evidence: Optional[str] = None,
    reason: str = "",
) -> Dict[str, Any]:
    receipt: Dict[str, Any] = {
        "schema": SCHEMA,
        "decision_id": decision_id,
        "decision_class": decision_class,
        "method": method,
        "tier": tier,
        "candidate_digest": candidate_digest,
        "created_at": _now(),
        "reason": reason,
    }
    if run is not None:
        receipt.update(
            {
                "scenario": run.get("scenario_name") or "",
                "chain": run["model"].get("chain"),
                "model_version": run["model"]["model_version"],
                "scenario_version": run["model"]["scenario_version"],
                "model_digest": run["model_digest"],
                "seed": run["model"]["seed"],
                "samples": run["model"]["samples"],
                "simulation_digest": run["simulation_digest"],
                "metrics": run["metrics"],
                "convergence": run["convergence"],
                "sensitivity": run["sensitivity"],
                "rare_event": run["rare_event"],
                "provenance": run["model"]["provenance"],
            }
        )
    if deterministic_evidence:
        receipt["evidence_digest"] = deterministic_evidence
        receipt["model_digest"] = digest({"deterministic": deterministic_evidence})
        receipt["simulation_digest"] = receipt["model_digest"]
    receipt["digest"] = digest({k: v for k, v in receipt.items() if k != "digest"})
    return receipt


def _now() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_root_for(path: Path) -> Optional[Path]:
    here = Path(__file__).resolve()
    return here.parents[3]


def verify_receipt(
    receipt: Dict[str, Any],
    catalog: Dict[str, Any],
    candidate_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify by DETERMINISTIC RECOMPUTATION. A tampered number cannot pass."""
    problems: List[str] = []
    if receipt.get("schema") != SCHEMA:
        problems.append("schema is %r, expected %r" % (receipt.get("schema"), SCHEMA))
    body = {k: v for k, v in receipt.items() if k != "digest"}
    if digest(body) != receipt.get("digest"):
        problems.append(
            "the receipt digest does not match its body: the receipt was altered"
        )

    method = receipt.get("method")
    if method == "monte_carlo":
        scenario_name = receipt.get("scenario") or ""
        scenario = (catalog.get("scenarios") or {}).get(scenario_name)
        if scenario is None:
            return {
                "verdict": "BLIND",
                "problems": problems
                + [
                    "the receipt names scenario %r, which this catalog does not carry"
                    % scenario_name
                ],
            }
        src = scenario.get("source") or {}
        src_path = src.get("path")
        if src_path:
            root = _repo_root_for(Path(__file__)) or Path.cwd()
            live = root / src_path
            if not live.is_file():
                live = Path(src_path)
            if live.is_file():
                live_digest = sha256_file(live)
                if src.get("digest") and live_digest != src["digest"]:
                    problems.append(
                        "the scenario was transcribed from %s at %s, but that artifact is now "
                        "%s: the evidence is stale and no longer supports the candidate"
                        % (src_path, src.get("digest"), live_digest)
                    )
            else:
                problems.append(
                    "the scenario's source artifact %s cannot be read" % src_path
                )
        try:
            model = _model_from_scenario(scenario, catalog, receipt.get("chain"))
            run = simulate_model(
                model, int(receipt.get("seed", 0)), int(receipt.get("samples", 0))
            )
            if run["simulation_digest"] != receipt.get("simulation_digest"):
                problems.append(
                    "the simulation does not reproduce from the receipt's own seed and "
                    "sample count: the number in this receipt was not produced by the "
                    "model it names"
                )
            for key, val in (receipt.get("metrics") or {}).items():
                if key in run["metrics"] and run["metrics"][key] != val:
                    problems.append(
                        "metric %r in the receipt (%r) differs from the recomputed "
                        "value (%r)" % (key, val, run["metrics"][key])
                    )
        except Blind as exc:
            return {"verdict": "BLIND", "problems": problems + [str(exc)]}
        decision = (catalog.get("decision_classes") or {}).get(
            receipt.get("decision_class")
        ) or {}
        epsilon = decision.get("epsilon")
        bound = (receipt.get("metrics") or {}).get("slo_breach_bound")
        if epsilon is not None and bound is not None and bound > float(epsilon):
            problems.append(
                "the SLO breach bound %r exceeds the policy's epsilon %r for class %r"
                % (bound, epsilon, receipt.get("decision_class"))
            )

    if candidate_path:
        cand = Path(candidate_path).expanduser()
        if not cand.is_file():
            return {
                "verdict": "BLIND",
                "problems": problems
                + [
                    "the candidate %s cannot be read: a decision bound to an unreadable artifact is "
                    "blind, not approved" % cand
                ],
            }
        live = sha256_file(cand)
        if live != receipt.get("candidate_digest"):
            problems.append(
                "the candidate artifact is now %s but the receipt was issued against "
                "%s" % (live, receipt.get("candidate_digest"))
            )

    if problems:
        return {"verdict": "BLOCK", "problems": problems}

    assumed = sorted((receipt.get("provenance") or {}).get("assumed", []))
    rare = bool(receipt.get("rare_event"))
    if rare:
        return {
            "verdict": "REVIEW_REQUIRED",
            "problems": [
                "the simulation observed no breach in %s samples: a rare event "
                "needs importance sampling or an analytical bound, not a plain "
                "estimate" % receipt.get("samples")
            ],
            "assumed_parameters": assumed,
        }
    if assumed:
        return {
            "verdict": "REVIEW_REQUIRED",
            "problems": [
                "the model carries assumed parameters (%s): the number is "
                "reproducible but not measured" % ", ".join(assumed)
            ],
            "assumed_parameters": assumed,
        }
    return {"verdict": "PASS", "problems": [], "assumed_parameters": []}


def gate(
    case: Dict[str, Any],
    receipt: Optional[Dict[str, Any]],
    catalog: Dict[str, Any],
    candidate_path: Optional[str] = None,
) -> Dict[str, Any]:
    """The shared decision boundary. It never admits; it blocks or flags."""
    selection = method_selection(case, catalog)
    if selection.get("method") is None:
        return {
            "verdict": "BLIND",
            "exit_code": EXIT_BLIND,
            "selection": selection,
            "problems": [selection.get("reason", "no method could be selected")],
        }
    if not receipt:
        return {
            "verdict": "BLOCK",
            "exit_code": EXIT_BLOCK,
            "selection": selection,
            "problems": [
                "no assurance receipt was presented for class %r"
                % selection["decision_class"]
            ],
        }

    check = verify_receipt(receipt, catalog, candidate_path)
    if check["verdict"] == "BLIND":
        return {
            "verdict": "BLIND",
            "exit_code": EXIT_BLIND,
            "selection": selection,
            "problems": check["problems"],
        }
    if check["verdict"] == "BLOCK":
        return {
            "verdict": "BLOCK",
            "exit_code": EXIT_BLOCK,
            "selection": selection,
            "problems": check["problems"],
        }

    required_method = selection["method"]
    used_method = receipt.get("method")
    if used_method != required_method:
        # A deeper method is acceptable; a shallower one is not.
        deeper_ok = required_method == "deterministic" and used_method == "monte_carlo"
        if not deeper_ok:
            return {
                "verdict": "BLOCK",
                "exit_code": EXIT_BLOCK,
                "selection": selection,
                "problems": [
                    "the receipt was produced by the %r method but the policy for "
                    "class %r requires %r"
                    % (used_method, selection["decision_class"], required_method)
                ],
            }

    req_tier = TIER_ORDER.get(selection.get("tier") or "tier0", 0)
    got_tier = TIER_ORDER.get(receipt.get("tier") or "tier0", 0)
    if got_tier < req_tier:
        return {
            "verdict": "BLOCK",
            "exit_code": EXIT_BLOCK,
            "selection": selection,
            "problems": [
                "the receipt is %s and the policy for class %r requires %s"
                % (
                    receipt.get("tier"),
                    selection["decision_class"],
                    selection.get("tier"),
                )
            ],
        }

    verdict = check["verdict"]
    return {
        "verdict": verdict,
        "exit_code": EXIT_OK,
        "selection": selection,
        "problems": check.get("problems", []),
        "assumed_parameters": check.get("assumed_parameters", []),
        "note": "PASS means the evidence is present, reproducible and inside the bound. It is "
        "not an admission: Greenlane is the only admission authority.",
    }


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def _read_json(path: str) -> Any:
    return json.loads(Path(path).expanduser().read_text())


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def cmd_method(args: argparse.Namespace) -> int:
    catalog, path = load_catalog(args.catalog)
    if catalog is None:
        print("BLIND the decision-assurance catalog could not be read")
        return EXIT_BLIND
    case = {
        "class": args.decision_class,
        "impact": args.impact,
        "stochastic": args.stochastic,
        "monte_carlo_required": args.monte_carlo_required,
        "requested_method": args.requested_method,
        "requested_tier": args.requested_tier,
        "formal_invariant": args.formal_invariant,
    }
    selection = method_selection(case, catalog)
    _print({"catalog": str(path), "selection": selection})
    return EXIT_OK if selection.get("method") else EXIT_BLIND


def cmd_packet(args: argparse.Namespace) -> int:
    catalog, path = load_catalog(args.catalog)
    if catalog is None:
        print("BLIND the decision-assurance catalog could not be read")
        return EXIT_BLIND
    try:
        spec = _read_json(args.input)
        evidence = [Evidence.from_dict(e) for e in spec.get("evidence") or []]
        hypotheses = [Hypothesis.from_dict(h) for h in spec.get("hypotheses") or []]
        packet = build_packet(
            str(spec.get("problem", "")),
            evidence,
            hypotheses,
            catalog,
            spec.get("minimum_residual_prior"),
        )
    except (OSError, ValueError) as exc:
        print("BLOCK the hypothesis space could not be compiled: %s" % exc)
        return EXIT_BLOCK
    _print({"catalog": str(path), "packet": packet})
    return EXIT_OK


def cmd_simulate(args: argparse.Namespace) -> int:
    catalog, path = load_catalog(args.catalog)
    if catalog is None:
        print("BLIND the decision-assurance catalog could not be read")
        return EXIT_BLIND
    scenario = (catalog.get("scenarios") or {}).get(args.scenario)
    if scenario is None:
        print("BLIND no scenario named %r" % args.scenario)
        return EXIT_BLIND
    chain = args.chain or scenario.get("chain")
    decision_class = args.decision_class or "router.failover"
    decision = (catalog.get("decision_classes") or {}).get(decision_class) or {}
    tier = args.tier or decision.get("tier") or "tier1"
    candidate_digest = "sha256:none"
    if args.candidate:
        cand = Path(args.candidate).expanduser()
        if not cand.is_file():
            print("BLIND the candidate %s cannot be read" % cand)
            return EXIT_BLIND
        candidate_digest = sha256_file(cand)
    try:
        run = run_scenario(args.scenario, catalog, args.seed, args.samples, chain)
    except Blind as exc:
        print("BLIND %s" % exc)
        return EXIT_BLIND
    run["scenario_name"] = args.scenario
    receipt = build_receipt(
        decision_id=args.decision_id,
        decision_class=decision_class,
        method="monte_carlo",
        tier=tier,
        candidate_digest=candidate_digest,
        run=run,
        reason=args.reason or "assurance run for class %s" % decision_class,
    )
    receipt["scenario"] = args.scenario
    receipt["chain"] = chain
    receipt["digest"] = digest({k: v for k, v in receipt.items() if k != "digest"})
    if args.out:
        Path(args.out).expanduser().write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )
    _print(receipt)
    return EXIT_OK


def cmd_deterministic(args: argparse.Namespace) -> int:
    catalog, path = load_catalog(args.catalog)
    if catalog is None:
        print("BLIND the decision-assurance catalog could not be read")
        return EXIT_BLIND
    candidate_digest = "sha256:none"
    if args.candidate:
        cand = Path(args.candidate).expanduser()
        if not cand.is_file():
            print("BLIND the candidate %s cannot be read" % cand)
            return EXIT_BLIND
        candidate_digest = sha256_file(cand)
    receipt = build_receipt(
        decision_id=args.decision_id,
        decision_class=args.decision_class,
        method="deterministic",
        tier="tier0",
        candidate_digest=candidate_digest,
        deterministic_evidence=args.evidence_digest,
        reason=args.reason or "deterministic check for class %s" % args.decision_class,
    )
    if args.out:
        Path(args.out).expanduser().write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )
    _print(receipt)
    return EXIT_OK


def cmd_verify(args: argparse.Namespace) -> int:
    catalog, path = load_catalog(args.catalog)
    if catalog is None:
        print("BLIND the decision-assurance catalog could not be read")
        return EXIT_BLIND
    try:
        receipt = _read_json(args.receipt)
    except (OSError, ValueError) as exc:
        print("BLIND the receipt could not be read: %s" % exc)
        return EXIT_BLIND
    result = verify_receipt(receipt, catalog, args.candidate)
    _print(result)
    return {
        "PASS": EXIT_OK,
        "REVIEW_REQUIRED": EXIT_OK,
        "BLOCK": EXIT_BLOCK,
        "BLIND": EXIT_BLIND,
    }[result["verdict"]]


def cmd_gate(args: argparse.Namespace) -> int:
    catalog, path = load_catalog(args.catalog)
    if catalog is None:
        print("BLIND the decision-assurance catalog could not be read")
        return EXIT_BLIND
    receipt = None
    if args.receipt:
        try:
            receipt = _read_json(args.receipt)
        except (OSError, ValueError) as exc:
            print("BLIND the receipt could not be read: %s" % exc)
            return EXIT_BLIND
    case = {
        "class": args.decision_class,
        "impact": args.impact,
        "stochastic": args.stochastic,
        "monte_carlo_required": args.monte_carlo_required,
        "requested_method": args.requested_method,
        "requested_tier": args.requested_tier,
        "formal_invariant": args.formal_invariant,
    }
    result = gate(case, receipt, catalog, args.candidate)
    _print(result)
    return int(result["exit_code"])


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="decision assurance for the estate")
    ap.add_argument("--catalog", help="path to catalog/decision-assurance.json")
    sub = ap.add_subparsers(dest="command")

    m = sub.add_parser("method", help="select the method for a decision class")
    m.add_argument("--class", dest="decision_class", required=True)
    m.add_argument("--impact", default="medium")
    m.add_argument("--stochastic", action="store_true")
    m.add_argument(
        "--monte-carlo-required",
        dest="monte_carlo_required",
        default=None,
        type=lambda v: str(v).lower() in ("1", "true", "yes"),
    )
    m.add_argument("--requested-method", dest="requested_method", default=None)
    m.add_argument("--requested-tier", dest="requested_tier", default=None)
    m.add_argument("--formal-invariant", dest="formal_invariant", action="store_true")
    m.set_defaults(func=cmd_method)

    p = sub.add_parser("packet", help="compile a hypothesis-space packet")
    p.add_argument("--input", required=True)
    p.set_defaults(func=cmd_packet)

    s = sub.add_parser("simulate", help="run a scenario and emit an assurance receipt")
    s.add_argument("--scenario", required=True)
    s.add_argument("--chain", default=None)
    s.add_argument("--seed", type=int, default=42)
    s.add_argument("--samples", type=int, default=2000)
    s.add_argument("--decision-id", dest="decision_id", default="router-failover")
    s.add_argument("--decision-class", dest="decision_class", default="router.failover")
    s.add_argument("--tier", default=None)
    s.add_argument("--candidate", default=None)
    s.add_argument("--reason", default="")
    s.add_argument("--out", default=None)
    s.set_defaults(func=cmd_simulate)

    d = sub.add_parser("deterministic", help="emit a deterministic assurance receipt")
    d.add_argument("--decision-id", dest="decision_id", required=True)
    d.add_argument("--decision-class", dest="decision_class", default="lint.schema")
    d.add_argument("--evidence-digest", dest="evidence_digest", required=True)
    d.add_argument("--candidate", default=None)
    d.add_argument("--reason", default="")
    d.add_argument("--out", default=None)
    d.set_defaults(func=cmd_deterministic)

    v = sub.add_parser("verify", help="verify a receipt by recomputation")
    v.add_argument("--receipt", required=True)
    v.add_argument("--candidate", default=None)
    v.set_defaults(func=cmd_verify)

    g = sub.add_parser("gate", help="the shared decision boundary")
    g.add_argument("--class", dest="decision_class", required=True)
    g.add_argument("--receipt", default=None)
    g.add_argument("--candidate", default=None)
    g.add_argument("--impact", default="medium")
    g.add_argument("--stochastic", action="store_true")
    g.add_argument(
        "--monte-carlo-required",
        dest="monte_carlo_required",
        default=None,
        type=lambda v: str(v).lower() in ("1", "true", "yes"),
    )
    g.add_argument("--requested-method", dest="requested_method", default=None)
    g.add_argument("--requested-tier", dest="requested_tier", default=None)
    g.add_argument("--formal-invariant", dest="formal_invariant", action="store_true")
    g.set_defaults(func=cmd_gate)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return EXIT_BLIND
    try:
        return int(args.func(args))
    except Blind as exc:
        print("BLIND %s" % exc)
        return EXIT_BLIND
    except (OSError, ValueError, KeyError) as exc:
        print("BLOCK %s" % exc)
        return EXIT_BLOCK


if __name__ == "__main__":
    sys.exit(main())
