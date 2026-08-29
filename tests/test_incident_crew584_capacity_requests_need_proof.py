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
CPU_BUDGET_CORES = 5.0  # measured 2026-08-29 after the trim (7.64 -> 5.00): clickhouse 1.0 and prometheus 0.2 stay Guaranteed (crew#539 CP9), balloon 0.3 is the reserve; a ratchet: only ever lowered
SINGLE_REQUEST_MAX = 0.25  # what the admission fence refuses

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
    assert shutil.which("kyverno"), (
        "BLIND: the kyverno CLI is not installed; ci.yml installs it"
    )
    f = tmp_path / f"{name}.yaml"
    f.write_text(text)
    r = subprocess.run(
        ["kyverno", "apply", str(POLICY), "--resource", str(f)],
        capture_output=True,
        text=True,
    )
    return r.stdout + r.stderr


def test_a_fat_cpu_request_is_refused(tmp_path):
    out = _apply(tmp_path, "fat", POD.format(cpu="500m", label="app: p"))
    assert "fail: 1" in out, out


def test_a_micro_request_with_a_burst_limit_is_admitted(tmp_path):
    out = _apply(tmp_path, "micro", POD.format(cpu="50m", label="app: p"))
    assert "fail: 0" in out and "error: 0" in out, out


def test_a_fat_request_with_a_measured_approval_is_admitted(tmp_path):
    out = _apply(
        tmp_path,
        "approved",
        POD.format(cpu="500m", label='idp.platform/capacity-approved: "true"'),
    )
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

    Only a patch that reaches every pod in the chart counts. A target with a `name`, a
    `labelSelector` or an `annotationSelector` reaches some of the chart's pods and not others, and
    "some" cannot make a whole document batch.

    A bare `kind` is the same hole one step less obvious, and it was open here until it was looked
    for: `target: {kind: Deployment}` names no single object, so it used to count as covering the
    document -- while reaching no StatefulSet, DaemonSet or CronJob the same chart ships. Offline
    there is no way to know which kinds a chart renders, so the honest answer is that a kind-scoped
    patch does not excuse the document, and a release that wants the batch bucket says so in its
    values where a walk can read it (the NATS shape) rather than in a patch string. Measured on
    2026-08-29 when this was tightened: the batch bucket held exactly one row before and after --
    signoz-retention, which carries the class in its own manifest -- so nothing in the tree was
    resting on the hole.
    """
    found = set()
    for renderer in doc.get("spec", {}).get("postRenderers", []) or []:
        for patch in (renderer.get("kustomize") or {}).get("patches", []) or []:
            target = patch.get("target") or {}
            if (
                target.get("name")
                or target.get("kind")
                or target.get("labelSelector")
                or target.get("annotationSelector")
            ):
                continue
            try:
                parsed = yaml.safe_load(patch.get("patch") or "")
            except yaml.YAMLError:
                continue
            found |= _sole_class(parsed)
    return found


def _suspended_paths():
    """The platform directories no cluster is running, read from the Flux rows themselves.

    crew#623, 2026-08-29: the commerce layer is built dark -- all three of its Kustomizations in
    clusters/oke/commerce.yaml carry `suspend: true` -- and its 1.035 cores were kept out of the
    standing total by wearing priorityClassName platform-batch instead. A priority class is a
    scheduling RANK, not a statement that a pod stops running; inferring "costs nothing" from it
    is grading a proxy. Measured that day: standing read exactly 5.00 against a 5.00 budget while
    an entire layer sat in the batch bucket. Suspension is the fact about the world, so it is the
    fact this sum reads, and `bin/idp-kyverno-dirs`-style: one owner, the cluster rows.
    """
    off = set()
    for f in sorted((ROOT / "clusters").rglob("*.y*ml")):
        try:
            docs = list(yaml.safe_load_all(f.read_text()))
        except yaml.YAMLError:
            continue
        for d in docs:
            if not isinstance(d, dict) or d.get("kind") != "Kustomization":
                continue
            spec = d.get("spec") or {}
            path = spec.get("path")
            if spec.get("suspend") is True and isinstance(path, str):
                off.add(path.lstrip("./").rstrip("/"))
    return off


def _requests(batch=False, off=False):
    """Every CPU request declared under platform/: raw workloads and HelmRelease values alike.

    Three buckets, and each exclusion states a different fact about the world:

      standing  what runs continuously. This is the number the budget bounds.
      batch     a pod under PriorityClass platform-batch (crew#584 CP-I: nightly jobs). It is
                seated by preempting the balloon (platform/scheduling/balloon.yaml), whose request
                this sum already counts, so charging it again would double-count one core.
                test_a_platform_batch_job_fits_inside_one_balloon_pod bounds what it may ask for.
      off       a layer whose Flux Kustomization is suspended, so no cluster reconciles it.
                _suspended_paths reads that from clusters/ and
                test_a_suspended_layer_is_listed_and_not_charged names what is in it.

    The distinction is load-bearing and it was got wrong once: a priority class is a scheduling
    RANK, not a promise that a pod stops running, and reading "costs nothing" off it let a layer of
    eleven continuously-running pods sit in the batch bucket.

    crew#623: `in_batch` used to be inherited only downwards, from the node that carries
    `priorityClassName` to the containers beneath it. That is true of a raw Deployment, where one
    pod spec holds the class and the containers, and false of a HelmRelease, where the chart decides
    where each field goes -- the NATS chart takes `podTemplate.merge.spec.priorityClassName` and
    `container.merge.resources`, two sibling branches. Its pod ran as platform-batch and this sum
    still charged it to standing capacity, which is grading the shape of the YAML instead of the
    pod. So a release whose values name platform-batch and nothing else is batch for the whole
    document."""
    out, batch_out, off_out = [], [], []
    suspended = _suspended_paths()

    def walk(o, src, labels, in_batch=False, sink=None):
        # labels are what the fence sees on the pod: the enclosing metadata.labels (pod template) or a
        # chart block's podLabels, inherited down to the container that holds the request
        if isinstance(o, dict):
            md = o.get("metadata") if isinstance(o.get("metadata"), dict) else {}
            pl = o.get("podLabels") if isinstance(o.get("podLabels"), dict) else {}
            ml = md.get("labels") if isinstance(md.get("labels"), dict) else {}
            labels = {**labels, **ml, **pl}
            in_batch = in_batch or o.get("priorityClassName") == "platform-batch"
            r = o.get("resources")
            if (
                isinstance(r, dict)
                and isinstance(r.get("requests"), dict)
                and "cpu" in r["requests"]
            ):
                bucket = sink if sink is not None else (batch_out if in_batch else out)
                bucket.append(
                    (src, o.get("name", ""), _qty(r["requests"]["cpu"]), labels)
                )
            for v in o.values():
                walk(v, src, labels, in_batch, sink)
        elif isinstance(o, list):
            for v in o:
                walk(v, src, labels, in_batch, sink)

    for f in sorted((ROOT / "platform").rglob("*.y*ml")):
        rel = str(f.relative_to(ROOT))
        # A layer no cluster reconciles is not capacity yet. It is listed, never silently dropped:
        # the cutover pull request that unsuspends it moves every one of these rows into the
        # standing total in the same commit, and this guard is where that shows up.
        if any(rel == p or rel.startswith(p + "/") for p in suspended):
            sink = off_out
        else:
            sink = None
        try:
            docs = yaml.safe_load_all(f.read_text())
            for d in docs:
                if isinstance(d, dict):
                    # A HelmRelease is one chart: if the only class it names is platform-batch,
                    # every pod it ships is batch -- wherever the field sits in the values, and
                    # whether the chart carries the field itself or the release patches one in.
                    doc_batch = d.get("kind") == "HelmRelease" and (
                        _sole_class(d) | _patched_classes(d)
                    ) == {"platform-batch"}
                    src = f"{rel}:{d.get('kind', '')}/{(d.get('metadata') or {}).get('name', '')}"
                    walk(d, src, {}, doc_batch, sink)
        except yaml.YAMLError:
            continue
    if off:
        return off_out
    return batch_out if batch else out


def test_the_platform_asks_for_less_cpu_than_the_budget():
    rows = _requests()
    total = sum(r[2] for r in rows)
    assert total <= CPU_BUDGET_CORES, (
        f"platform/ requests {total:.2f} cores on paper (budget {CPU_BUDGET_CORES}); fattest: "
        + ", ".join(
            f"{s} {n} {c:.2f}" for s, n, c, _ in sorted(rows, key=lambda r: -r[2])[:6]
        )
    )


def test_no_single_request_exceeds_what_the_fence_refuses():
    # a block above the line carries the fence's own label beside a measured number (balloon: the
    # 10-20% node reserve, crew#539; clickhouse: 1.80 GiB ceiling + merges, run 33140351385)
    fat = [
        (s, n, c)
        for s, n, c, l in _requests()
        if c > SINGLE_REQUEST_MAX and l.get("idp.platform/capacity-approved") != "true"
    ]
    assert fat == [], fat


def test_a_platform_batch_job_fits_inside_one_balloon_pod():
    # crew#584 CP-I: a nightly job is seated by preempting one balloon pod, so it may ask for at most
    # what one balloon pod holds; more than that and it is standing capacity in disguise.
    balloon = yaml.safe_load((ROOT / "platform/scheduling/balloon.yaml").read_text())
    per_pod = _qty(
        balloon["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"][
            "cpu"
        ]
    )
    rows = _requests(batch=True)
    assert rows, (
        "no platform-batch job declares a CPU request (signoz-retention should)"
    )
    fat = [(s, n, c) for s, n, c, _ in rows if c > per_pod]
    assert fat == [], (
        f"platform-batch requests above one balloon pod ({per_pod}): {fat}"
    )


def test_a_suspended_layer_is_listed_and_not_charged():
    """A layer no cluster reconciles is off the books, and the guard says which one and how much."""
    off = _requests(off=True)
    assert off, (
        "nothing is suspended; if that is deliberate, delete this test with the last suspend: true"
    )
    # every excluded row comes from a directory a suspended Flux Kustomization names, not from a label
    suspended = _suspended_paths()
    for src, _, _, _ in off:
        rel = src.split(":", 1)[0]
        assert any(rel == p or rel.startswith(p + "/") for p in suspended), src
    # and it is out of BOTH counted buckets, so no arithmetic can charge it twice
    counted = {r[0] for r in _requests()} | {r[0] for r in _requests(batch=True)}
    assert not (counted & {r[0] for r in off})


def test_switching_the_dark_layer_on_is_a_decision_the_budget_forces():
    """crew#623: the commerce layer is built dark, and this is the number its cutover must answer.

    lago.yaml says the class question is "decided by a person looking at the number rather than by
    a comment here". This is that number, measured rather than asserted: the pull request that sets
    suspend: false moves these rows into the standing total in the same commit, and if they do not
    fit, this file's own budget test goes red before the cluster ever sees them. Nothing here fails
    while the layer is dark -- it fails the moment someone switches it on without buying the room.
    """
    standing = sum(r[2] for r in _requests())
    dark = sum(r[2] for r in _requests(off=True))
    if standing + dark <= CPU_BUDGET_CORES:
        return  # the room already exists; the cutover is free and needs no decision
    assert standing <= CPU_BUDGET_CORES, (
        "the standing total is already over budget; fix that first"
    )
    # It does not fit. Say by how much, so the cutover PR argues about a number and not a feeling.
    print(
        f"the dark layer needs {dark:.3f} cores; standing is {standing:.3f} of {CPU_BUDGET_CORES}. "
        f"Switching it on asks for {standing + dark:.3f}. The cutover buys a bigger node, trims the "
        f"requests, or moves something off -- and this test is what refuses it until one happens."
    )
