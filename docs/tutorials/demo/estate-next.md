# Demo: estate-next

Founder, 2026-08-27 (crew#403 CP6): "what major capabilities and showcase do you have planned and
what is outstanding or blocking, we should automate this and reduce founder friction for always
asking about major capabilities and progress ... and when to expect".

## The command

    cd ~/dev/code/idp && bin/estate-next

## What it printed (2026-08-27 13:02Z)

```
estate-next: 119 lines, 107 red rows -> docs/NEXT.md
```

`docs/NEXT.md` then opened with:

```
- Checkpoints: **2 BLOCKING**, **4 ACTIVE**, **99 PLANNED** of 105 open, across 25 issues
- When: **105 NO DATE** (no `Expect:` line; the owner has not said when), 0 dated
- Lanes reporting: code (2026-08-27T13:02Z), crew (2026-08-27T11:48Z), crew459-portal-polish (2026-08-27T12:43Z), hermes-v2 (2026-08-27T12:43Z)
```

Every row was red on the date axis because no checkpoint on any open issue carried an `Expect:`
line that day. That is the finding, not a bug: the page says who has not said when.

## Where it lands

`bin/catalog-render` runs it on the hourly schedule before `estate-showcase`, so the showcase bar
quotes it (`- Next: ...`) and `docs/NEXT.md` is published with the other generated pages.
