// target_test.go: tests for the target-node picker. Pure functions over data; no fake client.
package controller

import (
	"testing"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	nodesoftwarev1alpha1 "github.com/chidionyema/idp/platform/nodesoftware-operator/controller/api/v1alpha1"
	"github.com/chidionyema/idp/platform/nodesoftware-operator/controller/internal/handler"
)

// ptrInt32 returns a pointer to the given int32 value.
func ptrInt32(v int32) *int32 { return &v }

// TestSortedTargetNodes verifies that annotation-pinned canary nodes come first, then the
// remaining nodes are sorted by name.
func TestSortedTargetNodes(t *testing.T) {
	nodes := []corev1.Node{
		{ObjectMeta: metav1.ObjectMeta{Name: "node-c"}},
		{ObjectMeta: metav1.ObjectMeta{Name: "node-a", Annotations: map[string]string{
			"nodesoftware.estate.io/canary": "true",
		}}},
		{ObjectMeta: metav1.ObjectMeta{Name: "node-b"}},
	}
	got := sortedTargetNodes(nodes)
	if len(got) != 3 {
		t.Fatalf("expected 3 targets, got %d", len(got))
	}
	if got[0].Name != "node-a" || !got[0].IsExplicitCanary {
		t.Errorf("first target: got %+v, want node-a pinned", got[0])
	}
	if got[1].Name != "node-b" {
		t.Errorf("second target: got %q, want node-b", got[1].Name)
	}
	if got[2].Name != "node-c" {
		t.Errorf("third target: got %q, want node-c", got[2].Name)
	}
}

// TestPickNextTarget covers the picking logic: empty history -> first node; partial history ->
// first untested; full Verified history -> "".
func TestPickNextTarget(t *testing.T) {
	targets := []targetNode{
		{Name: "node-a"}, {Name: "node-b"}, {Name: "node-c"},
	}

	t.Run("empty history -> first node", func(t *testing.T) {
		got := pickNextTarget(targets, nil, 1)
		if got != "node-a" {
			t.Errorf("got %q, want node-a", got)
		}
	})

	t.Run("first node Verified -> second node", func(t *testing.T) {
		hist := []nodesoftwarev1alpha1.RolloutHistoryEntry{{Node: "node-a", Outcome: string(OutcomeVerified)}}
		got := pickNextTarget(targets, hist, 1)
		if got != "node-b" {
			t.Errorf("got %q, want node-b", got)
		}
	})

	t.Run("first node Failed -> first node (needs rollback)", func(t *testing.T) {
		hist := []nodesoftwarev1alpha1.RolloutHistoryEntry{{Node: "node-a", Outcome: string(OutcomeFailed)}}
		got := pickNextTarget(targets, hist, 1)
		if got != "node-a" {
			t.Errorf("got %q, want node-a (rollback pending)", got)
		}
	})

	t.Run("first node Pending -> first node (mid-flight)", func(t *testing.T) {
		hist := []nodesoftwarev1alpha1.RolloutHistoryEntry{{Node: "node-a", Outcome: string(OutcomePending)}}
		got := pickNextTarget(targets, hist, 1)
		if got != "node-a" {
			t.Errorf("got %q, want node-a (pending)", got)
		}
	})

	t.Run("all Verified -> empty", func(t *testing.T) {
		hist := []nodesoftwarev1alpha1.RolloutHistoryEntry{
			{Node: "node-a", Outcome: string(OutcomeVerified)},
			{Node: "node-b", Outcome: string(OutcomeVerified)},
			{Node: "node-c", Outcome: string(OutcomeVerified)},
		}
		got := pickNextTarget(targets, hist, 1)
		if got != "" {
			t.Errorf("got %q, want \"\"", got)
		}
	})
}

