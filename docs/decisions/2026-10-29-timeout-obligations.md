# Keep timeout obligations inside the existing incident and approval planes

Decision: extend the incident loop and executor, with state streamed to Fleet and Face.
A timeout means an optimisation obligation, and cannot become success by waiting, retrying
or closing its issue. The founder's working surfaces are remote founder surfaces.

Alternatives rejected: a second timeout incident store (duplicate state), desktop dialogs
as the approval route (the founder does not operate the MacBook), and refusing every tool
globally (this prevents diagnosis and repair). Preserve the existing caller deadlines while
measuring their suitability; do not increase a number to hide a failure.

Cost: persistent obligations require explicit verified closure and UI delivery evidence.
Bulk graph parsing also trades temporary memory for fewer decoder invocations. Deadline,
memory and caller evidence must be measured in the real execution context.

Revisit if the existing incident or approval plane cannot carry a scoped, replay-protected
decision through Fleet/Face. Repair that plane rather than introducing an independent one.
See docs/specs/2026-10-29-timeout-optimisation.md. Claim: chidionyema/idp#7457.
