@label=@gates
@spec:docs/specs/2026-09-22-cryptographic-ci-gateway.md
Feature: Cryptographic CI Gateway and Zero-Trust Agent Enforcement
  To eradicate agent-induced outages and 954-branch CI queues
  As the enterprise governance system
  I want CI to act as a strict cryptographic gateway that physically rejects unproven agent mutations

  Rule: Agents cannot bypass the verifier

    Scenario: An AI agent submits a Pull Request
      Given the PR author is "estate-agent-007"
      When the CI pipeline triggers
      Then the "verifier" job MUST run
      And the bot exemption is ignored

  Rule: The verifier must fail closed (BLIND = FAIL)

    Scenario: The verifier tooling is unavailable or crashes
      Given the verifier job initiates
      And the "bin/idp-ci-verify" script exits with code 2
      When the job processes the exit code
      Then the job MUST fail the CI pipeline
      And the status check must be reported as "failure"

  Rule: Cryptographic attestations bypass heavy CI for humans, but are strictly required for agents

    Scenario: An agent submits a pre-verified, cryptographically sealed patch
      Given an agent PR contains a valid "sigstore-bundle"
      And the bundle's signature matches the local daemon's public key
      And the bundle's signed subject matches the PR's HEAD
      When the verifier job runs
      Then the pipeline verifies the signature without running structural or symbolic execution
      And the verifier job exits 0
      And the PR is cleared for the merge gate

    Scenario: An agent submits an unsealed patch (Hallucination/Bypass attempt)
      Given an agent PR lacks a "sigstore-bundle"
      When the verifier job runs
      Then the pipeline MUST instantly reject the PR with exit 1
      And the heavy "fast-gate" and "bdd-suites" jobs MUST NOT run

    Scenario: A human submits an unsealed patch
      Given a human PR lacks a "sigstore-bundle"
      When the verifier job runs
      Then the pipeline falls back to executing "bin/idp-ci-verify"
      And computes the structural, symbolic, and execution stages in CI
