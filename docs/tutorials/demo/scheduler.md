# Demo: the estate scheduler

One scheduler, one policy file, one launchd job. Two minutes.

```sh
bin/scheduler-up                 # dagster-daemon + UI on 127.0.0.1:3210
bin/scheduler-status             # every daemon healthy AND a schedule ticked in the last 10 min
open http://127.0.0.1:3210       # every job, every run, every log, one screen
```

Show the policy: `scheduler/schedule.yml`. Every estate job is one entry:

```yaml
  com.founder.estatesnapshot:
    cron: 3 0,2,4,6,8,10,12,14,16,18,20,22 * * *
    command: [~/.claude/scripts/hc-wrap.sh, estatesnapshot, $CODE/crew/scripts/estate-snapshot]
    max_load: 4.0            # skips, with the reason in the UI, while load is above this
    skip_on_battery: true    # skips while the Mac is discharging
    after: com.founder.ingit # optional: also runs when this job succeeds
```

Show the storm cannot happen: `run/dagster.yaml` queues runs, two at a time.
Show the circuit breaker: fail a job three times in the UI, watch its schedule skip with "circuit open"; launch it by hand once and it closes.

Stop: `bin/scheduler-down`.
