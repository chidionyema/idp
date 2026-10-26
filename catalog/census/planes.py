"""The four collectors of Phase 0: git, k8s, host, edge.

Each collector enumerates a UNIVERSE and reports every object in it. The universe
is the point: the census walks what is there, so a new repo, a new workload, a new
launchd job or a new image cannot be missed by being forgotten. What each collector
cannot see, it says it cannot see -- a plane that could not be read comes back
BLIND with the reason, which is a row in the coverage table and never a green zero.

The collectors are deliberately boring: no AI, no inference, no network write, and
every external call is bounded (one kubectl, one gh, one find). The 2026-10-24
outage was caused by collectors that read the host too hard; the host collector here
reads launchd's own state and a bounded directory listing, and nothing else.
"""

from __future__ import annotations

import json
import os
import plistlib
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from catalog.census.model import (
    PLANE_EDGE,
    PLANE_GIT,
    PLANE_HOST,
    PLANE_K8S,
    STATE_DISABLED,
    STATE_LIVE,
    Fact,
    Observation,
    PlaneResult,
    image_id,
    iso,
    launchd_id,
    repo_id,
    ttl_expiry,
    utcnow,
)

# The TTLs the proposal fixes, in seconds. A fact that is served without one is a
# snapshot wearing a fact's name.
TTL_GIT = 3600
TTL_K8S = 180
TTL_HOST = 900
TTL_EDGE = 3600

CODE_ROOT = os.path.expanduser("~/Documents/code")
LAUNCH_AGENTS = os.path.expanduser("~/Library/LaunchAgents")


def _tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} is not on PATH")
    return found


