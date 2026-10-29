"""The work graph: what depends on what, and the rules that keep it honest.

This is the AEE's one new planning structure. It does not schedule anything:
``platform/queue/dispatcher.py`` claims tasks and makes worktrees, and this
says which work is unblocked.

The rules below are the specification's invariants, made mechanical and made
falsifiable. Each one is a refusal with a name, so a caller can tell WHICH
rule it broke:

    no hard-dependency cycles          -> CycleError
    no accepted node without evidence  -> VerificationRequiredError
    objective acceptance independent of the work -> IndependenceRequiredError
    no completed child under an unaccepted parent -> AcceptanceRequiredError
    auditable evidence invalidation    -> the receipts stay, the node resets
    coordinated mutation ownership     -> OwnershipError
    authorised-scope enforcement        -> ScopeError
    no silent loss of work or reservations -> ReservationError / the dependents are BLOCKED

Every mutation appends a GraphRevision, so the graph's history is a chain of
addresses and not a log that can be edited.
"""

from __future__ import annotations

import time
from dataclasses import replace
from fnmatch import fnmatch
from typing import Dict, Iterable, List, Optional, Sequence

from .contracts import (
    CapacityReservation,
    ContractError,
    EconomicReceipt,
    ExecutionAttempt,
    ExecutionContract,
    GraphRevision,
    IntelligenceLane,
    MutationOp,
    NodeKind,
    NodeState,
    Objective,
    ReservationState,
    Verdict,
    VerificationLevel,
    VerificationReceipt,
    WorkNode,
)
from .digest import digest_of


class GraphError(RuntimeError):
    """A mutation the graph refuses."""


class UnknownNodeError(GraphError):
    """No such node."""


class CycleError(GraphError):
    """The mutation would make a node depend on its own descendant."""


class ScopeError(GraphError):
    """The mutation touches a path outside the authorised scope."""


class VerificationRequiredError(GraphError):
    """The node would be accepted without the evidence its contract demands."""


class AcceptanceRequiredError(GraphError):
    """The node would complete while a parent it depends on is unaccepted."""


class OwnershipError(GraphError):
    """Someone else owns this graph's mutations."""


class ReservationError(GraphError):
    """A reservation would be lost, overspent, or spent twice."""


class ContractViolation(GraphError):
    """A mutation contradicts the contract attached to the node."""


class IndependenceRequiredError(GraphError):
    """Objective acceptance was signed by the agent that did the work."""


def _scope_allows(pattern: str, path: str) -> bool:
    """Does ``pattern`` authorise ``path``?

    A glob (``*``/``?``) is matched with fnmatch; a plain path is a prefix, so
    ``packages/aee`` authorises everything under it.
    """
    if any(ch in pattern for ch in "*?["):
        return fnmatch(path, pattern)
    return path == pattern or path.startswith(pattern.rstrip("/") + "/")


