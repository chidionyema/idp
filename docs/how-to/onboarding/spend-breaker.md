# Onboarding: the spend circuit breaker and hourly digest

**What it is for.** It stops a runaway model bill. Every five minutes it reads the last hour
of spend from the model router's own database; past the limit it declares the breaker open,
holds that state for a cool-off, and counts consecutive trips, so a spike is caught within
five minutes instead of at the end of the month. A second job writes an hourly spend digest.

**What it costs.** Two CronJobs in the `llm` namespace. Both carry explicit CPU and memory
requests and limits; the check pod is 50m CPU / 64Mi at rest. No new database — it reads the
router's existing Postgres.

**Where it lives.** `platform/llm/spend-breaker-digest.yaml` in the platform repository,
reconciled like every other platform layer. The limit and cool-off are configuration:
`SPEND_VELOCITY_MAX_DOLLARS` (default 10.0) and `SPEND_VELOCITY_COOLDOWN_SECONDS`
(default 1800).

**Honest gap.** The hourly digest prints to the job log; it is not yet delivered to the
founder's phone. That wiring goes through the estate's one alert gateway, not a second path.

**How to stop it.** `kubectl -n llm patch cronjob spend-velocity-check -p '{"spec":{"suspend":true}}'`
and the same for `spend-digest`; or remove the file from the platform kustomization.
