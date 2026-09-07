// reconcile_install.go: install, verify, and rollback handlers. Each handler is idempotent and
// derives its sub-state from cluster state (existing handler pod, existing probe pod, etc.) on
// every reconcile.
package controller

import (
	"context"
	"fmt"
	"regexp"

	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/log"

	nodesoftwarev1alpha1 "github.com/chidionyema/idp/platform/nodesoftware-operator/controller/api/v1alpha1"
	"github.com/chidionyema/idp/platform/nodesoftware-operator/controller/internal/handler"
)

// handleInstall creates the handler pod (install command), waits for it to finish, then advances.
// Idempotent: if a handler pod for this node already exists, we observe its status; on Succeeded
// with exit 0 we advance, on Failed or non-zero exit we mark the node Failed and trigger rollback.
//
// FailurePolicy:
//   - FailClosed: any failure halts the rollout (the next reconcile will move to RollingBack).
//   - Ignore: the failure is recorded but the rollout continues to the next node.
func (r *Reconciler) handleInstall(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, nodeName string) (ctrlResult, error) {
	log := log.FromContext(ctx).WithValues("node", nodeName, "step", "install", "runtime", cr.Spec.Runtime)

	h, ok := r.Handlers.Get(cr.Spec.Runtime)
	if !ok {
		return r.failNode(ctx, cr, nodeName, fmt.Sprintf("no handler registered for runtime %q", cr.Spec.Runtime))
	}

	step, err := h.Install(ctx, nodeName, cr.Spec.Version)
	if err != nil {
		return r.failNode(ctx, cr, nodeName, fmt.Sprintf("handler.Install: %v", err))
	}

	// Find or create the install handler pod. Pods are labelled so we can list them.
	podName := handlerPodName(cr.Name, nodeName, "install")
	pod := &corev1.Pod{}
	err = r.Get(ctx, client.ObjectKey{Namespace: r.HandlerNamespace, Name: podName}, pod)
	if apierrors.IsNotFound(err) {
		// Create the install pod.
		p := buildHandlerPod(podName, r.HandlerNamespace, step, nodeName, cr)
		if err := r.Create(ctx, p); err != nil {
			return requeue, fmt.Errorf("create install pod %s: %w", podName, err)
		}
		log.Info("created install handler pod", "pod", podName, "image", step.Image)
		cr.Status.Message = fmt.Sprintf("installing on %s", nodeName)
		if err := r.Status().Update(ctx, cr); err != nil {
			return requeue, err
		}
		return requeue, nil
	}
	if err != nil {
		return requeue, err
	}

	// Pod exists -- check status.
	switch pod.Status.Phase {
	case corev1.PodSucceeded:
		log.Info("install pod succeeded")
		cr.Status.Message = fmt.Sprintf("install succeeded on %s; moving to verify", nodeName)
		// Clean up the install pod -- the controller's RBAC has pods/delete in its own namespace.
		_ = r.Delete(ctx, pod)
		if err := r.Status().Update(ctx, cr); err != nil {
			return requeue, err
		}
		return requeue, nil

	case corev1.PodFailed:
		log.Info("install pod failed", "message", pod.Status.Message)
		return r.failNode(ctx, cr, nodeName, fmt.Sprintf("install pod failed: %s", pod.Status.Message))

	default:
		// Pending / Running -- wait for terminal.
		log.Info("install pod still running", "phase", pod.Status.Phase)
		return requeue, nil
	}
}

