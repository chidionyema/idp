// Package controller holds the RuntimeInstall reconcile loop and its state machine.
//
// The state machine is split into pure functions (Decide, CanAdvance) and side-effecting code
// (the Reconciler). Pure functions are unit-tested without a fake client; side effects are
// covered by the reconciler's own tests using controller-runtime's fake client.
//
// The state machine mirrors RECONCILE-SPEC.md 1:1. Every transition is named, every terminal
// state is listed, and every non-trivial transition carries a Reason string in the status update.
package controller

// Phase is the state machine state. The string values are the same ones the CRD status enum
// requires (CRD enums in PR #2338's runtimeinstall.yaml), so adding a phase here without adding
// it to the CRD is a deliberate breach of contract that the gate's CRD-walker catches.
type Phase string

const (
	PhasePending     Phase = "Pending"     // initial: nothing done yet
	PhaseCanary      Phase = "Canary"      // canary node(s) being installed + verified
	PhasePaused      Phase = "Paused"      // waiting pauseDuration between waves
	PhaseRollingOut  Phase = "RollingOut"  // rest of the selector is being installed
	PhaseVerified    Phase = "Verified"    // all target nodes installed + verified
	PhaseFailed      Phase = "Failed"      // at least one node failed; failurePolicy applied
	PhaseRollingBack Phase = "RollingBack" // uninstall in progress (failurePolicy=FailClosed)
	PhaseRolledBack  Phase = "RolledBack"  // uninstall complete; status carries the reason
)

// Strategy is the rollout strategy. String values mirror the CRD enum.
type Strategy string

const (
	StrategyProgressiveCanary Strategy = "ProgressiveCanary"
	StrategyAllAtOnce         Strategy = "AllAtOnce"
	StrategyManual            Strategy = "Manual"
)

// FailurePolicy is what the controller does when a single node's install fails.
type FailurePolicy string

const (
	FailurePolicyFailClosed FailurePolicy = "FailClosed"
	FailurePolicyIgnore     FailurePolicy = "Ignore"
)

// NodeOutcome is one target node's reconcile result. Carried in Status.CanaryResults and
// Status.RolloutHistory. String values are stable; do not change without bumping v1alpha2.
type NodeOutcome string

const (
	OutcomeVerified NodeOutcome = "Verified"
	OutcomeFailed   NodeOutcome = "Failed"
	OutcomePending  NodeOutcome = "Pending" // mid-flight, not yet terminal
)

// Snapshot is what Decide and CanAdvance need to know. It is constructed by the Reconciler on
// each reconcile and passed to the pure functions; the pure functions do not touch the API.
type Snapshot struct {
	Phase            Phase
	Strategy         Strategy
	FailurePolicy    FailurePolicy
	TotalNodes       int   // total target nodes (selector-matched, after manual dedup)
	CanaryReplicas   int   // canary node count (>=1, <=TotalNodes)
	ObservedNodes    int   // count of nodes with outcome=Verified so far
	FailedNodes      int   // count of nodes with outcome=Failed so far
	PendingNodes     int   // count of nodes mid-flight
	PauseRemainingNs int64 // nanoseconds left in pause (0 if not paused)
	Suspended        bool  // honour the estate.estate.io/suspend annotation
}

// Action is what the Reconciler should do next. It is a verb + a target node (or "" if N/A).
type Action struct {
	Verb   ActionVerb
	Node   string // the node name to act on; "" for N/A verbs
	Reason string // short string for the status update; e.g. "install canary node-1"
}

// ActionVerb is one of the side-effecting verbs the Reconciler can perform.
type ActionVerb string

const (
	ActionWait     ActionVerb = "Wait"     // no action; requeue after a short timer
	ActionSkip     ActionVerb = "Skip"     // suspended or paused; nothing to do this tick
	ActionInstall  ActionVerb = "Install"  // appears in Spec.Verification.ProbePod on node
	ActionVerify   ActionVerb = "Verify"   // read probe pod logs, evaluate successCondition
	ActionCordon   ActionVerb = "Cordon"   // mark node unschedulable
	ActionDrain    ActionVerb = "Drain"    // evict pods honouring PDB
	ActionUncordon ActionVerb = "Uncordon" // mark node schedulable again
	ActionRollback ActionVerb = "Rollback" // run uninstall commands on node
	ActionFail     ActionVerb = "Fail"     // terminal; mark RuntimeInstall as Failed
	ActionComplete ActionVerb = "Complete" // terminal; mark as Verified
)

