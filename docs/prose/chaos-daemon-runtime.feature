# Prose until a drill runs it: both scenarios need the live OKE node and the daemon pod (crew#297).
# Incident 2026-08-26 (crew#268 lane, found while working crew#282): chaos-daemon on OKE was
# CrashLoopBackOff with 24 restarts. The chart value said runtime containerd; the node reports
# cri-o://1.35.2. A chaos daemon that cannot reach the container runtime injects nothing, and the
# Schedule that depends on it reads healthy because the controller-manager is up.
Feature: The chaos daemon speaks the container runtime the node actually runs
  Scenario: The daemon's runtime matches the node's containerRuntimeVersion
    Given the OKE node reports containerRuntimeVersion cri-o
    And platform/chaos/mesh/helmrelease.yaml sets chaosDaemon.runtime crio and socketPath /var/run/crio/crio.sock
    When Flux reconciles the chaos-mesh HelmRelease
    Then the chaos-daemon pod is Running with 0 restarts after 10 minutes
    And `kubectl -n chaos-mesh logs ds/chaos-daemon` carries no "failed to dial" line

  Scenario: A runtime value that names a socket the node does not have is a red row, not a quiet one
    Given a chaosDaemon.runtime of containerd on a cri-o node
    When the daemon starts
    Then it exits with "failed to dial /host-run/containerd.sock" and bin/idp-verify's chaos row reads CrashLoopBackOff
