# Recovering the old dashboards after the swap

## What happened

Decision 0018 swapped the dashboard tool: Metabase came out by the roots and Superset
took its place behind the gateway. The swap moved no content — the two tools store
dashboards in different shapes, and no export ran before the old server was deleted.
That is why the new dashboard page opened empty.

## What survived

The old server's 50Gi data volume, `pgdata-metabase-db-0`, was never deleted. It still
holds every saved question (name and query), every chart and every dashboard layout the
founder built. Nothing has served that data since the swap, and nothing has touched it.

## What this change does

A one-shot job, `metabase-recovery-dump`, starts the same database engine the old
server ran — same image, same user id, same data path — against that surviving volume.
It runs read queries only and prints the saved content as JSON to its log:
collections, questions with their queries, dashboards, and the layout rows that place
each chart. The log is the receipt; it lands in the central collector and the finished
pod keeps it readable for a week.

The job changes nothing on the volume. It retries never (`backoffLimit: 0`), dies after
ten minutes if stuck, and a failed query fails the whole job loudly rather than reading
green.

## What happens next

With the dump in hand, the content is rebuilt in Superset through its own interface:
each saved query becomes a dataset and chart, each dashboard a Superset dashboard. The
rebuild is a translation — charts return with their query and layout, not as
pixel-identical copies of the old visuals. The old volume stays untouched until the
founder says the rebuild is confirmed and the volume can go.
