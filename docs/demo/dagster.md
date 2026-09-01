# Demo: The estate scheduler (Dagster)

## What the founder opens

1. Open the **Backstage catalogue**: https://catalogue.\${ESTATE_ZONE}
2. Find the **estate-scheduler** component (or search for "scheduler")
3. Click on the component to see its overview card

## What he sees

On the estate-scheduler component card:

- **Dagster UI** link — opens the Dagster interface
- The schedules list shows every scheduled job (science runs, catalogue jobs)
- Each schedule shows:
  - **Last run**: timestamp and status (success/failure)
  - **Next run**: when it will run next
  - **Partition**: which partition/data slice it processes

## The schedules

The scheduler runs all jobs defined in:
- `scheduler/estate_scheduler/definitions.py` (the primary location)
- `crew/science/scheduler/estate_dagster/facts.py` (the science facts source)

Every schedule follows the same pattern:
1. A sensor or cron schedule triggers
2. Dagster queues the run
3. The daemon executes it on a run pod
4. The result is recorded (success/failure)

## Accessing from the Mac screen

Before this move, Dagster was reached through the Mac screen at port 3210. Now it runs on the cluster and the catalogue provides a direct link to the component.
