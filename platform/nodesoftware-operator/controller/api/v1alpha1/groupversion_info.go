// Package v1alpha1 contains the API Schema definitions for the nodesoftware.estate.io v1alpha1 API
// group. The Go types here mirror platform/nodesoftware-operator/crds/runtimeinstall.yaml
// (PR #2338 on feat/nodesoftware-operator). Drift between this file and that YAML is the
// "the gate admits a CR but the controller cannot parse it" class of incident; the contract test
// in internal/controller/crd_contract_test.go catches it once the CRD YAML lands on origin/main.
//
// The source of truth for the schema is the CRD YAML (the gate grades it offline, and the cluster
// admission webhooks it after C2 lands). The Go types here are the controller's read/write
// representation; every field on RuntimeInstallSpec has a 1:1 mapping to spec.<field> in the CR.
package v1alpha1

import (
	"k8s.io/apimachinery/pkg/runtime/schema"
	"sigs.k8s.io/controller-runtime/pkg/scheme"
)

// GroupVersion is group version used to register these objects.
var GroupVersion = schema.GroupVersion{Group: "nodesoftware.estate.io", Version: "v1alpha1"}

// SchemeBuilder collects every GroupVersion-kinded object this package exposes.
var SchemeBuilder = &scheme.Builder{GroupVersion: GroupVersion}

// AddToScheme registers the RuntimeInstall and RuntimeInstallList kinds with the runtime scheme.
var AddToScheme = SchemeBuilder.AddToScheme

func init() {
	SchemeBuilder.Register(&RuntimeInstall{}, &RuntimeInstallList{})
}
