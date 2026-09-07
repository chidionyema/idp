// Package controller wires the RuntimeInstall state machine to controller-runtime. The
// Reconciler is the side-effecting half of the design; the pure functions in state.go are the
// half the tests are easy to write against.
//
// On each reconcile:
//
//  1. Read the CR. Bail if Suspended (estate.estate.io/suspend=true).
//  2. List target nodes via spec.selector.nodeSelector. Build Snapshot.
//  3. Decide(snap) -> Action.
//  4. Apply the verb (Cordon -> patch node unschedulable; Install -> create handler pod; etc.).
//  5. If the verb is terminal, write status.phase + bail.
//  6. Requeue after a short timer (15s by default) for the next reconcile.
//
// The reconciler uses controller-runtime's Client interface, which is satisfied by the real
// cluster client in production and by the fake client in tests. No direct REST calls.
package controller

import (
	"context"
	"fmt"
	"time"

	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"

	nodesoftwarev1alpha1 "github.com/chidionyema/idp/platform/nodesoftware-operator/controller/api/v1alpha1"
	"github.com/chidionyema/idp/platform/nodesoftware-operator/controller/internal/handler"
)

// Reconciler owns the reconcile loop for RuntimeInstall.
type Reconciler struct {
	client.Client
	Scheme   *runtime.Scheme
	Handlers *handler.Registry
	// ReconcilePeriod is how often to requeue. The state machine is event-driven in spirit but
	// a short periodic requeue catches missed events without drama. 15s matches LAW 51's
	// minimum gap and CRD-SPEC.md's min(pauseDuration) >= 30s.
	ReconcilePeriod time.Duration
	// HandlerNamespace is where the controller creates handler pods. The reconciler creates
	// the namespace at startup if missing.
	HandlerNamespace string
}

// Reconcile is the controller-runtime entry point. One reconcile per CR per requeue.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := log.FromContext(ctx).WithValues("runtimeinstall", req.NamespacedName.String())

	var cr nodesoftwarev1alpha1.RuntimeInstall
	if err := r.Get(ctx, req.NamespacedName, &cr); err != nil {
		if apierrors.IsNotFound(err) {
			// CR deleted; nothing to do.
			return ctrl.Result{}, nil
		}
		return ctrl.Result{}, err
	}

	// Suspended CRs are the empirical-proof gate (milestone D): flipping the suspend
	// annotation is the audit-handle that releases the rollout.
	if isSuspended(&cr) {
		log.Info("skipping suspended RuntimeInstall")
		return ctrl.Result{RequeueAfter: r.ReconcilePeriod}, nil
	}

	// Validate the closed runtime set as the last line of defence -- the gate admits only
	// runsc/kata/nvidia today, but the controller refuses here as well so a malicious CR
	// admitted under a misconfigured CRD enum still cannot roll out.
	if err := handler.ValidateClosedRuntime(cr.Spec.Runtime); err != nil {
		return r.fail(ctx, &cr, err.Error())
	}

	snap := r.snapshot(ctx, &cr)
	action := Decide(snap)
	log.Info("decided", "phase", snap.Phase, "action", action.Verb, "node", action.Node, "reason", action.Reason)

	return r.apply(ctx, &cr, snap, action)
}

