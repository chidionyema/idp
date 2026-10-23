"""A shadow run fails a pull request only for a failure the pull request caused.

Incident, 2026-10-14, #6194: 24 lines of newTag: bumps on flux/image-updates went red on 14 of its
15 paths. Not one failure was the change's. Six were gaps the shadow has on any commit -- a
namespace, a CRD, a database secret that another row lays in production -- and eight were one
dagster pod stuck on a missing Secret, charged to every path whose wait was running at the time,
because the pod watch read every pod in the cluster.

Two rules, each tested here:
  - a stuck pod is charged only to the Kustomization whose objects own it;
  - the head is graded against the same paths at its merge-base, and a failure the base shows
    too is inherited, not introduced. A base run that is missing or BLIND excuses nothing.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "shadow-verify.yml"


def load_shadow():
    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow", str(REPO / "bin" / "idp-shadow")
    )
    spec = importlib.util.spec_from_loader("idp_shadow", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


# The failures #6194's run 38575906540 printed, verbatim, and the same failures as a second run
# of the same tree would print them: new pod suffixes, a different duration.
DAGSTER_POD = (
    "pod dagster/dagster-dagster-user-deployments-estate-scheduler-d945998bkr5v8 container "
    'dagster-user-deployments is CreateContainerConfigError (restarts 0): secret "estate-db-dagster" '
    "not found"
)
RUN_6194 = [
    (
        "platform/commerce/app",
        "platform/commerce/app: the environment refused to converge it -- "
        'HelmRepository/commerce/lago not found: namespaces "commerce" not found',
    ),
    (
        "platform/dagster",
        "platform/dagster: the environment refused to converge it -- pods past rescue: "
        + DAGSTER_POD,
    ),
    (
        "platform/jit",
        "platform/jit: the environment refused to converge it -- "
        'RoleBinding/agents/jit-broker-identity not found: namespaces "agents" not found',
    ),
    (
        "platform/nodesoftware-operator",
        "platform/nodesoftware-operator: the environment refused to converge it -- "
        "ServiceMonitor/nodesoftware-operator/nodesoftware-operator dry-run failed: no matches "
        'for kind "ServiceMonitor" in version "monitoring.coreos.com/v1"',
    ),
    (
        "platform/observability",
        "platform/observability: the environment refused to converge it -- health check failed "
        "after 1m1.194572576s: failed early due to stalled resources: "
        "[Job/observability/superset-memory-seed status: 'Failed']",
    ),
]
RERUN_6194 = [
    (
        sc,
        m.replace("d945998bkr5v8", "7f6c9b8d4-xkzqv").replace(
            "1m1.194572576s", "58.0021s"
        ),
    )
    for sc, m in RUN_6194
]


def record(tmp_path, name, head, rc, fails):
    shadow = load_shadow()
    path = tmp_path / f"{name}.json"
    shadow.write_record(str(path), head, rc, fails)
    return str(path)


# ------------------------------------------------------------------ attribution


def obj(kind, ns, name, uid, owner=None, labels=None):
    md = {"namespace": ns, "name": name, "uid": uid, "labels": labels or {}}
    if owner:
        md["ownerReferences"] = [{"uid": owner, "controller": True}]
    return {"kind": kind, "metadata": md}


DAGSTER_RELEASE = ("dagster", "dagster")
HELM = {
    "helm.toolkit.fluxcd.io/name": "dagster",
    "helm.toolkit.fluxcd.io/namespace": "dagster",
}
DEPLOY = obj("Deployment", "dagster", "estate-scheduler", "d1", labels=HELM)
RS = obj("ReplicaSet", "dagster", "estate-scheduler-d945998bk", "r1", owner="d1")
POD = obj("Pod", "dagster", "estate-scheduler-d945998bkr5v8", "p1", owner="r1")
BY_UID = {"d1": DEPLOY, "r1": RS}


def test_a_pod_is_charged_to_the_path_whose_release_owns_it():
    shadow = load_shadow()
    assert shadow.owned_by(POD, "shadow-platform-dagster", {DAGSTER_RELEASE}, BY_UID)


def test_a_pod_is_not_charged_to_a_path_that_does_not_own_it():
    """#6194: dagster's pod was the stated failure of epistemic-fabric, hindsight and six more."""
    shadow = load_shadow()
    assert not shadow.owned_by(POD, "shadow-platform-epistemic-fabric", set(), BY_UID)


