"""The concurrency envelope: what runs at the same time, on what capacity, at what cost.

G5 is the gate that makes the estate's execution economics hold at scale, and
it is a policy, not a new machine. The estate already has a queue
(``platform/queue/dispatcher.py``) and a worker pool
(``platform/execution/worker_pool.py``); this module decides WHICH work
becomes a queue task and WHEN. It is the admission controller in front of the
pool the estate already runs -- not a second pool, not a second queue, not a
second budget.

The six exit criteria, and where each one is enforced:

  * independent work runs at the same time, dependent work waits
    -> ``ScaleScheduler.admit`` walks ``WorkGraph.ready_nodes()``: a node is a
       candidate only when every parent is accepted, and the cap decides how
       many candidates start together.
  * overlapping code is detected before integration, not after
    -> ``scopes_conflict`` compares the authorised scopes of everything in
       flight, and the refusal names the other node and the path.
  * quota exhaustion mid-run diverts to the next lane, and the node does not fail
    -> ``ScaleScheduler.divert`` re-runs the ONE allocation policy (G4) with
       the exhausted lane excluded, under the SAME logical key.
  * cancellation releases the hold and stops the spend
    -> ``ScaleScheduler.cancel`` releases the reservation; nothing is committed.
  * a restart resumes without double spend and without a second execution
    -> ``SchedulerJournal`` carries the keys, the holds and the committed cost;
       a key that was already decided is never admitted again.
  * the budget ceiling stops work deterministically, with the reason recorded
    -> ``ScaleScheduler.admit`` stops the pass at the ceiling and writes
       ``cutoff_reason`` into the journal.

WHERE THE MONEY IS. The reservations and the economic receipts live in the
``WorkGraph``: that is the estate's record of what was held, spent and
measured. The journal is the scheduler's own resume record -- it never creates
money, it only names the receipt and the cost the scheduler already decided.

THE SEAM. The dispatcher has no dependency, scope, contract or idempotency
column, and it does not need one: the graph stays the only place the
dependency and scope state is written down, and the node's identity travels in
the goal text (``encode_goal`` / ``decode_goal``). Nothing here imports the
estate's substrate -- the substrate calls in, not the other way round -- so
this module stays deterministic and testable on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .allocation import (
    Allocation,
    AllocationError,
    AllocationRequest,
    SupplyOffer,
    allocate,
)
from .contracts import (
    CapacityReservation,
    EconomicReceipt,
    ExecutionContract,
    VerificationLevel,
    WorkNode,
)
from .digest import digest_of
from .graph import UnknownNodeError, WorkGraph

__all__ = [
    "Admission",
    "AdmissionOutcome",
    "JournalEntry",
    "NodeSupply",
    "ScaleError",
    "ScalePolicy",
    "ScaleScheduler",
    "SchedulerJournal",
    "decode_goal",
    "encode_goal",
    "scopes_conflict",
]

GOAL_PREFIX = "aee"


class ScaleError(RuntimeError):
    """The envelope refuses to act, and says why."""


class AdmissionOutcome(str, Enum):
    """What happened to one candidate in one admission pass.

    ``ADMITTED`` started, ``DEFERRED`` waits (the cap is full), ``REFUSED``
    cannot start (the scope is taken, no lane can take it, the budget ceiling
    is reached, or the work was already decided).
    """

    ADMITTED = "admitted"
    DEFERRED = "deferred"
    REFUSED = "refused"


@dataclass(frozen=True)
class ScalePolicy:
    """The envelope's shape: how much at once, and how much it may cost.

    ``budget_ceiling_usd`` of zero means no ceiling: the envelope then holds
    the budget authority's decision alone. A ceiling above zero is the
    envelope's own bound, and it counts the money that is already exposed --
    committed plus held -- because a hold is money the estate cannot spend
    twice.
    """

    max_concurrent: int = 4
    budget_ceiling_usd: float = 0.0
    budget_ref: str = "sovereign/engine/budget.py"

    def __post_init__(self) -> None:
        if self.max_concurrent < 1:
            raise ScaleError("a concurrency envelope must hold at least one slot")
        if self.budget_ceiling_usd < 0:
            raise ScaleError("a budget ceiling cannot be negative")
        if not self.budget_ref.strip():
            raise ScaleError(
                "a reservation must name the budget authority it holds against"
            )


@dataclass(frozen=True)
class NodeSupply:
    """What the estate can offer one node, right now.

    The supply is the caller's data: the envelope does not keep a view of the
    estate's lanes (that would be a second supply registry), it is told.
    """

    offers: Tuple[SupplyOffer, ...] = ()
    estimated_tokens: int = 0
    required_capabilities: Tuple[str, ...] = ()
    budget_usd: float = 0.0
    deadline_s: Optional[int] = None
    units: int = 1
    max_attempts: int = 1
    verification_levels: Tuple[VerificationLevel, ...] = (VerificationLevel.OPERATION,)

    def __post_init__(self) -> None:
        object.__setattr__(self, "offers", tuple(self.offers))
        object.__setattr__(
            self, "required_capabilities", tuple(self.required_capabilities)
        )
        object.__setattr__(self, "verification_levels", tuple(self.verification_levels))
        if self.estimated_tokens < 0:
            raise ScaleError("a supply cannot estimate negative tokens")
        if self.units < 1:
            raise ScaleError("a supply must offer at least one unit")
        if self.budget_usd < 0:
            raise ScaleError("a supply budget cannot be negative")


@dataclass(frozen=True)
class Admission:
    """One candidate's decision, with everything needed to act on it."""

    node_id: str
    outcome: AdmissionOutcome
    reason: str
    logical_key: str = ""
    attempt_id: str = ""
    contract: Optional[ExecutionContract] = None
    reservation: Optional[CapacityReservation] = None
    receipt: Optional[EconomicReceipt] = None


