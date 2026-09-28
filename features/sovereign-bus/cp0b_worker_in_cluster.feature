# crew#396 step 2: with the engine in the cluster (cp0), the worker that serves its task queue
# must be there too, or "close the laptop" still stops every workflow at the first activity.
Feature: The sovereign worker runs in the cluster next to the engine
  # Bound by sovereign/tests/bdd/test_cp0b_worker_in_cluster.py

  Scenario: The worker image is on the estate's one image list
    Given bin/dockerfiles
    Then it lists sovereign-worker built from sovereign-worker.Dockerfile
    And the Dockerfile runs python -m sovereign.engine.worker as a non-root user

  Scenario: The worker Deployment polls the in-cluster frontend and rolls on every main build
    When platform/temporal is built with kustomize
    Then a Deployment sovereign-worker points TEMPORAL_HOST at the chart's frontend Service
    And its image is ghcr.io/chidionyema/sovereign-worker on a tag the image policy rewrites
    And every probe tests the ready file the worker writes only while polling
    And the namespace mirrors ghcr-pull through the ghcr-pull ClusterSecretStore

  Scenario: The worker reports ready only while it is polling
    Given a worker connected to a fake frontend
    Then worker.ready appears after the Worker starts and is gone after it stops
