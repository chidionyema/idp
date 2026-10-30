"""NSVEE -- the Neuro-Symbolic Verifiable Execution Engine.

Two entry points, one engine:

  * `NSVEE.run(prompt)` -- the pipeline: formalize, generate, verify, feed back.
  * `nsvee.verify(artifact, tests)` -- the gate alone: verify an artifact that NSVEE did
    not write, with no model in the loop. This is the door every estate runtime uses
    (idp#7263, I-D); `platform/estate/intents/nsvee.verify.yaml` is its name in the
    estate's catalogue.

`verify` is exported here so the door never has to know where in the package it lives.
"""

from .engine import NSVEE, VerificationReport, Verdict, verify

__all__ = ["NSVEE", "VerificationReport", "Verdict", "verify"]
