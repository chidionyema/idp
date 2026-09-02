# Boot Dagster and Superset

What to check when either of these two platform workloads stalls, and what
their last stall was.

## Dagster

The scheduler image tag in `platform/dagster/dagster.yaml` must be a real
build tag. Image automation only writes tags under `platform/backstage`, so a
placeholder tag (`main-0-0000…`) sits forever until a person stamps the tag
the ImagePolicy resolved. The webserver and daemon pods also run as user 999
(the same user the bundled postgresql pod already runs as); without it the
kubelet refuses the pod with "container has runAsNonRoot and image will run
as root".

Check: the pods in the `dagster` namespace are Running and the HelmRelease is
Ready.

## Superset

The chart's image ships without the postgres driver, and the cluster keeps
every root filesystem read-only. The bootstrap script in
`platform/observability/superset.yaml` installs `psycopg2-binary` into the
writable `superset_home` volume at start-up. If the observability namespace
cannot reach pypi, the fallback is an image with the driver baked in.

Check: the superset pods in the `observability` namespace stop restarting and
the HelmRelease is Ready. The stall this page records was 28 restarts on
`ModuleNotFoundError: No module named 'psycopg2'`.
