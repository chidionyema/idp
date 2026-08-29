# Get a ticket verified

An agent does not close a ticket. It says the work is done and the prover decides
(crew#631 CP5).

1. Put the surface in the ticket body, one line: `Verify: langfuse`. The word is the
   `verdict-<surface>.yml` workflow in idp that proves that surface.
2. When the work is merged and deployed, add the label `RESOLVED_PENDING_VERIFICATION`.
3. Wait for the next prover run (hourly at :37, or `gh workflow run verdict-langfuse.yml`).
   `ticket-verification.yml` runs after it. A PASS verdict completed after the label moves the
   ticket to `VERIFIED`; a FAIL moves it to `REJECTED`; each move is a comment naming the run.

Rules the workflow enforces:

- `VERIFIED` or `REJECTED` set by anyone but the estate's App (`estate-agents[bot]`) is reverted
  to `RESOLVED_PENDING_VERIFICATION` with a comment. An agent cannot mark its own work verified.
- `VERIFIED` with no PASS verdict younger than 24 hours on its surface is reverted.
- A ticket with no `Verify:` line is told once and left alone.

Report without moving anything: `bin/idp-ticket-verify` (as any token that can read the board);
`--apply` moves labels and is what the workflow runs.
