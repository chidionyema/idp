// reconcile_actions.go: per-verb handlers for the Reconciler. Each handler does ONE thing:
// patches a node, evicts pods, creates a handler pod, reads its log, etc. The handlers are
// idempotent -- calling them twice produces the same cluster state and returns Requeue.
//
// Per-node lifecycle:
//
//	cordon   -> patch node.Spec.Unschedulable=true
//	drain    -> Eviction subresource for every pod on the node (PDB-aware), wait until empty
//	install  -> create handler pod (install command), wait for Succeeded, check exit code
//	verify   -> create probe pod (Spec.Verification.ProbePod), wait, check exit code + SuccessCondition
//	uncordon -> patch node.Spec.Unschedulable=false, append Verified entry to rolloutHistory
//
// The lifecycle is derived from cluster state on every reconcile -- the Reconciler does NOT
// persist sub-state. If the controller restarts mid-flight, it picks up where the cluster says
// it left off (node already cordoned -> skip Cordon, find existing handler pod, etc.).
package controller

import (
	"context"
	"fmt"
	"time"

	corev1 "k8s.io/api/core/v1"
	policyv1 "k8s.io/api/policy/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"

	nodesoftwarev1alpha1 "github.com/chidionyema/idp/platform/nodesoftware-operator/controller/api/v1alpha1"
)

// handleCordon patches node.Spec.Unschedulable=true. Idempotent: a node already cordoned is
// considered done; we move on. The next reconcile may pick this node up for drain.
func (r *Reconciler) handleCordon(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, nodeName string) (ctrlResult, error) {
	log := log.FromContext(ctx).WithValues("node", nodeName, "step", "cordon")

	var node corev1.Node
	if err := r.Get(ctx, client.ObjectKey{Name: nodeName}, &node); err != nil {
		return requeue, fmt.Errorf("get node %s: %w", nodeName, err)
	}
	if node.Spec.Unschedulable {
		log.Info("node already cordoned; advancing")
		// Mark the rolloutHistory entry as Pending so subsequent steps know this node is in flight.
		cr.Status.RolloutHistory = upsertEntry(cr.Status.RolloutHistory, nodesoftwarev1alpha1.RolloutHistoryEntry{
			Node:      nodeName,
			Outcome:   string(OutcomePending),
			StartedAt: nowRFC3339(),
		})
		// Phase advances Pending -> Canary on the first node, Pending -> RollingOut on subsequent nodes.
		if cr.Status.Phase == "" || cr.Status.Phase == string(PhasePending) {
			cr.Status.Phase = string(PhaseCanary)
		}
		cr.Status.Message = "cordoned; starting drain"
		if err := r.Status().Update(ctx, cr); err != nil {
			return noRequeue, err
		}
		return requeue, nil
	}

	node.Spec.Unschedulable = true
	if err := r.Update(ctx, &node); err != nil {
		return requeue, fmt.Errorf("cordon node %s: %w", nodeName, err)
	}
	log.Info("node cordoned")
	cr.Status.Message = "cordoned"
	if err := r.Status().Update(ctx, cr); err != nil {
		return requeue, err
	}
	return requeue, nil
}

// handleDrain evicts every pod on the node via the Eviction subresource (which honours PodDisruptionBudgets).
// Idempotent: a node with no pods is considered drained.
func (r *Reconciler) handleDrain(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, nodeName string) (ctrlResult, error) {
	log := log.FromContext(ctx).WithValues("node", nodeName, "step", "drain")

	var pods corev1.PodList
	if err := r.List(ctx, &pods, client.MatchingFields{"spec.nodeName": nodeName}); err != nil {
		// Older clusters may not have the nodeName indexer; fall back to the full list.
		if err := r.List(ctx, &pods); err != nil {
			return requeue, fmt.Errorf("list pods: %w", err)
		}
		var onNode []corev1.Pod
		for _, p := range pods.Items {
			if p.Spec.NodeName == nodeName {
				onNode = append(onNode, p)
			}
		}
		return r.evictPods(ctx, cr, nodeName, onNode, log)
	}
	return r.evictPods(ctx, cr, nodeName, pods.Items, log)
}