// handleVerify creates the probe pod (Spec.Verification.ProbePod with nodeSelector pinned to the
// target node and runtimeClassName=spec.runtime), waits for it, then evaluates SuccessCondition
// (a Go regexp) against the pod's stdout.
//
// On regex match: Uncordon.
// On regex miss or probe failure: failNode + (FailClosed -> Rollback) / (Ignore -> continue).
func (r *Reconciler) handleVerify(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, nodeName string) (ctrlResult, error) {
	log := log.FromContext(ctx).WithValues("node", nodeName, "step", "verify", "runtime", cr.Spec.Runtime)

	if cr.Spec.Verification.SuccessCondition == "" {
		// Defence-in-depth: the gate refuses this, but if a CR was admitted under a misconfigured
		// CRD the controller refuses again.
		return r.failNode(ctx, cr, nodeName, "spec.verification.successCondition is empty")
	}
	re, err := regexp.Compile(cr.Spec.Verification.SuccessCondition)
	if err != nil {
		return r.failNode(ctx, cr, nodeName, fmt.Sprintf("compile successCondition regex %q: %v", cr.Spec.Verification.SuccessCondition, err))
	}

	podName := probePodName(cr.Name, nodeName)
	pod := &corev1.Pod{}
	err = r.Get(ctx, client.ObjectKey{Namespace: r.HandlerNamespace, Name: podName}, pod)
	if apierrors.IsNotFound(err) {
		// Create the probe pod from the CR's template.
		p := buildProbePod(podName, r.HandlerNamespace, cr, nodeName)
		if err := r.Create(ctx, p); err != nil {
			return requeue, fmt.Errorf("create probe pod %s: %w", podName, err)
		}
		log.Info("created probe pod", "pod", podName)
		cr.Status.Message = fmt.Sprintf("verifying on %s", nodeName)
		if err := r.Status().Update(ctx, cr); err != nil {
			return requeue, err
		}
		return requeue, nil
	}
	if err != nil {
		return requeue, err
	}

	switch pod.Status.Phase {
	case corev1.PodSucceeded:
		// Read the probe pod's stdout via the controller's pods/log subresource.
		out, logErr := r.readPodLog(ctx, pod)
		if logErr != nil {
			return requeue, fmt.Errorf("read probe log: %w", logErr)
		}
		if !re.MatchString(out) {
			return r.failNode(ctx, cr, nodeName, fmt.Sprintf("probe stdout %q did not match successCondition %q", truncate(out, 200), cr.Spec.Verification.SuccessCondition))
		}
		log.Info("verify matched", "pattern", cr.Spec.Verification.SuccessCondition)
		_ = r.Delete(ctx, pod)
		cr.Status.Message = fmt.Sprintf("verified on %s; uncordoning", nodeName)
		if err := r.Status().Update(ctx, cr); err != nil {
			return requeue, err
		}
		return requeue, nil

	case corev1.PodFailed:
		return r.failNode(ctx, cr, nodeName, fmt.Sprintf("probe pod failed: %s", pod.Status.Message))

	default:
		return requeue, nil
	}
}

// handleRollback runs the runtime handler's Uninstall command. Same shape as handleInstall but
// uses the Uninstall Step. Idempotent: looks for an existing uninstall handler pod first.
//
// On uninstall success: write RolledBack entry, transition to PhaseFailed (terminal).
// On uninstall failure: log + retry on next reconcile.
func (r *Reconciler) handleRollback(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, nodeName string) (ctrlResult, error) {
	log := log.FromContext(ctx).WithValues("node", nodeName, "step", "rollback")

	h, ok := r.Handlers.Get(cr.Spec.Runtime)
	if !ok {
		return r.failNode(ctx, cr, nodeName, fmt.Sprintf("no handler registered for runtime %q (cannot roll back)", cr.Spec.Runtime))
	}
	step, err := h.Uninstall(ctx, nodeName, cr.Spec.Version)
	if err != nil {
		return r.failNode(ctx, cr, nodeName, fmt.Sprintf("handler.Uninstall: %v", err))
	}

	podName := handlerPodName(cr.Name, nodeName, "uninstall")
	pod := &corev1.Pod{}
	err = r.Get(ctx, client.ObjectKey{Namespace: r.HandlerNamespace, Name: podName}, pod)
	if apierrors.IsNotFound(err) {
		p := buildHandlerPod(podName, r.HandlerNamespace, step, nodeName, cr)
		if err := r.Create(ctx, p); err != nil {
			return requeue, fmt.Errorf("create uninstall pod %s: %w", podName, err)
		}
		log.Info("created uninstall handler pod", "pod", podName)
		cr.Status.Phase = string(PhaseRollingBack)
		cr.Status.Message = fmt.Sprintf("rolling back on %s", nodeName)
		if err := r.Status().Update(ctx, cr); err != nil {
			return requeue, err
		}
		return requeue, nil
	}
	if err != nil {
		return requeue, err
	}

	switch pod.Status.Phase {
	case corev1.PodSucceeded:
		log.Info("uninstall pod succeeded; rollout rolled back")
		_ = r.Delete(ctx, pod)
		now := nowRFC3339()
		cr.Status.RolloutHistory = upsertEntry(cr.Status.RolloutHistory, nodesoftwarev1alpha1.RolloutHistoryEntry{
			Node:       nodeName,
			Outcome:    string(OutcomeFailed),
			StartedAt:  startedAt(cr.Status.RolloutHistory, nodeName),
			FinishedAt: now,
			Error:      "rolled back after verify failure",
		})
		cr.Status.Phase = string(PhaseFailed)
		cr.Status.Message = fmt.Sprintf("rolled back on %s", nodeName)
		if err := r.Status().Update(ctx, cr); err != nil {
			return requeue, err
		}
		return noRequeue, nil

	case corev1.PodFailed:
		log.Info("uninstall pod failed; will retry next reconcile", "message", pod.Status.Message)
		cr.Status.Message = fmt.Sprintf("uninstall on %s failed; retrying", nodeName)
		if err := r.Status().Update(ctx, cr); err != nil {
			return requeue, err
		}
		return requeue, nil

	default:
		return requeue, nil
	}
}

