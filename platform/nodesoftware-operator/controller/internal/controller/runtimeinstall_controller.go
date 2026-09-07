// Package controller wires the RuntimeInstall state machine to controller-runtime. The
// Reconciler is the side-effecting half of the design; the pure functions in state.go are the
// half the tests are easy to write against.
//
// On each reconcile:
//
//  1. Read the CR. Bail if Suspended (estate.estate.io/suspend=true).
//  2. List target nodes via spec.selector.nodeSelector. Pick the next node (sorted, canary pin
//     honoured).
//  3. Build Snapshot from CR status + matched node list.
//  4. Decide(snap) -> Action. The action's verb tells us which side-effect to perform on the
//     picked node.
//  5. Apply the verb (Cordon/Drain/Install/Verify/Uncordon/Rollback).
//  6. Requeue after the standard reconcile period.
//
// The Reconciler does not persist sub-state. On restart, it derives where each node is from
// cluster state (node.Spec.Unschedulable, handler pods, probe pods) and picks up mid-flight.
package controller

import (
	"context"
	"fmt"
	"time"

	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	restclient "k8s.io/client-go/rest"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"

	nodesoftwarev1alpha1 "github.com/chidionyema/idp/platform/nodesoftware-operator/controller/api/v1alpha1"
	"github.com/chidionyema/idp/platform/nodesoftware-operator/controller/internal/handler"
)

// Reconciler owns the reconcile loop for RuntimeInstall.
type Reconciler struct {
	client.Client
	Scheme           *runtime.Scheme
	Handlers         *handler.Registry
	ReconcilePeriod  time.Duration
	HandlerNamespace string

	// RESTConfig is the in-cluster REST config. Used for reading pod logs (the SubResource
	// helper on Client doesn't return the streaming response we need). Optional: when nil,
	// pod log reads are skipped (the controller cannot verify, and the next reconcile will
	// retry after a pod restart).
	RESTConfig *restclient.Config
}

// Reconcile is the controller-runtime entry point.
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := log.FromContext(ctx).WithValues("runtimeinstall", req.NamespacedName.String())

	var cr nodesoftwarev1alpha1.RuntimeInstall
	if err := r.Get(ctx, req.NamespacedName, &cr); err != nil {
		if apierrors.IsNotFound(err) {
			return ctrl.Result{}, nil
		}
		return ctrl.Result{}, err
	}

	if isSuspended(&cr) {
		log.Info("skipping suspended RuntimeInstall")
		return r.requeue(), nil
	}

	if err := handler.ValidateClosedRuntime(cr.Spec.Runtime); err != nil {
		return r.fail(ctx, &cr, err.Error())
	}

	// List target nodes.
	var nodes corev1.NodeList
	if err := r.List(ctx, &nodes, client.MatchingLabels(cr.Spec.Selector.NodeSelector.MatchLabels)); err != nil {
		return r.requeue(), fmt.Errorf("list nodes: %w", err)
	}
	targets := sortedTargetNodes(nodes.Items)
	if len(targets) == 0 {
		return r.fail(ctx, &cr, "selector matches zero nodes")
	}

	// Pick the next target node.
	canaryReplicas := 1
	if cr.Spec.CanaryReplicas != nil {
		canaryReplicas = int(*cr.Spec.CanaryReplicas)
	}
	target := pickNextTarget(targets, cr.Status.RolloutHistory, canaryReplicas)
	if target == "" {
		// Every target node has a Verified entry -- rollout is complete.
		return r.complete(ctx, &cr, "all target nodes verified")
	}

	// Build snapshot and decide.
	snap := buildSnapshot(&cr, len(targets), cr.Status.RolloutHistory, isSuspended(&cr))
	action := Decide(snap)
	action.Node = target
	log.Info("decided", "phase", snap.Phase, "action", action.Verb, "node", target, "reason", action.Reason)

	return r.apply(ctx, &cr, action.Verb, target)
}

// apply dispatches on the verb. Each handler in reconcile_actions.go / reconcile_install.go
// owns its verb; this function is just the switchboard.
func (r *Reconciler) apply(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, verb ActionVerb, nodeName string) (ctrl.Result, error) {
	switch verb {
	case ActionSkip, ActionWait:
		return r.requeue(), nil
	case ActionComplete:
		return r.complete(ctx, cr, "all target nodes verified")
	case ActionFail:
		return r.fail(ctx, cr, "rollout failed")
	case ActionCordon:
		return r.handleCordon(ctx, cr, nodeName)
	case ActionDrain:
		return r.handleDrain(ctx, cr, nodeName)
	case ActionInstall:
		return r.handleInstall(ctx, cr, nodeName)
	case ActionVerify:
		return r.handleVerify(ctx, cr, nodeName)
	case ActionUncordon:
		return r.handleUncordon(ctx, cr, nodeName)
	case ActionRollback:
		return r.handleRollback(ctx, cr, nodeName)
	default:
		return ctrl.Result{}, fmt.Errorf("unknown action verb: %q", verb)
	}
}

// complete writes the terminal Verified phase.
func (r *Reconciler) complete(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, reason string) (ctrl.Result, error) {
	if cr.Status.Phase == string(PhaseVerified) {
		return ctrl.Result{}, nil
	}
	cr.Status.Phase = string(PhaseVerified)
	cr.Status.Message = reason
	if err := r.Status().Update(ctx, cr); err != nil {
		return r.requeue(), err
	}
	return ctrl.Result{}, nil
}

// fail writes the terminal Failed phase.
func (r *Reconciler) fail(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, reason string) (ctrl.Result, error) {
	cr.Status.Phase = string(PhaseFailed)
	cr.Status.Message = reason
	if err := r.Status().Update(ctx, cr); err != nil {
		return r.requeue(), err
	}
	return ctrl.Result{}, nil
}

// requeue returns a Result that requeues after the configured period.
func (r *Reconciler) requeue() ctrl.Result {
	d := r.ReconcilePeriod
	if d == 0 {
		d = 15 * time.Second
	}
	return ctrl.Result{RequeueAfter: d}
}

// buildSnapshot assembles the Snapshot for Decide. Counts come from rolloutHistory; total
// comes from the caller (matched node list size).
func buildSnapshot(cr *nodesoftwarev1alpha1.RuntimeInstall, totalNodes int, history []nodesoftwarev1alpha1.RolloutHistoryEntry, suspended bool) Snapshot {
	snap := Snapshot{
		Phase:          Phase(cr.Status.Phase),
		Strategy:       Strategy(cr.Spec.RolloutStrategy),
		FailurePolicy:  FailurePolicy(cr.Spec.FailurePolicy),
		CanaryReplicas: 1,
		TotalNodes:     totalNodes,
		Suspended:      suspended,
	}
	if cr.Spec.CanaryReplicas != nil {
		snap.CanaryReplicas = int(*cr.Spec.CanaryReplicas)
	}
	for _, h := range history {
		switch NodeOutcome(h.Outcome) {
		case OutcomeVerified:
			snap.ObservedNodes++
		case OutcomeFailed:
			snap.FailedNodes++
		case OutcomePending:
			snap.PendingNodes++
		}
	}
	return snap
}

// isSuspended honours the estate.estate.io/suspend annotation.
func isSuspended(cr *nodesoftwarev1alpha1.RuntimeInstall) bool {
	if cr.Annotations == nil {
		return true
	}
	v, ok := cr.Annotations["estate.estate.io/suspend"]
	if !ok {
		return true
	}
	return v == "true"
}

// SetupWithManager wires the Reconciler into a controller-runtime manager.
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
