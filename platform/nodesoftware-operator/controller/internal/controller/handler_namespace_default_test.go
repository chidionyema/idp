package controller

import (
	"testing"
	"time"
)

// Found reviewing #2401, 2026-09-07. The Reconciler's HandlerNamespace default
// was "nodesoftware-operator-system" -- a kubebuilder scaffold name that
// does not match the namespace in
// platform/nodesoftware-operator/{rbac.yaml,namespace.yaml}, the
// --handler-namespace arg in deployment.yaml, or the namespace hardcoded in
// the existing incident_* tests. Without an override the controller would
// schedule handler pods in a namespace it does not own; with an override
// (PR #2401) the flag carries the contract and the default carries nothing.
//
// This test pins the default by calling the production code path
// (applyDefaults, which SetupWithManager invokes) so a future revert cannot
// silently re-introduce the kubebuilder scaffold name.
//
// The matching fix in cmd/main.go (the --handler-namespace flag default of
// "nodesoftware-operator-system") is a follow-up; the deployment override
// in #2401 masks it, but the controller-source path still has the wrong
// default as a fallback that this test pins.

func TestReconciler_applyDefaults_FillsHandlerNamespaceToOperatorNamespace(t *testing.T) {
	r := &Reconciler{HandlerNamespace: ""}

	r.applyDefaults()

	if r.HandlerNamespace != "nodesoftware-operator" {
		t.Errorf("default HandlerNamespace drifted; got %q, want %q -- the kubebuilder scaffold name 'nodesoftware-operator-system' must not come back",
			r.HandlerNamespace, "nodesoftware-operator")
	}
}

// A second test locks in that applyDefaults ALSO fills ReconcilePeriod to 15s
// while it is there. ReconcilePeriod had the same one-line provenance as the
// HandlerNamespace fix and is just as easy to revert silently.

func TestReconciler_applyDefaults_FillsReconcilePeriodTo15s(t *testing.T) {
	r := &Reconciler{ReconcilePeriod: 0}

	r.applyDefaults()

	if r.ReconcilePeriod != 15*time.Second {
		t.Errorf("default ReconcilePeriod drifted; got %v, want 15s -- the default keeps the loop under min(spec.pauseDuration)=30s",
			r.ReconcilePeriod)
	}
}

// A third test exercises a Reconciler constructed with zero values for both
// fields, the shape main.go hands in when both flags are missing. It exists
// so a future refactor cannot drop a field from applyDefaults without a test
// failing.

func TestReconciler_applyDefaults_ZeroValueFillsBoth(t *testing.T) {
	r := &Reconciler{}

	r.applyDefaults()

	if r.HandlerNamespace != "nodesoftware-operator" {
		t.Errorf("HandlerNamespace default-fill dropped; got %q", r.HandlerNamespace)
	}
	if r.ReconcilePeriod != 15*time.Second {
		t.Errorf("ReconcilePeriod default-fill dropped; got %v", r.ReconcilePeriod)
	}
}

// A fourth test covers the case where the caller has already supplied an
// explicit value -- applyDefaults must not clobber it. (This is the "operator
// runs with --handler-namespace=foo" case.)

func TestReconciler_applyDefaults_PreservesExplicitValues(t *testing.T) {
	cases := []struct {
		name              string
		handlerNS         string
		reconcilePeriod   time.Duration
		wantHandlerNS     string
		wantReconcilePerd time.Duration
	}{
		{
			name:              "explicit handler namespace preserved",
			handlerNS:         "custom",
			reconcilePeriod:   0,
			wantHandlerNS:     "custom",
			wantReconcilePerd: 15 * time.Second,
		},
		{
			name:              "explicit reconcile period preserved",
			handlerNS:         "",
			reconcilePeriod:   30 * time.Second,
			wantHandlerNS:     "nodesoftware-operator",
			wantReconcilePerd: 30 * time.Second,
		},
		{
			name:              "both explicit",
			handlerNS:         "alt-ns",
			reconcilePeriod:   60 * time.Second,
			wantHandlerNS:     "alt-ns",
			wantReconcilePerd: 60 * time.Second,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			r := &Reconciler{
				HandlerNamespace: tc.handlerNS,
				ReconcilePeriod:  tc.reconcilePeriod,
			}
			r.applyDefaults()
			if r.HandlerNamespace != tc.wantHandlerNS {
				t.Errorf("HandlerNamespace = %q, want %q", r.HandlerNamespace, tc.wantHandlerNS)
			}
			if r.ReconcilePeriod != tc.wantReconcilePerd {
				t.Errorf("ReconcilePeriod = %v, want %v", r.ReconcilePeriod, tc.wantReconcilePerd)
			}
		})
	}
}