// evictPods creates an Eviction per pod. Pods that are Succeeded/Failed are skipped (no eviction
// needed). Mirrors kubectl drain's "ignore daemonsets" behaviour: we do NOT evict pods owned by
// a DaemonSet -- the runtime install needs them, and they will respawn on uncordon.
//
// Returns requeue=true while there are still pods to drain. The reconcile loop drives the wait.
func (r *Reconciler) evictPods(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, nodeName string, pods []corev1.Pod, log ctrlLogger) (ctrlResult, error) {
	remaining := 0
	for i := range pods {
		p := &pods[i]
		if p.Spec.NodeName != nodeName {
			continue
		}
		if p.Status.Phase == corev1.PodSucceeded || p.Status.Phase == corev1.PodFailed {
			continue
		}
		if isDaemonSetPod(p) {
			continue
		}
		if isMirrorPod(p) {
			continue
		}
		// Already being deleted? skip.
		if p.DeletionTimestamp != nil {
			remaining++
			continue
		}
		ev := &policyv1.Eviction{
			ObjectMeta: metav1.ObjectMeta{
				Name:      p.Name,
				Namespace: p.Namespace,
			},
		}
		if err := r.SubResource("eviction").Create(ctx, p, ev); err != nil {
			if apierrors.IsNotFound(err) {
				continue
			}
			if apierrors.IsTooManyRequests(err) {
				// PDB blocked; requeue and try again next tick.
				remaining++
				continue
			}
			return requeue, fmt.Errorf("evict pod %s/%s: %w", p.Namespace, p.Name, err)
		}
		log.Info("evicted pod", "pod", p.Name, "namespace", p.Namespace)
		remaining++
	}
	if remaining > 0 {
		cr.Status.Message = fmt.Sprintf("draining: %d pods remaining on %s", remaining, nodeName)
		if err := r.Status().Update(ctx, cr); err != nil {
			return requeue, err
		}
		return requeue, nil
	}
	log.Info("drain complete")
	cr.Status.Message = "drained"
	if err := r.Status().Update(ctx, cr); err != nil {
		return requeue, err
	}
	return requeue, nil
}

// handleUncordon patches node.Spec.Unschedulable=false and appends a Verified entry to the
// rolloutHistory. After this, the next reconcile picks the next sorted target node.
func (r *Reconciler) handleUncordon(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, nodeName string) (ctrlResult, error) {
	log := log.FromContext(ctx).WithValues("node", nodeName, "step", "uncordon")

	var node corev1.Node
	if err := r.Get(ctx, client.ObjectKey{Name: nodeName}, &node); err != nil {
		return requeue, fmt.Errorf("get node %s: %w", nodeName, err)
	}
	if node.Spec.Unschedulable {
		node.Spec.Unschedulable = false
		if err := r.Update(ctx, &node); err != nil {
			return requeue, fmt.Errorf("uncordon node %s: %w", nodeName, err)
		}
	}

	now := nowRFC3339()
	cr.Status.RolloutHistory = upsertEntry(cr.Status.RolloutHistory, nodesoftwarev1alpha1.RolloutHistoryEntry{
		Node:       nodeName,
		Outcome:    string(OutcomeVerified),
		StartedAt:  startedAt(cr.Status.RolloutHistory, nodeName),
		FinishedAt: now,
	})
	cr.Status.ObservedNodes++
	cr.Status.Message = fmt.Sprintf("verified node %s", nodeName)

	// Phase advances Canary -> Paused or RollingOut -> Paused on the last node (Verified).
	// Phase is set to RollingOut before the next reconcile so the snapshot picks the next node.
	if cr.Status.Phase == string(PhaseCanary) {
		cr.Status.Phase = string(PhaseRollingOut)
	}
	cr.Status.Phase = nextPhaseAfterUncordon(cr.Status.Phase)

	if err := r.Status().Update(ctx, cr); err != nil {
		return requeue, err
	}
	log.Info("node verified", "historyLen", len(cr.Status.RolloutHistory))
	return requeue, nil
}

// isDaemonSetPod returns true if the pod has a DaemonSet owner ref.
func isDaemonSetPod(p *corev1.Pod) bool {
	for _, ref := range p.OwnerReferences {
		if ref.Kind == "DaemonSet" {
			return true
		}
	}
	return false
}

// isMirrorPod returns true if the pod has the mirror pod annotation. Mirror pods are owned by
// the kubelet (not the API) and cannot be evicted via the Eviction subresource.
func isMirrorPod(p *corev1.Pod) bool {
	if p.Annotations == nil {
		return false
	}
	v, ok := p.Annotations["kubernetes.io/config.mirror"]
	return ok && v != ""
}

// nextPhaseAfterUncordon returns the phase the controller should be in after a node's Uncordon.
// Verified CRs get the Verified terminal phase; otherwise RollingOut (so the next reconcile
// picks the next target node).
func nextPhaseAfterUncordon(current string) string {
	switch current {
	case string(PhaseRollingOut), string(PhaseCanary):
		return string(PhaseRollingOut)
	}
	return current
}

// startedAt looks up an existing history entry's StartedAt; returns "" if no entry exists.
func startedAt(history []nodesoftwarev1alpha1.RolloutHistoryEntry, node string) string {
	if e := findEntry(history, node); e != nil {
		return e.StartedAt
	}
	return nowRFC3339()
}

// nowRFC3339 returns the current time formatted as RFC3339 (the format Status fields use).
func nowRFC3339() string {
	return time.Now().UTC().Format(time.RFC3339)
}