// failNode records the node as Failed in rolloutHistory and decides whether to halt the rollout.
// FailClosed -> transition to RollingBack (which the next reconcile will pick up as the verb
// for this node).
// Ignore -> just record the failure; the next reconcile will pick the next target node.
func (r *Reconciler) failNode(ctx context.Context, cr *nodesoftwarev1alpha1.RuntimeInstall, nodeName, reason string) (ctrlResult, error) {
	log := log.FromContext(ctx).WithValues("node", nodeName, "failure", reason)

	now := nowRFC3339()
	cr.Status.RolloutHistory = upsertEntry(cr.Status.RolloutHistory, nodesoftwarev1alpha1.RolloutHistoryEntry{
		Node:       nodeName,
		Outcome:    string(OutcomeFailed),
		StartedAt:  startedAt(cr.Status.RolloutHistory, nodeName),
		FinishedAt: now,
		Error:      reason,
	})
	cr.Status.FailedNodes++

	if cr.Spec.FailurePolicy == string(FailurePolicyIgnore) {
		log.Info("recording failure and continuing (failurePolicy=Ignore)")
		cr.Status.Message = fmt.Sprintf("node %s failed (ignored): %s", nodeName, reason)
		// Phase stays as-is; the next reconcile picks the next target node.
		if err := r.Status().Update(ctx, cr); err != nil {
			return requeue, err
		}
		return requeue, nil
	}

	log.Info("recording failure; entering RollingBack (failurePolicy=FailClosed)")
	cr.Status.Phase = string(PhaseRollingBack)
	cr.Status.Message = fmt.Sprintf("node %s failed: %s; rolling back", nodeName, reason)
	if err := r.Status().Update(ctx, cr); err != nil {
		return requeue, err
	}
	return requeue, nil
}

// buildHandlerPod constructs the handler pod spec from a handler.Step. The pod is privileged
// (runtime install needs /etc/crio writes etc.) and hostPath-mounted.
func buildHandlerPod(name, namespace string, step *handler.Step, nodeName string, cr *nodesoftwarev1alpha1.RuntimeInstall) *corev1.Pod {
	hostPathType := corev1.HostPathDirectory
	return &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
			Labels: map[string]string{
				"nodesoftware.estate.io/runtimeinstall": cr.Name,
				"nodesoftware.estate.io/node":           nodeName,
				"nodesoftware.estate.io/managed-by":     "nodesoftware-operator",
			},
		},
		Spec: corev1.PodSpec{
			NodeName:      nodeName,
			RestartPolicy: corev1.RestartPolicyNever,
			HostNetwork:   false,
			HostPID:       false,
			Containers: []corev1.Container{{
				Name:    "handler",
				Image:   step.Image,
				Command: step.Command,
				SecurityContext: &corev1.SecurityContext{
					Privileged:               boolPtr(true),
					RunAsNonRoot:             boolPtr(false),
					ReadOnlyRootFilesystem:   boolPtr(false),
					AllowPrivilegeEscalation: boolPtr(true),
				},
				VolumeMounts: []corev1.VolumeMount{{
					Name:      "host",
					MountPath: "/host",
				}},
			}},
			Volumes: []corev1.Volume{{
				Name: "host",
				VolumeSource: corev1.VolumeSource{
					HostPath: &corev1.HostPathVolumeSource{
						Path: "/",
						Type: &hostPathType,
					},
				},
			}},
		},
	}
}

