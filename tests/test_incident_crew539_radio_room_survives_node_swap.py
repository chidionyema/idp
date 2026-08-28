"""Incident 2026-08-27 (crew#539): the oke-check surge swapped the node, the surviving node was CPU
starved, telemetry-coverage, cluster-state and the gateway sat Pending on "Insufficient cpu" and
langfuse answered 503 for nine minutes. Nothing paged: the only alert was a Flux reconcile event
raised from inside the cluster that was starving. Founder: "how come monitoring and alerts and
traces didn't detect this, what happened to autoscaling".

The fix is three Kubernetes-native primitives (founder spec, verbatim on crew#539) plus a guard:
balloon pods the scheduler preempts for headroom, an infrastructure-critical PriorityClass on the
radio-room set, an out-of-cluster ping that posts to Telegram, and a Kyverno policy that refuses
any of the radio-room set that drops the class (traefik joined it on crew#555). This file is the offline proof of each; no sockets.
"""
import pathlib
import re

import yaml

IDP = pathlib.Path(__file__).resolve().parents[1]
SCHED = IDP / "platform/scheduling"
RADIO_ROOM = {
    # crew#555: the front door joined the set. Every hostname the founder can open enters through
    # this pod; a radio room nobody can reach is not a radio room.
    "traefik": "platform/edge/traefik.yaml",
    "langfuse-web": "platform/observability/langfuse.yaml",
    "langfuse-worker": "platform/observability/langfuse.yaml",
    "agentgateway": "platform/mcp/agentgateway-deploy.yaml",
    "hermes-agent-gateway": "platform/hermes-agent/gateway.yaml",
    "telemetry-coverage": "platform/observability/telemetry-coverage.yaml",
    "cluster-state": "platform/state/cluster-state.yaml",
}
NODE_MILLICPU = 4000  # one 4 OCPU node (platform/keda/keda.yaml sizing note)


def docs(rel):
    return [d for d in yaml.safe_load_all((IDP / rel).read_text()) if d]


def test_priority_classes_are_the_founders_values():
    by_name = {d["metadata"]["name"]: d for d in docs("platform/scheduling/priorityclasses.yaml")}
    assert by_name["infrastructure-critical"]["value"] == 1000000
    assert by_name["balloon"]["value"] == -1
    assert by_name["balloon"]["preemptionPolicy"] == "Never", "a balloon must never evict a real pod"
    assert not any(d.get("globalDefault") for d in by_name.values())


def test_balloon_reserves_ten_to_twenty_percent_of_the_node_and_is_preemptible():
    (dep,) = docs("platform/scheduling/balloon.yaml")
    pod = dep["spec"]["template"]["spec"]
    assert pod["priorityClassName"] == "balloon"
    (c,) = pod["containers"]
    assert c["image"].startswith("registry.k8s.io/pause:"), "k8s.gcr.io is frozen"
    m = re.fullmatch(r"(\d+)m", c["resources"]["requests"]["cpu"])
    total = int(m.group(1)) * dep["spec"]["replicas"]
    assert 0.10 * NODE_MILLICPU <= total <= 0.20 * NODE_MILLICPU, total


def test_radio_room_set_and_nothing_else_carries_infrastructure_critical():
    for name, rel in RADIO_ROOM.items():
        text = (IDP / rel).read_text()
        assert "priorityClassName: infrastructure-critical" in text, f"{name} in {rel}"
    carriers = {
        p.relative_to(IDP).as_posix()
        for p in (IDP / "platform").rglob("*.yaml")
        if "priorityClassName: infrastructure-critical" in p.read_text()
        and p.relative_to(IDP).as_posix() != "platform/scheduling/require-priority-class.yaml"
    }
    assert carriers == set(RADIO_ROOM.values()), "the founder said strictly"


def test_langfuse_patches_seat_both_web_and_worker():
    (hr,) = [d for d in docs("platform/observability/langfuse.yaml") if d["kind"] == "HelmRelease"]
    patches = hr["spec"]["postRenderers"][0]["kustomize"]["patches"]
    seated = {
        p["target"]["name"]
        for p in patches
        if yaml.safe_load(p["patch"]).get("spec", {}).get("template", {}).get("spec", {}).get("priorityClassName")
        == "infrastructure-critical"
    }
    assert seated == {"langfuse-web", "langfuse-worker"}


def test_kyverno_policy_enforces_the_six_and_only_audits_the_rest():
    (pol,) = docs("platform/scheduling/require-priority-class.yaml")
    rules = {r["name"]: r for r in pol["spec"]["rules"]}
    critical = rules["radio-room-set-is-critical"]
    assert critical["validate"]["failureAction"] == "Enforce"
    assert set(critical["match"]["any"][0]["resources"]["names"]) == set(RADIO_ROOM)
    assert rules["platform-workload-names-a-class"]["validate"]["failureAction"] == "Audit", (
        "LAW 38: flip to Enforce only after a zero-violation pass, the crew#341 way"
    )


def test_flux_rows_seat_the_class_before_anyone_names_it():
    rows = {d["metadata"]["name"]: d for d in docs("clusters/oke/platform.yaml")}
    assert rows["scheduling"]["spec"]["path"] == "./platform/scheduling"
    assert rows["healing"]["spec"]["path"] == "./platform/healing"
    for row in ("observability", "mcp", "hermes-agent", "cluster-state"):
        deps = {d["name"] for d in rows[row]["spec"].get("dependsOn", [])}
        assert "scheduling" in deps, row
    assert {d["name"] for d in rows["healing"]["spec"]["dependsOn"]} >= {"scheduling", "llm"}
    kust = yaml.safe_load((SCHED / "kustomization.yaml").read_text())
    assert set(kust["resources"]) == {"namespace.yaml", "priorityclasses.yaml", "balloon.yaml", "require-priority-class.yaml", "capacity-affinity.yaml", "require-availability.yaml"}


def test_ping_lives_outside_the_cluster_and_pages_the_existing_bot():
    text = (IDP / ".github/workflows/ping.yml").read_text()
    wf = yaml.safe_load(text)
    assert wf[True]["schedule"] == [{"cron": "*/5 * * * *"}]
    assert "secrets.SEED_HERMES_TELEGRAM_BOT_TOKEN" in text and "secrets.SEED_HERMES_TELEGRAM_HOME_CHANNEL" in text
    assert "backstage/founder/catalog-info.yaml" in text, "one list, the portal's"
    assert "-o /dev/null" in text and "curl -sI" not in text and " -I " not in text, "GET, never HEAD"
    assert not re.search(r"bot\d{6,}:", text), "no bot token literal"
    assert not re.search(r"chat_id=-?\d{5,}", text), "no chat id literal"
    assert "steps.prev.outputs.conclusion == 'failure'" in text, "recovery message after a red tick"
