# 2026-11-07: No symptom workarounds

## Status

Accepted by founder instruction on 2026-11-07. Estate-wide.

## Context

Repeated deliveries turned observable failures into apparent progress: a timeout counted as an
expected browser exit, an offline cloud page was called operational, a static HTTP 200 stood in for
rendering the user path, and Mac-local fallbacks were repaired after the cloud replacement failed.
Those decisions hid the defect, consumed more agent time and returned the estate to the same state.

## Decision

1. A timeout, exit `124`, empty observation, `UNKNOWN`, `BLIND`, `offline`, missing capability or
   absent receipt is a failure.
2. Retries, sleeps, deadline extensions and expected-timeout branches are not proof. They may be
   observability or resilience features only after the deterministic defect is fixed.
3. A cloud deployment gate renders the real founder path in a browser, waits for named visible
   content, rejects cloud screens that depend on the Mac, and exits normally.
4. A finite cloud projection uses a finite snapshot. It does not open an endless live stream.
5. A Mac-local fallback is never described as cloud completion.
6. Architecture, failure modes, test mechanism and completion proof are defined before the build.
7. A future plan cannot replace a fix available in the current change.

## Consequences

- Some deployments remain red until the underlying mechanism is fixed.
- Browser proof is required for founder-facing surfaces.
- Static projections must identify themselves and expose finite APIs.
- Agents spend less time rediscovering workarounds because the rule is executable policy, not lore.

## Proof

- `AGENTS.md` section 3 carries the zero-tolerance rule.
- The Cloudflare founder-surface workflow uses Playwright to require a normal browser exit,
  visible module content, no page errors, no same-origin HTTP failures and no Mac-dependent copy.