// TestBuildSnapshot verifies the snapshot counts derived from rolloutHistory.
func TestBuildSnapshot(t *testing.T) {
	cr := &nodesoftwarev1alpha1.RuntimeInstall{
		Spec: nodesoftwarev1alpha1.RuntimeInstallSpec{
			Runtime:        "runsc",
			FailurePolicy:  string(FailurePolicyFailClosed),
			CanaryReplicas: ptrInt32(2),
		},
		Status: nodesoftwarev1alpha1.RuntimeInstallStatus{
			Phase: string(PhaseRollingOut),
			RolloutHistory: []nodesoftwarev1alpha1.RolloutHistoryEntry{
				{Node: "node-a", Outcome: string(OutcomeVerified)},
				{Node: "node-b", Outcome: string(OutcomeFailed)},
				{Node: "node-c", Outcome: string(OutcomePending)},
			},
		},
	}
	snap := buildSnapshot(cr, 5, cr.Status.RolloutHistory, false)
	if snap.Phase != PhaseRollingOut {
		t.Errorf("Phase: got %q, want %q", snap.Phase, PhaseRollingOut)
	}
	if snap.CanaryReplicas != 2 {
		t.Errorf("CanaryReplicas: got %d, want 2", snap.CanaryReplicas)
	}
	if snap.TotalNodes != 5 {
		t.Errorf("TotalNodes: got %d, want 5", snap.TotalNodes)
	}
	if snap.ObservedNodes != 1 {
		t.Errorf("ObservedNodes: got %d, want 1", snap.ObservedNodes)
	}
	if snap.FailedNodes != 1 {
		t.Errorf("FailedNodes: got %d, want 1", snap.FailedNodes)
	}
	if snap.PendingNodes != 1 {
		t.Errorf("PendingNodes: got %d, want 1", snap.PendingNodes)
	}
}

// TestIsSuspended honours the annotation contract: default-suspended unless explicitly "false".
func TestIsSuspended(t *testing.T) {
	cases := []struct {
		name string
		cr   *nodesoftwarev1alpha1.RuntimeInstall
		want bool
	}{
		{
			name: "no annotations -> suspended",
			cr:   &nodesoftwarev1alpha1.RuntimeInstall{},
			want: true,
		},
		{
			name: "annotation true -> suspended",
			cr: &nodesoftwarev1alpha1.RuntimeInstall{
				ObjectMeta: metav1.ObjectMeta{
					Annotations: map[string]string{"estate.estate.io/suspend": "true"},
				},
			},
			want: true,
		},
		{
			name: "annotation false -> not suspended",
			cr: &nodesoftwarev1alpha1.RuntimeInstall{
				ObjectMeta: metav1.ObjectMeta{
					Annotations: map[string]string{"estate.estate.io/suspend": "false"},
				},
			},
			want: false,
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := isSuspended(c.cr); got != c.want {
				t.Errorf("got %v, want %v", got, c.want)
			}
		})
	}
}

// TestBuildHandlerPod verifies the handler pod shape: privileged, hostPath-mounted, labelled.
func TestBuildHandlerPod(t *testing.T) {
	step := &handler.Step{Image: "ghcr.io/test/handler:1.0.0", Command: []string{"/bin/sh", "-c", "echo ok"}}
	var stepPtr *handler.Step = step
	_ = stepPtr
	cr := &nodesoftwarev1alpha1.RuntimeInstall{
		ObjectMeta: metav1.ObjectMeta{Name: "runsc-canary"},
	}
	pod := buildHandlerPod("rti-runsc-canary-node-a-install", "nodesoftware-operator-system", step, "node-a", cr)
	if pod.Spec.NodeName != "node-a" {
		t.Errorf("nodeName: got %q, want node-a", pod.Spec.NodeName)
	}
	if !*pod.Spec.Containers[0].SecurityContext.Privileged {
		t.Errorf("handler pod should be privileged")
	}
	if len(pod.Spec.Volumes) != 1 || pod.Spec.Volumes[0].HostPath == nil || pod.Spec.Volumes[0].HostPath.Path != "/" {
		t.Errorf("handler pod missing hostPath mount")
	}
	if pod.Labels["nodesoftware.estate.io/runtimeinstall"] != "runsc-canary" {
		t.Errorf("label mapping wrong: %v", pod.Labels)
	}
	if pod.Labels["nodesoftware.estate.io/node"] != "node-a" {
		t.Errorf("node label wrong: %v", pod.Labels)
	}
}