// Decide is the pure state-machine step. Given a snapshot, return the next action. The Reconciler
// interprets the action and performs the side effect, then loops.
//
// Rules (from RECONCILE-SPEC.md §3, "State machine"):
//
//   - Suspended CRs never advance. Suspended is set by the estate.estate.io/suspend annotation;
//     flipping it to "false" is the empirical-proof milestone D's audit gate.
//   - Pending -> Install (canary) when canary node picked
//   - Canary -> Verify when install finished on the canary node
//   - Verify -> Uncordon when success, or -> Rollback when fail with FailClosed
//   - Verify -> Uncordon when fail with Ignore (counted in failedNodes but rollout continues)
//   - RollingOut -> Install (next node)  -- sequential, not parallel
//   - Paused -> Wait until pauseRemainingNs reaches 0
//   - Verified -> Complete (terminal)
//   - RolledBack -> Complete (terminal)
//   - Failed -> Fail (terminal, only after rollback succeeds or rollback wasn't needed)
func Decide(s Snapshot) Action {
	if s.Suspended {
		return Action{Verb: ActionSkip, Reason: "suspended (estate.estate.io/suspend=true)"}
	}

	// A CR the API server has just admitted carries no status at all: the CRD's status is
	// `x-kubernetes-preserve-unknown-fields: true` with no phase property, so nothing defaults
	// it and Phase arrives as "". Before this line "" matched no case, fell through to the
	// "unknown phase" Wait at the bottom, and the reconciler requeued it every 15s forever --
	// and since ActionCordon is returned only from case PhasePending, handleCordon's own
	// `if cr.Status.Phase == ""` branch (reconcile_actions.go) was unreachable too. No CR
	// could ever begin a rollout. "" is the initial state; Pending is its name.
	if s.Phase == "" {
		s.Phase = PhasePending
	}

	switch s.Phase {
	case PhasePending:
		if s.TotalNodes == 0 {
			// Nothing to do -- selector matched zero nodes. The gate refuses this at admission,
			// but if a CR was admitted and then nodes were removed, the controller refuses to
			// roll out.
			return Action{Verb: ActionFail, Reason: "selector matches zero nodes"}
		}
		return Action{
			Verb:   ActionCordon,
			Reason: "begin rollout: cordon canary node(s)",
		}

	case PhaseCanary:
		if s.PendingNodes > 0 {
			return Action{Verb: ActionVerify, Reason: "verify the just-installed canary node"}
		}
		return Action{Verb: ActionInstall, Reason: "install runtime on canary node"}

	case PhasePaused:
		if s.PauseRemainingNs > 0 {
			return Action{Verb: ActionWait, Reason: "paused between waves"}
		}
		return Action{
			Verb:   ActionInstall,
			Reason: "pause elapsed; install runtime on next node",
		}

	case PhaseRollingOut:
		if s.PendingNodes > 0 {
			return Action{Verb: ActionVerify, Reason: "verify the just-installed rollout node"}
		}
		if s.ObservedNodes >= s.TotalNodes {
			return Action{Verb: ActionComplete, Reason: "all target nodes verified"}
		}
		return Action{Verb: ActionInstall, Reason: "install runtime on next rollout node"}

	case PhaseRollingBack:
		return Action{Verb: ActionRollback, Reason: "uninstall after verification failure"}

	case PhaseVerified, PhaseRolledBack:
		return Action{Verb: ActionComplete, Reason: "terminal phase reached"}

	case PhaseFailed:
		// Failed is entered when Rollback completed successfully OR when the policy is Ignore
		// and a failure was already recorded. Either way it's terminal.
		return Action{Verb: ActionFail, Reason: "terminal: rollout failed"}
	}

	// Reached only by a phase string no version of this controller writes -- a hand-edited
	// status, or a CR left behind by a newer controller that was rolled back. Waiting is the
	// safe answer: the controller neither advances nor terminalises a state it does not
	// understand. It is NOT the path a fresh CR takes; that is normalised to Pending above.
	return Action{Verb: ActionWait, Reason: "unknown phase"}
}

// CanAdvance answers: is the current snapshot allowed to leave its current phase? Returning
// false means the phase is terminal.
//
// Not called by the Reconciler. The doc comment used to say it was, and it never has been --
// the Reconciler writes status.phase from the individual verb handlers without asking. Left
// exported and tested because the C3 handlers should be routed through it; saying so honestly
// is better than a comment that describes a wiring that does not exist.
//
// Rules:
//   - Verified, RolledBack, Failed are terminal. Never advance.
//   - All other phases can advance IF Decide returns a verb other than Wait/Skip.
func CanAdvance(s Snapshot) bool {
	switch s.Phase {
	case PhaseVerified, PhaseRolledBack, PhaseFailed:
		return false
	}
	return true
}

// TerminalPhases returns the set of phases from which no further action is taken. Used by tests
// and by the contract test in crd_contract_test.go to validate the status enum.
func TerminalPhases() []Phase {
	return []Phase{PhaseVerified, PhaseRolledBack, PhaseFailed}
}

// ShouldFailClosed returns true when the snapshot's failedNodes count warrants a Rollback/Failed
// transition. FailClosed means any failure halts the rollout; Ignore means the failure is
// recorded and the rollout continues past the failed node.
//
// Not called by the Reconciler either: reconcile_install.go reads cr.Spec.FailurePolicy
// directly (line 237). The two are the same rule written twice, which is one place for them to
// drift apart.
func ShouldFailClosed(s Snapshot) bool {
	return s.FailurePolicy == FailurePolicyFailClosed && s.FailedNodes > 0
}