def test_a_pod_whose_workload_the_kustomization_applied_is_charged_to_it():
    shadow = load_shadow()
    deploy = obj(
        "Deployment",
        "jit",
        "jit-broker",
        "d2",
        labels={"kustomize.toolkit.fluxcd.io/name": "shadow-platform-jit"},
    )
    rs = obj("ReplicaSet", "jit", "jit-broker-5b4984d45d", "r2", owner="d2")
    pod = obj("Pod", "jit", "jit-broker-5b4984d45d-kjc9j", "p2", owner="r2")
    by_uid = {"d2": deploy, "r2": rs}
    assert shadow.owned_by(pod, "shadow-platform-jit", set(), by_uid)
    assert not shadow.owned_by(pod, "shadow-platform-dagster", set(), by_uid)


def test_an_owner_cycle_ends_the_walk():
    shadow = load_shadow()
    a = obj("ReplicaSet", "x", "a", "a", owner="b")
    b = obj("ReplicaSet", "x", "b", "b", owner="a")
    assert not shadow.owned_by(a, "shadow-platform-x", set(), {"a": a, "b": b})


def test_the_pod_watch_reports_only_the_paths_own_pods(monkeypatch):
    shadow = load_shadow()
    stuck = dict(POD)
    stuck["status"] = {
        "containerStatuses": [
            {
                "name": "dagster-user-deployments",
                "state": {
                    "waiting": {
                        "reason": "CreateContainerConfigError",
                        "message": 'secret "estate-db-dagster" not found',
                    }
                },
            }
        ]
    }
    lists = {
        "pods": [stuck],
        shadow.OWNER_KINDS: [DEPLOY, RS],
        "helmreleases.helm.toolkit.fluxcd.io": [
            {"metadata": {"namespace": "dagster", "name": "dagster"}}
        ],
    }

    def kube(argv, check=True, timeout=300):
        if argv[0] == "logs":
            return subprocess.CompletedProcess(argv, 1, "", "")
        items = lists[argv[1]]
        if (
            argv[1].startswith("helmreleases")
            and "shadow-platform-dagster" not in argv[-3]
        ):
            items = []
        return subprocess.CompletedProcess(argv, 0, json.dumps({"items": items}), "")

    monkeypatch.setattr(shadow, "kube", kube)
    assert shadow.pod_failures("shadow-platform-dagster"), "the owner lost its own pod"
    assert shadow.pod_failures("shadow-platform-hindsight") == []
    assert len(shadow.pod_failures()) == 1, "ks=None still reads every pod"


# ------------------------------------------------------------------ signature and judge


def test_the_same_failure_on_two_runs_has_one_signature():
    shadow = load_shadow()
    assert len(RUN_6194) == len(RERUN_6194)
    for i, (_, a) in enumerate(RUN_6194):
        b = RERUN_6194[i][1]
        assert shadow.signature(a) == shadow.signature(b), (a, b)


def test_different_failures_keep_different_signatures():
    shadow = load_shadow()
    missing_secret = shadow.signature(DAGSTER_POD)
    pull = shadow.signature(
        DAGSTER_POD.replace("CreateContainerConfigError", "ImagePullBackOff")
    )
    other_secret = shadow.signature(
        DAGSTER_POD.replace("estate-db-dagster", "estate-db-x")
    )
    assert len({missing_secret, pull, other_secret}) == 3


