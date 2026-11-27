<!-- estate:routed-from AGENTS.md -- current law, not history. It is loaded on demand through the AGENTS.md route table instead of at Turn 1 (idp#8636). Moved verbatim. -->

<!-- ESTATE_CAPABILITY_ADVERTISING_START -->
## Capability advertising is operating law

Advertise the right next action where agents choose tools and procedures. Put the
outcome and first safe step first, together with the current owner, runtime,
authorization, prerequisite, proof of success, and fallback. Use the existing
capability registry, context compiler, and execution gateway. Match the language
people actually use for the task, and let the approved route answer old names.

Publish current and verified routes prominently. Label declared or unverified
routes as such. Retire a route by withdrawing its active advertisement, refusing
the obsolete action at its entry point, and pointing the old source to its
successor. Preserve history as evidence. Put `<!-- estate:historical current=PATH -->`
on the first line of retired Markdown so the context compiler withholds obsolete
excerpts even when retrieval ranks them first. Use a repository-relative PATH to
the current authority. A search result or advertisement does not grant authority.

Follow the evidence when agents repeat a wrong turn. Record the observed failure
class and fix the prompt, discovery result, default, or execution boundary that
led there. Verify the correction by replaying the same lure and observing the
selected action. Preserve the evidence under KARMA and test recurrence across
harnesses before claiming fleet-wide improvement.
<!-- ESTATE_CAPABILITY_ADVERTISING_END -->

### Infrastructure incident first step

For a service outage, run `bin/idp-estate-homes --no-file --service SERVICE`
for `llm-router`, `otto`, or `estate-doors`. It probes the published endpoints
without updating the issue tracker. Read the matching incident and confirm
where the service runs before choosing a repair. A successful probe verifies
the endpoint behavior it measured. If no current runtime can be verified,
record the missing observation and continue read-only inventory.

