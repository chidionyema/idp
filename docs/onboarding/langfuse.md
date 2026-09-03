# Langfuse — watching what the agents actually do

## What it is for

Six agent sessions run on this estate and none of them can see each other. When
one of them burns tokens on a loop, takes a wrong turn, or quietly fails, the
only record is a transcript nobody reads. Langfuse turns that into something
searchable: every agent run becomes a trace, with what it was asked, what it
called, how long it took and what it cost.

The second reason is LAW 30. A run that teaches something and leaves no
queryable trace has taught nobody. This is where the trace goes.

## What it costs

**£0 / $0.** Langfuse's core is MIT licensed and the self-hosted build has no
feature caps, no seat limits and no trial clock. The paid self-hosted tier adds
only enterprise administration — RBAC, audit logs, data masking, SCIM, retention
policies. None of that matters for one founder.

The real cost is memory, not money. Seven containers, ceilings totalling
**3.63 GiB**, measured against roughly 6.1 GiB of Docker headroom on this
laptop. Upstream recommends a 16 GiB VM; that number sizes for production ingest
volume and this estate sends a few thousand spans a day, so every container is
capped in `observability/langfuse.yml` and ClickHouse is given
`observability/clickhouse-low-memory.xml` so it backs off instead of being
OOM-killed.

## What it watches, and what it does not

It receives **OpenTelemetry traces over OTLP**, from anything that can send
them. It is not tied to a model provider, which is the point given LAW 34 — if
Anthropic disappeared tomorrow, the traces from whatever replaced it land in the
same place, unchanged.

It does **not** watch the machine, the containers or the network. That is
Healthchecks' job. This watches agent behaviour only.

## Where it lives

```
observability/langfuse.yml              the stack
observability/clickhouse-low-memory.xml the ceiling that keeps it on a laptop
observability/otel-fallback.yaml        the fallback receiver
observability/.env                      every secret, chmod 600, gitignored
bin/langfuse-up                         start (safe to re-run)
bin/langfuse-down                       stop, keeping data
bin/langfuse-status                     what is receiving, and what has landed
bin/langfuse-verify                     proof: a span sent in comes back out
bin/langfuse-password                   UI password to clipboard, never printed
```

Only `127.0.0.1:3200` is published. Postgres, Redis, ClickHouse, MinIO and the
worker stay inside the Docker network — upstream publishes all of them on the
host and none of it is needed (LAW 21, default closed).

## The fallback

There is never one of anything here.

| | receiver | endpoint | shares runtime with the other? |
|---|---|---|---|
| primary | Langfuse | `http://127.0.0.1:3200/api/public/otel` | — |
| fallback | OTel Collector | `http://127.0.0.1:4318` | no |

The fallback is a single Go binary writing JSONL to a volume. It has never heard
of node, ClickHouse or Postgres, so nothing that breaks Langfuse can break it,
and it is **already running** — switching is changing one environment variable,
not starting a service and hoping:

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
```

`bin/langfuse-verify` sends a real span to both and reads it back from both, so
the fallback is drilled rather than assumed (LAW 19).

## How to turn it off

```
bin/langfuse-down
```

Containers stop, every trace survives, `bin/langfuse-up` brings it all back.

To delete the data as well — this cannot be undone:

```
bin/langfuse-down --purge
```

## How to turn it back on

```
bin/langfuse-up
```

Safe to run repeatedly. It never regenerates existing secrets.

## Signing in

```
bin/langfuse-password
```

Puts the password on the clipboard and prints only the email address. The
password is never displayed, logged or screenshotted (LAW 21). Langfuse creates
the org, project, user and API key pair on first boot from `LANGFUSE_INIT_*`, so
there is no sign-up wizard and no key to copy out of a browser.

## What goes wrong

**Containers get OOM-killed and it looks like a crash.** The ceilings total
3.63 GiB. If Docker Desktop has less free, `bin/langfuse-up` warns before
starting. Check with `docker stats`; either stop something else or raise
Docker's memory allocation.

**`ENCRYPTION_KEY` must never be regenerated.** Once traces exist, rotating it
makes every stored API key undecryptable. `bin/langfuse-up` therefore never
overwrites an existing `observability/.env`. If that file is lost, the data is
effectively lost with it — back it up alongside other credentials.

**Langfuse answers 200 while dropping everything.** If the worker cannot reach
ClickHouse, `/api/public/health` still returns 200 and the dashboard renders
fine and empty. That is why `bin/langfuse-verify` exists and why "is port 3200
up" is not the check. Run `docker logs --tail 40 langfuse-worker`.

**First boot takes a few minutes.** ClickHouse migrations run before the web
container reports healthy. `bin/langfuse-up` waits up to 10 minutes.

**Media uploads do not work.** MinIO is not published on the host, so Langfuse
cannot hand a browser a presigned URL for multimodal content. Traces, spans,
scores and costs are unaffected. Publishing MinIO would fix it and open another
door; it has not been worth it.
