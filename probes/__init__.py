"""Probe definitions for the Verification Plane (crew#631).

A probe is code the prover runs against a live target and turns into assertions: {name, expected,
actual, ok}. Probes live here, apart from bin/, because the agent token cannot write here in the
control repository and the prover loads them at the commit under test. An agent that wants green
fixes the target, not the probe.
"""
