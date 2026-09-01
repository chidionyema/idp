# Runbook: Dagster scheduler

## Who does what

- **Founder**: Merges the branch after `APPROVE: crew#716`
- **Flux**: Reconciles the chart install
- **You**: Monitors the rollout

## Verification after merge

```bash
# Check Flux reconciled the dagster row
flux get hr -n dagster

# Should show: dagster    True    Helm upgrade succeeded
```

## Common issues

### Run pod refused by Kyverno

If a scheduled run pod is rejected by admission policies:

```bash
# Check the policy report
kubectl get policyreport -n dagster

# Check which policy failed
kubectl describe policyreport -n dagster
```

The dagster-exception.yaml (platform/edge/dagster-exception.yaml) should allow:
- `secrets-not-from-env-vars` for the postgres password (DAGSTER_PG_PASSWORD, POSTGRES_PASSWORD)

If a new secret pattern appears, add it to the exception.

### Rolling the user-code image

The estate-scheduler image updates automatically on every main push. To force a manual rollout:

```bash
# Patch the deployment to force a rollout
kubectl rollout restart deployment/estate-scheduler -n dagster
```

### Postgres PVC backup

**Not yet implemented**: backups land with a later checkpoint of [the scheduler move](https://github.com/chidionyema/crew/issues/716).

The postgres data is stored in a PVC:
```bash
kubectl get pvc -n dagster
```

To back up manually:
```bash
# Get the pvc name
PVC=$(kubectl get pvc -n dagster -o jsonpath='{.items[0].metadata.name}')

# Copy to a temp pod
kubectl run backup --rm -i --tty --image=docker.io/library/busybox:1.28 -- \
  tar czf - -C /var/lib/postgresql/data . | \
  kubectl exec -i -n dagster deployment/estate-scheduler -- \
  tar xzf - -C /tmp/backup
```

A later checkpoint adds automated backups.

### Debugging a schedule

```bash
# List schedules
kubectl exec -n dagster deploy/estate-scheduler -- \
  dagster schedule list -m estate_scheduler.definitions

# View schedule logs
kubectl logs -n dagster -l component=dagster-daemon

# View a specific run
# 1. Open Dagster UI (from catalogue link)
# 2. Find the run in the Runs tab
# 3. Click on the run to see logs
```

## Scale and resources

The current resource requests:
- postgresql: 100m CPU, 256Mi memory
- dagster-webserver: 100m CPU, 512Mi memory
- dagster-daemon: 100m CPU, 384Mi memory
- runLauncher: 50m CPU, 256Mi memory
- user-deploy (estate-scheduler): 100m CPU, 384Mi memory

**Total CPU requests: 450m**

If you need to increase limits, add a proof label per platform/edge/capacity-policy.yaml.