// buildProbePod constructs the probe pod from Spec.Verification.ProbePod, pinning it to the
// target node and setting runtimeClassName.
func buildProbePod(name, namespace string, cr *nodesoftwarev1alpha1.RuntimeInstall, nodeName string) *corev1.Pod {
	tpl := cr.Spec.Verification.ProbePod
	pod := &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
			Labels: map[string]string{
				"nodesoftware.estate.io/runtimeinstall": cr.Name,
				"nodesoftware.estate.io/node":           nodeName,
				"nodesoftware.estate.io/managed-by":     "nodesoftware-operator",
			},
		},
		Spec: *tpl.Spec.DeepCopy(),
	}
	pod.Spec.NodeName = nodeName
	if pod.Spec.RuntimeClassName == nil {
		rc := cr.Spec.Runtime
		pod.Spec.RuntimeClassName = &rc
	}
	pod.Spec.RestartPolicy = corev1.RestartPolicyNever
	return pod
}

// readPodLog fetches the probe pod's stdout via the pods/log subresource. The controller's
// RBAC (PR #2338) has pods/log get on the operator's namespace.
//
// We use client-go's pod log helper against r.RESTConfig. The controller-runtime SubResource
// helper doesn't return a streaming response shape we can read directly, so we use the typed
// client-go helper instead. If RESTConfig is nil (test mode), we return an empty string; the
// Reconciler's test will not exercise this code path.
func (r *Reconciler) readPodLog(ctx context.Context, pod *corev1.Pod) (string, error) {
	if r.RESTConfig == nil {
		return "", nil
	}
	clientset, err := kubernetes.NewForConfig(r.RESTConfig)
	if err != nil {
		return "", fmt.Errorf("kubernetes client: %w", err)
	}
	stream, err := clientset.CoreV1().Pods(pod.Namespace).GetLogs(pod.Name, &corev1.PodLogOptions{}).Stream(ctx)
	if err != nil {
		return "", fmt.Errorf("stream pod log: %w", err)
	}
	defer func() { _ = stream.Close() }()
	buf := make([]byte, 0, 4096)
	tmp := make([]byte, 1024)
	for {
		n, err := stream.Read(tmp)
		if n > 0 {
			buf = append(buf, tmp[:n]...)
		}
		if err != nil {
			break
		}
	}
	return string(buf), nil
}

// handlerPodName returns the deterministic pod name for a handler step on a node.
func handlerPodName(crName, nodeName, step string) string {
	return fmt.Sprintf("rti-%s-%s-%s", crName, sanitiseForDNS(nodeName), step)
}

// probePodName returns the deterministic probe pod name.
func probePodName(crName, nodeName string) string {
	return fmt.Sprintf("rti-%s-%s-probe", crName, sanitiseForDNS(nodeName))
}

// sanitiseForDNS lowercases and replaces dots/dots with dashes so the name is RFC 1123.
func sanitiseForDNS(s string) string {
	out := make([]byte, 0, len(s))
	for i := 0; i < len(s); i++ {
		c := s[i]
		switch {
		case c >= 'A' && c <= 'Z':
			out = append(out, c+'a'-'A')
		case c >= 'a' && c <= 'z', c >= '0' && c <= '9', c == '-':
			out = append(out, c)
		default:
			out = append(out, '-')
		}
	}
	return string(out)
}

// boolPtr is a tiny helper for *bool fields.
func boolPtr(v bool) *bool { return &v }

// truncate caps a string at n bytes (for status messages).
func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}

// keep the apierrors import live.
var _ = apierrors.IsNotFound
