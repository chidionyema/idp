package controller

import (
	"context"
	"testing"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	nodesoftwarev1alpha1 "github.com/chidionyema/idp/platform/nodesoftware-operator/controller/api/v1alpha1"
)

// Found reviewing #2367/#2382, 2026-09-07. Three defects, each of which only shows up when the
// reconciler is driven from a real CR rather than from a Snapshot built by hand in a table test.
// That is why every one of them survived a green unit suite:
//
//  1. A freshly admitted CR carries no status at all -- the CRD's status is
//     x-kubernetes-preserve-unknown-fields with no phase property, so nothing defaults it.
//     Phase arrived as "", matched no case in Decide's switch, and fell through to the
//     "unknown phase" Wait. The reconciler requeued it every 15s forever. handleCordon has an
//     `if cr.Status.Phase == ""` branch that reads as if this were handled, but ActionCordon is
//     returned only from `case PhasePending`, so that branch was unreachable.
//  2. Reconcile listed nodes with client.MatchingLabels(...MatchLabels) off a
//     metav1.LabelSelector. matchExpressions were dropped, and the resulting empty selector is
//     not "no nodes" -- it is every node in the cluster.
//  3. Decide routes PhaseRolledBack to ActionComplete, and ActionComplete wrote PhaseVerified.

func testScheme(t *testing.T) *runtime.Scheme {
	t.Helper()
	s := runtime.NewScheme()
	if err := clientgoscheme.AddToScheme(s); err != nil {
		t.Fatalf("core scheme: %v", err)
	}
	if err := nodesoftwarev1alpha1.AddToScheme(s); err != nil {
		t.Fatalf("runtimeinstall scheme: %v", err)
	}
	return s
}

func node(name string, labels map[string]string) *corev1.Node {
	return &corev1.Node{ObjectMeta: metav1.ObjectMeta{Name: name, Labels: labels}}
}

func runtimeInstall(sel metav1.LabelSelector) *nodesoftwarev1alpha1.RuntimeInstall {
	return &nodesoftwarev1alpha1.RuntimeInstall{
		ObjectMeta: metav1.ObjectMeta{
			Name:        "gvisor",
			Namespace:   "nodesoftware-operator",
			Annotations: map[string]string{"estate.estate.io/suspend": "false"},
		},
		Spec: nodesoftwarev1alpha1.RuntimeInstallSpec{
			Runtime:         "runsc",
			Version:         "20240301.0",
			RolloutStrategy: string(StrategyProgressiveCanary),
			FailurePolicy:   string(FailurePolicyFailClosed),
			Selector: nodesoftwarev1alpha1.RuntimeInstallNodeSelector{
				NodeSelector: sel,
			},
		},
	}
}

// 1. The state machine's entry point has to be reachable from the state a real CR arrives in.
func TestDecide_AFreshCRWithNoStatusEntersPending(t *testing.T) {
	got := Decide(Snapshot{Phase: "", TotalNodes: 3, CanaryReplicas: 1,
		Strategy: StrategyProgressiveCanary, FailurePolicy: FailurePolicyFailClosed})
	if got.Verb != ActionCordon {
		t.Fatalf("a CR with no status must begin the rollout, got %q (%s)", got.Verb, got.Reason)
	}
	// And the fallthrough must still exist for a phase string no controller writes.
	if got := Decide(Snapshot{Phase: "Wat", TotalNodes: 3}); got.Verb != ActionWait {
		t.Fatalf("an unrecognised phase must Wait, got %q", got.Verb)
	}
}

func TestPhaseOrPending(t *testing.T) {
	if phaseOrPending("") != PhasePending {
		t.Fatal(`"" is the initial state and must read as Pending`)
	}
	if phaseOrPending("Canary") != PhaseCanary {
		t.Fatal("a real phase must survive unchanged")
	}
}

