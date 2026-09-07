// Package runsc is the gVisor runsc runtime handler. The handler image ships:
//   - /usr/local/bin/nodesoftware-runsc-install   (writes /etc/crio/crio.conf.d/99-gvisor.conf
//     and reloads cri-o.service)
//   - /usr/local/bin/nodesoftware-runsc-uninstall (removes the drop-in, reloads)
//   - /usr/local/bin/nodesoftware-runsc-probe     (prints the running kernel name; the
//     controller's successCondition parses stdout
//     for "[0-9.]+-gvisor-[0-9]+" -- the gVisor
//     kernel suffix that proves the install worked
//     inside the pod sandbox)
//
// The handler pod is short-lived, hostPath-mounted at /host, runs as root, and exits. The
// reconciler waits for the pod to terminate, then runs the probe pod. The handler does NOT
// touch the k8s API; all control flow is in the reconciler.
//
// Why runsc ships first: the CRD's closed set is runsc/kata/nvidia, but only runsc has a real
// handler today. kata + nvidia have stub Handler implementations that return ErrNotImplemented.
// When the kata/nvidia handlers land, the registry wiring in cmd/main.go is updated.
package runsc

import (
	"context"
	"fmt"
	"strings"

	"github.com/chidionyema/idp/platform/nodesoftware-operator/controller/internal/handler"
)

// Handler is the runsc handler implementation.
type Handler struct {
	// InstallImage is the handler image (carries the install/uninstall/probe scripts). Pinned
	// by digest in production. The chart substitutes IMAGE_TAG at deploy time.
	InstallImage string

	// HostRoot is the hostPath the handler pod mounts to access the target node's filesystem.
	// /host is the convention; the chart overrides it per cluster if needed.
	HostRoot string
}

// New constructs a runsc Handler with sensible defaults.
func New(installImage, hostRoot string) *Handler {
	if installImage == "" {
		installImage = "ghcr.io/chidionyema/nodesoftware-runsc-handler:IMAGE_TAG"
	}
	if hostRoot == "" {
		hostRoot = "/host"
	}
	return &Handler{InstallImage: installImage, HostRoot: hostRoot}
}

// Runtime returns "runsc".
func (h *Handler) Runtime() string { return "runsc" }

// Install returns the Step to install runsc on the target node. The shell command is a single
// invocation of the install script; the handler pod is privileged and hostPath-mounted.
func (h *Handler) Install(_ context.Context, targetNode, version string) (*handler.Step, error) {
	if !validVersion(version) {
		return nil, fmt.Errorf("runsc: refusing version %q (must match %s)", version, versionPattern)
	}
	return &handler.Step{
		Image:          h.InstallImage,
		Command:        []string{"/usr/local/bin/nodesoftware-runsc-install", version, h.HostRoot},
		TimeoutSeconds: 300,
	}, nil
}

// Uninstall returns the Step to roll back the install. Same image; different script.
func (h *Handler) Uninstall(_ context.Context, targetNode, version string) (*handler.Step, error) {
	if !validVersion(version) {
		return nil, fmt.Errorf("runsc: refusing version %q (must match %s)", version, versionPattern)
	}
	return &handler.Step{
		Image:          h.InstallImage,
		Command:        []string{"/usr/local/bin/nodesoftware-runsc-uninstall", version, h.HostRoot},
		TimeoutSeconds: 180,
	}, nil
}

// ProbeCommand returns the shell command the verification probe runs. The probe runs INSIDE
// a daily-driver runsc sandbox on the target node (runtimeClassName=runsc), so `uname -r` shows
// the gVisor kernel suffix when the install worked. The successCondition on the CR is the
// grep pattern the controller evaluates against the probe's stdout.
func (h *Handler) ProbeCommand(context.Context, string, string) ([]string, error) {
	return []string{"/usr/local/bin/nodesoftware-runsc-probe"}, nil
}

// versionPattern is the allowed-shape regex for runsc versions. vMAJOR.MINOR.PATCH where each
// component is 1-3 digits. Anything else is rejected so a CR cannot smuggle shell metachars.
const versionPattern = `^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$`

func validVersion(v string) bool {
	if v == "" {
		return false
	}
	// Quick reject for shell metachars before the regex.
	for _, ch := range v {
		if ch == ';' || ch == '|' || ch == '&' || ch == '$' || ch == '`' || ch == '\n' {
			return false
		}
	}
	// Use simple parsing instead of regexp to keep the handler dependency-free.
	parts := strings.Split(v, ".")
	if len(parts) != 3 {
		return false
	}
	for _, p := range parts {
		if p == "" {
			return false
		}
		for _, ch := range p {
			if ch < '0' || ch > '9' {
				return false
			}
		}
	}
	return true
}