def test_the_record_is_written_into_a_directory_nothing_created(tmp_path):
    """CI passes --record $RUNNER_TEMP/record/<side>.json, and record/ does not exist yet. On
    10-14 write_record raised FileNotFoundError there on both sides, so every pull request
    touching a platform/ dir reached judge with no records and was red for it."""
    shadow = load_shadow()
    for side in ("head", "base"):
        path = tmp_path / "record" / f"{side}.json"
        shadow.write_record(str(path), "abc1234", 1, [("platform/x", "boom")])
        assert json.loads(path.read_text())["failures"][0]["scope"] == "platform/x"


def test_6194_is_green_when_every_failure_is_inherited(tmp_path):
    shadow = load_shadow()
    head = record(tmp_path, "head", "68d1b51", 1, RUN_6194)
    base = record(tmp_path, "base", "10d5e16", 1, RERUN_6194)
    rc, why = shadow.judge(head, base)
    assert (rc, why) == (0, [])


def test_a_failure_the_base_does_not_show_is_the_prs(tmp_path):
    shadow = load_shadow()
    broken = (
        "platform/jit",
        "platform/jit: the environment refused to converge it -- pods past rescue: pod "
        "jit/jit-broker-5b4984d45d-kjc9j container jit is ImagePullBackOff (restarts 0): "
        "ghcr.io/chidionyema/jit:main-14434 not found",
    )
    head = record(tmp_path, "head", "68d1b51", 1, RUN_6194[:2] + [broken])
    base = record(tmp_path, "base", "10d5e16", 1, RERUN_6194)
    rc, why = shadow.judge(head, base)
    assert rc == 1
    assert why == [broken[1]], "only the introduced failure is the PR's"


def test_a_failure_on_another_path_is_not_excused(tmp_path):
    """Same message, different scope: the base failing elsewhere excuses nothing here."""
    shadow = load_shadow()
    sc, msg = RUN_6194[0]
    head = record(tmp_path, "head", "h", 1, [("platform/other", msg)])
    base = record(tmp_path, "base", "b", 1, [(sc, msg)])
    assert shadow.judge(head, base)[0] == 1


def test_a_missing_base_excuses_nothing(tmp_path):
    shadow = load_shadow()
    head = record(tmp_path, "head", "68d1b51", 1, RUN_6194)
    rc, why = shadow.judge(head, str(tmp_path / "absent.json"))
    assert rc == 1 and len(why) == len(RUN_6194)


def test_a_blind_base_excuses_nothing(tmp_path):
    shadow = load_shadow()
    head = record(tmp_path, "head", "68d1b51", 1, RUN_6194)
    base = record(tmp_path, "base", "10d5e16", 2, RERUN_6194)
    assert shadow.judge(head, base)[0] == 1


def test_an_unreadable_base_excuses_nothing(tmp_path):
    shadow = load_shadow()
    head = record(tmp_path, "head", "68d1b51", 1, RUN_6194)
    junk = tmp_path / "base.json"
    junk.write_text("{not json")
    assert shadow.judge(head, str(junk))[0] == 1


def test_no_head_record_is_blind_never_green(tmp_path):
    shadow = load_shadow()
    base = record(tmp_path, "base", "10d5e16", 0, [])
    assert shadow.judge(str(tmp_path / "absent.json"), base)[0] == 2


def test_a_blind_head_is_blind_even_over_a_green_base(tmp_path):
    shadow = load_shadow()
    head = record(tmp_path, "head", "h", 2, [("run", "k3d is not installed")])
    base = record(tmp_path, "base", "b", 0, [])
    assert shadow.judge(head, base)[0] == 2


def test_a_red_head_that_names_no_failure_is_not_green(tmp_path):
    shadow = load_shadow()
    head = record(tmp_path, "head", "h", 1, [])
    base = record(tmp_path, "base", "b", 1, [])
    assert shadow.judge(head, base)[0] == 1


