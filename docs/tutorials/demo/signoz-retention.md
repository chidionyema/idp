# Demo: the retention job that had been failing every morning

One minute. A defect that hid for days behind its own successful reads.

## Before

```bash
kubectl -n observability logs job/signoz-retention-29821157
```

```
FAIL signoz-retention logs 500 {"errors":[{"code":500,"msg":"SetTTLV2 only supported"}]}
```

One signal, every morning, for days. `traces` and `metrics` were already at 168h,
so the job never had to write them, and the v1 GET kept answering 200 for all
three. **A job that writes nothing looks exactly like a job that works.**

## Run it

```bash
kubectl -n observability port-forward svc/signoz 18090:8080 &
python3 -m pytest tests/bdd/test_signoz_retention_ttl_engine.py -q
```

## After

```
..........                                                               [100%]
10 passed in 0.16s
```

And the job itself, against the live SigNoz with the fix:

```
plan: []
failed: []
OK
```

`plan: []` is the correct answer for an estate already at the knob: nothing to
write. That empty list is the whole point — the job reads first, because
`ALTER TABLE ... MODIFY TTL` is not free.

## What to look at

**Two API generations, one engine.** v1 answers `logs_ttl_duration_hrs: -1` for a
signal v2 has already set to 15 days. A job that reads one and writes the other
reports a change every single morning forever, which is a job nobody would notice
was wrong.

**A failed read is planned, not skipped.** The test
`test_a_signal_whose_ttl_cannot_be_read_is_planned_not_skipped` pins it: an
unreadable TTL is a reason to apply, never a reason to stay silent. Treating
"could not look" as "is correct" is the same defect as
`bin/idp-compile-helm` reporting eleven failed charts as an empty estate.

**409 is pending, not failed.** ClickHouse mid-`ALTER` is a change still running;
the next run finishes it. Marking that red would page on every long retention
change.

## Prove the write lands

```bash
kubectl -n observability port-forward svc/signoz 18090:8080 &
# authenticate as signoz-root, then:
curl -s -H "Authorization: Bearer $TOKEN" 'http://127.0.0.1:18090/api/v2/settings/ttl?type=logs'
```

A signal with a custom TTL answers without `default_ttl_days` — that absence *is*
the success. The logs signal had `-1` (unset) before this change and answers
`{"version":"v2","status":"success","cold_storage_ttl_days":-1}` now.
