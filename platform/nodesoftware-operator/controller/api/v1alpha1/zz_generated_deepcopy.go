// Hand-written DeepCopy generated methods for the v1alpha1 types. controller-gen would produce
// these automatically (`make generate`), but we hand-write them so `go build` works without
// running a code generator -- the controller binary compiles from a fresh checkout with
// `go build ./...` and nothing else.

package v1alpha1

import (
	corev1 "k8s.io/api/core/v1"
	runtime "k8s.io/apimachinery/pkg/runtime"
)

// DeepCopyInto copies a RuntimeInstall into out.
func (in *RuntimeInstall) DeepCopyInto(out *RuntimeInstall) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ObjectMeta.DeepCopyInto(&out.ObjectMeta)
	in.Spec.DeepCopyInto(&out.Spec)
	in.Status.DeepCopyInto(&out.Status)
}

// DeepCopy returns a deep copy of a RuntimeInstall.
func (in *RuntimeInstall) DeepCopy() *RuntimeInstall {
	if in == nil {
		return nil
	}
	out := new(RuntimeInstall)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyObject returns a deep copy as runtime.Object.
func (in *RuntimeInstall) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}

// DeepCopyInto copies a RuntimeInstallList into out.
func (in *RuntimeInstallList) DeepCopyInto(out *RuntimeInstallList) {
	*out = *in
	out.TypeMeta = in.TypeMeta
	in.ListMeta.DeepCopyInto(&out.ListMeta)
	if in.Items != nil {
		out.Items = make([]RuntimeInstall, len(in.Items))
		for i := range in.Items {
			in.Items[i].DeepCopyInto(&out.Items[i])
		}
	}
}

// DeepCopy returns a deep copy of a RuntimeInstallList.
func (in *RuntimeInstallList) DeepCopy() *RuntimeInstallList {
	if in == nil {
		return nil
	}
	out := new(RuntimeInstallList)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyObject returns a deep copy as runtime.Object.
func (in *RuntimeInstallList) DeepCopyObject() runtime.Object {
	if c := in.DeepCopy(); c != nil {
		return c
	}
	return nil
}

// DeepCopyInto copies a RuntimeInstallSpec into out.
func (in *RuntimeInstallSpec) DeepCopyInto(out *RuntimeInstallSpec) {
	*out = *in
	in.Selector.DeepCopyInto(&out.Selector)
	if in.CanaryReplicas != nil {
		out.CanaryReplicas = new(int32)
		*out.CanaryReplicas = *in.CanaryReplicas
	}
	if in.PauseDuration != nil {
		out.PauseDuration = in.PauseDuration.DeepCopy()
	}
	in.Verification.DeepCopyInto(&out.Verification)
	if in.Rollback != nil {
		out.Rollback = new(RuntimeInstallRollback)
		(*in.Rollback).DeepCopyInto(out.Rollback)
	}
}

// DeepCopy returns a deep copy of a RuntimeInstallSpec.
func (in *RuntimeInstallSpec) DeepCopy() *RuntimeInstallSpec {
	if in == nil {
		return nil
	}
	out := new(RuntimeInstallSpec)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto copies a RuntimeInstallNodeSelector into out.
func (in *RuntimeInstallNodeSelector) DeepCopyInto(out *RuntimeInstallNodeSelector) {
	*out = *in
	in.NodeSelector.DeepCopyInto(&out.NodeSelector)
	if in.Tolerations != nil {
		out.Tolerations = make([]corev1.Toleration, len(in.Tolerations))
		for i := range in.Tolerations {
			in.Tolerations[i].DeepCopyInto(&out.Tolerations[i])
		}
	}
}

// DeepCopy returns a deep copy of a RuntimeInstallNodeSelector.
func (in *RuntimeInstallNodeSelector) DeepCopy() *RuntimeInstallNodeSelector {
	if in == nil {
		return nil
	}
	out := new(RuntimeInstallNodeSelector)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto copies a RuntimeInstallVerification into out.
func (in *RuntimeInstallVerification) DeepCopyInto(out *RuntimeInstallVerification) {
	*out = *in
	in.ProbePod.DeepCopyInto(&out.ProbePod)
	if in.TimeoutSeconds != nil {
		out.TimeoutSeconds = new(int32)
		*out.TimeoutSeconds = *in.TimeoutSeconds
	}
}

// DeepCopy returns a deep copy of a RuntimeInstallVerification.
func (in *RuntimeInstallVerification) DeepCopy() *RuntimeInstallVerification {
	if in == nil {
		return nil
	}
	out := new(RuntimeInstallVerification)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto copies a RuntimeInstallRollback into out.
func (in *RuntimeInstallRollback) DeepCopyInto(out *RuntimeInstallRollback) {
	*out = *in
	if in.Commands != nil {
		out.Commands = make([]string, len(in.Commands))
		copy(out.Commands, in.Commands)
	}
	if in.TimeoutSeconds != nil {
		out.TimeoutSeconds = new(int32)
		*out.TimeoutSeconds = *in.TimeoutSeconds
	}
}

// DeepCopy returns a deep copy of a RuntimeInstallRollback.
func (in *RuntimeInstallRollback) DeepCopy() *RuntimeInstallRollback {
	if in == nil {
		return nil
	}
	out := new(RuntimeInstallRollback)
	in.DeepCopyInto(out)
	return out
}

// DeepCopyInto copies a RuntimeInstallStatus into out.
func (in *RuntimeInstallStatus) DeepCopyInto(out *RuntimeInstallStatus) {
	*out = *in
	if in.CanaryResults != nil {
		out.CanaryResults = make([]CanaryResult, len(in.CanaryResults))
		copy(out.CanaryResults, in.CanaryResults)
	}
	if in.RolloutHistory != nil {
		out.RolloutHistory = make([]RolloutHistoryEntry, len(in.RolloutHistory))
		copy(out.RolloutHistory, in.RolloutHistory)
	}
}

// DeepCopy returns a deep copy of a RuntimeInstallStatus.
func (in *RuntimeInstallStatus) DeepCopy() *RuntimeInstallStatus {
	if in == nil {
		return nil
	}
	out := new(RuntimeInstallStatus)
	in.DeepCopyInto(out)
	return out
}