def test_a_run_that_raises_still_leaves_a_blind_record(tmp_path, monkeypatch):
    shadow = load_shadow()
    monkeypatch.setattr(shadow, "have", lambda tool: True)
    monkeypatch.setattr(shadow, "serve_tree", lambda: subprocess.Popen(["true"]))

    def boom(head):
        raise RuntimeError("could not create the shadow source")

    monkeypatch.setattr(shadow, "flux_source", boom)
    out = tmp_path / "head.json"
    try:
        shadow.verify("a" * 40, ["platform/llm"], str(out))
    except RuntimeError:
        pass
    assert json.loads(out.read_text())["rc"] == 2
    assert shadow.judge(str(out), None)[0] == 2


# ------------------------------------------------------------------ the workflow


def workflow():
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]


def test_the_check_other_tools_read_is_the_judge():
    """deploy-when-green and bin/idp-pr-landable read the check named shadow-verify."""
    jobs = workflow()
    judge = jobs["shadow-verify"]
    assert judge.get("name", "shadow-verify") == "shadow-verify"
    assert judge["if"] == "always()"
    assert set(judge["needs"]) == {"scope", "run"}
    script = "\n".join(str(s.get("run", "")) for s in judge["steps"])
    assert "bin/idp-shadow judge" in script
    assert "--head-record" in script and "--base-record" in script


def test_head_and_base_run_side_by_side_and_the_base_is_the_merge_base():
    jobs = workflow()
    assert jobs["run"]["strategy"]["matrix"]["side"] == ["head", "base"]
    assert jobs["run"]["strategy"]["fail-fast"] is False
    scope = "\n".join(str(s.get("run", "")) for s in jobs["scope"]["steps"])
    assert "git merge-base" in scope
    verify = next(s for s in jobs["run"]["steps"] if s.get("id") == "verify")
    assert "--record" in verify["run"]
    assert "IDP_SHADOW_TREE" in verify["env"]


def test_the_signature_ignores_how_many_containers_are_stuck():
    """Run 39935488278: one stuck litellm pod on the base, two on the head, same crash."""
    shadow = load_shadow()
    one = "pods past rescue: pod llm/litellm-c955dc58-4pzhv container litellm is CrashLoopBackOff (restarts 3)"
    two = "pods past rescue: 2 stuck container(s), first: pod llm/litellm-7c797c54f5-67nxb container litellm is CrashLoopBackOff (restarts 4)"
    assert shadow.signature(one) == shadow.signature(two)


def test_the_signature_ignores_the_kubelet_pod_tail():
    """Run 39940650771: same temporal crash on both sides, different pod suffix and uid."""
    shadow = load_shadow()

    def msg(rs, sfx, uid):
        return (
            f"pods past rescue: 4 stuck container(s), first: pod temporal/sovereign-worker-{rs}-{sfx} "
            f"container worker is CrashLoopBackOff (restarts 3): back-off 40s restarting failed "
            f"container=worker pod=sovereign-worker-{rs}-{sfx}_temporal({uid})"
        )

    a = msg("76dd6776cc", "vj4rm", "b9d9e82e-a133-47db-9674-535f1322837b")
    b = msg("5c76858dc9", "bmwxp", "a91a972b-b477-494e-81ab-de09a2b08032")
    assert shadow.signature(a) == shadow.signature(b)


def test_a_key_read_from_a_mounted_file_is_laid(tmp_path, monkeypatch):
    """Run 39948889099: litellm cats LITELLM_DB_PASSWORD from the mount; no secretKeyRef names it."""
    shadow = load_shadow()
    d = tmp_path / "platform" / "llm"
    d.mkdir(parents=True)
    (d / "x.yaml").write_text(
        "metadata:\n  namespace: llm\n"
        "          volumeMounts:\n"
        "            - { name: upstream, mountPath: /run/secrets/litellm/upstream, readOnly: true }\n"
        "      volumes:\n"
        "        - name: upstream\n"
        "          secret: { secretName: litellm-upstream }\n"
        '          x: "$(cat /run/secrets/litellm/upstream/LITELLM_DB_PASSWORD)"\n'
    )
    monkeypatch.setattr(shadow, "REPO", str(tmp_path))
    assert (
        "LITELLM_DB_PASSWORD"
        in shadow.consumer_secret_keys()[("llm", "litellm-upstream")]
    )
