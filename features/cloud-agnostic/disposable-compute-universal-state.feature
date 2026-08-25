# Founder, 2026-08-25 (crew#250): "Rebuilding the same Oracle cluster faster is just automating
# our own lock-in." Sits beside features/estate-rebuild/rebuild-and-gates.feature (R35) and outranks it where they disagree. The platform must
# not know or care who owns the servers it runs on: GitOps-only hydration, abstracted secrets,
# S3-compatible and Postgres wire-protocol data only, provider-agnostic ingress.
Feature: Disposable compute, universal state
  The Kubernetes cluster is one ephemeral compute node. It can be destroyed, recreated on another
  provider, and heal itself from git and the vault. No application manifest names a cloud.

  Scenario: Bring-your-own-Kubernetes hydration
    Given a vanilla Kubernetes cluster from a different provider such as AWS EKS or local k3s
    When the GitOps controller is installed and pointed at the idp repository
    Then Backstage, Argo, MLflow, Medusa and all alerting are running within 15 minutes
    And no application manifest needed a code change

  Scenario: Cross-cloud secret portability
    Given a migration from Oracle Cloud to AWS
    When the ClusterSecretStore manifest is changed from the Oracle vault to AWS Secrets Manager
    Then every ExternalSecret reports SecretSynced with the same keys as before
    And the application pods restart and authenticate without knowing the vault changed

  Scenario: Stateless compute disaster recovery
    Given the complete, unrecoverable deletion of the primary Kubernetes cluster
    When compute is restored on a secondary provider
    Then research artifacts, traces and customer orders are available as before
    And no persistent state lived inside the cluster: only S3-compatible storage and external Postgres

  Scenario: Agnostic ingress routing
    Given a traffic switch from the current cluster to a cluster on another provider
    When the Cloudflare DNS target is changed to the new cluster's generic ingress address
    Then cert-manager issues certificates from Let's Encrypt without a manual step
    And API, Backstage and storefront traffic routes correctly with no provider-specific load balancer rules

  Scenario: No provider-specific service or annotation in the platform
    Given the audit command runs over every Kubernetes manifest and module in the repository
    When it counts provider-specific annotations, services and API groups outside the raw compute provisioner
    Then the count is zero
    And a pull request that adds one is refused in CI with the line that introduced it
