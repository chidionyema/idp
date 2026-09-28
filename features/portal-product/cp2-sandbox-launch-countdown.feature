@cp2
Feature: a person launches the buyer sandbox from the showcase page, and watches it expire
  docs/specs/backstage-as-a-product.md CP2. docs/runbooks/demo-sandbox.md documents the launch as
  a command a person types by hand; this checkpoint is that same command behind one button, and
  the countdown the platform's own TTL policy already enforces, shown rather than typed about.
  "Agents never deploy" is unchanged: the button still waits for a person to press it.

  Scenario: the launch button dispatches the documented command, unchanged
    Given the demo-sandbox-launch workflow is the button's target
    When the workflow runs
    Then it runs the same flux create kustomization command docs/runbooks/demo-sandbox.md names
    And it names no host, region or account as a literal in the workflow file

  Scenario: the countdown reflects the Kustomization's own TTL label
    Given a demo-sandbox Kustomization exists with a cleanup.kyverno.io/ttl label and a creation timestamp
    When the showcase page reads it through the Kubernetes proxy
    Then the time remaining shown equals the label's duration minus time since creation
    And the value refreshes without a page reload

  Scenario: after expiry the showcase page shows the sandbox is gone, not stale
    Given the demo-sandbox Kustomization has been deleted by the cleanup controller
    When the showcase page next reads cluster state
    Then it shows no countdown and offers the launch button again

  Scenario: no new agent capability is created
    Given the estate's capability declarations in AGENTS.md
    When this checkpoint ships
    Then no agent capability list gains a sandbox-create or sandbox-delete action
