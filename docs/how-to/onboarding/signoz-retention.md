# Onboarding the retention knob

`platform/observability/signoz-retention.yaml`. It is a CronJob that runs once a
day at 03:17 and applies the estate's retention promise.

## What it is for

The feature registry promises `knobs: { retention_days: 7 }` and says "retention
is a tier knob, not a hand edit". The SigNoz chart has no retention value and the
docs point at *Settings -> Retention Controls*, which is a hand edit. The same
setting is an admin API, so a Job applies it.

## The defect it carried, and why it was invisible

The job failed every morning on exactly one signal:

```
FAIL signoz-retention logs 500 {"errors":[{"code":500,"msg":"SetTTLV2 only supported"}]}
```

`traces` and `metrics` were already at 168h, so the job never had to write them.
The v1 GET kept answering 200 for all three. **A job that writes nothing looks
identical to a job that works**, so this hid for days behind its own successful
reads.

The v1 POST is refused because this deployment is on the v2 TTL engine. Measured
on the live estate 2026-09-13:

| call | result |
|---|---|
| `GET /api/v1/settings/ttl?type=logs` | 200, `logs_ttl_duration_hrs: -1` (unset) |
| `GET /api/v2/settings/ttl?type=logs` | 200, `default_ttl_days: 15` |
| `POST /api/v2/settings/ttl {"type":"logs","duration":"168h"}` | 200, `custom retention TTL has been successfully set up` |

The two generations disagree about the current value, so **v2 is read as well as
written**. Reading v1 while writing v2 is how a knob lands and the job still
reports a change every single morning.

## The three functions

- `current_days(http, token, sig)` — the signal's retention in days as v2 reports
  it, or `None` when unreadable. v2 drops `default_ttl_days` once a custom TTL is
  in force; that absence is read as the knob, not as "unreadable", or the job
  would rewrite every signal every day.
- `plan(http, token, days)` — the signals whose TTL is not the knob. **Always
  reads before writing**, because `ALTER TABLE ... MODIFY TTL` is not free. A
  signal whose TTL cannot be read is **planned, not skipped**: a failed read is a
  reason to apply, never a reason to stay silent.
- `apply(http, token, days, todo)` — the v2 write as a JSON body. `409` means
  ClickHouse is mid-`ALTER` and the next run finishes it, which is pending and not
  a red job. Anything else is reported and reaches the exit code.

## Running it

The Job does it. To run it by hand against a forwarded SigNoz:

```bash
kubectl -n observability port-forward svc/signoz 18090:8080 &
python3 -c "
import yaml, json, urllib.request, urllib.parse
docs=[d for d in yaml.safe_load_all(open('platform/observability/signoz-retention.yaml')) if d]
src=next(d for d in docs if d.get('kind')=='ConfigMap' and d['metadata']['name']=='signoz-retention-apply')['data']['apply.py']
ns={}; exec(compile(src,'apply','exec'), ns)
# ... define http() against 127.0.0.1:18090, log in with the signoz-root Secret,
# then: ns['plan'](http, tok, 7) and ns['apply'](http, tok, 7, todo)
"
```

A correct estate prints `plan: []` and `failed: []` — nothing to do, because
everything is already at the knob.

## Tests

```bash
python3 -m pytest tests/bdd/test_signoz_retention_ttl_engine.py -q
```

Ten scenarios, offline. They grade the contract in the ConfigMap itself: the
write goes to v2, no v1 write survives, the read uses the same engine as the
write, a correct signal is not rewritten, a wrong one is planned, a custom TTL
already in force is read as the knob, an unreadable TTL is planned rather than
skipped, the write carries the signal and the duration as a JSON body, a refused
write is reported and never swallowed, and a 409 is pending rather than failed.
