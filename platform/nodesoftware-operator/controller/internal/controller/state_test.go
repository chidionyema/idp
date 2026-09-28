package controller

import (
	"testing"

	nodesoftwarev1alpha1 "github.com/chidionyema/idp/platform/nodesoftware-operator/controller/api/v1alpha1"
)

// TestDecide_Pending covers the entry transitions. Pending -> Cordon (canary first).
func TestDecide_Pending(t *testing.T) {
	cases := []struct {
		name   string
		snap   Snapshot
		want   ActionVerb
		reason string
	}{
		{
			name: "Pending with 3 nodes -> Cordon",
			snap: Snapshot{
				Phase: PhasePending, Strategy: StrategyProgressiveCanary,
				TotalNodes: 3, CanaryReplicas: 1,
				FailurePolicy: FailurePolicyFailClosed,
			},
			want:   ActionCordon,
			reason: "begin rollout: cordon canary node(s)",
		},
		{
			name: "Pending with 0 nodes -> Fail (selector matched zero nodes)",
			snap: Snapshot{
				Phase: PhasePending, Strategy: StrategyProgressiveCanary,
				TotalNodes: 0, CanaryReplicas: 1,
			},
			want:   ActionFail,
			reason: "selector matches zero nodes",
		},
		{
			name: "Pending but Suspended -> Skip",
			snap: Snapshot{
				Phase: PhasePending, Strategy: StrategyProgressiveCanary,
				TotalNodes: 3, CanaryReplicas: 1,
				Suspended: true,
			},
			want: ActionSkip,
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := Decide(c.snap)
			if got.Verb != c.want {
				t.Errorf("verb: got %q, want %q (reason=%q)", got.Verb, c.want, got.Reason)
			}
			if c.reason != "" && got.Reason != c.reason {
				t.Errorf("reason: got %q, want %q", got.Reason, c.reason)
			}
		})
	}
}

// TestDecide_Canary covers the canary loop. Canary -> Install until something is pending, then
// Canary -> Verify.
func TestDecide_Canary(t *testing.T) {
	cases := []struct {
		name string
		snap Snapshot
		want ActionVerb
	}{
		{
			name: "Canary with nothing pending -> Install",
			snap: Snapshot{
				Phase: PhaseCanary, Strategy: StrategyProgressiveCanary,
				TotalNodes: 3, CanaryReplicas: 1,
				PendingNodes: 0,
			},
			want: ActionInstall,
		},
		{
			name: "Canary with one node pending -> Verify",
			snap: Snapshot{
				Phase: PhaseCanary, Strategy: StrategyProgressiveCanary,
				TotalNodes: 3, CanaryReplicas: 1,
				PendingNodes: 1,
			},
			want: ActionVerify,
		},
		{
			name: "Canary suspended -> Skip",
			snap: Snapshot{
				Phase: PhaseCanary, Strategy: StrategyProgressiveCanary,
				TotalNodes: 3, CanaryReplicas: 1,
				Suspended: true,
			},
			want: ActionSkip,
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := Decide(c.snap)
			if got.Verb != c.want {
				t.Errorf("verb: got %q, want %q (reason=%q)", got.Verb, c.want, got.Reason)
			}
		})
	}
}

// TestDecide_RollingOut covers the post-canary phase. Same shape as Canary but the canary is
// already verified; the controller moves through the rest of the selector one node at a time.
func TestDecide_RollingOut(t *testing.T) {
	cases := []struct {
		name string
		snap Snapshot
		want ActionVerb
	}{
		{
			name: "RollingOut, next node pending -> Verify",
			snap: Snapshot{
				Phase: PhaseRollingOut, Strategy: StrategyProgressiveCanary,
				TotalNodes: 5, CanaryReplicas: 1, ObservedNodes: 1,
				PendingNodes: 1,
			},
			want: ActionVerify,
		},
		{
			name: "RollingOut, all observed -> Complete",
			snap: Snapshot{
				Phase: PhaseRollingOut, Strategy: StrategyProgressiveCanary,
				TotalNodes: 5, CanaryReplicas: 1, ObservedNodes: 5,
				PendingNodes: 0,
			},
			want: ActionComplete,
		},
		{
			name: "RollingOut, idle -> Install next",
			snap: Snapshot{
				Phase: PhaseRollingOut, Strategy: StrategyProgressiveCanary,
				TotalNodes: 5, CanaryReplicas: 1, ObservedNodes: 2,
				PendingNodes: 0,
			},
			want: ActionInstall,
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := Decide(c.snap)
			if got.Verb != c.want {
				t.Errorf("verb: got %q, want %q", got.Verb, c.want)
			}
		})
	}
}