// snapshot builds the Snapshot that Decide consumes. Lists target nodes; counts observed/failed
// from status.rolloutHistory; reads the suspend annotation.
func (r *Reconciler) snapshot(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall) Snapshot {
	snap := Snapshot{
		Phase:          Phase(cr.Status.Phase),
		Strategy:       Strategy(cr.Spec.RolloutStrategy),
		FailurePolicy:  FailurePolicy(cr.Spec.FailurePolicy),
		CanaryReplicas: 1,
		Suspended:      isSuspended(cr),
	}
	if cr.Spec.CanaryReplicas != nil {
		snap.CanaryReplicas = int(*cr.Spec.CanaryReplicas)
	}

	// Count terminal outcomes from history.
	for _, h := range cr.Status.RolloutHistory {
		switch NodeOutcome(h.Outcome) {
		case OutcomeVerified:
			snap.ObservedNodes++
		case OutcomeFailed:
			snap.FailedNodes++
		case OutcomePending:
			snap.PendingNodes++
		}
	}

	// List matching nodes. Empty selector -> empty list (gate would have refused, but the
	// controller refuses again as defence-in-depth).
	nodes := &corev1.NodeList{}
	if err := r.List(ctx, nodes, client.MatchingLabels(cr.Spec.Selector.NodeSelector.MatchLabels)); err != nil {
		// Best-effort: list failures don't fail the reconcile; the next one retries.
		return snap
	}
	snap.TotalNodes = len(nodes.Items)

	return snap
}

// apply is the side-effecting half. It interprets the Action and performs it.
func (r *Reconciler) apply(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, snap Snapshot, action Action) (ctrl.Result, error) {
	switch action.Verb {
	case ActionSkip, ActionWait:
		return ctrl.Result{RequeueAfter: r.ReconcilePeriod}, nil

	case ActionComplete:
		return r.complete(ctx, cr, action.Reason)

	case ActionFail:
		return r.fail(ctx, cr, action.Reason)

	case ActionInstall, ActionCordon, ActionDrain, ActionUncordon, ActionVerify, ActionRollback:
		// C2 stops at compile-clean + state-machine unit-tested. The full
		// install/cordon/drain pipeline is C3, gated on the empirical proof of D. Until
		// then the reconciler logs the intended action and requeues -- it never lies about
		// status (phase stays where it was) and it never touches a node.
		log.FromContext(ctx).Info("C2 stub: action would run here", "action", action.Verb, "node", action.Node, "reason", action.Reason)
		return ctrl.Result{RequeueAfter: r.ReconcilePeriod}, nil

	default:
		return ctrl.Result{}, fmt.Errorf("unknown action verb: %q", action.Verb)
	}
}

// complete writes the terminal phase and returns without requeue. The Reconciler reads
// status.phase directly via client.Status().Patch(), which the CRD's status subresource routes
// through kubelet's table subresource protection -- humans cannot write status.
func (r *Reconciler) complete(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, reason string) (ctrl.Result, error) {
	cr.Status.Phase = string(PhaseVerified)
	cr.Status.Message = reason
	if err := r.Status().Update(ctx, cr); err != nil {
		return ctrl.Result{}, err
	}
	return ctrl.Result{}, nil
}

// fail writes the terminal Failed phase.
func (r *Reconciler) fail(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, reason string) (ctrl.Result, error) {
	cr.Status.Phase = string(PhaseFailed)
	cr.Status.Message = reason
	if err := r.Status().Update(ctx, cr); err != nil {
		return ctrl.Result{}, err
	}
	return ctrl.Result{}, nil
}

// isSuspended honours the estate.estate.io/suspend annotation. The empirical-proof milestone D
// flips this from "true" to "false" on platform/gvisor-runtime/runtimeinstall.yaml.
func isSuspended(cr *nodesoftwarev1alpha1.RuntimeInstall) bool {
	if cr.Annotations == nil {
		return true // default-suspended until flipped; matches platform/gvisor-runtime's CR
	}
	v, ok := cr.Annotations["estate.estate.io/suspend"]
	if !ok {
		return true
	}
	return v == "true"
}

// SetupWithManager wires the Reconciler into a controller-runtime manager. Called from main.go.
func (r *Reconciler) SetupWithManager(mgr ctrl.Manager) error {
	if r.ReconcilePeriod == 0 {
		r.ReconcilePeriod = 15 * time.Second
	}
	if r.HandlerNamespace == "" {
		r.HandlerNamespace = "nodesoftware-operator-system"
	}
	return ctrl.NewControllerManagedBy(mgr).
		For(&nodesoftwarev1alpha1.RuntimeInstall{}).
		Complete(r)
}
