Feature: placement is measured, published and read on the portal
  bin/idp-fits-a-node grades whether the workloads that run could be placed on the nodes that
  exist. Until now its answer reached a CI job and nowhere else: on 2026-09-12 the cluster sat at
  96% of CPU REQUESTS while using 39%/85% of ACTUAL CPU, the second catalogue replica was Pending,
  and the only place that fact existed was a job's stdout. A measurement nobody reads is not an
  instrument.
  # Bound by sovereign/tests/bdd/test_placement_published.py. The page logic is graded by
  # backstage/packages/app/src/modules/home/placement.test.ts (9 tests); this file grades the
  # publication, which is the half that was missing.

  Scenario: the cluster publishes its placement receipt
    Given the cluster-state job has run
    When it writes its receipt
    Then a placement document is written beside the other rendered state
    And it carries the placement section, the capacity figures and the time it was taken

  Scenario: the render carries the placement document forward
    Given a placement document is on the estate state
    When the render force-pushes that branch
    Then the placement document is staged with the other carried files

  Scenario: the portal reads it through the proxy it already has
    Given the placement document is published
    When the portal asks for it on the estate state proxy
    Then the answer is the same document, and no second endpoint was added

  Scenario: a cluster at its request ceiling is explained, never just reported
    Given the receipt says 10468m requested and 5379m used
    When the page summarises it, which placement.ts does
    Then the sentence names 5089m reserved but idle
    And it does not call the cluster full without saying why it can be idle and full at once