@dataclass(frozen=True)
class JournalEntry:
    """One decision the scheduler made, in the form a restart can read.

    ``state`` is the control fact: ``running`` (a hold is out), ``committed``
    (the work is done and its cost is known), ``failed`` (the attempt died and
    the hold went back) or ``cancelled`` (the work was stopped). The logical
    key is the identity of the WORK, not of the lane: a diversion moves the
    work to another lane without changing the key, so a restart can tell
    "already done" from "not started yet".
    """

    logical_key: str
    node_id: str
    attempt_no: int = 1
    attempt_id: str = ""
    contract_id: str = ""
    lane_id: str = ""
    reservation_id: str = ""
    state: str = "running"
    reserved_usd: float = 0.0
    committed_usd: float = 0.0
    receipt_id: str = ""
    at: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        return {
            "logical_key": self.logical_key,
            "node_id": self.node_id,
            "attempt_no": self.attempt_no,
            "attempt_id": self.attempt_id,
            "contract_id": self.contract_id,
            "lane_id": self.lane_id,
            "reservation_id": self.reservation_id,
            "state": self.state,
            "reserved_usd": self.reserved_usd,
            "committed_usd": self.committed_usd,
            "receipt_id": self.receipt_id,
            "at": self.at,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "JournalEntry":
        if not isinstance(raw, Mapping):
            raise ScaleError("a journal entry is a mapping")
        try:
            return cls(
                logical_key=str(raw["logical_key"]),
                node_id=str(raw["node_id"]),
                attempt_no=int(raw.get("attempt_no", 1)),  # type: ignore[arg-type]
                attempt_id=str(raw.get("attempt_id", "")),
                contract_id=str(raw.get("contract_id", "")),
                lane_id=str(raw.get("lane_id", "")),
                reservation_id=str(raw.get("reservation_id", "")),
                state=str(raw.get("state", "running")),
                reserved_usd=float(raw.get("reserved_usd", 0.0)),  # type: ignore[arg-type]
                committed_usd=float(raw.get("committed_usd", 0.0)),  # type: ignore[arg-type]
                receipt_id=str(raw.get("receipt_id", "")),
                at=float(raw.get("at", 0.0)),  # type: ignore[arg-type]
            )
        except KeyError as err:
            raise ScaleError("a journal entry is missing %s" % err) from err


@dataclass
class SchedulerJournal:
    """The scheduler's durable state: what is in flight, what was spent.

    It is a resume record, not a ledger: every committed amount it carries is
    the cost of a receipt it names, and the graph holds the receipts and the
    reservations themselves.
    """

    entries: Dict[str, JournalEntry] = field(default_factory=dict)
    cutoff_reason: str = ""
    diversions: List[Dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "version": 1,
            "cutoff_reason": self.cutoff_reason,
            "diversions": [dict(d) for d in self.diversions],
            "entries": {
                key: self.entries[key].to_dict() for key in sorted(self.entries)
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "SchedulerJournal":
        if not isinstance(data, Mapping):
            raise ScaleError("a journal is a mapping")
        raw_entries = data.get("entries") or {}
        if not isinstance(raw_entries, Mapping):
            raise ScaleError("a journal's entries are a mapping")
        entries = {}
        for key, raw in raw_entries.items():
            entry = JournalEntry.from_dict(raw)  # type: ignore[arg-type]
            entries[str(key)] = entry
        diversions = data.get("diversions") or []
        if not isinstance(diversions, (list, tuple)):
            raise ScaleError("a journal's diversions are a list")
        return cls(
            entries=entries,
            cutoff_reason=str(data.get("cutoff_reason", "")),
            diversions=[dict(d) for d in diversions],  # type: ignore[arg-type]
        )

    def digest(self) -> str:
        return digest_of(self.to_dict())

    def running(self) -> List[JournalEntry]:
        return [e for e in self.entries.values() if e.state == "running"]

    def committed_usd(self) -> float:
        return round(sum(e.committed_usd for e in self.entries.values()), 6)

    def held_usd(self) -> float:
        return round(
            sum(e.reserved_usd for e in self.entries.values() if e.state == "running"),
            6,
        )


def _literal_prefix(pattern: str) -> str:
    """The part of a path pattern before its first wildcard."""
    for index, char in enumerate(pattern):
        if char in "*?[":
            return pattern[:index]
    return pattern


def _segment_prefix(one: str, other: str) -> bool:
    """Whether one path is the other, or a path-segment prefix of it."""
    left = one.rstrip("/")
    right = other.rstrip("/")
    if not left or not right:
        return False
    return left == right or right.startswith(left + "/") or left.startswith(right + "/")


def _paths_conflict(one: str, other: str) -> bool:
    """Whether two authorised paths can name the same file."""
    if one == other:
        return True
    if any(char in one for char in "*?[") or any(char in other for char in "*?["):
        left = _literal_prefix(one).rstrip("/")
        right = _literal_prefix(other).rstrip("/")
        if not left or not right:
            # A bare wildcard can reach anything: refuse rather than guess.
            return True
        return _segment_prefix(left, right)
    return _segment_prefix(one, other)


def scopes_conflict(one: Sequence[str], other: Sequence[str]) -> str:
    """The paths both scopes could authorise, or "" when they cannot.

    Conservative and deterministic: two scopes conflict when they name the
    same path, when one is a path-segment prefix of the other, or when their
    glob literal prefixes overlap. Over-refusal is safe -- the work waits --
    while under-refusal is two workers writing the same file.
    """
    for left in one:
        for right in other:
            if _paths_conflict(left, right):
                return "%s and %s" % (left, right)
    return ""


def encode_goal(node_id: str, logical_key: str, title: str = "") -> str:
    """Carry the node's identity in the queue goal, without a schema change.

    The dispatcher stores a goal string and nothing else. The envelope needs
    the node and its key on the other side of the queue, so they travel in the
    goal -- and the graph stays the only place the dependency and scope state
    is written down.
    """
    return "%s|%s|%s|%s" % (GOAL_PREFIX, logical_key, node_id, title)


def decode_goal(goal: str) -> Optional[Tuple[str, str, str]]:
    """The (logical key, node id, title) a goal carries, or None."""
    parts = goal.split("|", 3)
    if len(parts) != 4 or parts[0] != GOAL_PREFIX:
        return None
    return parts[1], parts[2], parts[3]


class ScaleScheduler:
    """The concurrency envelope over one work graph.

    It is deterministic: the same graph, the same supply and the same moment
    produce the same admissions, the same contracts and the same holds. The
    only inputs are the arguments -- there is no clock and no randomness in
    here -- so a decision can be replayed and audited.
    """

    def __init__(
        self,
        graph: WorkGraph,
        *,
        policy: ScalePolicy,
        journal: Optional[SchedulerJournal] = None,
        actor: str = "",
    ) -> None:
        if not isinstance(graph, WorkGraph):
            raise ScaleError("the envelope runs over a WorkGraph")
        if not isinstance(policy, ScalePolicy):
            raise ScaleError("the envelope runs under a ScalePolicy")
        if journal is not None and not isinstance(journal, SchedulerJournal):
            raise ScaleError("the envelope resumes from a SchedulerJournal")
        self.graph = graph
        self.policy = policy
        self.journal = journal if journal is not None else SchedulerJournal()
        self.actor = actor or graph.owner
        # The keys this process decided. A key that is in the journal but not
        # in here was decided by a PREVIOUS process: that is a restart, and a
        # restart resumes the work under the same key rather than repeating
        # it.
        self._decided: set[str] = set()

    # ---- what the estate has exposed ----------------------------------

    def running_nodes(self) -> List[str]:
        return sorted(e.node_id for e in self.journal.running())

    def held_usd(self) -> float:
        return self.journal.held_usd()

    def committed_usd(self) -> float:
        return self.journal.committed_usd()

    def exposure_usd(self) -> float:
        """The money the estate cannot spend twice: committed plus held."""
        return round(self.committed_usd() + self.held_usd(), 6)

    # ---- identity -----------------------------------------------------

    def logical_key(self, node_id: str, attempt_no: int) -> str:
        """The identity of the WORK, independent of the lane it runs on.

        G4's contract key includes the lane, so a diversion would change it.
        This key does not: a node and its attempt are the same work whichever
        lane takes it, which is what lets a restart tell "already done" from
        "not started yet".
        """
        digest = digest_of(
            {"graph": self.graph.graph_id, "node": node_id, "attempt": attempt_no}
        )
        return "lk-%s" % digest[:16]

    def _entries_for(self, node_id: str) -> List[JournalEntry]:
        return [e for e in self.journal.entries.values() if e.node_id == node_id]

    def _latest_entry(self, node_id: str) -> Optional[JournalEntry]:
        entries = self._entries_for(node_id)
        if not entries:
            return None
        return max(entries, key=lambda e: (e.attempt_no, e.at))

    def _attempt_no(self, node_id: str) -> int:
        latest = self._latest_entry(node_id)
        if latest is None:
            return 1
        if latest.state == "failed":
            # A failed attempt is a new attempt: the work is the same, the
            # attempt number is not.
            return latest.attempt_no + 1
        return latest.attempt_no

    def _running_entry(self, node_id: str) -> Optional[JournalEntry]:
        for entry in self._entries_for(node_id):
            if entry.state == "running":
                return entry
        return None

    # ---- admission ----------------------------------------------------

    def admit(
        self,
        supply: Mapping[str, NodeSupply],
        *,
        now: float = 0.0,
    ) -> List[Admission]:
        """Decide, in one deterministic pass, what starts now.

        Every candidate gets an answer, and the answer says why. A candidate
        is refused rather than guessed at, and a candidate that cannot start
        yet is deferred rather than failed.
        """
        results: List[Admission] = []
        cutoff = self.journal.cutoff_reason
        for node in self.graph.ready_nodes():
            if cutoff:
                results.append(
                    Admission(
                        node.id,
                        AdmissionOutcome.REFUSED,
                        "the envelope is closed: %s" % cutoff,
                    )
                )
                continue

            attempt_no = self._attempt_no(node.id)
            key = self.logical_key(node.id, attempt_no)
            latest = self._latest_entry(node.id)

            if latest is not None and latest.state in ("committed", "cancelled"):
                results.append(
                    Admission(
                        node.id,
                        AdmissionOutcome.REFUSED,
                        "already %s under key %s; no second execution"
                        % (latest.state, latest.logical_key),
                        logical_key=latest.logical_key,
                    )
                )
                continue

            stale = None
            if latest is not None and latest.state == "running":
                if key in self._decided:
                    results.append(
                        Admission(
                            node.id,
                            AdmissionOutcome.REFUSED,
                            "already in flight under key %s" % key,
                            logical_key=key,
                        )
                    )
                    continue
                # A previous process left this work in flight: resume it under
                # the same key, with a fresh hold.
                stale = latest

            conflict = self._scope_conflict(node)
            if conflict:
                results.append(
                    Admission(
                        node.id, AdmissionOutcome.REFUSED, conflict, logical_key=key
                    )
                )
                continue

            in_flight = [e for e in self.journal.running() if e.node_id != node.id]
            if len(in_flight) >= self.policy.max_concurrent:
                results.append(
                    Admission(
                        node.id,
                        AdmissionOutcome.DEFERRED,
                        "the envelope holds %d of %d; this waits"
                        % (len(in_flight), self.policy.max_concurrent),
                        logical_key=key,
                    )
                )
                continue

            node_supply = supply.get(node.id)
            if node_supply is None:
                results.append(
                    Admission(
                        node.id,
                        AdmissionOutcome.REFUSED,
                        "no supply was offered for node %r" % node.id,
                        logical_key=key,
                    )
                )
                continue

            try:
                allocation = self._allocate(node, node_supply, now=now)
            except AllocationError as err:
                results.append(
                    Admission(
                        node.id, AdmissionOutcome.REFUSED, str(err), logical_key=key
                    )
                )
                continue

            cost = allocation.reservation.usd
            projected = round(self.exposure_usd() + cost, 6)
            ceiling = self.policy.budget_ceiling_usd
            if ceiling > 0 and projected > ceiling:
                cutoff = (
                    "the budget ceiling of %.6f usd is reached: node %s would need "
                    "%.6f usd on top of %.6f usd already exposed"
                    % (ceiling, node.id, cost, self.exposure_usd())
                )
                self.journal.cutoff_reason = cutoff
                results.append(
                    Admission(
                        node.id, AdmissionOutcome.REFUSED, cutoff, logical_key=key
                    )
                )
                continue

            self._hold(node, allocation, stale=stale, now=now)
            self.journal.entries[key] = JournalEntry(
                logical_key=key,
                node_id=node.id,
                attempt_no=attempt_no,
                attempt_id=allocation.receipt.attempt_id,
                contract_id=allocation.contract.id,
                lane_id=allocation.contract.lane.id,
                reservation_id=allocation.reservation.id,
                state="running",
                reserved_usd=allocation.reservation.usd,
                committed_usd=0.0,
                receipt_id="",
                at=now,
            )
            self._decided.add(key)
            results.append(
                Admission(
                    node.id,
                    AdmissionOutcome.ADMITTED,
                    allocation.reason,
                    logical_key=key,
                    attempt_id=allocation.receipt.attempt_id,
                    contract=allocation.contract,
                    reservation=allocation.reservation,
                    receipt=allocation.receipt,
                )
            )
        return results

    def _allocate(
        self, node: WorkNode, node_supply: NodeSupply, *, now: float
    ) -> Allocation:
        request = AllocationRequest(
            node=node,
            offers=node_supply.offers,
            required_capabilities=node_supply.required_capabilities,
            budget_usd=node_supply.budget_usd,
            deadline_s=node_supply.deadline_s,
            estimated_tokens=node_supply.estimated_tokens,
            units=node_supply.units,
            max_attempts=node_supply.max_attempts,
            now=now,
            budget_ref=self.policy.budget_ref,
            verification_levels=node_supply.verification_levels,
        )
        return allocate(request)

    def _scope_conflict(self, node: WorkNode) -> str:
        """The conflict with something in flight, or "" when there is none."""
        for entry in self.journal.running():
            if entry.node_id == node.id:
                continue
            try:
                other = self.graph.node(entry.node_id)
            except UnknownNodeError:
                # A rebuilt graph may not know the node a previous process left in flight.
                continue
            overlap = scopes_conflict(node.scope, other.scope)
            if overlap:
                return "scope conflict: node %r and %r both authorise %s" % (
                    node.id,
                    other.id,
                    overlap,
                )
        return ""

    def _hold(
        self,
        node: WorkNode,
        allocation: Allocation,
        *,
        stale: Optional[JournalEntry],
        now: float,
    ) -> None:
        """Take the hold: the contract, the reservation, then the start."""
        if stale is not None and stale.reservation_id:
            if stale.reservation_id in self.graph.reservations:
                self.graph.release_reservation(stale.reservation_id, actor=self.actor)
        self.graph.attach_contract(allocation.contract, actor=self.actor)
        self.graph.reserve(
            node.id,
            lane=allocation.contract.lane,
            units=allocation.reservation.units,
            usd=allocation.reservation.usd,
            budget_ref=self.policy.budget_ref,
            window_s=allocation.reservation.window_s,
            reservation_id=allocation.reservation.id,
            actor=self.actor,
        )
        self.graph.mark_running(
            node.id,
            attempt_id=allocation.receipt.attempt_id,
            contract_id=allocation.contract.id,
            actor=self.actor,
        )

    # ---- what happened to the work ------------------------------------

    def commit(
        self,
        node_id: str,
        *,
        cost_usd: float,
        ledger_hash: str,
        now: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> EconomicReceipt:
        """The attempt is done and measured: the hold becomes spend.

        The cost that lands here is the measured cost, and it names the signed
        ledger row it derives from. The receipt and the committed reservation
        live in the graph; the journal only records the decision, so a restart
        can refuse to spend the same work twice.
        """
        entry = self._running_entry(node_id)
        if entry is None:
            raise ScaleError("node %r has no work in flight to commit" % node_id)
        if cost_usd < 0:
            raise ScaleError("a measured cost cannot be negative")
        if not ledger_hash.strip():
            raise ScaleError("a measured cost must name the ledger row it derives from")
        contract = self.graph.contract_for(node_id)
        receipt = EconomicReceipt(
            id="eco-%s" % digest_of({"key": entry.logical_key, "at": now})[:16],
            attempt_id=entry.attempt_id,
            node_id=node_id,
            contract_id=entry.contract_id,
            provider=contract.lane.provider if contract else "unknown",
            model=contract.lane.model if contract else "",
            at=now,
            cost_usd=cost_usd,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            ledger_hash=ledger_hash,
            unit_price_usd_per_1k=contract.lane.cost_usd_per_1k if contract else 0.0,
            waste_class="productive",
        )
        self.graph.record_economics(receipt)
        self.graph.commit_reservation(entry.reservation_id, actor=self.actor)
        self.journal.entries[entry.logical_key] = replace(
            entry,
            state="committed",
            committed_usd=cost_usd,
            receipt_id=receipt.id,
            at=now,
        )
        return receipt

    def fail(self, node_id: str, *, reason: str, now: float = 0.0) -> None:
        """The attempt died: the hold goes back, the node is failed."""
        entry = self._running_entry(node_id)
        if entry is None:
            raise ScaleError("node %r has no work in flight to fail" % node_id)
        self.graph.release_reservation(entry.reservation_id, actor=self.actor)
        self.graph.fail(node_id, reason=reason, actor=self.actor)
        self.journal.entries[entry.logical_key] = replace(
            entry, state="failed", reserved_usd=0.0, at=now
        )

    def cancel(self, node_id: str, *, reason: str, now: float = 0.0) -> None:
        """Stop the work: the hold goes back and nothing is spent.

        The committed spend does not move: cancelling work that has already
        cost money does not un-cost it, and the estate's record says so.
        """
        entry = self._running_entry(node_id)
        self.graph.cancel(node_id, reason=reason, actor=self.actor)
        if entry is None:
            return
        self.journal.entries[entry.logical_key] = replace(
            entry, state="cancelled", reserved_usd=0.0, at=now
        )

    def divert(
        self,
        node_id: str,
        *,
        supply: NodeSupply,
        now: float = 0.0,
    ) -> Admission:
        """Move the work to another lane because the first one ran out.

        The node does not fail: the work is the same work, so it keeps its
        logical key, and the allocation policy runs again with the exhausted
        lane left out. The old hold is given back and the new one is taken
        under the same key.
        """
        entry = self._running_entry(node_id)
        if entry is None:
            raise ScaleError("node %r has no work in flight to divert" % node_id)
        node = self.graph.node(node_id)
        exhausted = entry.lane_id
        offers = tuple(offer for offer in supply.offers if offer.lane.id != exhausted)
        if not offers:
            raise ScaleError(
                "no lane other than %s can take node %r" % (exhausted, node_id)
            )
        diverted_supply = replace(supply, offers=offers)
        allocation = self._allocate(node, diverted_supply, now=now)

        self.graph.release_reservation(entry.reservation_id, actor=self.actor)
        self.graph.replace(node_id, contract=allocation.contract, actor=self.actor)
        self.graph.reserve(
            node_id,
            lane=allocation.contract.lane,
            units=allocation.reservation.units,
            usd=allocation.reservation.usd,
            budget_ref=self.policy.budget_ref,
            window_s=allocation.reservation.window_s,
            reservation_id=allocation.reservation.id,
            actor=self.actor,
        )
        self.graph.mark_running(
            node_id,
            attempt_id=allocation.receipt.attempt_id,
            contract_id=allocation.contract.id,
            actor=self.actor,
        )
        self.journal.entries[entry.logical_key] = replace(
            entry,
            attempt_id=allocation.receipt.attempt_id,
            contract_id=allocation.contract.id,
            lane_id=allocation.contract.lane.id,
            reservation_id=allocation.reservation.id,
            reserved_usd=allocation.reservation.usd,
            at=now,
        )
        self.journal.diversions.append(
            {
                "logical_key": entry.logical_key,
                "node_id": node_id,
                "from_lane": exhausted,
                "to_lane": allocation.contract.lane.id,
                "at": now,
            }
        )
        return Admission(
            node_id,
            AdmissionOutcome.ADMITTED,
            "diverted from %s to %s under key %s"
            % (exhausted, allocation.contract.lane.id, entry.logical_key),
            logical_key=entry.logical_key,
            attempt_id=allocation.receipt.attempt_id,
            contract=allocation.contract,
            reservation=allocation.reservation,
            receipt=allocation.receipt,
        )
