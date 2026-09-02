# Dagster runs on estate-built images

## Decision

Every Dagster process on the cluster — web page, daemon and the scheduler code — runs the
estate's own `estate-scheduler` image, built by `build-multiarch.yml` for both machine
kinds (`amd64` and `arm64`). No vendor Dagster image is pulled.

## Why

The chart's default images come from the vendor's registry
(`docker.io/dagster/dagster-celery-k8s` for the web page and daemon), and the vendor
publishes **no `arm64` build in any tag** (measured against the registry's tag list,
2026-09-02). Every node in this cluster is `arm64`. The kubelet refused the pull with:

```
no image found in image index for architecture "arm64"
```

so the web page and daemon could never boot — not a crash, an impossible pull.

The estate already builds its own scheduler image from `estate-scheduler.Dockerfile` for
both machine kinds. That image now also installs `dagster-webserver`, so one image serves
all three processes and the automatic tag-stamping keeps all three lines on the same
version.

## The celery secret that can never exist

The chart generates its celery configuration `Secret` only when the run launcher is
`CeleryK8sRunLauncher` (the chart’s celery secret template). This estate uses
`K8sRunLauncher`, so the `Secret` never renders — yet a patch in the release forced the
scheduler container to require it, and the pod sat in `CreateContainerConfigError` with:

```
secret "dagster-celery-config-secret" not found
```

The fix is removal, not a guard: `celeryConfigSecretName` is set to the empty string so
no template renders a reference to the impossible `Secret`, and the forcing patch is
deleted. See the memory rule: remove the bad input, do not guard it.

## Guard

`tests/test_incident_dagster_amd64_only_images.py` fails any change that points the web
page or daemon back at a vendor image, or that reintroduces a reference to the celery
`Secret`.

## Runtime security follow-up (2026-09-02, same day)

The arm64 image landed and three pods still failed, all one class: security
settings that disagree with the image.

- The code server and launched-run pods set `runAsNonRoot` with no numeric uid.
  The image names its user (`scheduler`), and the kubelet refuses what it
  cannot verify: "container has runAsNonRoot and image has non-numeric user."
  Every `runAsNonRoot` in the release now carries `runAsUser: 999`.
- The daemon crashed writing a telemetry id into its home directory, which is a
  read-only mount here. Telemetry is off in the release values.
- The image now declares `USER 10001` numerically, so the kubelet check can
  never trip on it again.

Guard: `tests/test_incident_dagster_nonroot_needs_numeric_uid.py`.
