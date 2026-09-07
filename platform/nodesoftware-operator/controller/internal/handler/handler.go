// Package handler defines the runtime-handler interface that the RuntimeInstall reconciler uses
// to install and uninstall closed-set runtimes. One handler per runtime; the reconciler looks up
// the handler by name from a registry.
//
// The reconciler never executes shell on the target node directly. Instead, the handler returns a
// Pod manifest (hostPath-mounted, with the right ServiceAccount) and a shell command. The
// reconciler creates the pod, the pod runs the command, the command exits, the pod is deleted.
// The handler's responsibility is to produce the pod and the command; the reconciler owns the
// loop.
package handler

import (
	"context"

	corev1 "k8s.io/api/core/v1"

	nodesoftwarev1alpha1 "github.com/chidionyema/idp/platform/nodesoftware-operator/controller/api/v1alpha1"
)

// Plan describes how the controller should install/uninstall a runtime on a specific node.
// The handler returns a Plan; the reconciler executes it.
type Plan struct {
	// Runtime is the closed-set runtime name (e.g. "runsc"). Echoed back so callers don't
	// have to carry the lookup-key separately.
	Runtime string

	// Version is the runtime version (e.g. "1.0.0"). Echoed back; useful for audit.
	Version string

	// TargetNode is the node the plan runs against.
	TargetNode string

	// Install is the install plan (nil for Verify-only or Uninstall-only handlers).
	Install *Step

	// Uninstall is the rollback plan (nil if the runtime has no rollback). The gate forbids
	// free-form rollback commands; the handler must ship the uninstall script as a binary in
	// the handler image.
	Uninstall *Step
}

// Step is one shell command + the pod that runs it.
type Step struct {
	// Image is the runtime-handler image (the one shipping the install/uninstall scripts).
	// Pinned by digest in production; the controller's Helm chart substitutes the tag.
	Image string

	// Command is the shell command executed on the host via the handler pod's hostPath mount.
	// The handler pod MUST run privileged (runtime install needs /etc/crio writes etc.); the
	// controller's RBAC does not need pods/exec because the handler runs its own pod.
	Command []string

	// ProbeCommand is the shell command run by the verification probe pod on the target node.
	// The reconciler attaches this to Spec.Verification.ProbePod before launching the probe.
	// For Uninstall-only handlers this is empty.
	ProbeCommand []string

	// TimeoutSeconds bounds the install/uninstall. The Reconciler adds this to the pod spec.
	TimeoutSeconds int32
}

// Handler is the per-runtime install/uninstall logic. The reconciler picks one by name from a
// registry. Each Handler implementation is stateless; the reconciler holds the per-CR state.
type Handler interface {
	// Runtime returns the closed-set runtime name, e.g. "runsc".
	Runtime() string

	// Install returns the Plan to install the runtime on the target node at the requested version.
	// The handler MUST validate the version against its own allowlist; a malicious CR that
	// requests "1.0.0; rm -rf /" must be refused here as well as at the gate.
	Install(ctx context.Context, targetNode, version string) (*Step, error)

	// Uninstall returns the Step to roll back the install on the target node. The Step's image
	// MUST be the same handler image (so the uninstall script is on board).
	Uninstall(ctx context.Context, targetNode, version string) (*Step, error)

	// ProbeCommand returns the shell command the verification probe runs on the target node.
	// Its stdout is checked against Spec.Verification.SuccessCondition. Empty means "no
	// automatic probe"; the gate also refuses that case.
	ProbeCommand(ctx context.Context, targetNode, version string) ([]string, error)
}

// Registry maps runtime name -> handler. The reconciler holds one of these; main.go wires it up.
type Registry struct {
	handlers map[string]Handler
}

// NewRegistry constructs an empty registry. Use Register to add handlers.
func NewRegistry() *Registry {
	return &Registry{handlers: map[string]Handler{}}
}

// Register adds a handler. Panics if the handler's Runtime() returns a duplicate name -- this is
// a programming error and the controller should refuse to start.
func (r *Registry) Register(h Handler) {
	name := h.Runtime()
	if _, ok := r.handlers[name]; ok {
		panic("handler already registered for runtime " + name)
	}
	r.handlers[name] = h
}

// Get returns the handler for the named runtime, or false if no handler is registered.
func (r *Registry) Get(runtime string) (Handler, bool) {
	h, ok := r.handlers[runtime]
	return h, ok
}

// Names returns the registered runtime names in arbitrary order. Used by the operator's startup
// log line so operators can see which runtimes the controller knows about.
func (r *Registry) Names() []string {
	out := make([]string, 0, len(r.handlers))
	for name := range r.handlers {
		out = append(out, name)
	}
	return out
}

// ValidateClosedRuntime asserts that the runtime is in the closed set. Returns nil if it is,
// an error naming the runtime and the closed set if it isn't. The reconciler calls this on every
// reconcile -- it is the last line of defence before the controller does anything to a node.
func ValidateClosedRuntime(runtime string) error {
	if _, ok := nodesoftwarev1alpha1.ClosedRuntimes[runtime]; !ok {
		return &NotClosedError{Runtime: runtime}
	}
	return nil
}

// NotClosedError is returned when a CR references a runtime outside the closed set. The
// Reconciler surfaces this in Status.Message and writes Status.Phase=Failed.
type NotClosedError struct {
	Runtime string
}

func (e *NotClosedError) Error() string {
	return "runtime " + e.Runtime + " is not in the closed set; refusing to install"
}

// HandlerPodSecurityContext returns the standard pod securityContext for a handler pod. The
// handler pod MUST run privileged (runtime install touches /etc/crio and friends); the controller
// pod itself is PSS-restricted, and only the handler pods are privileged. The handler pod is
// short-lived and created/deleted by the controller; the controller's RBAC does not need
// pods/exec because the controller never execs into the handler pod.
func HandlerPodSecurityContext() *corev1.SecurityContext {
	return &corev1.SecurityContext{
		Privileged:               ptr(true),
		RunAsNonRoot:             ptr(false),
		ReadOnlyRootFilesystem:   ptr(false),
		AllowPrivilegeEscalation: ptr(true),
	}
}

func ptr[T any](v T) *T { return &v }
