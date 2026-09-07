// RuntimeInstall is the Schema for the nodesoftware.estate.io/v1alpha1 API.
// A RuntimeInstall is a request to install a closed-set runtime on a selector-matched set of
// nodes, one canary at a time, with verification before uncordon. The NodeSoftwareOperator
// (this controller) owns the cordon/drain/install/verify/uncordon cycle.
//
// The 1:1 mapping between these Go fields and the CRD YAML's openAPIV3Schema is checked by
// internal/controller/crd_contract_test.go -- the offline gate grades the YAML side; the contract
// test grades the Go side. Drift in either direction fails CI before merge.
package v1alpha1

import (
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// ClosedRuntimes is the set of runtime values the controller knows how to install. A CR with any
// other value is refused by the gate; the controller also refuses on safety grounds (a runtime
// outside the closed set has no handler module and would silently no-op). This set MUST match
// platform/nodesoftware-operator/crds/runtimeinstall.yaml's spec.runtime enum AND the python
// CLOSED_RUNTIMES set in bin/lib/nodesoftware_operator_gate.py. All three are the same lever.
var ClosedRuntimes = map[string]struct{}{
	"runsc":  {}, // gVisor -- the first shipped runtime, deployed on a canary node
	"kata":   {}, // Kata Containers -- stub, follow-up ticket NodeSoftwareOperator: kata-runtime-handler
	"nvidia": {}, // NVIDIA device plugin -- stub, follow-up NodeSoftwareOperator: nvidia-runtime-handler
}

// RuntimeInstallSpec defines the desired state of a RuntimeInstall.
type RuntimeInstallSpec struct {
	// Runtime is the closed-set runtime to install. MUST be one of ClosedRuntimes.
	// The CRD enum + the gate + the controller all refuse anything else.
	Runtime string `json:"runtime"`

	// Version is the exact runtime version. The handler looks up the digest-pinned image and
	// records this string in status.rolloutHistory for human audit.
	Version string `json:"version"`

	// Selector picks which nodes the install targets. An empty selector would match every node;
	// the gate refuses that case.
	Selector RuntimeInstallNodeSelector `json:"selector"`

	// RolloutStrategy is how the install spreads across selected nodes.
	// +kubebuilder:validation:Enum=ProgressiveCanary;AllAtOnce;Manual
	RolloutStrategy string `json:"rolloutStrategy,omitempty"`

	// CanaryReplicas is the number of selected nodes in the canary phase. Required when
	// rolloutStrategy != AllAtOnce; the CRD enforces >= 1.
	CanaryReplicas *int32 `json:"canaryReplicas,omitempty"`

	// PauseDuration is the wait between canary verification and the rest, and between subsequent
	// nodes. Must be parseable as a Go duration string and >= 30s.
	PauseDuration *metav1.Duration `json:"pauseDuration,omitempty"`

	// FailurePolicy is what the controller does when a single node's install fails.
	// +kubebuilder:validation:Enum=FailClosed;Ignore
	FailurePolicy string `json:"failurePolicy,omitempty"`

	// Verification is how the controller proves the install worked on the just-touched node.
	Verification RuntimeInstallVerification `json:"verification"`

	// Rollback is how the controller uninstalls if verification fails. Free-form commands are
	// forbidden by the gate; the controller ships one uninstall script per runtime, named
	// /usr/local/bin/nodesoftware-<runtime>-uninstall.
	Rollback *RuntimeInstallRollback `json:"rollback,omitempty"`
}

// RuntimeInstallNodeSelector is the standard k8s nodeSelector shape plus optional tolerations.
// The controller's reconcile loop uses client.MatchingLabels + a manual matchExpressions filter.
type RuntimeInstallNodeSelector struct {
	NodeSelector metav1.LabelSelector `json:"nodeSelector"`
	Tolerations  []corev1.Toleration  `json:"tolerations,omitempty"`
}

// RuntimeInstallVerification describes the probe pod the controller runs on each target node.
type RuntimeInstallVerification struct {
	// ProbePod is the pod template. The controller fills nodeSelector (pin to target node) and
	// runtimeClassName (set to spec.runtime) on every reconcile.
	ProbePod corev1.PodTemplateSpec `json:"probePod"`

	// SuccessCondition is the shell expression the controller evaluates against the probe pod's
	// stdout. Empty = no verdict (refused by the gate, but checked again here as a safety net).
	SuccessCondition string `json:"successCondition"`

	// TimeoutSeconds bounds how long the controller waits for the probe pod to complete.
	TimeoutSeconds *int32 `json:"timeoutSeconds,omitempty"`
}

// RuntimeInstallRollback is how the controller uninstalls a runtime if verification fails.
type RuntimeInstallRollback struct {
	// Commands is the list of uninstall commands. Each MUST match the closed-form pattern
	// /usr/local/bin/nodesoftware-<runtime>-uninstall; the gate enforces this.
	Commands []string `json:"commands,omitempty"`

	// TimeoutSeconds bounds the uninstall.
	TimeoutSeconds *int32 `json:"timeoutSeconds,omitempty"`
}

// RuntimeInstallStatus defines the observed state of a RuntimeInstall.
// Controller-managed; humans do not write status (subresource gate enforces this).
type RuntimeInstallStatus struct {
	// Phase is the state machine state. See internal/controller/state.go for the transitions.
	// +kubebuilder:validation:Enum=Pending;Canary;Paused;RollingOut;Verified;Failed;RollingBack;RolledBack
	Phase string `json:"phase,omitempty"`

	// Message is the last human-readable explanation of phase; overwritten on each transition.
	Message string `json:"message,omitempty"`

	// ObservedNodes is the count of nodes the controller has fully touched (cordon + install +
	// verify + uncordon complete) in this rollout. Read by the offline gate's empirical-proof
	// contract: the milestone-D PR body must cite this count for the canary node.
	ObservedNodes int32 `json:"observedNodes,omitempty"`

	// CanaryResults records the per-canary-node outcome (used for the empirical proof).
	CanaryResults []CanaryResult `json:"canaryResults,omitempty"`

	// RolloutHistory is every node the controller has touched in this rollout, kept for audit.
	// The empirical-proof commit's PR body quotes the entry with outcome=Verified.
	RolloutHistory []RolloutHistoryEntry `json:"rolloutHistory,omitempty"`
}

// CanaryResult records one canary node's reconcile outcome.
type CanaryResult struct {
	Node       string `json:"node"`
	StartedAt  string `json:"startedAt"`
	FinishedAt string `json:"finishedAt"`
	Outcome    string `json:"outcome"` // Verified | Failed
	Log        string `json:"log,omitempty"`
}

// RolloutHistoryEntry records one node's reconcile outcome (canary or subsequent).
type RolloutHistoryEntry struct {
	Node       string `json:"node"`
	StartedAt  string `json:"startedAt"`
	FinishedAt string `json:"finishedAt"`
	Outcome    string `json:"outcome"` // Verified | Failed
	Error      string `json:"error,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:scope=Namespaced,shortName=rti

// RuntimeInstall is the Schema for the nodesoftware.estate.io/v1alpha1 API.
type RuntimeInstall struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   RuntimeInstallSpec   `json:"spec,omitempty"`
	Status RuntimeInstallStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

// RuntimeInstallList contains a list of RuntimeInstall.
type RuntimeInstallList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []RuntimeInstall `json:"items"`
}
