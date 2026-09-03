# The otto door is a standing query, not a question to a person

On 2026-09-03 the founder asked whether the new Otto was operational, and the only offered
proof was "send the bot a message". He rejected that, correctly: a live surface must be
measured by the platform, and the answer must be readable without a human probing anything.

This page records the first step of that proof plane, and why it is shaped this way.

## What was blind, and what now watches

Two existing instruments should have covered the door at `otto.<zone>` and did not:

- **The catalogue.** The `layer-otto-golden` entity carried no link with its own hostname's
  url, so `bin/idp-catalogue-drift` failed on every cluster check with "1 unregistered of 12
  live hostnames". The fix is one `links:` entry on the entity — the drift check reads
  hostnames straight out of catalogue urls, so registering a hostname IS adding its link.
- **The blackbox probe.** `platform/monitoring/rules/founder-surfaces-probe.yaml` never
  listed the door, so `FounderSurfaceDown` could not fire when it died. One target line —
  `https://otto.<zone>/healthz` — puts the door on the same sixty-second watch as every
  other founder surface, alerting through the existing roads (Telegram alert channel,
  robusta), never a new sink.

Both additions watch **our hostname**, not any chat vendor. Under the founder's event-gateway
directive (crew branch `spec/otto-gateway-tenancy`), channel-specific proof — webhook
registration with the vendor, a canary tenant round-trip — belongs to the Universal Event
Gateway's namespace and lands with it; this page's two lines are the channel-agnostic floor
under all of it.

## How to read the answer

- `bin/idp-catalogue-drift` — "ok ... 0 unregistered" once this change is live.
- The `FounderSurfaceDown` alert, or the founder-surfaces Grafana/SigNoz view, for the door's
  minute-by-minute state. A dead door alerts; nobody has to notice.
