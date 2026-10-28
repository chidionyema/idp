#!/usr/bin/env python3
"""telegram-agent-doctor -- is every Telegram agent healthy, which link broke, and what fixes it.

WHY (founder, 2026-10-28): "it needs to be seamless for any agent to monitor live, diagnose and
resolve any issues with any telegram agent/otto."

The estate already has several one-off doors -- voice-doctor walks the voice chain, router-doctor
heals the laptop router, k8s-diag grades the cluster, silence-audit grades alert coverage -- and
three separate probes of Otto: the founder-surfaces probe (the public door is up), the
registration reconciler (the Telegram vendor will deliver to this webhook) and the answer probe
(a real completion comes back). Each answers one question about one surface, and none of them
answers the question an agent actually has:

    is the Telegram agent healthy RIGHT NOW, which link broke, and what fixes it?

This is that door. One call, every Telegram agent, each agent's chain walked in the order a
message meets it, the FIRST broken link named with the fix that repairs it, and -- with
--heal -- that fix applied through the intent layer and the link re-checked afterwards.

WHAT IT DOES NOT DO. It does not replace the three probes: the reconciler still owns the webhook,
the answer probe still asks the real lanes, and both still write their own receipts. This door
reads their truth and adds the one thing they lack -- a single answer, and the first broken
link. A second copy of a probe would be a second layer of the same thing (AGENTS.md, one of each
layer).

THE CHAIN, PER AGENT (the registry below is the ONE place that says what healthy means for a
Telegram agent; nothing else has to know):
  edge          the public door, https://otto.${ESTATE_ZONE}/healthz. Careful: on this host that
                exact path is answered by otto-golden, so this link proves the EDGE, not
                otto-gateway -- otto-gateway has no public health path by design.
  workload      the deployment the bot answers from -- ready replicas, read from the cluster.
  registration  the reconciler's last run. It is the only writer of the webhook (OWNER.yaml) and
                it asks Telegram where the webhook points every five minutes.
  answer        the answer probe's last run: a real completion on every lane the door can route
                to. A door that answers 200 and says nothing is the failure this link exists for.

BLIND IS NOT FAIL. A link whose source cannot be read (the cluster is dark, kubectl times out,
the executor is missing) is BLIND: never a failure, never a pass. The estate's rule that an
unreadable source is not zero, applied to a health door. Exit 3 says "could not tell"; exit 1
says "a link is broken"; exit 0 says every agent is healthy.

EXIT CODES
  0  every Telegram agent's chain is healthy
  1  a link is broken (the first one is named, with its fix)
  2  the registry could not be read (no agent list at all)
  3  blind -- a link could not be read, so health could not be established

Usage
  telegram-agent-doctor.py [--agent ID] [--heal] [--json]
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# The estate's DNS zone. The one place it is written is clusters/oke/estate-config.yaml
# (ESTATE_ZONE: mumchimp.com); every platform file says ${ESTATE_ZONE} and the zone gate
# refuses a literal. This is the fallback for a runtime install that has no checkout to read
# it from and no ESTATE_ZONE in the environment.
ESTATE_ZONE_DEFAULT = "mumchimp.com"

# The one place the zone is written, when this script runs from a checkout.
ZONE_CONFIG_RELATIVE = ("clusters", "oke", "estate-config.yaml")

CLUSTER_TIMEOUT = 20  # a cluster link that cannot be read is blind, not a hang
HEAL_TIMEOUT = 45  # flux reconcile has its own 2m budget; we give up first
HTTP_TIMEOUT = 12

OK = "ok"
FAIL = "FAIL"
BLIND = "BLIND"


def _fix(row: str) -> dict:
    """The sanctioned fix for a drifted row: let Flux re-apply it.

    AGENTS.md is explicit that a hand-applied change is forbidden -- a row that drifted is
    repaired by the reconciler that owns it, through the intent layer, so the repair is
    recorded. clusters/oke names every Flux row after the platform directory it applies
    (clusters/oke/jit.yaml: name jit, path ./platform/jit), so the row for a platform
    directory is that directory's name.
    """
    return {
        "intent": "flux-reconcile",
        "args": {"kind": "kustomization", "name": row, "namespace": "flux-system"},
        "how": "estate-invoke flux-reconcile kind=kustomization name={} namespace=flux-system".format(
            row
        ),
    }


# --------------------------------------------------------------------------------------
# THE REGISTRY. One entry per Telegram-facing agent in the estate, in the order a founder
# would ask about them. Each link is a step in that agent's chain, with what it proves and
# what repairs it.
# --------------------------------------------------------------------------------------
TELEGRAM_AGENTS = [
    {
        "id": "otto-gateway",
        "title": "Otto's Telegram door (the estate's one bot, @Ottototbot)",
        "source": "platform/otto-gateway/OWNER.yaml",
        "links": [
            {
                "id": "edge",
                "kind": "http",
                "url": "https://otto.${ESTATE_ZONE}/healthz",
                "expect": 200,
                "what": "the edge that carries every inbound Telegram event (on this host /healthz is answered by otto-golden, so this proves the edge, not the door)",
                "fix": _fix("otto-gateway"),
            },
            {
                "id": "workload",
                "kind": "ready",
                "resource": "deployments",
                "name": "otto-gateway",
                "namespace": "otto-gateway",
                "min_ready": 1,
                "what": "the deployment the bot answers from",
                "fix": _fix("otto-gateway"),
            },
            {
                "id": "registration",
                "kind": "last_run",
                "resource": "jobs",
                "name_prefix": "otto-registration-reconciler",
                "namespace": "otto-gateway",
                "max_age_min": 15,
                "what": "the vendor's truth: the reconciler is the only writer of the webhook and asks Telegram where it points every five minutes",
                "fix": _fix("otto-gateway"),
            },
            {
                "id": "answer",
                "kind": "last_run",
                "resource": "jobs",
                "name_prefix": "otto-answer-probe",
                "namespace": "otto-gateway",
                "max_age_min": 30,
                "what": "a real completion on every lane the door can route to -- a door that answers 200 and says nothing is the failure this link exists for",
                "fix": _fix("otto-gateway"),
            },
        ],
    },
    {
        "id": "otto-golden",
        "title": "Otto numun (@numun_bot) -- the staging bot; answers /healthz only",
        "source": "platform/otto-golden/httproute.yaml",
        "links": [
            {
                "id": "edge",
                "kind": "http",
                "url": "https://otto.${ESTATE_ZONE}/healthz",
                "expect": 200,
                "what": "the staging bot's own liveness path (this exact path is otto-golden's, so on this host the edge link above and this one agree by design)",
                "fix": _fix("otto-golden"),
            },
            {
                "id": "workload",
                "kind": "ready",
                "resource": "deployments",
                "name": "otto-golden",
                "namespace": "otto-golden",
                "min_ready": 1,
                "what": "the staging deployment",
                "fix": _fix("otto-golden"),
            },
        ],
    },
    {
        "id": "jit-broker",
        "title": "the JIT broker -- reads a mirrored copy of every inbound Telegram POST",
        "source": "platform/otto-gateway/OWNER.yaml",
        "links": [
            {
                "id": "workload",
                "kind": "ready",
                "resource": "deployments",
                "name": "jit-broker",
                "namespace": "jit",
                "min_ready": 1,
                "what": "the broker that must never touch the Bot API and only reads the mirror",
                "fix": _fix("jit"),
            }
        ],
    },
]

# Agents that are NOT Telegram agents, with the declaration that says so. Listed so the door
# can answer "what about hermes-agent?" without a second place to keep the answer in.
DECLARED_OUT = [
    {
        "id": "hermes-agent",
        "why": "its Telegram token is removed (platform/otto-gateway/OWNER.yaml), so it is not a Telegram agent; the gateway runs the same image",
    }
]

# The scheduled plane, READ and not duplicated. The estate already runs otto-parity every
# fifteen minutes (.github/workflows/otto-parity.yml): it mints a kubeconfig, grades both
# Ottos and the layers under them, and alerts the founder on Telegram when the tick turns
# red. That is the scheduler and the alerter. The doctor does not grade the same thing a
# second time -- it reads that verdict and puts it next to its own chain, so there is one
# set of rows and two planes: the scheduled one and the callable one.
SCHEDULED_PLANES = [
    {
        "workflow": "otto-parity.yml",
        "what": "the estate's own 15-minute SLA tick for both Ottos and the layers under them -- it already alerts the founder on Telegram when a tick turns red",
    }
]


# --------------------------------------------------------------------------------------
# Running things through the estate's own layer. Every action this doctor takes goes
# through an intent, so it is recorded the way everything else in the estate is.
# --------------------------------------------------------------------------------------
def executor_path() -> str:
    """The estate executor, if this machine has one."""
    found = shutil.which("estate-execute")
    if found:
        return found
    local = os.path.expanduser("~/.estate/bin/estate-execute")
    return local if os.path.exists(local) else ""


def run_intent(intent: str, args: dict, timeout: int) -> tuple:
    """Run one estate intent. Returns (rc, stdout, stderr, receipt)."""
    exe = executor_path()
    if not exe:
        return (
            127,
            "",
            "the estate executor (estate-execute) is not on this machine",
            "",
        )
    argv = [exe, intent]
    for key, value in args.items():
        argv.append("{}={}".format(key, value))
    try:
        proc = subprocess.run(  # noqa: S603
            argv, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return 124, "", "the intent did not answer in {}s".format(timeout), ""
    except OSError as exc:
        return 127, "", "the intent could not be started: {}".format(exc), ""
    receipt = ""
    for line in (proc.stderr or "").splitlines():
        if "ticket=" in line:
            receipt = line.split("ticket=", 1)[1].strip()
            break
    return proc.returncode, proc.stdout or "", proc.stderr or "", receipt


def probe_workflow(workflow: str) -> tuple:
    """The last verdict of a scheduled workflow -- the scheduled plane, read.

    The verdict is context, not a link in the chain: the tick grades the Ottos AND the
    layers under them, so a red tick is not proof about a Telegram agent. It is reported,
    with its run, next to the chain this doctor walked.
    """
    path = "actions/workflows/{}/runs?per_page=1".format(workflow)
    rc, out, err, _receipt = run_intent(
        "gh-api", {"path": path, "params": "--jq .workflow_runs[0].conclusion"}, 30
    )
    if rc == 124:
        return BLIND, "the workflow API did not answer in 30s"
    if rc != 0:
        lines = (err or out or "").strip().splitlines()
        return BLIND, "the workflow API did not answer: {}".format(
            (lines[-1] if lines else "")[:160]
        )
    lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
    verdict = lines[-1] if lines else ""
    if not verdict:
        return BLIND, "{} has never run".format(workflow)
    if verdict == "success":
        return OK, "the last tick of {} was green".format(workflow)
    if verdict == "failure":
        return FAIL, "the last tick of {} was red".format(workflow)
    if verdict == "cancelled":
        return BLIND, "the last tick of {} was cancelled -- it measured nothing".format(
            workflow
        )
    return BLIND, "the last tick of {} was {}".format(workflow, verdict)


# --------------------------------------------------------------------------------------
# Probes. Each returns (status, detail). A probe never raises: an unreadable source is
# BLIND, and that is the whole point of the BLIND state.
# --------------------------------------------------------------------------------------
def resolve_zone() -> str:
    """The estate's DNS zone, from the environment, the checkout, or the declared default."""
    zone = os.environ.get("ESTATE_ZONE", "").strip()
    if zone:
        return zone
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    config = os.path.join(root, *ZONE_CONFIG_RELATIVE)
    if os.path.exists(config):
        try:
            with open(config, "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip().startswith("ESTATE_ZONE:"):
                        return line.split(":", 1)[1].strip().strip('"')
        except OSError:
            pass
    return ESTATE_ZONE_DEFAULT


def probe_http(link: dict, zone: str) -> tuple:
    """Read a public path. The only link that can be read without the cluster."""
    url = link["url"].replace("${ESTATE_ZONE}", zone)
    started = time.time()
    try:
        request = urllib.request.Request(  # noqa: S310 - https only, from the registry
            url, headers={"User-Agent": "telegram-agent-doctor/1"}
        )
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:  # noqa: S310
            code = response.getcode()
            elapsed = time.time() - started
            if code == link.get("expect", 200):
                return OK, "{} in {:.2f}s  {}".format(code, elapsed, url)
            return FAIL, "{} (expected {}) in {:.2f}s  {}".format(
                code, link.get("expect", 200), elapsed, url
            )
    except urllib.error.HTTPError as exc:
        return FAIL, "{} from {} in {:.2f}s  {}".format(
            exc.code, url, time.time() - started, url
        )
    except Exception as exc:  # noqa: BLE001 - any unreadable source is blind, not a crash
        return BLIND, "{}: {} in {:.2f}s  {}".format(
            type(exc).__name__, exc, time.time() - started, url
        )


def _items(payload: object) -> list:
    """kubectl answers with one object or a list; both become a list here."""
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _parse_time(value: str):
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def probe_cluster(link: dict) -> tuple:
    """Read one link's truth from the cluster, through the estate's read-only kubectl intent."""
    args = {
        "resource": link["resource"],
        "namespace": link["namespace"],
        "output": "json",
    }
    rc, out, err, _receipt = run_intent("kubectl", args, CLUSTER_TIMEOUT)
    if rc == 124:
        return BLIND, "the cluster did not answer in {}s".format(CLUSTER_TIMEOUT)
    if rc != 0:
        detail = (err or out or "").strip().splitlines()
        tail = detail[-1] if detail else "no detail"
        return BLIND, "the kubectl intent did not answer: {}".format(tail[:200])
    try:
        payload = json.loads(out)
    except ValueError:
        return BLIND, "kubectl did not answer with json"

    if link["kind"] == "ready":
        for item in _items(payload):
            if item.get("metadata", {}).get("name") != link["name"]:
                continue
            status = item.get("status", {})
            ready = int(status.get("readyReplicas") or 0)
            desired = int(status.get("replicas") or 0)
            if ready >= link.get("min_ready", 1):
                return OK, "{}/{} ready  deployment/{}".format(
                    ready, desired, link["name"]
                )
            return FAIL, "{}/{} ready  deployment/{}".format(
                ready, desired, link["name"]
            )
        return FAIL, "deployment/{} is not in {} at all".format(
            link["name"], link["namespace"]
        )

    if link["kind"] == "last_run":
        prefix = link["name_prefix"]
        jobs = [
            item
            for item in _items(payload)
            if str(item.get("metadata", {}).get("name", "")).startswith(prefix)
        ]
        if not jobs:
            return FAIL, "no job named {}* has ever run in {}".format(
                prefix, link["namespace"]
            )
        jobs.sort(
            key=lambda item: (
                item.get("metadata", {}).get("creationTimestamp", "") or ""
            ),
            reverse=True,
        )
        newest = jobs[0]
        name = newest.get("metadata", {}).get("name", prefix)
        status = newest.get("status", {})
        succeeded = int(status.get("succeeded") or 0)
        failed = int(status.get("failed") or 0)
        finished = _parse_time(
            status.get("completionTime")
            or newest.get("metadata", {}).get("creationTimestamp", "")
        )
        age_min = None
        if finished is not None:
            age_min = (
                datetime.now(timezone.utc) - finished.astimezone(timezone.utc)
            ).total_seconds() / 60.0
        if succeeded < 1:
            return FAIL, "the last run of {} failed ({} failed, {} succeeded)".format(
                name, failed, succeeded
            )
        if age_min is not None and age_min > link.get("max_age_min", 30):
            return (
                FAIL,
                "the last run of {} succeeded {:.0f}m ago (stale: over {}m)".format(
                    name, age_min, link.get("max_age_min", 30)
                ),
            )
        if age_min is None:
            return OK, "{} succeeded (age unknown)".format(name)
        return OK, "{} succeeded {:.0f}m ago".format(name, age_min)

    return BLIND, "the registry names a link kind this doctor does not know: {}".format(
        link["kind"]
    )


# --------------------------------------------------------------------------------------
# The walk. Pure functions: they take a probe and a healer, so a test can drive them with
# no cluster, no network and no executor.
# --------------------------------------------------------------------------------------
def walk(agent: dict, probe) -> dict:
    """Walk one agent's chain. Stops at the first broken link; a blind link does not stop
    the walk (a later link may still be broken, and that is the more actionable fact)."""
    results = []
    broken = None
    blind = None
    cluster_blind = ""
    for link in agent["links"]:
        if link["kind"] in ("ready", "last_run") and cluster_blind:
            status, detail = BLIND, cluster_blind
        else:
            status, detail = probe(link)
            if status == BLIND and link["kind"] in ("ready", "last_run"):
                cluster_blind = detail
        row = {
            "id": link["id"],
            "kind": link["kind"],
            "what": link.get("what", ""),
            "status": status,
            "detail": detail,
            "fix": link.get("fix"),
        }
        results.append(row)
        if status == FAIL and broken is None:
            broken = row
            break
        if status == BLIND and blind is None:
            blind = row
    return {
        "id": agent["id"],
        "title": agent.get("title", agent["id"]),
        "source": agent.get("source", ""),
        "links": results,
        "first_broken": broken,
        "first_blind": blind,
    }


def diagnose(agents: list, probe, scheduled=None) -> dict:
    """Walk every agent's chain and summarise."""
    reports = [walk(agent, probe) for agent in agents]
    planes = []
    for plane in SCHEDULED_PLANES:
        status, detail = (
            scheduled(plane["workflow"]) if scheduled else (BLIND, "not read")
        )
        planes.append(
            {
                "workflow": plane["workflow"],
                "what": plane["what"],
                "status": status,
                "detail": detail,
            }
        )
    broken = [report for report in reports if report["first_broken"]]
    blind = [
        report
        for report in reports
        if not report["first_broken"] and report["first_blind"]
    ]
    healthy = [
        report
        for report in reports
        if not report["first_broken"] and not report["first_blind"]
    ]
    return {
        "when": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zone": resolve_zone(),
        "agents": reports,
        "declared_out": DECLARED_OUT,
        "scheduled": planes,
        "counts": {
            "agents": len(reports),
            "healthy": len(healthy),
            "broken": len(broken),
            "blind": len(blind),
        },
    }


def heal(report: dict, row: dict, healer, probe) -> dict:
    """Apply one link's declared fix through the intent layer, then re-read the link."""
    fix = row.get("fix") or {}
    intent = fix.get("intent")
    args = fix.get("args") or {}
    if not intent:
        return {
            "intent": "",
            "args": {},
            "receipt": "",
            "status": BLIND,
            "detail": "this link declares no fix",
            "after": BLIND,
            "after_detail": "this link declares no fix",
        }
    receipt, status, detail = healer(intent, args)
    after = probe(row)
    return {
        "intent": intent,
        "args": args,
        "receipt": receipt,
        "status": status,
        "detail": detail,
        "after": after[0],
        "after_detail": after[1],
    }


# --------------------------------------------------------------------------------------
# The CLI.
# --------------------------------------------------------------------------------------
def render(report: dict) -> str:
    lines = []
    lines.append(
        "telegram-agent-doctor  {}  zone={}".format(report["when"], report["zone"])
    )
    lines.append("")
    for agent in report["agents"]:
        lines.append("{}  {}".format(agent["id"], agent["title"]))
        for row in agent["links"]:
            lines.append(
                "  {:<5} {:<13} {}".format(row["status"], row["id"], row["detail"])
            )
        if agent["first_broken"]:
            broken = agent["first_broken"]
            fix = broken.get("fix") or {}
            lines.append(
                "  FIRST BROKEN LINK: {} -- {}".format(broken["id"], broken["what"])
            )
            lines.append(
                "  FIX: {}  {}".format(
                    fix.get("intent", "?"),
                    " ".join(
                        "{}={}".format(k, v) for k, v in (fix.get("args") or {}).items()
                    ),
                )
            )
        elif agent["first_blind"]:
            blind = agent["first_blind"]
            lines.append(
                "  FIRST UNREADABLE LINK: {} -- {} ({})".format(
                    blind["id"], blind["what"], blind["detail"]
                )
            )
        else:
            lines.append("  healthy: every link in the chain answered")
        lines.append("")
    for out in report["declared_out"]:
        lines.append("not a Telegram agent: {} -- {}".format(out["id"], out["why"]))
    if report.get("scheduled"):
        lines.append("")
        lines.append("the scheduled plane (read, not graded again):")
        for plane in report["scheduled"]:
            lines.append(
                "  {:<5} {:<16} {}".format(
                    plane["status"], plane["workflow"], plane["detail"]
                )
            )
    counts = report["counts"]
    lines.append(
        "{} agents: {} healthy, {} broken, {} blind".format(
            counts["agents"], counts["healthy"], counts["broken"], counts["blind"]
        )
    )
    return "\n".join(lines)


def default_probe(link: dict) -> tuple:
    """The real probe: a public path, or the cluster."""
    if link["kind"] == "http":
        return probe_http(link, resolve_zone())
    return probe_cluster(link)


def make_probe():
    """The real probe, with one piece of state: the cluster is ONE source.

    When the cluster does not answer, every cluster link in the run is blind for the same
    reason -- so the run waits for that answer once, not once per agent. A blind source that
    is asked again is the same blind source asked again.
    """
    state = {"cluster_blind": ""}

    def probe(link: dict) -> tuple:
        if link["kind"] == "http":
            return probe_http(link, resolve_zone())
        if state["cluster_blind"]:
            return BLIND, state["cluster_blind"]
        status, detail = probe_cluster(link)
        if status == BLIND:
            state["cluster_blind"] = detail
        return status, detail

    return probe


def default_healer(intent: str, args: dict) -> tuple:
    """The real heal: one estate intent, and its receipt."""
    rc, out, err, receipt = run_intent(intent, args, HEAL_TIMEOUT)
    detail = (out or err or "").strip().splitlines()
    tail = detail[-1] if detail else ""
    status = OK if rc == 0 else FAIL
    return receipt, status, "exit {}: {}".format(rc, tail[:200])


def main(argv: list) -> int:
    args = list(argv[1:])
    only = ""
    want_heal = False
    as_json = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--agent" and index + 1 < len(args):
            only = args[index + 1]
            index += 2
            continue
        if arg == "--heal":
            want_heal = True
        elif arg == "--json":
            as_json = True
        index += 1

    agents = TELEGRAM_AGENTS
    if only and only != "all":
        agents = [agent for agent in TELEGRAM_AGENTS if agent["id"] == only]
        if not agents:
            print(
                "ERROR: no Telegram agent named {} in the registry ({})".format(
                    only, ", ".join(a["id"] for a in TELEGRAM_AGENTS)
                )
            )
            return 2

    report = diagnose(agents, make_probe(), scheduled=probe_workflow)

    if want_heal:
        for agent in report["agents"]:
            row = agent.get("first_broken")
            if not row:
                continue
            result = heal(agent, row, default_healer, default_probe)
            agent["heal"] = result
            row["healed"] = result

    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render(report))
        for agent in report["agents"]:
            result = agent.get("heal")
            if not result:
                continue
            print("")
            print(
                "HEAL {}: {} -> {} ({})".format(
                    agent["id"],
                    result["status"],
                    result["after"],
                    result["receipt"] or "no receipt",
                )
            )
            print("  {}".format(result["after_detail"]))

    if report["counts"]["broken"]:
        return 1
    if report["counts"]["blind"]:
        return 3
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(130)
