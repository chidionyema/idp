# Onboarding: Adding a new scheduled job

## Overview

The estate scheduler runs all scheduled jobs (science runs, catalogue jobs) on the cluster. Jobs are defined in the `scheduler/` directory and loaded by the Dagster user-code deployment.

## How a new job is added

### Step 1: Add the schedule to scheduler/schedule.yml

Edit `scheduler/schedule.yml` (or create a new job definition in `scheduler/estate_scheduler/`):

```yaml
jobs:
  - name: my-new-job
    schedule:
      cron: "0 * * * *"  # every hour
    pipeline: my_pipeline
    config:
      # run config for the job
```

### Step 2: Push to main

Commit and push your changes to the `main` branch:

```bash
git add scheduler/
git commit -m "crew#716: add my-new-job schedule"
git push origin main
```

### Step 3: Image rebuild

The image automation detects the push to main and builds a new `estate-scheduler` image:
- Image: `ghcr.io/chidionyema/estate-scheduler:main-<run>-<sha>`
- Tag format: `main-<run>-<sha>`

The build runs in GitHub Actions (see `.github/workflows/build-multiarch.yml`).

### Step 4: Flux rolls the deployment

Flux reconciles the `dagster-user-deployments` chart install in the `dagster` area of the cluster:
- Detects the new image tag from the ImagePolicy
- Rolls the `estate-scheduler` Deployment
- The new code location is loaded automatically

Verify with:
```bash
flux get hr -n dagster
kubectl get pods -n dagster -l backstage.io/kubernetes-id=estate-scheduler
```

## How it works

1. **Image automation** (platform/image-automation/estate-scheduler.yaml):
   - Watches `ghcr.io/chidionyema/estate-scheduler`
   - On new image, updates the tag in `platform/dagster/dagster.yaml`

2. **Flux reconciliation** (clusters/oke/platform.yaml row `dagster`):
   - Pulls the updated chart install
   - Updates the user-code deployment

3. **Dagster**:
   - The gRPC server loads the definitions from `scheduler/workspace.yaml`
   - The daemon ticks the schedules
   - Runs are launched as Kubernetes jobs

## Troubleshooting

### Schedule not ticking

Check the Dagster daemon logs:
```bash
kubectl logs -n dagster -l app.kubernetes.io/name=dagster -c dagster-daemon
```

### Run pod refused by Kyverno

If a run pod is rejected by admission policies:
```bash
kubectl get policyreport -n dagster
```

The dagster-exception.yaml (platform/edge/dagster-exception.yaml) allows the postgres password pattern.

### Image not updating

Check the ImagePolicy status:
```bash
flux get image policy -n flux-system estate-scheduler
```