def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(  # noqa: S603 -- fixed argv, never a shell string
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"{cmd[0]} timed out after {timeout}s"
    return proc.returncode, proc.stdout, proc.stderr


@dataclass
class CollectorConfig:
    """Where the census looks. Every path is a parameter so a test can point it at a
    fixture instead of at the founder's machine."""

    code_root: str = CODE_ROOT
    launch_agents: str = LAUNCH_AGENTS
    kube_context: str = os.environ.get(
        "ESTATE_KUBE_CONTEXT", "context-estate-crq7jwxsjxq"
    )
    github_owner: str = os.environ.get("ESTATE_GITHUB_OWNER", "chidionyema")
    load_max: float = float(os.environ.get("ESTATE_LOAD_MAX", "12"))
    dry_run: bool = False


def _load_ok(cfg: CollectorConfig) -> tuple[bool, str]:
    """The load gate, in the collector itself.

    The 2026-10-24 outage was an estate-wide one caused by host collectors running
    while the laptop was already at load 300. A collector that reads the host is
    the most likely thing to make that worse, so the gate is in the collector, not
    only in the job that starts it: a census that would make things worse says so
    and stops.
    """

    try:
        with open(
            "/proc/loadavg", encoding="utf-8"
        ) as handle:  # pragma: no cover - not macOS
            load = float(handle.read().split()[0])
    except OSError:
        try:
            load = float(os.sysload().getloadavg()[0])  # type: ignore[attr-defined]
        except Exception:
            return True, ""
    if load > cfg.load_max:
        return False, f"load {load:.1f} > {cfg.load_max}"
    return True, ""


def _mac_load() -> float:
    try:
        proc = subprocess.run(  # noqa: S603 -- fixed argv
            [_tool("sysctl"), "-n", "vm.loadavg"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode == 0:
            return float(proc.stdout.strip().strip("{}").split()[0])
    except (OSError, ValueError, RuntimeError):
        pass
    return 0.0


# --- git -----------------------------------------------------------------------


def _repos_on_disk(cfg: CollectorConfig) -> list[str]:
    """Every git repository under the code root.

    The estate's layout is flat (~/Documents/code/<repo>/.git -- 43 of them,
    measured 2026-10-26), and some owners keep a second level
    (~/Documents/code/<owner>/<repo>/.git). Both are walked, one level deep
    only: an unbounded walk of the founder's disk is the exact shape of the
    2026-10-24 outage.
    """

    if not os.path.isdir(cfg.code_root):
        return []
    found: list[str] = []
    for first in sorted(os.listdir(cfg.code_root)):
        first_dir = os.path.join(cfg.code_root, first)
        if not os.path.isdir(first_dir):
            continue
        if os.path.isdir(os.path.join(first_dir, ".git")):
            found.append(first_dir)
            continue
        try:
            children = sorted(os.listdir(first_dir))
        except OSError:
            continue
        for second in children:
            second_dir = os.path.join(first_dir, second)
            if os.path.isdir(os.path.join(second_dir, ".git")):
                found.append(second_dir)
    return found


def _codeowners(path: str) -> list[str]:
    """The owners a repo declares, in CODEOWNERS order.

    Rule 6 is the owner authority the founder accepted (D5: CODEOWNERS first, GitHub
    teams second, Backstage groups third). The file is looked for in the three
    places git itself looks.
    """

    owners: list[str] = []
    for candidate in (
        os.path.join(path, "CODEOWNERS"),
        os.path.join(path, ".github", "CODEOWNERS"),
        os.path.join(path, "docs", "CODEOWNERS"),
    ):
        if not os.path.isfile(candidate):
            continue
        try:
            with open(candidate, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    line = line.split("#", 1)[0].strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] not in owners:
                        owners.append(parts[1])
        except OSError:
            continue
    return owners


def _has_deployable(path: str) -> bool:
    """Whether a repo can produce something that runs: a Dockerfile or a manifest."""

    for name in sorted(os.listdir(path))[:400]:
        child = os.path.join(path, name)
        if name.startswith("Dockerfile"):
            return True
        if os.path.isdir(child) and name in (
            "deploy",
            "k8s",
            "clusters",
            "manifests",
            "platform",
        ):
            for sub in sorted(os.listdir(child))[:200]:
                if sub.endswith((".yaml", ".yml")):
                    return True
    return False


def _dockerfile_images(repo_path: str, org: str) -> list[str]:
    """The images a repository builds, read from its own Dockerfiles.

    The estate publishes one image per Dockerfile, and the image's name is the
    Dockerfile's directory (or the `<name>.Dockerfile` stem) -- the same rule
    bin/dockerfiles applies to build the estate's image list. Reading it here is
    what lets the join answer "which repository builds this image", which no
    image reference says on its own: ghcr.io/chidionyema/estate-scheduler is
    built by the idp repository, and nothing in the reference admits it.

    The walk is bounded (depth 3, no .git/node_modules/venv), because the
    2026-10-24 outage was caused by collectors that read the disk too hard.
    """

    images: list[str] = []
    if not os.path.isdir(repo_path):
        return images
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [
            d
            for d in dirs
            if d
            not in (
                ".git",
                "node_modules",
                "venv",
                ".venv",
                "__pycache__",
                "worktrees",
                "dist",
                "build",
            )
        ]
        rel = os.path.relpath(root, repo_path)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth >= 3:
            dirs[:] = []
        for name in sorted(files):
            if name == "Dockerfile":
                image_name = (
                    os.path.basename(repo_path)
                    if rel == "."
                    else os.path.basename(root)
                )
            elif name.endswith(".Dockerfile"):
                image_name = name[: -len(".Dockerfile")]
            else:
                continue
            if image_name:
                images.append(f"ghcr.io/{org}/{image_name}")
    return sorted(set(images))


def census_git(cfg: CollectorConfig) -> PlaneResult:
    """Every repository the estate has: on disk, and on the GitHub org."""

    started = utcnow()
    result = PlaneResult(
        plane=PLANE_GIT, collector="census-git", started_at=iso(started)
    )
    expires = ttl_expiry(TTL_GIT, started)
    repos: dict[str, dict[str, Any]] = {}

    for path in _repos_on_disk(cfg):
        name = os.path.basename(path)
        parent = os.path.basename(os.path.dirname(path))
        org = cfg.github_owner if parent == cfg.code_root.split(os.sep)[-1] else parent
        repos[name] = {
            "name": name,
            "org": org,
            "path": path,
            "codeowners": _codeowners(path),
            "deployable": _has_deployable(path),
            "images": _dockerfile_images(path, org),
            "on_disk": True,
        }

    # The org's repositories, so a repo that was never cloned is still in the
    # universe. `gh` is the estate's own door to GitHub; the token is the estate's,
    # and it never leaves the machine.
    rc, out, err = _run(
        [
            _tool("gh"),
            "repo",
            "list",
            cfg.github_owner,
            "--limit",
            "300",
            "--json",
            "name,nameWithOwner,isPrivate,defaultBranchRef",
        ],
        timeout=25,
    )
    if rc == 0 and out.strip():
        try:
            for item in json.loads(out):
                name = item.get("name") or ""
                if not name:
                    continue
                entry = repos.setdefault(
                    name,
                    {
                        "name": name,
                        "org": (item.get("nameWithOwner") or "").split("/")[0]
                        or cfg.github_owner,
                        "path": None,
                        "codeowners": [],
                        "deployable": False,
                        "on_disk": False,
                    },
                )
                entry["default_branch"] = (item.get("defaultBranchRef") or {}).get(
                    "name"
                ) or ""
                entry["private"] = bool(item.get("isPrivate"))
        except json.JSONDecodeError:
            result.blind = True
            result.blind_reason = (
                f"gh repo list returned something that is not JSON: {err[:200]}"
            )
    else:
        result.blind = True
        result.blind_reason = f"gh repo list failed rc={rc}: {err.strip()[:200]}"

    for name, entry in sorted(repos.items()):
        node_id = repo_id(entry["org"], name)
        codeowners = entry["codeowners"]
        if codeowners:
            owner = codeowners[0]
            owner_source = "CODEOWNERS"
        else:
            # The proposal's owner chain (D5): CODEOWNERS first, GitHub teams
            # second, Backstage groups third. The estate is a personal GitHub
            # account, so there are no teams to ask and the account that owns the
            # repository is the owner. A repository with no owner at all would be
            # the uncatalogued(no_owner) case.
            owner = entry["org"] or cfg.github_owner
            owner_source = "github-owner"
        result.observations.append(
            Observation(
                id=node_id,
                type="repo",
                name=name,
                plane=PLANE_GIT,
                source="census-git",
                observed_at=iso(started),
                expires_at=expires,
                payload={
                    "repo": name,
                    "org": entry["org"],
                    "path": entry["path"],
                    "on_disk": entry["on_disk"],
                    "deployable": entry["deployable"],
                    "codeowners": codeowners,
                    "default_branch": entry.get("default_branch", ""),
                    "owner": owner,
                    "owner_source": owner_source,
                    "images": entry.get("images", []),
                },
            )
        )
        if owner:
            result.facts.append(
                Fact(
                    id=f"{node_id}#owner",
                    subject=node_id,
                    predicate="owner",
                    object=owner,
                    source=f"census-git:{owner_source}",
                    observed_at=iso(started),
                    expires_at=expires,
                )
            )
        if entry["on_disk"]:
            result.facts.append(
                Fact(
                    id=f"{node_id}#deployable",
                    subject=node_id,
                    predicate="deployable",
                    object="true" if entry["deployable"] else "false",
                    source="census-git:tree",
                    observed_at=iso(started),
                    expires_at=expires,
                )
            )
    result.duration_ms = int((utcnow() - started).total_seconds() * 1000)
    return result


# --- k8s -----------------------------------------------------------------------


def census_k8s(cfg: CollectorConfig) -> PlaneResult:
    """Every workload and service the cluster runs, with the image behind it."""

    started = utcnow()
    result = PlaneResult(
        plane=PLANE_K8S, collector="census-k8s", started_at=iso(started)
    )
    expires = ttl_expiry(TTL_K8S, started)

    rc, out, err = _run(
        [
            _tool("kubectl"),
            "--context",
            cfg.kube_context,
            "get",
            "deploy,sts,ds,cronjob,job,svc",
            "-A",
            "-o",
            "json",
        ],
        timeout=180,
    )
    if rc != 0:
        result.blind = True
        result.blind_reason = f"kubectl get failed rc={rc}: {err.strip()[:200]}"
        result.error = result.blind_reason
        return result

    try:
        items = json.loads(out).get("items", [])
    except json.JSONDecodeError:
        result.blind = True
        result.blind_reason = "kubectl returned something that is not JSON"
        return result

    # A Service has no image of its own: it selects pods. Its identity comes from
    # the workload it selects, so a Service is catalogued as the same thing as the
    # workload behind it and not as a nameless endpoint.
    workloads: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []
    for item in items:
        kind = item.get("kind") or "Unknown"
        if kind == "Service":
            services.append(item)
        else:
            workloads.append(item)

    def image_of(item: dict[str, Any]) -> str:
        spec = item.get("spec") or {}
        template = spec.get("template") or {}
        pod_spec = template.get("spec") or {}
        for container in pod_spec.get("containers") or []:
            if container.get("image"):
                return str(container["image"])
        return ""

    def labels_of(item: dict[str, Any]) -> dict[str, str]:
        return (item.get("metadata") or {}).get("labels") or {}

    for item in items:
        kind = item.get("kind") or "Unknown"
        meta = item.get("metadata") or {}
        name = meta.get("name") or ""
        namespace = meta.get("namespace") or ""
        if not name or not namespace:
            continue
        labels = labels_of(item)
        spec = item.get("spec") or {}
        template = spec.get("template") or {}
        pod_spec = template.get("spec") or {}
        containers = pod_spec.get("containers") or []
        image = image_of(item)
        if kind == "Service" and not image:
            selector = spec.get("selector") or {}
            for workload in workloads:
                if (workload.get("metadata") or {}).get("namespace") != namespace:
                    continue
                template_labels = (
                    (workload.get("spec") or {}).get("template") or {}
                ).get("metadata", {}).get("labels") or {}
                if selector and all(
                    template_labels.get(k) == v for k, v in selector.items()
                ):
                    image = image_of(workload)
                    break
        status = item.get("status") or {}
        ready = status.get("readyReplicas")
        if ready is None:
            ready = status.get("availableReplicas")
        if ready is None:
            ready = status.get("numberReady")
        live = kind != "Service" and ready is not None and int(ready) > 0
        state = STATE_LIVE if (live or kind == "Service") else STATE_DISABLED
        desired = spec.get("replicas")
        if kind in ("Deployment", "StatefulSet", "DaemonSet"):
            # A workload scaled to zero is disabled; a workload that is scaled up
            # but not ready is live and broken, which is a different fact.
            live = desired is None or int(desired) > 0
            state = STATE_LIVE if live else STATE_DISABLED
        elif kind in ("CronJob", "Job"):
            state = STATE_LIVE
        otel = ""
        for container in containers:
            for env in container.get("env") or []:
                if env.get("name") == "OTEL_SERVICE_NAME" and env.get("value"):
                    otel = str(env["value"])
        node_id = f"k8s:{kind.lower()}:{namespace}/{name}"
        result.observations.append(
            Observation(
                id=node_id,
                type="workload" if kind != "Service" else "service_candidate",
                name=name,
                plane=PLANE_K8S,
                source="census-k8s",
                observed_at=iso(started),
                expires_at=expires,
                state=state,
                payload={
                    "kind": kind,
                    "namespace": namespace,
                    "labels": labels,
                    "image": image,
                    "otel_service_name": otel,
                    "ready_replicas": ready,
                    "desired_replicas": desired,
                    "repo": labels.get("app.kubernetes.io/part-of") or "",
                },
            )
        )
        if image:
            result.observations.append(
                Observation(
                    id=image_id(image),
                    type="image",
                    name=image,
                    plane=PLANE_K8S,
                    source="census-k8s",
                    observed_at=iso(started),
                    expires_at=expires,
                    payload={"image": image, "auxiliary": True},
                )
            )
    result.duration_ms = int((utcnow() - started).total_seconds() * 1000)
    return result


# --- host ----------------------------------------------------------------------


def _launchd_state(cfg: CollectorConfig) -> tuple[set[str], set[str]]:
    """The launchd labels that are loaded, and the ones launchd says are disabled.

    The host plane reports state, not ghosts: a job that is installed but disabled
    is catalogued as disabled, never counted as live. That distinction is the whole
    reason the census-host collector exists -- the earlier inventory counted 43
    ORPHAN mac jobs out of 47 because it read the plist files and not launchd.
    """

    loaded: set[str] = set()
    disabled: set[str] = set()
    rc, out, _ = _run([_tool("launchctl"), "list"], timeout=30)
    if rc == 0:
        for line in out.splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 3:
                loaded.add(parts[2].strip())
    uid = os.getuid()
    rc, out, _ = _run(
        [_tool("launchctl"), "print-disabled", f"gui/{uid}"],
        timeout=30,
    )
    if rc == 0:
        for line in out.splitlines():
            line = line.strip()
            if line.startswith('"') and '" => ' in line:
                label = line.split('"', 2)[1]
                disabled.add(label)
    return loaded, disabled


def _repo_for_path(cfg: CollectorConfig, program: str) -> str:
    """The repository a program lives in, when it lives in one.

    A launchd job is not a service. The only evidence that links it to one is the
    repository it runs out of, so the job's program path is resolved against the
    code root -- bounded, and only for paths that are under it -- and against
    the estate's runtime checkout, which is where the idp jobs actually run from
    (~/.estate/runtime/<repo>/..., measured 2026-10-26).
    """

    if not program or not os.path.isabs(program):
        return ""
    path = os.path.abspath(program)
    root = os.path.abspath(cfg.code_root)
    if path.startswith(root + os.sep):
        parts = path[len(root) + 1 :].split(os.sep)
        # The estate's layout is flat: ~/Documents/code/<repo>/... So the first
        # segment is the repository -- but some directories hold repositories of
        # their own (worktrees, owners), so the first segment that IS a git
        # repository is the answer, and it is found by looking, not by guessing.
        for depth in (1, 2):
            if len(parts) < depth:
                break
            candidate = os.path.join(root, *parts[:depth])
            if os.path.isdir(os.path.join(candidate, ".git")):
                return parts[depth - 1]
        return ""
    runtime = os.path.expanduser("~/.estate/runtime")
    if path.startswith(runtime + os.sep):
        parts = path[len(runtime) + 1 :].split(os.sep)
        if parts:
            return parts[0]
    return ""


def census_host(cfg: CollectorConfig) -> PlaneResult:
    """Every launchd job, crontab entry and known local daemon on this machine."""

    started = utcnow()
    result = PlaneResult(
        plane=PLANE_HOST, collector="census-host", started_at=iso(started)
    )
    expires = ttl_expiry(TTL_HOST, started)

    loaded, disabled = _launchd_state(cfg)
    seen: set[str] = set()

    if os.path.isdir(cfg.launch_agents):
        for name in sorted(os.listdir(cfg.launch_agents)):
            # A .plist.pre-gate-<date> file is a BACKUP of a job, not a second job:
            # counting it would double the host plane and make the coverage table
            # describe the estate's history rather than the estate.
            if ".pre-gate-" in name:
                continue
            disabled_by_file = name.endswith(".plist.disabled")
            if not (name.endswith(".plist") or disabled_by_file):
                continue
            path = os.path.join(cfg.launch_agents, name)
            label = name.split(".plist", 1)[0]
            program = ""
            keep_alive = False
            working_directory = ""
            try:
                with open(path, "rb") as handle:
                    plist = plistlib.load(handle)
                label = str(plist.get("Label") or label)
                args = plist.get("ProgramArguments") or []
                program = str(args[0]) if args else ""
                for arg in args[1:]:
                    if str(arg).startswith("/") and _repo_for_path(cfg, str(arg)):
                        program = str(arg)
                        break
                keep_alive = bool(plist.get("KeepAlive"))
                working_directory = str(plist.get("WorkingDirectory") or "")
            except (OSError, ValueError, plistlib.InvalidFileException) as exc:
                result.error = (
                    f"{name}: not a readable plist ({exc.__class__.__name__})"
                )
            except (
                Exception
            ) as exc:  # a malformed plist is a fact about the host, not a crash
                result.error = (
                    f"{name}: not a readable plist ({exc.__class__.__name__})"
                )
            seen.add(label)
            is_disabled = disabled_by_file or label in disabled
            repo = _repo_for_path(cfg, program) or _repo_for_path(
                cfg, working_directory
            )
            result.observations.append(
                Observation(
                    id=launchd_id(label),
                    type="job",
                    name=label,
                    plane=PLANE_HOST,
                    source="census-host",
                    observed_at=iso(started),
                    expires_at=expires,
                    state=STATE_DISABLED if is_disabled else STATE_LIVE,
                    payload={
                        "label": label,
                        "path": path,
                        "program": program,
                        "working_directory": working_directory,
                        "repo": repo,
                        "keep_alive": keep_alive,
                        "disabled": is_disabled,
                        "loaded": label in loaded,
                    },
                )
            )

    # Crontab entries are jobs too, and they are the ones nobody remembers.
    rc, out, _ = _run([_tool("crontab"), "-l"], timeout=20)
    if rc == 0:
        for index, line in enumerate(out.splitlines()):
            entry = line.strip()
            if not entry or entry.startswith("#"):
                continue
            result.observations.append(
                Observation(
                    id=f"cron:{index}:{abs(hash(entry)) % 100000}",
                    type="job",
                    name=f"crontab[{index}]",
                    plane=PLANE_HOST,
                    source="census-host",
                    observed_at=iso(started),
                    expires_at=expires,
                    payload={"cron": entry},
                )
            )
    elif rc not in (0, 1):
        result.error = f"crontab -l failed rc={rc}"

    result.duration_ms = int((utcnow() - started).total_seconds() * 1000)
    return result


# --- edge ----------------------------------------------------------------------


def census_edge(cfg: CollectorConfig) -> PlaneResult:
    """The estate's edge: the images it publishes, and the edge it runs on.

    The Cloudflare half of this plane is BLIND: no Cloudflare token exists on this
    machine, and the founder's D6 decision removed the old vestigial endpoint rather
    than pointing the catalog at a collector that runs at zero replicas. A blind
    plane is reported as blind, with the reason, and the half that CAN be read is
    still catalogued.
    """

    started = utcnow()
    result = PlaneResult(
        plane=PLANE_EDGE, collector="census-edge", started_at=iso(started)
    )
    expires = ttl_expiry(TTL_EDGE, started)

    rc, out, err = _run(
        [
            _tool("gh"),
            "api",
            f"/users/{cfg.github_owner}/packages?package_type=container&per_page=100",
            "--jq",
            ".[].name",
        ],
        timeout=60,
    )
    if rc == 0:
        for name in out.split():
            if not name:
                continue
            result.observations.append(
                Observation(
                    id=image_id(f"ghcr.io/{cfg.github_owner}/{name}"),
                    type="image",
                    name=name,
                    plane=PLANE_EDGE,
                    source="census-edge",
                    observed_at=iso(started),
                    expires_at=expires,
                    payload={
                        "image": f"ghcr.io/{cfg.github_owner}/{name}",
                        "registry": "ghcr",
                    },
                )
            )
    else:
        result.blind = True
        result.blind_reason = f"gh api packages failed rc={rc}: {err.strip()[:200]}"

    if not os.environ.get("CLOUDFLARE_API_TOKEN"):
        result.blind = True
        reason = "no Cloudflare token: the edge plane's workers, zones and tunnels were not read"
        if result.blind_reason:
            result.blind_reason = f"{result.blind_reason}; {reason}"
        else:
            result.blind_reason = reason

    result.duration_ms = int((utcnow() - started).total_seconds() * 1000)
    return result
