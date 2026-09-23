# promoter -- a demo

This page demonstrates the redteam promoter running against the
estate's redteam payloads. The promoter is the loop that takes a
payload the red team proved defeating and teaches the proxy to block
it -- the write half of the red team -> proxy loop.

## How to run it

```
python3 bin/redteam_promoter/promoter.py --help
```

The promoter runs in dry-run by default; promoting a payload does
not require Redis or Postgres to be reachable for its decision to be
right. The decision is the part a fixture grades; the write half is
the part a real cluster would consume.

## What to look for

The promoter's signature derivation. A defeating payload derives a
stable signature; a dynamic-only payload derives nothing (so the
loop cannot ban a bare UUID and refuse correct work).