// TestDecide_Paused covers the pause between waves.
func TestDecide_Paused(t *testing.T) {
	cases := []struct {
		name string
		snap Snapshot
		want ActionVerb
	}{
		{
			name: "Paused with time remaining -> Wait",
			snap: Snapshot{
				Phase: PhasePaused, Strategy: StrategyProgressiveCanary,
				PauseRemainingNs: 5_000_000_000, // 5s
			},
			want: ActionWait,
		},
		{
			name: "Paused with no time remaining -> Install next",
			snap: Snapshot{
				Phase: PhasePaused, Strategy: StrategyProgressiveCanary,
				PauseRemainingNs: 0, TotalNodes: 3, CanaryReplicas: 1, ObservedNodes: 1,
			},
			want: ActionInstall,
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := Decide(c.snap)
			if got.Verb != c.want {
				t.Errorf("verb: got %q, want %q", got.Verb, c.want)
			}
		})
	}
}

// TestDecide_Terminal covers terminal phases. Verified, RolledBack, Failed never advance.
func TestDecide_Terminal(t *testing.T) {
	for _, p := range TerminalPhases() {
		t.Run(string(p), func(t *testing.T) {
			got := Decide(Snapshot{Phase: p, Strategy: StrategyProgressiveCanary})
			if got.Verb != ActionComplete && got.Verb != ActionFail {
				t.Errorf("terminal phase %q returned %q, want Complete or Fail", p, got.Verb)
			}
		})
	}
}

// TestCanAdvance locks in the rule that Verified/RolledBack/Failed never advance.
func TestCanAdvance(t *testing.T) {
	terminal := TerminalPhases()
	for _, p := range terminal {
		if CanAdvance(Snapshot{Phase: p}) {
			t.Errorf("phase %q advanced but should be terminal", p)
		}
	}
	// Pending/Canary/Paused/RollingOut/RollingBack all advance.
	for _, p := range []Phase{PhasePending, PhaseCanary, PhasePaused, PhaseRollingOut, PhaseRollingBack} {
		if !CanAdvance(Snapshot{Phase: p}) {
			t.Errorf("phase %q did not advance", p)
		}
	}
}

// TestShouldFailClosed enforces: FailClosed policy + at least one failed node => trigger rollback.
// Ignore policy + failed nodes => no rollback (carry on).
func TestShouldFailClosed(t *testing.T) {
	cases := []struct {
		name string
		snap Snapshot
		want bool
	}{
		{
			name: "FailClosed with one failed node -> true",
			snap: Snapshot{FailurePolicy: FailurePolicyFailClosed, FailedNodes: 1},
			want: true,
		},
		{
			name: "FailClosed with zero failed -> false",
			snap: Snapshot{FailurePolicy: FailurePolicyFailClosed, FailedNodes: 0},
			want: false,
		},
		{
			name: "Ignore with one failed -> false",
			snap: Snapshot{FailurePolicy: FailurePolicyIgnore, FailedNodes: 1},
			want: false,
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := ShouldFailClosed(c.snap); got != c.want {
				t.Errorf("got %v, want %v", got, c.want)
			}
		})
	}
}

// TestClosedRuntimesLocked covers the closed runtime set. The Go types, the python
// CLOSED_RUNTIMES set in bin/lib/nodesoftware_operator_gate.py, and the CRD YAML enum must all
// agree. This test enforces the Go side; the CRD-walker in the gate enforces the YAML side.
// The runtime list MUST match the one in CRD-SPEC.md and the gate fixture.
func TestClosedRuntimesLocked(t *testing.T) {
	got := make([]string, 0, len(nodesoftwarev1alpha1.ClosedRuntimes))
	for r := range nodesoftwarev1alpha1.ClosedRuntimes {
		got = append(got, r)
	}
	// Order-independent comparison.
	want := map[string]struct{}{"runsc": {}, "kata": {}, "nvidia": {}}
	if len(got) != len(want) {
		t.Fatalf("ClosedRuntimes size: got %d, want %d (%v)", len(got), len(want), got)
	}
	for _, r := range got {
		if _, ok := want[r]; !ok {
			t.Errorf("ClosedRuntimes contains %q which is not in the locked set %v", r, want)
		}
	}
}