class WorkGraph:
    """A versioned, dependency-aware plan with the authority to change it.

    ``owner`` is the agent that may mutate the graph. A second agent is
    refused until ownership is handed over, and the handover is itself a
    revision -- so "who changed the plan" is never a matter of opinion.
    """

    def __init__(
        self,
        objective: Objective,
        graph_id: str,
        *,
        owner: str = "unknown",
        clock=time.time,
    ) -> None:
        if not isinstance(objective, Objective):
            raise ContractError("a graph is built over an Objective")
        self.objective = objective
        self.graph_id = graph_id
        self.owner = owner
        self._clock = clock
        self.nodes: Dict[str, WorkNode] = {}
        self.contracts: Dict[str, ExecutionContract] = {}
        self.attempts: Dict[str, List[ExecutionAttempt]] = {}
        self.verifications: Dict[str, VerificationReceipt] = {}
        self.economics: Dict[str, EconomicReceipt] = {}
        self.reservations: Dict[str, CapacityReservation] = {}
        self.reservations_by_node: Dict[str, str] = {}
        self.revisions: List[GraphRevision] = []
        self._revision(MutationOp.ADD, owner, "graph created")

    # ---- state -------------------------------------------------------

    def node(self, node_id: str) -> WorkNode:
        try:
            return self.nodes[node_id]
        except KeyError as err:
            raise UnknownNodeError(
                "no node %r in graph %r" % (node_id, self.graph_id)
            ) from err

    def contract_for(self, node_id: str) -> Optional[ExecutionContract]:
        node = self.node(node_id)
        if not node.contract_id:
            return None
        return self.contracts.get(node.contract_id)

    def state(self) -> Dict[str, object]:
        """The whole graph as plain data -- the thing a digest is taken over."""
        return {
            "graph_id": self.graph_id,
            "objective_id": self.objective.id,
            "nodes": {
                nid: {
                    "state": n.state.value,
                    "kind": n.kind.value,
                    "depends_on": list(n.depends_on),
                    "scope": list(n.scope),
                    "priority": n.priority,
                    "owner": n.owner,
                    "attempt_id": n.attempt_id,
                    "contract_id": n.contract_id,
                    "verification_ids": list(n.verification_ids),
                    "reservation_id": n.reservation_id,
                    "reason": n.reason,
                }
                for nid, n in sorted(self.nodes.items())
            },
            "reservations": {
                rid: {
                    "state": r.state.value,
                    "usd": r.usd,
                    "units": r.units,
                    "lane_id": r.lane_id,
                    "node_id": self.reservations_by_node.get(rid, ""),
                }
                for rid, r in sorted(self.reservations.items())
            },
        }

    def digest(self) -> str:
        return digest_of(self.state())

    def revision_count(self) -> int:
        return len(self.revisions)

    # ---- internals ---------------------------------------------------

    def _actor(self, actor: str) -> str:
        who = actor or self.owner
        if who != self.owner:
            raise OwnershipError(
                "graph %r is owned by %r; %r may not mutate it"
                % (self.graph_id, self.owner, who)
            )
        return who

    def _revision(self, op: MutationOp, actor: str, summary: str) -> GraphRevision:
        st = self.state()
        parent = self.revisions[-1].digest if self.revisions else ""
        revision = GraphRevision(
            number=len(self.revisions) + 1,
            digest=digest_of(st),
            parent_digest=parent,
            op=op,
            actor=actor,
            at=self._clock(),
            summary=summary,
            node_states=tuple(
                (nid, str(info["state"])) for nid, info in sorted(st["nodes"].items())
            ),
        )
        self.revisions.append(revision)
        return revision

    def _set(self, node_id: str, **changes) -> WorkNode:
        node = replace(self.nodes[node_id], **changes)
        self.nodes[node_id] = node
        return node

    def _check_scope(self, scope: Sequence[str], what: str) -> None:
        allowed = self.objective.scope
        for path in scope:
            if not isinstance(path, str) or not path.strip():
                raise ScopeError("%s carries an empty path" % what)
            if not allowed:
                continue
            if not any(_scope_allows(pattern, path) for pattern in allowed):
                raise ScopeError(
                    "%s touches %r, outside the objective's authorised scope %r"
                    % (what, path, list(allowed))
                )

    def _would_cycle(self, node_id: str, depends_on: Iterable[str]) -> bool:
        """Would ``node_id`` depending on ``depends_on`` close a loop?"""
        edges = {nid: set(n.depends_on) for nid, n in self.nodes.items()}
        edges[node_id] = set(depends_on)
        seen = set()
        stack = list(depends_on)
        while stack:
            cur = stack.pop()
            if cur == node_id:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(edges.get(cur, ()))
        return False

    def _require_deps(self, depends_on: Sequence[str], what: str) -> None:
        for dep in depends_on:
            if dep not in self.nodes:
                raise UnknownNodeError("%s depends on unknown node %r" % (what, dep))

    # ---- building ----------------------------------------------------

    def add_node(self, node: WorkNode, *, actor: str = "") -> WorkNode:
        who = self._actor(actor)
        if node.id in self.nodes:
            raise ContractError("node %r is already in the graph" % node.id)
        self._check_scope(node.scope, "node %r" % node.id)
        self._require_deps(node.depends_on, "node %r" % node.id)
        if self._would_cycle(node.id, node.depends_on):
            raise CycleError("node %r would depend on its own descendant" % node.id)
        self.nodes[node.id] = node
        self._revision(MutationOp.ADD, who, "added node %s" % node.id)
        return node

    def attach_contract(
        self, contract: ExecutionContract, *, actor: str = ""
    ) -> ExecutionContract:
        who = self._actor(actor)
        node = self.node(contract.node_id)
        self._check_scope(contract.scope, "contract %r" % contract.id)
        if self.objective.scope:
            for path in node.scope:
                if not any(_scope_allows(p, path) for p in contract.scope):
                    raise ScopeError(
                        "contract %r does not authorise node %r's path %r"
                        % (contract.id, node.id, path)
                    )
        self.contracts[contract.id] = contract
        self._set(node.id, contract_id=contract.id)
        self._revision(
            MutationOp.ADD, who, "attached contract %s to %s" % (contract.id, node.id)
        )
        return contract

    # ---- evidence and money ------------------------------------------

    def record_attempt(self, attempt: ExecutionAttempt) -> ExecutionAttempt:
        if attempt.contract_id not in self.contracts:
            raise ContractViolation(
                "attempt %r names contract %r, which is not attached"
                % (attempt.id, attempt.contract_id)
            )
        self.attempts.setdefault(attempt.node_id, []).append(attempt)
        return attempt

    def record_verification(self, receipt: VerificationReceipt) -> VerificationReceipt:
        if receipt.node_id not in self.nodes:
            raise UnknownNodeError(
                "verification names unknown node %r" % receipt.node_id
            )
        node = self.nodes[receipt.node_id]
        if (
            receipt.level is VerificationLevel.OBJECTIVE
            and node.owner
            and receipt.verifier == node.owner
        ):
            raise IndependenceRequiredError(
                "objective verification %r for node %r was signed by %r, which owns the work; "
                "objective acceptance must be independent of the work that was done"
                % (receipt.id, receipt.node_id, receipt.verifier)
            )
        self.verifications[receipt.id] = receipt
        return receipt

    def record_economics(self, receipt: EconomicReceipt) -> EconomicReceipt:
        self.economics[receipt.id] = receipt
        return receipt

    def reserve(
        self,
        node_id: str,
        *,
        lane: IntelligenceLane,
        units: int = 1,
        usd: float = 0.0,
        budget_ref: str,
        window_s: int = 0,
        reservation_id: str = "",
        actor: str = "",
    ) -> CapacityReservation:
        """Hold capacity for a node against the budget authority.

        The reservation is refused when it exceeds the contract's own budget:
        the contract is the authority on what this work may cost, and a
        reservation cannot quietly spend more than it was granted.
        """
        who = self._actor(actor)
        node = self.node(node_id)
        contract = self.contract_for(node_id)
        if contract is not None and usd > contract.budget_usd:
            raise ReservationError(
                "reservation of %.4f usd exceeds contract %r's budget of %.4f usd"
                % (usd, contract.id, contract.budget_usd)
            )
        rid = reservation_id or "res-%s-%d" % (node_id, len(self.reservations) + 1)
        if rid in self.reservations:
            raise ReservationError("reservation %r already exists" % rid)
        reservation = CapacityReservation(
            id=rid,
            lane_id=lane.id,
            units=units,
            usd=usd,
            budget_ref=budget_ref,
            state=ReservationState.HELD,
            window_s=window_s,
        )
        self.reservations[rid] = reservation
        self.reservations_by_node[rid] = node_id
        self._set(node.id, reservation_id=rid)
        self._revision(MutationOp.ADD, who, "reserved %s for %s" % (rid, node_id))
        return reservation

    def commit_reservation(
        self, reservation_id: str, *, actor: str = ""
    ) -> CapacityReservation:
        who = self._actor(actor)
        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            raise ReservationError("no reservation %r" % reservation_id)
        if reservation.state is not ReservationState.HELD:
            raise ReservationError(
                "reservation %r is %s, not held"
                % (reservation_id, reservation.state.value)
            )
        spent = replace(reservation, state=ReservationState.COMMITTED)
        self.reservations[reservation_id] = spent
        self._revision(MutationOp.ADD, who, "committed %s" % reservation_id)
        return spent

    def release_reservation(
        self, reservation_id: str, *, actor: str = ""
    ) -> CapacityReservation:
        """Give the capacity back. A reservation is never dropped."""
        who = self._actor(actor)
        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            raise ReservationError("no reservation %r" % reservation_id)
        if reservation.state is ReservationState.RELEASED:
            return reservation
        freed = replace(reservation, state=ReservationState.RELEASED)
        self.reservations[reservation_id] = freed
        self._revision(MutationOp.ADD, who, "released %s" % reservation_id)
        return freed

    # ---- the work ----------------------------------------------------

    def ready_nodes(self) -> List[WorkNode]:
        """Nodes whose parents are all accepted and which are still to do."""
        out = []
        for node in self.nodes.values():
            if node.state not in (NodeState.PENDING, NodeState.READY):
                continue
            if all(self.nodes[d].state is NodeState.ACCEPTED for d in node.depends_on):
                out.append(node)
        return sorted(out, key=lambda n: (-n.priority, n.id))

    def mark_running(
        self, node_id: str, *, attempt_id: str, contract_id: str = "", actor: str = ""
    ) -> WorkNode:
        who = self._actor(actor)
        node = self.node(node_id)
        if node.state not in (NodeState.PENDING, NodeState.READY):
            raise ContractViolation(
                "node %r is %s and cannot start" % (node_id, node.state.value)
            )
        running = self._set(
            node_id,
            state=NodeState.RUNNING,
            attempt_id=attempt_id,
            contract_id=contract_id or node.contract_id,
        )
        self._revision(MutationOp.RUN, who, "started %s as %s" % (node_id, attempt_id))
        return running

    def fail(self, node_id: str, *, reason: str, actor: str = "") -> WorkNode:
        """Record a failed attempt. The attempt stays on the record."""
        who = self._actor(actor)
        node = self.node(node_id)
        if node.state is NodeState.ACCEPTED:
            raise ContractViolation("an accepted node cannot fail")
        failed = self._set(node_id, state=NodeState.FAILED, reason=reason)
        self._revision(MutationOp.FAIL, who, "failed %s: %s" % (node_id, reason))
        return failed

    def complete(
        self,
        node_id: str,
        *,
        verification_ids: Sequence[str] = (),
        actor: str = "",
    ) -> WorkNode:
        """Accept a node: the evidence is there, and its parents are accepted.

        Both of the specification's acceptance rules are enforced here, and
        they are enforced in the same place so neither can be forgotten.
        """
        who = self._actor(actor)
        node = self.node(node_id)
        if node.state is NodeState.ACCEPTED:
            raise ContractViolation("node %r is already accepted" % node_id)

        for dep in node.depends_on:
            dep_state = self.nodes[dep].state
            if dep_state is not NodeState.ACCEPTED:
                raise AcceptanceRequiredError(
                    "node %r depends on %r, which is %s, not accepted"
                    % (node_id, dep, dep_state.value)
                )

        required = (VerificationLevel.OPERATION,)
        contract = self.contract_for(node_id)
        if contract is not None:
            required = contract.verification_levels

        passed = set()
        for vid in verification_ids:
            receipt = self.verifications.get(vid)
            if receipt is None:
                raise VerificationRequiredError(
                    "node %r names verification %r, which does not exist"
                    % (node_id, vid)
                )
            if receipt.node_id != node_id:
                raise VerificationRequiredError(
                    "verification %r belongs to node %r, not %r"
                    % (vid, receipt.node_id, node_id)
                )
            if receipt.verdict is Verdict.PASS:
                passed.add(receipt.level)
        missing = [level.value for level in required if level not in passed]
        if missing:
            raise VerificationRequiredError(
                "node %r cannot be accepted without a passing %s verification"
                % (node_id, ", ".join(missing))
            )

        accepted = self._set(
            node_id, state=NodeState.ACCEPTED, verification_ids=tuple(verification_ids)
        )
        self._revision(MutationOp.COMPLETE, who, "accepted %s" % node_id)
        return accepted

    def integrate(
        self,
        node_id: str,
        into_id: str,
        *,
        verification_ids: Sequence[str] = (),
        actor: str = "",
    ) -> WorkNode:
        """Integrate a verified node's result into the node that consumes it."""
        who = self._actor(actor)
        node = self.node(node_id)
        target = self.node(into_id)
        if node.id not in target.depends_on:
            raise ContractViolation(
                "node %r does not depend on %r, so nothing to integrate into"
                % (into_id, node_id)
            )
        evidence = [
            self.verifications[v] for v in verification_ids if v in self.verifications
        ]
        if not evidence:
            raise VerificationRequiredError(
                "integrating %r into %r needs the integrating evidence"
                % (node_id, into_id)
            )
        if not any(e.verdict is Verdict.PASS for e in evidence):
            raise VerificationRequiredError(
                "integrating %r into %r has no passing evidence" % (node_id, into_id)
            )
        self._set(
            node_id,
            state=NodeState.ACCEPTED,
            verification_ids=tuple(verification_ids),
        )
        merged = tuple(sorted(set(target.verification_ids) | set(verification_ids)))
        self._set(into_id, verification_ids=merged)
        self._revision(
            MutationOp.INTEGRATE, who, "integrated %s into %s" % (node_id, into_id)
        )
        return self.node(node_id)

    def block(self, node_id: str, reason: str, *, actor: str = "") -> WorkNode:
        who = self._actor(actor)
        node = self.node(node_id)
        if node.state is NodeState.ACCEPTED:
            raise ContractViolation("an accepted node cannot be blocked")
        blocked = self._set(node_id, state=NodeState.BLOCKED, reason=reason)
        self._revision(MutationOp.BLOCK, who, "blocked %s: %s" % (node_id, reason))
        return blocked

    def unblock(self, node_id: str, *, actor: str = "") -> WorkNode:
        who = self._actor(actor)
        node = self.node(node_id)
        if node.state is not NodeState.BLOCKED:
            raise ContractViolation(
                "node %r is %s, not blocked" % (node_id, node.state.value)
            )
        unblocked = self._set(node_id, state=NodeState.PENDING, reason="")
        self._revision(MutationOp.UNBLOCK, who, "unblocked %s" % node_id)
        return unblocked

    def retry(self, node_id: str, *, attempt_id: str, actor: str = "") -> WorkNode:
        """Try again. The earlier attempts stay on the record."""
        who = self._actor(actor)
        node = self.node(node_id)
        if node.state is not NodeState.FAILED:
            raise ContractViolation(
                "only a failed node can be retried, %r is %s"
                % (node_id, node.state.value)
            )
        contract = self.contract_for(node_id)
        if contract is not None:
            done = len(self.attempts.get(node_id, []))
            if done >= contract.max_attempts:
                raise ContractViolation(
                    "contract %r allows %d attempts and %d are used"
                    % (contract.id, contract.max_attempts, done)
                )
        retried = self._set(
            node_id, state=NodeState.PENDING, attempt_id=attempt_id, reason=""
        )
        self._revision(
            MutationOp.RETRY, who, "retrying %s as %s" % (node_id, attempt_id)
        )
        return retried

    def replace(
        self,
        node_id: str,
        *,
        contract: Optional[ExecutionContract] = None,
        lane: Optional[IntelligenceLane] = None,
        actor: str = "",
    ) -> WorkNode:
        """Swap how a node is done, invalidating the evidence it had.

        The receipts are NOT deleted -- they stay in the graph's record, and
        the node's own evidence list is cleared, so an audit can see that the
        evidence belonged to a plan that no longer holds.
        """
        who = self._actor(actor)
        node = self.node(node_id)
        if node.state is NodeState.ACCEPTED:
            raise ContractViolation("an accepted node cannot be replaced")
        if contract is not None:
            self._check_scope(contract.scope, "contract %r" % contract.id)
            self.contracts[contract.id] = contract
            new_contract = contract.id
        else:
            new_contract = node.contract_id
        if lane is not None:
            existing = self.contract_for(node_id)
            if existing is None:
                raise ContractViolation(
                    "node %r has no contract to change the lane of" % node_id
                )
            swapped = replace(existing, lane=lane)
            self.contracts[swapped.id] = swapped
        replaced = self._set(
            node_id,
            state=NodeState.PENDING,
            contract_id=new_contract,
            verification_ids=(),
            attempt_id="",
            reason="replaced",
        )
        self._revision(MutationOp.REPLACE, who, "replaced %s" % node_id)
        return replaced

    def cancel(self, node_id: str, *, reason: str, actor: str = "") -> WorkNode:
        """Cancel a node without losing what it held or what depends on it.

        The reservation is released and the dependents are BLOCKED with the
        reason -- never silently dropped, because a dropped dependent is work
        that disappears from the estate's sight.
        """
        who = self._actor(actor)
        node = self.node(node_id)
        if node.state is NodeState.ACCEPTED:
            raise ContractViolation("an accepted node cannot be cancelled")
        if node.reservation_id:
            self.release_reservation(node.reservation_id, actor=who)
        cancelled = self._set(node_id, state=NodeState.CANCELLED, reason=reason)
        for other in self.nodes.values():
            if node_id in other.depends_on and other.state not in (
                NodeState.ACCEPTED,
                NodeState.CANCELLED,
            ):
                self._set(
                    other.id,
                    state=NodeState.BLOCKED,
                    reason="dependency %s cancelled" % node_id,
                )
        self._revision(MutationOp.CANCEL, who, "cancelled %s: %s" % (node_id, reason))
        return cancelled

    def reprioritise(self, node_id: str, priority: int, *, actor: str = "") -> WorkNode:
        who = self._actor(actor)
        moved = self._set(node_id, priority=int(priority))
        self._revision(
            MutationOp.REPRIORITISE, who, "reprioritised %s to %d" % (node_id, priority)
        )
        return moved

    def replan(
        self, node_id: str, depends_on: Sequence[str], *, actor: str = ""
    ) -> WorkNode:
        """Change what a node depends on. The plan changed, so the evidence
        for the old plan no longer stands for the node."""
        who = self._actor(actor)
        node = self.node(node_id)
        if node.state is NodeState.ACCEPTED:
            raise ContractViolation("an accepted node cannot be replanned")
        deps = tuple(depends_on)
        self._require_deps(deps, "node %r" % node_id)
        if self._would_cycle(node_id, deps):
            raise CycleError("replanning %r would close a dependency loop" % node_id)
        replanned = self._set(
            node_id,
            depends_on=deps,
            state=NodeState.PENDING,
            verification_ids=(),
            reason="replanned",
        )
        self._revision(MutationOp.REPLAN, who, "replanned %s" % node_id)
        return replanned

    def split(
        self, node_id: str, parts: Sequence[WorkNode], *, actor: str = ""
    ) -> List[WorkNode]:
        """Replace a node with the parts that together satisfy it."""
        who = self._actor(actor)
        node = self.node(node_id)
        if node.state is NodeState.ACCEPTED:
            raise ContractViolation("an accepted node cannot be split")
        if not parts:
            raise ContractError("splitting a node into nothing is not a split")
        created = []
        for part in parts:
            if part.id in self.nodes:
                raise ContractError("node %r already exists" % part.id)
            self._check_scope(part.scope, "part %r" % part.id)
            deps = tuple(part.depends_on) or node.depends_on
            self._require_deps(deps, "part %r" % part.id)
            if self._would_cycle(part.id, deps):
                raise CycleError("part %r would depend on its own descendant" % part.id)
            created.append(replace(part, depends_on=deps))
            self.nodes[part.id] = created[-1]
        # The parent is replaced, not deleted: the record of what it was stays.
        self._set(
            node_id,
            state=NodeState.REPLACED,
            reason="split into %d parts" % len(created),
        )
        self._revision(
            MutationOp.SPLIT,
            who,
            "split %s into %s" % (node_id, [p.id for p in created]),
        )
        return created

    def spawn(self, node_id: str, child: WorkNode, *, actor: str = "") -> WorkNode:
        """Add work that depends on a node."""
        who = self._actor(actor)
        parent = self.node(node_id)
        if child.id in self.nodes:
            raise ContractError("node %r already exists" % child.id)
        self._check_scope(child.scope, "spawned node %r" % child.id)
        deps = tuple(child.depends_on) or (parent.id,)
        self._require_deps(deps, "spawned node %r" % child.id)
        if self._would_cycle(child.id, deps):
            raise CycleError(
                "spawned node %r would depend on its own descendant" % child.id
            )
        spawned = replace(child, depends_on=deps)
        self.nodes[child.id] = spawned
        self._revision(
            MutationOp.SPAWN, who, "spawned %s after %s" % (child.id, parent.id)
        )
        return spawned

    def merge(
        self, node_ids: Sequence[str], merged: WorkNode, *, actor: str = ""
    ) -> WorkNode:
        """Combine several nodes into one."""
        who = self._actor(actor)
        ids = list(node_ids)
        if len(ids) < 2:
            raise ContractError("a merge needs at least two nodes")
        for nid in ids:
            node = self.node(nid)
            if node.state is NodeState.ACCEPTED:
                raise ContractViolation("accepted node %r cannot be merged away" % nid)
        if merged.id in self.nodes:
            raise ContractError("node %r already exists" % merged.id)
        self._check_scope(merged.scope, "merged node %r" % merged.id)
        deps: List[str] = []
        for nid in ids:
            for dep in self.node(nid).depends_on:
                if dep not in deps:
                    deps.append(dep)
        self._require_deps(deps, "merged node %r" % merged.id)
        if self._would_cycle(merged.id, deps):
            raise CycleError(
                "merged node %r would depend on its own descendant" % merged.id
            )
        self.nodes[merged.id] = replace(merged, depends_on=tuple(deps))
        for nid in ids:
            self._set(
                nid, state=NodeState.REPLACED, reason="merged into %s" % merged.id
            )
        self._revision(MutationOp.MERGE, who, "merged %s into %s" % (ids, merged.id))
        return self.nodes[merged.id]

    def join(
        self, node_ids: Sequence[str], *, join_id: str = "", actor: str = ""
    ) -> WorkNode:
        """Create a barrier that stands for all of the given nodes."""
        who = self._actor(actor)
        ids = list(node_ids)
        if not ids:
            raise ContractError("a join needs at least one node")
        for nid in ids:
            self.node(nid)
        jid = join_id or "join-%s" % ("-".join(sorted(ids))[:48])
        if jid in self.nodes:
            raise ContractError("node %r already exists" % jid)
        barrier = WorkNode(
            id=jid,
            kind=NodeKind.BARRIER,
            title="join %s" % ", ".join(sorted(ids)),
            depends_on=tuple(ids),
        )
        self.nodes[jid] = barrier
        self._revision(MutationOp.JOIN, who, "joined %s into %s" % (ids, jid))
        return barrier

    def handover(self, new_owner: str, *, actor: str = "") -> GraphRevision:
        """Give the graph's mutations to another agent. The handover is a
        revision, so the chain of who could change what is complete."""
        who = self._actor(actor)
        self.owner = new_owner
        return self._revision(MutationOp.ADD, who, "handed the graph to %s" % new_owner)
