// target.go: node selection for the reconcile loop. The Reconciler picks the next node to act on
// based on the sorted selector-matched list and the rollout history. The pick is deterministic
// (sorted by name) so requeue cycles are reproducible; humans can pin a specific node with the
// `nodesoftware.estate.io/canary` annotation on the node (checked first).
package controller

import (
	"sort"

	corev1 "k8s.io/api/core/v1"

	nodesoftwarev1alpha1 "github.com/chidionyema/idp/platform/nodesoftware-operator/controller/api/v1alpha1"
)

// targetNode describes one node in the rollout plan, with the canary annotation pin honoured.
type targetNode struct {
	Name             string
	IsExplicitCanary bool // pinned via nodesoftware.estate.io/canary=true annotation
}

// sortedTargetNodes returns the selector-matched nodes sorted by name, with annotation-pinned
// canary nodes first. The CR's canaryReplicas count is not applied here -- the Reconciler walks
// the canary count first (1 by default), then the rest, one node at a time.
func sortedTargetNodes(nodes []corev1.Node) []targetNode {
	out := make([]targetNode, 0, len(nodes))
	for _, n := range nodes {
		t := targetNode{Name: n.Name}
		if v, ok := n.Annotations["nodesoftware.estate.io/canary"]; ok && v == "true" {
			t.IsExplicitCanary = true
		}
		out = append(out, t)
	}
	sort.SliceStable(out, func(i, j int) bool {
		// Annotation-pinned canary first.
		if out[i].IsExplicitCanary != out[j].IsExplicitCanary {
			return out[i].IsExplicitCanary
		}
		return out[i].Name < out[j].Name
	})
	return out
}

// pickNextTarget returns the next node the controller should act on. It is the first node in
// sortedTargetNodes that does not have a terminal entry in rolloutHistory. A "terminal" entry is
// one with outcome=Verified; Failed entries are NOT terminal -- they still need rollback.
//
// If the rolloutHistory is empty AND no canary has been touched yet, the canary is the
// annotation-pinned node (if any), else the first sorted node. The CR's canaryReplicas count is
// applied during history walk; the first N nodes are canaries (Verified/Failed), and after that
// the rest are the rollout set.
//
// Returns "" if every matched node has a terminal entry (i.e. the rollout is complete).
func pickNextTarget(targets []targetNode, history []nodesoftwarev1alpha1.RolloutHistoryEntry, canaryReplicas int) string {
	canaryReplicas = max(canaryReplicas, 1)
	for _, t := range targets {
		// Find this node's existing history entry.
		var entry *nodesoftwarev1alpha1.RolloutHistoryEntry
		for i := range history {
			if history[i].Node == t.Name {
				entry = &history[i]
				break
			}
		}
		// No entry: this node hasn't been touched yet.
		if entry == nil {
			return t.Name
		}
		// Entry exists with terminal outcome: skip (this node is done).
		if entry.Outcome == string(OutcomeVerified) {
			continue
		}
		// Entry is Pending or Failed: this node needs more work.
		return t.Name
	}
	return ""
}

// findEntry returns the rolloutHistory entry for the named node, or nil if there isn't one.
func findEntry(history []nodesoftwarev1alpha1.RolloutHistoryEntry, node string) *nodesoftwarev1alpha1.RolloutHistoryEntry {
	for i := range history {
		if history[i].Node == node {
			return &history[i]
		}
	}
	return nil
}

// appendEntry appends a new entry; returns the new slice. Caller writes back via Status().Update.
func appendEntry(history []nodesoftwarev1alpha1.RolloutHistoryEntry, entry nodesoftwarev1alpha1.RolloutHistoryEntry) []nodesoftwarev1alpha1.RolloutHistoryEntry {
	// Don't double-append if the entry already exists.
	if findEntry(history, entry.Node) != nil {
		return history
	}
	return append(history, entry)
}

// upsertEntry inserts or updates the entry for the named node; returns the new slice.
func upsertEntry(history []nodesoftwarev1alpha1.RolloutHistoryEntry, entry nodesoftwarev1alpha1.RolloutHistoryEntry) []nodesoftwarev1alpha1.RolloutHistoryEntry {
	for i := range history {
		if history[i].Node == entry.Node {
			history[i] = entry
			return history
		}
	}
	return append(history, entry)
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
