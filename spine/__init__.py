"""The event spine: the environment emits facts, an agent responds.

Four pieces, and the seams between them are the whole design:

    Flux (the environment)  ->  NATS JetStream (the fabric)  ->  the bridge (the only
    component that knows both)  ->  Temporal (the agent's clock)  ->  a receipt.

The bridge is the only component that knows both NATS and Temporal. Every Flux controller
speaks NATS; every agent speaks Temporal; neither leaks into the other's domain. That rule
is what keeps the seam countable: one place knows both, so the place can be tested, and
everywhere else can be replaced without touching the other.

The estate already owns the fabric (platform/event-bus: NATS with JetStream, file store) and
the clock (platform/temporal, and the sovereign SessionWorkflow that owns agent sessions).
What is new here is the wiring between them and the workflow that answers a reconcile event
by reading the reconciliation's own status.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
