# Demo: langfuse-up / langfuse-down / langfuse-status / langfuse-verify / langfuse-password

`bin/langfuse-status` shows both receivers, memory in use, and what has landed.
Run against this estate's running stack:

```
$ bin/langfuse-status
RECEIVER   LOCAL                          HTTP   ENDPOINT FOR OTEL_EXPORTER_OTLP_ENDPOINT
primary    127.0.0.1:3200 langfuse        200    http://127.0.0.1:3200/api/public/otel
fallback   127.0.0.1:4318 otel-col        200    http://127.0.0.1:4318

CONTAINERS
langfuse-clickhouse               580.2MiB / 1.172GiB     78.26%
langfuse-web                      742.2MiB / 1.5GiB       7.38%
langfuse-worker                   462.8MiB / 768MiB       6.95%
  ---
  total 2001MiB in use against 3717MiB of ceilings

UI        http://127.0.0.1:3200/    (password: bin/langfuse-password)
```

Both receivers down at once is the only failure this reports as a code: `HTTP`
reads `down` for both rows and the command still exits 0, because a status
check that returns non-zero on "one receiver is intentionally down" cannot be
used as an ordinary check — `bin/langfuse-verify` is what proves ingestion
actually works, not this.

`bin/langfuse-up` starts the stack: it validates
`observability/clickhouse-low-memory.xml` as XML before starting anything
(a double-hyphen inside a comment once crash-looped ClickHouse silently), then
generates `observability/.env` on first run only — it never overwrites an
existing one, because rotating `ENCRYPTION_KEY` after traces exist makes every
stored API key undecryptable. `bin/langfuse-down` stops the containers and
keeps every trace; `bin/langfuse-down --purge` deletes the trace data as well,
after a five-second window to cancel. `bin/langfuse-password` puts the UI
password on the clipboard and prints only the sign-in email, never the
password itself (LAW 21).

`bin/langfuse-verify` is the actual proof of "is this observing": it sends a
real span through the OTLP endpoint and reads it back out of the API, for both
the primary and the fallback receiver, because Langfuse can answer 200 on
`/api/public/health` while its worker cannot write to ClickHouse and every
span sent to it is silently dropped. Full detail in
`docs/onboarding/langfuse.md`.
