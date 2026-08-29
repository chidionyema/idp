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

## CP6: the freshness gate

`verify/verdict-fresh` is a required check on main. On a pull request it runs
`bin/idp-verdict-fresh langfuse --changed <files>`: when no changed file is on
`platform/observability/langfuse*` it passes and says so; otherwise it reads the newest completed
`verdict-langfuse.yml` run on main, downloads its `verdict-langfuse` artifact and grades the
record with `probes.verdict.grade` (no key on this runner: the signature is not recomputed, but an
unsigned, expired, FAIL or digest-less record is refused). Trust rests on GitHub's attestation of
the run: only that workflow holds the key and only it can create the `verify/langfuse` check-run.
The gate cannot be satisfied by an agent: there is no path to a fresh PASS but a Langfuse that
answers L1, L2 and L3 now. How-to: `docs/how-to/merge-a-langfuse-change.md`.

## CP5: the ticket state machine

Three labels on the board: `RESOLVED_PENDING_VERIFICATION`, `VERIFIED`, `REJECTED`. An agent may
set only the first. `ticket-verification.yml` runs after every prover run and hourly, as the
estate's GitHub App (lane `ticket-verifier`), and is the only thing that sets the other two: a
fresh PASS verdict completed after the label verifies, a FAIL rejects. A `VERIFIED` set by anyone
else, or one with no PASS younger than 24 hours behind it, goes back to pending with a comment.
The decision is one pure function, `decide`, in `bin/idp-ticket-verify`, graded in
`tests/test_incident_crew631_cp5_ticket_state_machine.py`. How-to:
`docs/how-to/get-a-ticket-verified.md`.
## CP7: the L4 journey

L2 proves the API answers a key; L4 proves data flows. The prover emits one OTLP span through
`POST /api/public/otel/v1/traces` (vendor: Basic auth public:secret key, HTTP/JSON) with a fresh
32-hex trace id per run, then polls `GET /api/public/traces/{id}` for up to 60 s. The assertion
is `l4.journey.returned_id_equals_emitted_id`; the ingest 2xx is recorded but never sufficient,
because an accepted span that never lands is silent green. Negative control: the same span with
no key must be refused. `probes/langfuse.py` `l4_journey`, graded in
`tests/test_incident_crew631_cp7_l4_trace_journey.py` against a door that accepts-and-drops.

## Not done yet

CP2 scopes the key to the runner identity only. CP3 stores verdicts in Postgres, append-only.
CP5 and CP6 make the check required and move tickets on verdicts. CP8 runs each probe against a
broken target weekly.

## Who can read the signing key (CP2)

Only the prover. `estate-ci` sits in `estate-provers`, whose one grant is a read on
`verdict-hmac-key`. The operators' and the worker nodes' secret grants exclude that name, so an agent
on a laptop or in a pod cannot mint a signature. How the grants land and the one founder step:
`docs/how-to/scope-the-verdict-key-to-the-prover.md`.
