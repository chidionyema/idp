# Demo: every backup, with its timestamp, on the Ops page

Founder, 2026-08-30: "when you are finished, I would like to see all of our backups are in
backoffice with timestamp".

Before this, the only way to know what was backed up was to run the offsite grader on the
founder's Mac by hand. Run that way on 2026-08-30 at 10:25Z it said the money database's newest
copy was 31.6 hours old against a declared 24-hour interval, and nothing on any page said so,
because the Mac's launchd backup jobs were not loaded. The backup bucket is the backend of record,
so the page now reads it (LAW 50: coverage is proved by querying the backend).

## The command

    cd ~/dev/code/idp && bin/estate-backups --listing listing.json --out docs/backups.json

where `listing.json` is `rclone lsjson :s3:<bucket> --recursive`. On the render schedule the
`catalog-render` workflow makes that listing itself and passes it in; nobody runs this by hand.

## What it prints

```
ok    estate-backups: 4 source(s) in prospector-backup, 2 older than 30h -> docs/backups.json
      engine-db              newest 2026-08-23T00:00:00Z    178.5h  copies 1
      money-db               newest 2026-08-29T02:50:19Z     31.7h  copies 2
      agent-estate           newest 2026-08-29T02:53:26Z     31.6h  copies 1
      engine-repo            newest 2026-08-30T02:41:07Z      7.8h  copies 1
```

That is the fixture in `tests/test_estate_backups.py`; the live run's numbers are in the
workflow's step summary and on the tile.

## What the founder sees

Portal, sidebar **Ops**, tile **Backups**: one sentence (`13 sources backed up, 6 older than
30h.`), then a table, stalest first: source, newest copy in UTC, age (marked `stale` past 30
hours), copies, size. When the bucket could not be listed the tile says the bucket could not be
listed and no backup is known to exist, with the reason; it never shows an empty green table.

## What it does not cover yet

The cluster's own Postgres databases (Backstage, commerce, Langfuse, LiteLLM and the rest) have no
backup job at all, so they have no row. A row cannot be drawn for a backup that does not exist;
that gap is filed as its own issue.
