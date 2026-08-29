# The Verification Plane

Owner: @chidionyema. Board: crew#631.

## What it guarantees

A work item cannot be called done without a fresh, signed verdict about the exact artifact that
was running, produced by a process the agent cannot run. It removes self-certification. It does
not remove error.

## Three planes

- Actor plane: agents. They read and edit code and open pull requests. They hold no probe
  credential and no signing key.
- Verification plane: the prover, `.github/workflows/verdict-langfuse.yml`, running on the estate's
  machine identity. It runs `bin/idp-prove`, which loads the probes in `probes/`, reads the running
  image from the cluster, and writes one signed verdict.
- Control plane: the check-run `verify/langfuse` on each commit, and later the ticket state machine.
  It reads verdicts only.

## The verdict record

`probes/verdict.py`. Fields: the check, the target, the commit, the image digest that was running,
the release revision, a one-time nonce, start and end times, a time to live, the outcome, the list
of assertions, an evidence link, the prover, and the signature. `bin/idp-verdict verify FILE` grades
a file the way a gate does: unsigned, expired, or about another digest reads as UNVERIFIED.

## Probe levels for Langfuse

`probes/langfuse.py`. L1: the health endpoint answers, database included. L2: the public API
answers the project key, and refuses a call with no key. L3: a cold browser sign-in through the
front door (the existing `bin/idp-login-drill`) yields a session whose email is the drill user,
and a browser holding nothing gets no user. Every level with an auth claim carries its negative
control. No screen layout is graded.

## Using it

- `gh workflow run verdict-langfuse.yml` then read the run summary, or download the artifact and
  run `bin/idp-verdict show verdict.json`.
- The signing key is `verdict-hmac-key` in the vault, minted by `platform/oci/identity/main.tf`
  on the next `oke-check` apply. Until it exists the prover prints UNSIGNED and exits 2.

## Not done yet

CP2 scopes the key to the runner identity only. CP3 stores verdicts in Postgres, append-only.
CP5 and CP6 make the check required and move tickets on verdicts. CP8 runs each probe against a
broken target weekly.
