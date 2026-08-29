"""crew#584 (founder, 2026-08-29): "why 4 cores, do we need all that capacity?" The platform asked
for 7.64 cores on paper (97 resource blocks) while idling at a fraction of it; the paper number is
what bought the 6-core node. This pins the fix three ways: the fat requests are trimmed in git (the
sum of CPU requests across platform/ stays under a budget), the cluster refuses a new fat request
without a capacity-approved label, and a Job that forgets its TTL gets one hour, never forever."""
import pathlib
import shutil
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "platform/edge/capacity-policy.yaml"
CPU_BUDGET_CORES = 5.0        # measured 2026-08-29 after the trim (7.64 -> 5.00): clickhouse 1.0 and prometheus 0.2 stay Guaranteed (crew#539 CP9), balloon 0.3 is the reserve; a ratchet: only ever lowered
SINGLE_REQUEST_MAX = 0.25     # what the admission fence refuses

POD = """apiVersion: v1
kind: Pod
metadata:
  name: p
  namespace: hermes-agent
  labels:
    {label}
spec:
  containers:
    - name: c
      image: registry.k8s.io/pause:3.9
      resources:
        requests: {{ cpu: {cpu}, memory: 64Mi }}
        limits: {{ cpu: "2", memory: 2Gi }}
"""

JOB = """apiVersion: batch/v1
kind: Job
metadata:
  name: j
  namespace: backstage
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: c
          image: registry.k8s.io/pause:3.9
"""


def _qty(v):
    v = str(v or "0")
    if v.endswith("m"):
        return float(v[:-1]) / 1000
    return float(v)


def _apply(tmp_path, name, text):
    assert shutil.which("kyverno"), "BLIND: the kyverno CLI is not installed; ci.yml installs it"
    f = tmp_path / f"{name}.yaml"
    f.write_text(text)
    r = subprocess.run(["kyverno", "apply", str(POLICY), "--resource", str(f)], capture_output=True, text=True)
    return r.stdout + r.stderr


def test_a_fat_cpu_request_is_refused(tmp_path):
    out = _apply(tmp_path, "fat", POD.format(cpu="500m", label="app: p"))
    assert "fail: 1" in out, out


def test_a_micro_request_with_a_burst_limit_is_admitted(tmp_path):
    out = _apply(tmp_path, "micro", POD.format(cpu="50m", label="app: p"))
    assert "fail: 0" in out and "error: 0" in out, out


def test_a_fat_request_with_a_measured_approval_is_admitted(tmp_path):
    out = _apply(tmp_path, "approved", POD.format(cpu="500m", label='idp.platform/capacity-approved: "true"'))
    assert "fail: 0" in out and "error: 0" in out, out


def test_a_job_without_a_ttl_gets_one_hour(tmp_path):
    out = _apply(tmp_path, "job", JOB)
    assert "ttlSecondsAfterFinished: 3600" in out, out


def test_the_policy_is_applied_by_the_edge_kustomization():
    kust = yaml.safe_load((ROOT / "platform/edge/kustomization.yaml").read_text())
    assert "capacity-policy.yaml" in kust["resources"]


def _sole_class(o, found=None):
    """Every distinct priorityClassName anywhere in one document, at any depth."""
    found = set() if found is None else found
    if isinstance(o, dict):
        v = o.get("priorityClassName")
        if isinstance(v, str) and v:
            found.add(v)
        for x in o.values():
            _sole_class(x, found)
    elif isinstance(o, list):
        for x in o:
            _sole_class(x, found)
    return found


def _patched_classes(doc):
    """The classes a HelmRelease patches onto the chart's pods at render time.

    A chart this estate does not own often has no `priorityClassName` field at all, so the class
    is added by a `postRenderers` kustomize patch -- the estate's existing way to bend such a
    chart (temporal, hindsight, langfuse, traefik, signoz and five more do it). The class the pod
    actually runs under is then in a YAML string, invisible to a walk over the release's values,
    and the pod was charged to standing capacity while the scheduler treated it as batch. That is
    grading the shape of the file instead of the pod (crew#623, the Lago release).

    Only a patch that names no single object counts: a target with a `name` or a `labelSelector`
    reaches some of the chart's pods and not others, and "some" cannot make a whole document batch.
    """
    found = set()
    for renderer in doc.get("spec", {}).get("postRenderers", []) or []:
        for patch in (renderer.get("kustomize") or {}).get("patches", []) or []:
            target = patch.get("target") or {}
            if target.get("name") or target.get("labelSelector") or target.get("annotationSelector"):
                continue
            try:
                parsed = yaml.safe_load(patch.get("patch") or "")
            except yaml.YAMLError:
                continue
            found |= _sole_class(parsed)
    return found