// 2. matchExpressions must reach the List, and an empty selector must never mean "every node".
func TestReconcile_SelectorHonoursMatchExpressionsAndRefusesAnEmptyOne(t *testing.T) {
	s := testScheme(t)

	t.Run("matchExpressions selects, and does not silently widen to the fleet", func(t *testing.T) {
		cr := runtimeInstall(metav1.LabelSelector{
			MatchExpressions: []metav1.LabelSelectorRequirement{{
				Key: "estate.io/sandbox", Operator: metav1.LabelSelectorOpIn, Values: []string{"yes"},
			}},
		})
		c := fake.NewClientBuilder().WithScheme(s).
			WithObjects(cr,
				node("sandbox-1", map[string]string{"estate.io/sandbox": "yes"}),
				node("control-1", nil),
				node("control-2", nil)).
			WithStatusSubresource(cr).Build()

		r := &Reconciler{Client: c, Scheme: s, HandlerNamespace: "nodesoftware-operator"}
		if _, err := r.Reconcile(context.Background(), ctrl.Request{
			NamespacedName: types.NamespacedName{Name: "gvisor", Namespace: "nodesoftware-operator"},
		}); err != nil {
			t.Fatalf("reconcile: %v", err)
		}

		var got nodesoftwarev1alpha1.RuntimeInstall
		if err := c.Get(context.Background(), types.NamespacedName{
			Name: "gvisor", Namespace: "nodesoftware-operator"}, &got); err != nil {
			t.Fatalf("get: %v", err)
		}
		if got.Status.Phase == string(PhaseFailed) {
			t.Fatalf("a matchExpressions selector that matches one node must not fail: %q", got.Status.Message)
		}
		// The discriminating assertion: with matchExpressions dropped the selector is empty,
		// the List returns all three nodes, and the first one sorted -- control-1 -- gets
		// cordoned. Cordoning a control node nobody selected is the whole failure.
		var nodes corev1.NodeList
		if err := c.List(context.Background(), &nodes); err != nil {
			t.Fatalf("list nodes: %v", err)
		}
		for _, n := range nodes.Items {
			if n.Name != "sandbox-1" && n.Spec.Unschedulable {
				t.Fatalf("cordoned %q, which the selector does not match", n.Name)
			}
		}
		for _, h := range got.Status.RolloutHistory {
			if h.Node != "sandbox-1" {
				t.Fatalf("rollout touched %q; only sandbox-1 matches the selector", h.Node)
			}
		}
	})

	t.Run("an empty selector is refused, not treated as every node", func(t *testing.T) {
		cr := runtimeInstall(metav1.LabelSelector{})
		c := fake.NewClientBuilder().WithScheme(s).
			WithObjects(cr, node("control-1", nil), node("control-2", nil)).
			WithStatusSubresource(cr).Build()

		r := &Reconciler{Client: c, Scheme: s, HandlerNamespace: "nodesoftware-operator"}
		if _, err := r.Reconcile(context.Background(), ctrl.Request{
			NamespacedName: types.NamespacedName{Name: "gvisor", Namespace: "nodesoftware-operator"},
		}); err != nil {
			t.Fatalf("reconcile: %v", err)
		}
		var got nodesoftwarev1alpha1.RuntimeInstall
		if err := c.Get(context.Background(), types.NamespacedName{
			Name: "gvisor", Namespace: "nodesoftware-operator"}, &got); err != nil {
			t.Fatalf("get: %v", err)
		}
		if got.Status.Phase != string(PhaseFailed) {
			t.Fatalf("an empty nodeSelector must fail the CR, not target every node; phase=%q", got.Status.Phase)
		}
		if len(got.Status.RolloutHistory) != 0 {
			t.Fatalf("an empty selector must touch no node, touched %d", len(got.Status.RolloutHistory))
		}
	})
}

// 3. Complete must not report Verified for a rollout that was rolled back.
func TestCompleteTerminal_NeverStampsVerifiedOverRolledBack(t *testing.T) {
	s := testScheme(t)
	cr := runtimeInstall(metav1.LabelSelector{MatchLabels: map[string]string{"estate.io/sandbox": "yes"}})
	cr.Status.Phase = string(PhaseRolledBack)
	cr.Status.Message = "rolled back after verification failure"
	c := fake.NewClientBuilder().WithScheme(s).WithObjects(cr).WithStatusSubresource(cr).Build()

	r := &Reconciler{Client: c, Scheme: s, HandlerNamespace: "nodesoftware-operator"}
	if _, err := r.completeTerminal(context.Background(), cr); err != nil {
		t.Fatalf("completeTerminal: %v", err)
	}
	if cr.Status.Phase != string(PhaseRolledBack) {
		t.Fatalf("a rolled-back rollout must not report %q", cr.Status.Phase)
	}
	// Decide still routes RolledBack through ActionComplete, which is what made this reachable.
	if got := Decide(Snapshot{Phase: PhaseRolledBack, TotalNodes: 1}); got.Verb != ActionComplete {
		t.Fatalf("guard assumes Decide routes RolledBack to Complete, got %q", got.Verb)
	}
}
