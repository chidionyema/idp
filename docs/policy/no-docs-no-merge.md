# No docs, no merge

Founder blueprint, 2026-08-31 (captured verbatim by the founder-doc hook, id
`2026-08-31T0959Z-ou-are-completely-justified-in-being-tired-of-b276fe41`, in the claude-estate repository):
documentation is enforced at the git layer, never by scanning an agent's chat replies.

**The rule:** a pull request that changes code (any file outside `docs/` that is not Markdown) and
adds or updates nothing under `docs/` fails the fast gate with **Missing Architectural Record**.

**Exemptions, all printed loud in the job log:**
- Bot pull requests (`*[bot]` authors: image updates, dependency bumps).
- Pull requests opened before 2026-09-01 — warn only, so the gate never lands on work that
  branched before it existed (rule: a new gate is graded against the estate before it merges;
  every open pull request was graded on 2026-08-31 — humans' pull requests are grandfathered, bots exempt).
- A pull request body line `Docs-exempt: <reason>` — the escape valve a guard must have (the self-service-with-guardrails law); the
  reason is printed into the run log and is on the record.

**Where it runs:** the `no docs, no merge` step in `.github/workflows/fast-gate.yml`, which every
pipeline calls first. The same step, same wording, runs in the crew repository's `crew-qa.yml`.