def _requests(batch=False):
    """Every CPU request declared under platform/: raw workloads and HelmRelease values alike.

    A pod under PriorityClass platform-batch (crew#584 CP-I: nightly jobs) is not standing capacity:
    it is seated by preempting the balloon (platform/scheduling/balloon.yaml), whose request this
    sum already counts, so its own request is listed by batch=True and kept out of the paper total.
    test_a_platform_batch_job_fits_inside_one_balloon_pod bounds it.

    crew#623: `in_batch` used to be inherited only downwards, from the node that carries
    `priorityClassName` to the containers beneath it. That is true of a raw Deployment, where one
    pod spec holds the class and the containers, and false of a HelmRelease, where the chart decides
    where each field goes -- the NATS chart takes `podTemplate.merge.spec.priorityClassName` and
    `container.merge.resources`, two sibling branches. Its pod ran as platform-batch and this sum
    still charged it to standing capacity, which is grading the shape of the YAML instead of the
    pod. So a release whose values name platform-batch and nothing else is batch for the whole
    document."""
    out, batch_out = [], []

    def walk(o, src, labels, in_batch=False):
        # labels are what the fence sees on the pod: the enclosing metadata.labels (pod template) or a
        # chart block's podLabels, inherited down to the container that holds the request
        if isinstance(o, dict):
            md = o.get("metadata") if isinstance(o.get("metadata"), dict) else {}
            pl = o.get("podLabels") if isinstance(o.get("podLabels"), dict) else {}
            ml = md.get("labels") if isinstance(md.get("labels"), dict) else {}
            labels = {**labels, **ml, **pl}
            in_batch = in_batch or o.get("priorityClassName") == "platform-batch"
            r = o.get("resources")
            if isinstance(r, dict) and isinstance(r.get("requests"), dict) and "cpu" in r["requests"]:
                (batch_out if in_batch else out).append((src, o.get("name", ""), _qty(r["requests"]["cpu"]), labels))
            for v in o.values():
                walk(v, src, labels, in_batch)
        elif isinstance(o, list):
            for v in o:
                walk(v, src, labels, in_batch)

    for f in sorted((ROOT / "platform").rglob("*.y*ml")):
        try:
            docs = yaml.safe_load_all(f.read_text())
            for d in docs:
                if isinstance(d, dict):
                    # A HelmRelease is one chart: if the only class it names is platform-batch,
                    # every pod it ships is batch -- wherever the field sits in the values, and
                    # whether the chart carries the field itself or the release patches one in.
                    doc_batch = d.get("kind") == "HelmRelease" and (_sole_class(d) | _patched_classes(d)) == {
                        "platform-batch"
                    }
                    walk(d, f"{f.relative_to(ROOT)}:{d.get('kind', '')}/{(d.get('metadata') or {}).get('name', '')}", {}, doc_batch)
        except yaml.YAMLError:
            continue
    return batch_out if batch else out


def test_the_platform_asks_for_less_cpu_than_the_budget():
    rows = _requests()
    total = sum(r[2] for r in rows)
    assert total <= CPU_BUDGET_CORES, f"platform/ requests {total:.2f} cores on paper (budget {CPU_BUDGET_CORES}); fattest: " + \
        ", ".join(f"{s} {n} {c:.2f}" for s, n, c, _ in sorted(rows, key=lambda r: -r[2])[:6])


def test_no_single_request_exceeds_what_the_fence_refuses():
    # a block above the line carries the fence's own label beside a measured number (balloon: the
    # 10-20% node reserve, crew#539; clickhouse: 1.80 GiB ceiling + merges, run 33140351385)
    fat = [(s, n, c) for s, n, c, l in _requests() if c > SINGLE_REQUEST_MAX and l.get("idp.platform/capacity-approved") != "true"]
    assert fat == [], fat


def test_a_platform_batch_job_fits_inside_one_balloon_pod():
    # crew#584 CP-I: a nightly job is seated by preempting one balloon pod, so it may ask for at most
    # what one balloon pod holds; more than that and it is standing capacity in disguise.
    balloon = yaml.safe_load((ROOT / "platform/scheduling/balloon.yaml").read_text())
    per_pod = _qty(balloon["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]["cpu"])
    rows = _requests(batch=True)
    assert rows, "no platform-batch job declares a CPU request (signoz-retention should)"
    fat = [(s, n, c) for s, n, c, _ in rows if c > per_pod]
    assert fat == [], f"platform-batch requests above one balloon pod ({per_pod}): {fat}"
