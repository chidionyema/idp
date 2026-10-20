#!/usr/bin/env python3
"""One parameterised path from "serve <label>.<zone>" to the files Flux converges.

WHY THIS EXISTS. Standing up meridian by hand took FOUR merged fixes after the site itself was
already written, and not one was a bug in the application. Each was a declaration missing from a
*different* shared file, and each failed in a way that pointed somewhere else:

  #6503  the listener that names the hostname lives in prospector, not here. The HTTPRoute was
         Accepted, the Service answered 200 inside the namespace, and the public name was a
         Traefik 404 because no listener had claimed it.
  #6511  cert-manager could not open port 80 or 443 to reach itself for the HTTP-01 self-check, so
         the certificate stayed RequestChanged and HTTPS could not be trusted.
  #6513  edge could not reach the new namespace, so the public request hung *after* a completed TLS
         handshake -- a dropped packet, not a 502, because Traefik's SYN never arrived.
  #6518  cert-manager had no `ingress_from: [edge]`, so the self-check's return packet was dropped
         by default-deny and every challenge timed out with "context deadline exceeded" while the
         same URL answered 200 from the node.

All four are the estate's one-direction-only declaration defect, and all four are mechanically
derivable from a name and a hostname. So they are derived here once instead of rediscovered per
site. That is the whole job of this file.

WHAT IT DOES NOT DO. It never talks to the cluster: Flux is the only writer (AGENTS.md section 2),
so this writes files into the worktree and prints the one command that submits them. It does not
scaffold the application either -- repo, tests, CI, scanners and guards are the Backstage golden
path (docs/specs/self-service-golden-paths.md). This is the platform half of the same ask.

    site-onboard.py plan   --name <name> [params]     what would change (the default)
    site-onboard.py write  --name <name> [params]     write it into the worktree
    site-onboard.py verify --name <name>              read-only gate: every declaration present?

Runbook: docs/runbooks/new-site.md. Requirement: docs/reference/requirements/site-onboarding.md.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - the executor image carries pyyaml
    sys.stderr.write(
        "REFUSED: site-onboard needs pyyaml (python3 -m pip install pyyaml)\n"
    )
    raise SystemExit(2) from None

ZONE = "${ESTATE_ZONE}"
NAME_RE = re.compile(r"^[a-z]([a-z0-9]*(-[a-z0-9]+)*)?$")
LABEL_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
# A namespace list, not a security boundary: adopting a name a platform layer already owns would
# generate a second, conflicting declaration for the same object. Picking another label is free.
RESERVED = {
    "kube-system",
    "kube-public",
    "kube-node-lease",
    "default",
    "flux-system",
    "edge",
    "monitoring",
    "observability",
    "cert-manager",
    "kyverno",
    "external-secrets",
    "sealed-secrets",
    "traefik",
    "prospector",
    "identity",
    "llm",
    "backstage",
    "nats",
    "postgres",
    "temporal",
    "ns-fences",
    "image-automation",
}
REPO_MARKERS = ("clusters/oke/estate-config.yaml", "platform/estate/intents")


class Refused(Exception):
    """A refusal is a verdict, not a crash: REFUSED and exit 2, like every door here."""


def refuse(msg: str) -> None:
    raise Refused(msg)


def find_repo(explicit: str) -> Path:
    """The idp checkout, found rather than assumed.

    The executor's cwd is not a promise, so an explicit --repo wins, then $IDP_ROOT, then a walk up
    from the cwd, then the one conventional path. The markers are two files that exist only in a
    full idp checkout, so a stray subdirectory is refused instead of half-populated.
    """
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("IDP_ROOT"):
        candidates.append(Path(os.environ["IDP_ROOT"]).expanduser())
    here = Path.cwd()
    candidates.extend([here, *here.parents])
    candidates.append(Path.home() / "Documents" / "code" / "idp")
    for cand in candidates:
        if all((cand / marker).exists() for marker in REPO_MARKERS):
            return cand.resolve()
    refuse("cannot find an idp checkout; pass --repo /path/to/idp")


def parse_bool(text) -> bool:
    if isinstance(text, bool):
        return text
    return str(text).strip().lower() in ("1", "true", "yes", "on")


def params(ns) -> dict:
    """Validate everything before a single byte is written.

    Every refusal here is a value that would otherwise reach the cluster and fail there, where the
    error names the object rather than the mistake: a namespace that never schedules, a quota that
    refuses the pod, a probe that fails forever, a listener that cannot exist.
    """
    name = (ns.name or "").strip()
    if not name:
        refuse("--name is required: it is the namespace, the Service and the image")
    if not NAME_RE.match(name) or len(name) > 40:
        refuse(
            f"--name {name!r}: use a DNS-1123 label (lowercase, digits, '-', max 40)"
        )
    if name in RESERVED:
        refuse(f"--name {name!r}: a platform layer already owns that namespace")

    hostname = (ns.hostname or "").strip()
    if hostname:
        if "." in hostname or "*" in hostname or "$" in hostname:
            refuse(
                f"--hostname {hostname!r}: give the label only ({ZONE} is appended). A literal "
                "hostname is refused by bin/estate-zone-gate."
            )
        if not LABEL_RE.match(hostname) or len(hostname) > 63:
            refuse(f"--hostname {hostname!r}: not a DNS label")

    if ns.kind not in ("website", "api"):
        refuse(f"--kind {ns.kind!r}: website | api")

    try:
        port = int(ns.port)
    except (TypeError, ValueError):
        refuse(f"--port {ns.port!r}: not an integer")
    if not 1 <= port <= 65535:
        refuse(f"--port {port}: outside 1-65535")

    try:
        replicas = int(ns.replicas)
    except (TypeError, ValueError):
        refuse(f"--replicas {ns.replicas!r}: not an integer")
    if replicas < 1:
        refuse("--replicas 0: a Deployment with no pod serves nothing")
    if ns.tier not in ("founder-facing", "internal"):
        refuse(f"--tier {ns.tier!r}: founder-facing | internal")
    # Kyverno `founder-facing-runs-two` (crew#555) is Enforce: the cluster refuses this anyway, and
    # it should be refused here, where the message can say why.
    if ns.tier == "founder-facing" and replicas < 2:
        refuse(
            f"--replicas {replicas} with --tier founder-facing: the cluster policy "
            "founder-facing-runs-two refuses it (one pod is one node event away from a 503, "
            "catalogue 2026-08-28 06:20Z). Use --replicas 2 or --tier internal."
        )
    if ns.runtime not in ("always-on", "scale-to-zero"):
        refuse(f"--runtime {ns.runtime!r}: always-on | scale-to-zero")
    if ns.runtime == "scale-to-zero" and ns.tier == "founder-facing":
        refuse(
            "scale-to-zero on a founder-facing surface: a cold start is a first impression "
            "(AGENTS.md section 8). Place it with the free-tier ladder instead."
        )

    image = (ns.image or "").strip() or f"ghcr.io/chidionyema/{name}"
    if "/" not in image:
        refuse(f"--image {image!r}: give a full repository path")

    health = (ns.health_path or "").strip() or (
        "/" if ns.kind == "website" else "/healthz"
    )
    if not health.startswith("/"):
        refuse(f"--health-path {health!r}: must start with /")

    for flag, value in (
        ("cpu-request", ns.cpu_request),
        ("memory-request", ns.memory_request),
        ("cpu-limit", ns.cpu_limit),
        ("memory-limit", ns.memory_limit),
    ):
        if not re.match(r"^[0-9]+(m|Mi|Gi|M|G)?$", str(value)):
            refuse(f"--{flag} {value!r}: a quantity such as 60m, 160Mi, 1Gi")

    secret_entry = (ns.secret_entry or "").strip()
    if secret_entry and not NAME_RE.match(secret_entry):
        refuse(f"--secret-entry {secret_entry!r}: a vault entry name (DNS-1123 label)")

    contact = (ns.contact or "").strip()
    if contact not in ("", "telegram"):
        refuse(f"--contact {contact!r}: telegram, or omit for none")
    if contact and secret_entry:
        refuse(
            "--contact telegram and --secret-entry both name the site's one Secret; pick one"
        )

    return {
        "name": name,
        "hostname": hostname,
        "zone_host": f"{hostname}.{ZONE}" if hostname else "",
        "kind": ns.kind,
        "container": "web" if ns.kind == "website" else "api",
        "port": port,
        "image": image,
        "replicas": replicas,
        "tier": ns.tier,
        "runtime": ns.runtime,
        "health_path": health,
        "cpu_request": ns.cpu_request,
        "memory_request": ns.memory_request,
        "cpu_limit": ns.cpu_limit,
        "memory_limit": ns.memory_limit,
        "secret_entry": secret_entry,
        "contact": contact,
        "has_secret": bool(secret_entry or contact),
        "cert_secret": ns.cert_secret,
        "force": parse_bool(ns.force),
    }


# --------------------------------------------------------------------------------------------------
# the generated files


def ns_manifest(p: dict) -> str:
    edge = '    idp.estate/edge-attach: "true"\n' if p["hostname"] else ""
    edge_note = (
        "#\n# The edge-attach label is what lets the shared Gateway reach this namespace at all: every\n"
        "# HTTPS listener on prospector-edge allows routes only from namespaces carrying it\n"
        "# (allowedRoutes.namespaces.from: Selector), so a route in a namespace without it is\n"
        "# Accepted by no listener and the public name answers Traefik's default 404.\n"
        if p["hostname"]
        else "#\n# No edge-attach label: this site publishes no hostname, so no listener selects it. The label\n"
        "# and the hostname are added together or not at all -- an attachable namespace with no route\n"
        "# is a listener selector that matches nothing.\n"
    )
    return f"""# {p["name"]}: the namespace everything else in this row lives in.
#
# Namespace, Service, Deployment and image all carry the same name, so there is one string to look
# up when a request is not answered. The estate's repeated cost is a name spelled four ways that
# matches in none of them.
{edge_note}apiVersion: v1
kind: Namespace
metadata:
  annotations:
    # Never garbage-collected by Flux: a namespace dropped from git stays, with everything in it
    # (portal 404, 2026-08-29 01:05Z, idp#648).
    kustomize.toolkit.fluxcd.io/prune: disabled
  name: {p["name"]}
  labels:
    # The pod either runs as a non-root user with a read-only root filesystem, or it does not run.
    pod-security.kubernetes.io/enforce: restricted
    availability.idp/tier: {p["tier"]}
{edge}"""


def telegram_secret_manifest(p: dict) -> str:
    return f"""# The contact form's destination is Telegram: Otto numun (@numun_bot) posting to the founder's chat.
# Both values already live in the vault and are read by name, so there is nothing to seed and
# nothing in git names a bot or a chat. They are mounted as the two files web/lib/contact.ts reads,
# TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID. If either entry is ever missing this object reports an
# error and creates nothing; the Deployment mounts the Secret optionally, so the site serves every
# page and the form answers 503 `delivery_not_configured` rather than accepting a lead it would drop.
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: {p["name"]}
  namespace: {p["name"]}
spec:
  refreshInterval: 10m
  secretStoreRef: {{kind: ClusterSecretStore, name: estate-vault}}
  target:
    name: {p["name"]}
    creationPolicy: Owner
  data:
    - secretKey: TELEGRAM_BOT_TOKEN
      remoteRef: {{key: otto-staging-telegram, property: token}}
    - secretKey: TELEGRAM_CHAT_ID
      remoteRef: {{key: notify-apprise-founder-telegram, property: chat}}
"""


def vault_secret_manifest(p: dict) -> str:
    if p["contact"] == "telegram":
        return telegram_secret_manifest(p)
    return f"""# The vault entry {p["secret_entry"]}, read by External Secrets Operator over the cluster store.
#
# `dataFrom: extract` takes the entry whole, so every property of {p["secret_entry"]} becomes one key
# of the Secret and one file under the mount, and nothing in git names a key. That is deliberate:
# `target.template` with a plain `data:` list is refused by the API server ("either data or dataFrom
# should be specified") and was the shape that failed meridian's first reconcile.
#
# Until the entry exists this object reports an error and creates nothing. That is the honest state,
# not a misconfiguration: the Deployment mounts the Secret optionally, so the site serves and any
# endpoint that needs the secret answers 503 instead of accepting work it would drop.
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: {p["name"]}
  namespace: {p["name"]}
spec:
  refreshInterval: 10m
  secretStoreRef: {{kind: ClusterSecretStore, name: estate-vault}}
  target:
    name: {p["name"]}
    creationPolicy: Owner
  dataFrom:
    - extract: {{key: {p["secret_entry"]}}}
"""


def deployment_manifest(p: dict) -> str:
    name = p["name"]
    replicas_note = (
        "  # crew#555: a founder-facing Deployment runs at least 2, and they must not share a node --\n"
        "  # one pod is one node event away from a 503 (catalogue, 2026-08-28 06:20Z).\n"
        if p["tier"] == "founder-facing"
        else "  # Internal: one replica is allowed. The cluster policy refuses a single replica only on a\n"
        "  # founder-facing surface (founder-facing-runs-two, crew#555).\n"
    )
    volumes = "        - name: tmp\n          emptyDir: {}\n"
    mounts = "            - {name: tmp, mountPath: /tmp}\n"
    if p["kind"] == "website":
        volumes = (
            "        # readOnlyRootFilesystem: true, so every path the server writes goes here. A\n"
            "        # Next-style server writes optimized images under .next/cache.\n"
            "        - name: cache\n          emptyDir: {}\n" + volumes
        )
        mounts = "            - {name: cache, mountPath: /app/.next/cache}\n" + mounts
    secret_mount = secret_volume = secret_env = ""
    if p["has_secret"]:
        upper = name.upper().replace("-", "_")
        secret_mount = (
            f"            # Every property of the site's Secret is a file here.\n"
            f"            - {{name: secrets, mountPath: /etc/{name}-secrets, readOnly: true}}\n"
        )
        secret_volume = (
            "        # optional: the site serves before the vault entry exists; an endpoint that\n"
            "        # needs it refuses rather than accepts-and-drops.\n"
            "        - name: secrets\n          secret:\n"
            f"            secretName: {name}\n            optional: true\n"
        )
        secret_env = (
            f"            - {{name: {upper}_SECRETS_DIR, value: /etc/{name}-secrets}}\n"
        )
    credential = (
        "a secret arrives as a mounted file (kyverno refuses it as an env var)"
        if p["has_secret"]
        else "this service needs no secret"
    )
    return f"""# {name}: the workload the route points at.
#
# One Service so the route has a backend, one Deployment so the Service has endpoints. Nothing here
# holds a credential: {credential}.
apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {name}
  labels:
    app.kubernetes.io/name: {name}
    # require-catalogue-entity (Enforce) refuses a Service that serves a port without naming its
    # catalogue entity. The entity is backstage/platform/catalog-info.yaml's {name}, written by
    # site-onboard beside this file.
    backstage.io/kubernetes-id: {name}
spec:
  selector:
    app.kubernetes.io/name: {name}
  ports:
    - name: http
      port: 80
      targetPort: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {name}
  labels:
    app.kubernetes.io/name: {name}
spec:
{replicas_note}  replicas: {p["replicas"]}
  selector:
    matchLabels:
      app.kubernetes.io/name: {name}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {name}
        backstage.io/kubernetes-id: {name}
    spec:
      # The package is private (build-multiarch sets no visibility), so every pull needs this
      # Secret. pull-secret.yaml creates it here from the ghcr-pull cluster store, so no laptop has
      # to exist for a node to pull.
      imagePullSecrets:
        - name: ghcr-pull
      topologySpreadConstraints:
        # Two replicas on one node are one replica. DoNotSchedule rather than ScheduleAnyway: a
        # spread that is allowed to fail is not a spread.
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: {name}
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        fsGroup: 65532
        seccompProfile: {{type: RuntimeDefault}}
      containers:
        - name: {p["container"]}
          image: {p["image"]}
          ports:
            - {{name: http, containerPort: {p["port"]}}}
          env:
{secret_env}            # The estate's one collector (LAW 50). Unset on a laptop, where there is none.
            - {{name: OTEL_EXPORTER_OTLP_ENDPOINT, value: "http://signoz-otel-collector.observability.svc:4318"}}
            - name: POD_NAMESPACE
              valueFrom: {{fieldRef: {{fieldPath: metadata.namespace}}}}
          # The probe asks for what a person asks for, not a dedicated route that can stay green
          # while the real page is broken.
          readinessProbe:
            httpGet: {{path: {p["health_path"]}, port: http}}
            periodSeconds: 20
            failureThreshold: 3
          livenessProbe:
            httpGet: {{path: {p["health_path"]}, port: http}}
            periodSeconds: 60
            failureThreshold: 3
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: {{drop: [ALL]}}
          resources:
            requests: {{cpu: {p["cpu_request"]}, memory: {p["memory_request"]}}}
            limits: {{cpu: {p["cpu_limit"]}, memory: {p["memory_limit"]}}}
          volumeMounts:
{secret_mount}{mounts}      volumes:
{secret_volume}{volumes}"""


def door_manifest(p: dict) -> str:
    return f"""# {p["name"]}'s address from anywhere: {p["hostname"]}.{ZONE}.
#
# The hostname is a token, substituted at reconcile time from clusters/oke/estate-config.yaml, so no
# literal hostname is written down on this path (bin/estate-zone-gate refuses one -- the zone moves
# with the estate, so a hard-coded name is a name that stops resolving).
#
# The listener is the one site-onboard added to platform/edge/prospector-gateway.yaml. That listener
# is what puts this hostname on a certificate: cert-manager issues one certificate whose SANs are
# the hostnames of the listeners naming it, so a new hostname costs a listener and a re-issue, not a
# new certificate. This route attaches to that listener, which is why the namespace carries
# idp.estate/edge-attach.
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: {p["name"]}
  namespace: {p["name"]}
  labels:
    backstage.io/kubernetes-id: {p["name"]}
spec:
  parentRefs:
    - name: prospector-edge
      namespace: prospector
      sectionName: https-{p["hostname"]}
  hostnames:
    - "{p["zone_host"]}"
  rules:
    # Everything. This is one application serving its own pages and API out of one process; a path
    # list here would be a second copy of the app's routing table, and every route added to the app
    # would need this file reopened.
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: {p["name"]}
          port: 80
"""


def pull_secret_manifest(p: dict) -> str:
    return f"""# ghcr-pull for this namespace, from the cluster store rather than from a laptop
# (platform/image-automation/pull-secret.yaml, crew#396). Same shape as platform/llm/pull-secret.yaml.
#
# bin/idp-flux-bootstrap writes a pull secret from a laptop into a fixed list of namespaces, and
# {p["name"]} is not one of them: a namespace that pulls from ghcr must not need a laptop to exist,
# which is the whole point of the cluster-scoped store.
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: ghcr-pull
  namespace: {p["name"]}
spec:
  refreshInterval: 10m
  secretStoreRef: {{kind: ClusterSecretStore, name: ghcr-pull}}
  target:
    name: ghcr-pull
    creationPolicy: Owner
    template:
      type: kubernetes.io/dockerconfigjson
  data:
    - secretKey: .dockerconfigjson
      remoteRef: {{key: ghcr-pull, property: .dockerconfigjson}}
"""


def kustomization_manifest(p: dict) -> str:
    marker = '{"$imagepolicy": "flux-system:' + p["name"] + ':tag"}'
    resources = ["namespace.yaml"]
    if p["hostname"]:
        resources.append("public-door.yaml")
    if p["has_secret"]:
        resources.append("vault-secret.yaml")
    resources += ["pull-secret.yaml", "deployment.yaml"]
    listed = "\n".join(f"  - {r}" for r in resources)
    return f"""apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
# Explicit rather than a top-level namespace transform: the HTTPRoute names a parent Gateway in
# another namespace and the ExternalSecrets name cluster-scoped stores, so the objects that do not
# live in {p["name"]} are named by their own files and left alone.
resources:
{listed}
images:
  # Set by Flux image automation, never by hand. A typed tag rots: cyrus sat in ImagePullBackOff
  # from the day it was applied because its Deployment asked for a `:main` tag that was never
  # pushed (platform/image-automation/cyrus.yaml).
  - name: {p["image"]}
    newTag: main-0-bootstrap # {marker}
"""


def flux_row_manifest(p: dict) -> str:
    runtime = (
        "    # A surface that is asked for by name must be up. Always-on rather than scale-to-zero: the\n"
        "    # founder sends clients here, so a cold start is a first impression.\n"
        if p["runtime"] == "always-on"
        else "    # Scale-to-zero: nothing asks for this by name, so it costs nothing while idle. KEDA\n"
        "    # scales it from the trigger it declares (AGENTS.md section 8, the ladder's rung 6).\n"
    )
    return f"""# {p["name"]}: platform/{p["name"]}, converged like every other row.
#
# The zone is substituted here from the one ConfigMap that holds it
# (clusters/oke/estate-config.yaml) and the image tag comes from the ImagePolicy in
# platform/image-automation/{p["name"]}.yaml. Nothing on this path is typed by hand.
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  annotations:
{runtime}    idp.estate.io/runtime: {p["runtime"]}
  name: {p["name"]}
  namespace: flux-system
spec:
  interval: 30s
  retryInterval: 1m
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./platform/{p["name"]}
  prune: true
  wait: true
  timeout: 2m
  postBuild:
    substituteFrom:
      - kind: ConfigMap
        name: estate-config
"""


def image_automation_manifest(p: dict) -> str:
    return f"""# {p["name"]}'s image. build-multiarch discovers web/{p["name"]}.Dockerfile on its own --
# bin/dockerfiles names a `<name>.Dockerfile` by its stem -- and pushes `main-<run>-<sha>` like every
# other estate image. This row is what moves platform/{p["name"]}/kustomization.yaml onto each one.
#
# No tag is typed anywhere: the kustomization carries the `$imagepolicy` marker and Flux writes the
# tag. Until the first image is pushed the Deployment sits in ImagePullBackOff with
# `main-0-bootstrap`, which is the honest bootstrap state and not a misconfiguration.
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImageRepository
metadata:
  name: {p["name"]}
  namespace: flux-system
spec:
  image: {p["image"]}
  interval: 5m
  secretRef:
    name: ghcr-pull
---
apiVersion: image.toolkit.fluxcd.io/v1
kind: ImagePolicy
metadata:
  name: {p["name"]}
  namespace: flux-system
spec:
  imageRepositoryRef:
    name: {p["name"]}
  filterTags:
    pattern: '^main-(?P<run>[0-9]+)-[0-9a-f]{{40}}$'
    extract: '$run'
  policy:
    numerical:
      order: asc
"""


def catalogue_entry(p: dict) -> str:
    title = "API" if p["kind"] == "api" else "site"
    where = f" at {p['hostname']}.{ZONE}" if p["hostname"] else ""
    return f"""---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: {p["name"]}
  title: '{p["name"]} (the {title})'
  description: >-
    {p["name"]}: the {title} served from platform/{p["name"]}{where}, one always-on
    {p["container"]} server behind the estate edge.
  tags: [platform]
spec:
  type: service
  lifecycle: production
"""


def gateway_listener(p: dict) -> str:
    return f"""    - name: https-{p["hostname"]}
      hostname: {p["zone_host"]}
      port: 8443
      protocol: HTTPS
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              idp.estate/edge-attach: "true"
      tls:
        mode: Terminate
        certificateRefs:
          - group: ""
            kind: Secret
            name: {p["cert_secret"]}
"""


def ns_flow_entry(p: dict) -> str:
    return f"""  {p["name"]}:
    # {p["name"]}.{ZONE} is served by an HTTPRoute in this namespace, so edge must reach it and it
    # must admit edge back. Both halves or neither: a one-direction-only declaration is cut by
    # default-deny and presents as a request that hangs after a completed TLS handshake, not as a
    # 502 (meridian, 2026-10-18 -- Traefik's SYN never arrived and nothing sent a reset).
    ingress_from: [edge]
"""


# --------------------------------------------------------------------------------------------------
# shared-file edits: precise text insertion, never a YAML round-trip


def _insert_before(
    text: str, anchor: str, block: str, what: str, first: bool = False
) -> str:
    """Insert `block` immediately before the single line matching `anchor` (a regex).

    A round-trip through yaml.safe_dump would be simpler and would delete every comment in the
    target file -- and in this estate the comments are the memory of which outage produced each
    line. So the edit is textual, anchored, and refused when the anchor is not unique: a silently
    wrong insertion into the Gateway costs every hostname on it.
    """
    lines = text.splitlines(True)
    hits = [i for i, line in enumerate(lines) if re.match(anchor, line)]
    if not hits or (len(hits) != 1 and not first):
        refuse(
            f"{what}: expected {'at least one' if first else 'a single'} line matching "
            f"{anchor!r}, found {len(hits)}"
        )
    lines.insert(hits[0], block)
    return "".join(lines)


def _insert_resource_row(text: str, item: str, what: str) -> str:
    """Append `  - <item>` to the `resources:` list of a kustomization.

    clusters/oke/kustomization.yaml states that an unlisted file there is silently not applied and,
    with prune, its objects are deleted. So the row is written by the same step that writes the
    file, rather than left as a note for later.
    """
    lines = text.splitlines(True)
    # re.search, not re.match: re.match anchors at position 0 however re.M is set, so it only found
    # the row when pulsera.yaml happened to be the FIRST resource -- and every re-run then appended
    # the row again. Found by the second-write test, which is the only test that can see it.
    if re.search(rf"^  - {re.escape(item)}\s*$", text, re.M):
        return text
    starts = [i for i, line in enumerate(lines) if re.match(r"^resources:\s*$", line)]
    if len(starts) != 1:
        refuse(f"{what}: expected one `resources:` line, found {len(starts)}")
    start = starts[0]
    # Walk the contiguous block only. A later key has rows of its own (`patches:` holds
    # `- target:`), and appending after the last of THOSE writes the new file into a patch body --
    # which is a broken kustomization, and it was found on the real file the first time this ran.
    at = start + 1
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if re.match(r"^  - ", line):
            at = i + 1
        elif not line.strip() or line.lstrip().startswith("#"):
            pass
        else:
            break
        i += 1
    lines.insert(at, f"  - {item}\n")
    return "".join(lines)


def _append_to_flow_list(text: str, owner: str, key: str, value: str, what: str) -> str:
    """Add `value` to the last position of `<owner>:` -> `key: [...]`, single- or multi-line.

    allowances.yaml's lists are hand-wrapped and carry a comment per entry, so the closing bracket
    is found by scanning rather than assumed to be on the key's line (edge's egress list spans 20
    lines of prose).
    """
    lines = text.splitlines(True)
    owners = [
        i
        for i, line in enumerate(lines)
        if re.match(rf"^  {re.escape(owner)}:\s*$", line)
    ]
    if len(owners) != 1:
        refuse(f"{what}: expected one `  {owner}:` block, found {len(owners)}")
    start = owners[0]
    opens = [
        i
        for i, line in enumerate(lines)
        if i > start and re.match(rf"^    {key}: \[", line)
    ]
    if not opens:
        refuse(f"{what}: {owner} has no `{key}: [` list to extend")
    open_at = opens[0]
    # Comment lines in this file talk about brackets -- "declares `ingress_from: [edge]` to match
    # this side" is one -- so the closing bracket is only the first NON-comment line that holds
    # one. Grading that naively put the new namespace inside a comment, which is invalid YAML and
    # was caught by the plan's own strict parse before anything was written.
    close_at = None
    for i in range(open_at, len(lines)):
        if lines[i].lstrip().startswith("#"):
            continue
        if "]" in lines[i]:
            close_at = i
            break
    if close_at is None:
        refuse(f"{what}: {owner}.{key} never closes its list")
    line = lines[close_at]
    pos = line.rindex("]")
    body, tail = line[:pos], line[pos:]
    if not body.rstrip().endswith(("[", ",")):
        body = body.rstrip() + ","
    indent = re.match(r"^\s*", line).group(0)
    lines[close_at] = body + "\n" + indent + value + tail
    return "".join(lines)


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses a repeated mapping key.

    PyYAML keeps the last of two identical keys and says nothing. On a 700-line allowances.yaml a
    second `edge:` block would replace the first silently, and every fence generated from it would
    be wrong without one line of output saying so.
    """

    def construct_mapping(self, node, deep=False):
        seen = []
        for key_node, _value in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                refuse(f"duplicate key {key!r} at line {key_node.start_mark.line + 1}")
            seen.append(key)
        return super().construct_mapping(node, deep=deep)


def strict_load_all(text: str) -> list:
    return [d for d in yaml.load_all(text, Loader=_StrictLoader) if isinstance(d, dict)]


# --------------------------------------------------------------------------------------------------
# plan / write


def site_files(p: dict) -> dict:
    """Every NEW file for one site, keyed by path relative to the repo root."""
    name = p["name"]
    files = {
        f"platform/{name}/namespace.yaml": ns_manifest(p),
        f"platform/{name}/deployment.yaml": deployment_manifest(p),
        f"platform/{name}/pull-secret.yaml": pull_secret_manifest(p),
        f"platform/{name}/kustomization.yaml": kustomization_manifest(p),
        f"clusters/oke/{name}.yaml": flux_row_manifest(p),
        f"platform/image-automation/{name}.yaml": image_automation_manifest(p),
    }
    if p["hostname"]:
        files[f"platform/{name}/public-door.yaml"] = door_manifest(p)
    if p["has_secret"]:
        files[f"platform/{name}/vault-secret.yaml"] = vault_secret_manifest(p)
    for rel, content in files.items():
        try:
            if not list(yaml.safe_load_all(content)):
                refuse(f"generated {rel} is empty")
        except yaml.YAMLError as exc:
            refuse(f"generated {rel} is not valid YAML: {exc}")
    return files


def check_target_free(repo: Path, p: dict) -> None:
    d = repo / "platform" / p["name"]
    if d.exists() and any(d.iterdir()) and not p["force"]:
        refuse(
            f"platform/{p['name']}/ already exists and is not empty; pass force=true to overwrite "
            "(a second site on one namespace is the duplicate-layer defect, AGENTS.md section 6)"
        )


def plan_edits(repo: Path, p: dict) -> list:
    """The declarations that live in shared files, as (path, new_text, description) triples."""
    name = p["name"]
    edits = []
    for rel, item in (
        ("clusters/oke/kustomization.yaml", f"{name}.yaml"),
        ("platform/image-automation/kustomization.yaml", f"{name}.yaml"),
    ):
        path = repo / rel
        if not path.exists():
            refuse(f"{rel} is missing from this checkout")
        edits.append(
            (
                rel,
                _insert_resource_row(path.read_text(), item, rel),
                f"resources += {item}",
            )
        )

    catalogue = repo / "backstage/platform/catalog-info.yaml"
    if not catalogue.exists():
        refuse("backstage/platform/catalog-info.yaml is missing")
    text = catalogue.read_text()
    if not re.search(rf"^  name: {re.escape(name)}$", text, re.M):
        edits.append(
            (
                "backstage/platform/catalog-info.yaml",
                text + catalogue_entry(p),
                f"component {name}",
            )
        )

    if not p["hostname"]:
        return edits

    gateway = repo / "platform/edge/prospector-gateway.yaml"
    if not gateway.exists():
        refuse("platform/edge/prospector-gateway.yaml is missing")
    gateway_text = gateway.read_text()
    listeners = (strict_load_all(gateway_text)[0].get("spec") or {}).get(
        "listeners"
    ) or []
    hostnames = [l.get("hostname") for l in listeners]
    if p["zone_host"] not in hostnames:
        # first=True: every listener starts with `    - name: https-`, so the anchor is repeated on
        # purpose and uniqueness is the wrong test. Listener order carries no meaning in the
        # Gateway API; the new one goes before the first HTTPS listener.
        edits.append(
            (
                "platform/edge/prospector-gateway.yaml",
                _insert_before(
                    gateway_text,
                    r"^    - name: https-",
                    gateway_listener(p),
                    "prospector-gateway.yaml",
                    first=True,
                ),
                f"listener https-{p['hostname']}",
            )
        )

    allowances = repo / "platform/ns-fences/allowances.yaml"
    if not allowances.exists():
        refuse("platform/ns-fences/allowances.yaml is missing")
    text = allowances.read_text()
    flows = strict_load_all(text)[0].get("flows") or {}
    if name in flows:
        # A second `meridian:` block would be a duplicate mapping key: PyYAML keeps the last one and
        # the generated fences follow whichever it kept. Extending a hand-written entry is a
        # judgement call about that namespace's other traffic, so it is refused rather than guessed.
        if "edge" not in ((flows.get(name) or {}).get("ingress_from") or []):
            refuse(
                f"allowances.yaml already has a flows.{name} entry without edge; extend it by hand "
                "(this generator will not add ingress_from to a hand-written block)"
            )
    else:
        text = _insert_before(
            text, r"^  edge:\s*$", ns_flow_entry(p), "allowances flows"
        )
    if name not in ((flows.get("edge") or {}).get("egress") or []):
        text = _append_to_flow_list(
            text, "edge", "egress", name, "allowances edge.egress"
        )
    edits.append(
        (
            "platform/ns-fences/allowances.yaml",
            text,
            f"edge<->{name} both halves, then bin/idp-ns-fence-gen",
        )
    )
    return edits


def run(repo: Path, p: dict, write: bool) -> int:
    check_target_free(repo, p)
    files = site_files(p)
    edits = plan_edits(repo, p)
    for rel, text, description in edits:
        # The plan is graded before it is printed, not after it is written: an insertion that turns
        # the Gateway or the allowances file into invalid or ambiguous YAML must be refused while
        # the repository is still untouched.
        try:
            strict_load_all(text)
        except (yaml.YAMLError, ValueError) as exc:
            refuse(f"{rel} would not parse after '{description}': {exc}")
    verb = "CREATE" if write else "WOULD CREATE"
    print(f"site-onboard {'write' if write else 'plan'}: {p['name']}")
    if p["hostname"]:
        print(f"  address    {p['zone_host']} (shared cert {p['cert_secret']})")
    else:
        print("  address    none -- internal only, no listener and no allowance")
    print(f"  image      {p['image']}  replicas {p['replicas']}  tier {p['tier']}")
    for rel in sorted(files):
        print(f"  {verb} {rel}")
    for rel, _text, description in edits:
        print(f"  {'EDIT' if write else 'WOULD EDIT'} {rel}: {description}")
    if not write:
        print("\nNothing was written. Re-run with mode=write, then site-verify.")
        return 0

    for rel, content in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    for rel, text, _description in edits:
        (repo / rel).write_text(text)

    fence_gen = repo / "bin/idp-ns-fence-gen"
    if fence_gen.exists() and p["hostname"]:
        result = subprocess.run(
            [str(fence_gen)], cwd=str(repo), capture_output=True, text=True
        )
        tail = (result.stdout or result.stderr).strip().splitlines()[-1:] or [""]
        print(
            f"  {'ok  ' if result.returncode == 0 else 'FAIL'} bin/idp-ns-fence-gen {tail[0]}"
        )
    print(
        "\nWritten. Flux is the only writer of the cluster, so the next step is a lane:"
    )
    print("  estate-execute lane-submit  (Claim: #<issue>  Agent: <name>)")
    print(f"  estate-execute site-verify  name={p['name']}")
    return 0


# --------------------------------------------------------------------------------------------------
# verify: a read-only gate, graded from the tree rather than from these arguments


def _docs(path: Path) -> list:
    if not path.exists():
        return []
    return [d for d in yaml.safe_load_all(path.read_text()) if isinstance(d, dict)]


def _first(path: Path) -> dict:
    docs = _docs(path)
    return docs[0] if docs else {}


def verify(repo: Path, name: str) -> int:
    """Every declaration one public site needs, checked in the tree.

    This exists because the four fixes were each *somewhere else*: grading the site's own folder
    would have passed while the public address answered 404, 502 or nothing at all. A check that
    only reads the files this generator wrote cannot fail on the defect this generator exists to
    prevent.
    """
    results = []

    def add(label: str, ok: bool, detail: str = "") -> None:
        results.append((label, bool(ok), detail))

    site = repo / "platform" / name
    required = [
        "namespace.yaml",
        "deployment.yaml",
        "pull-secret.yaml",
        "kustomization.yaml",
    ]
    missing = [f for f in required if not (site / f).exists()]
    add(f"manifests in platform/{name}/", not missing, ", ".join(missing))
    if missing:
        return report(name, results)

    ns = _first(site / "namespace.yaml")
    labels = (ns.get("metadata") or {}).get("labels") or {}
    annotations = (ns.get("metadata") or {}).get("annotations") or {}
    add(
        "namespace: restricted + never pruned",
        labels.get("pod-security.kubernetes.io/enforce") == "restricted"
        and annotations.get("kustomize.toolkit.fluxcd.io/prune") == "disabled",
    )

    deployment_docs = {d.get("kind"): d for d in _docs(site / "deployment.yaml")}
    service = deployment_docs.get("Service") or {}
    deployment = deployment_docs.get("Deployment") or {}
    pod_spec = ((deployment.get("spec") or {}).get("template") or {}).get("spec") or {}
    replicas = (deployment.get("spec") or {}).get("replicas") or 1
    tier = labels.get("availability.idp/tier", "")
    add(
        "replica floor (founder-facing-runs-two)",
        tier != "founder-facing" or replicas >= 2,
        f"tier={tier} replicas={replicas}",
    )
    spread = pod_spec.get("topologySpreadConstraints") or []
    add(
        "spread across nodes (DoNotSchedule)",
        any(s.get("whenUnsatisfiable") == "DoNotSchedule" for s in spread),
    )
    add(
        "pulls with the cluster store's secret",
        any(
            s.get("name") == "ghcr-pull"
            for s in (pod_spec.get("imagePullSecrets") or [])
        ),
    )

    kust_text = (site / "kustomization.yaml").read_text()
    kust = yaml.safe_load(kust_text) or {}
    marker = '{"$imagepolicy": "flux-system:' + name + ':tag"}'
    add("image tag is Flux-owned, not typed", marker in kust_text)
    listed = kust.get("resources") or []
    absent = [r for r in listed if not (site / r).exists()]
    add("kustomization lists only real files", not absent, ", ".join(absent))
    image = ((kust.get("images") or [{}])[0] or {}).get("name", "")

    row = _first(repo / "clusters/oke" / f"{name}.yaml")
    row_spec = row.get("spec") or {}
    substitutes = (row_spec.get("postBuild") or {}).get("substituteFrom") or []
    add(
        "flux row converges platform/<name>",
        row_spec.get("path") == f"./platform/{name}",
    )
    add(
        "flux row substitutes the zone",
        any(s.get("name") == "estate-config" for s in substitutes),
    )
    add(
        "flux row is listed",
        f"  - {name}.yaml" in (repo / "clusters/oke/kustomization.yaml").read_text(),
    )

    automation = _docs(repo / "platform/image-automation" / f"{name}.yaml")
    add(
        "image automation tracks that image",
        bool(automation) and (automation[0].get("spec") or {}).get("image") == image,
        f"image={image}",
    )
    add(
        "image automation is listed",
        f"  - {name}.yaml"
        in (repo / "platform/image-automation/kustomization.yaml").read_text(),
    )
    add(
        "catalogue entity exists (require-catalogue-entity)",
        bool(
            re.search(
                rf"^  name: {re.escape(name)}$",
                (repo / "backstage/platform/catalog-info.yaml").read_text(),
                re.M,
            )
        ),
    )

    door = site / "public-door.yaml"
    if door.exists():
        route = _first(door)
        route_spec = route.get("spec") or {}
        hosts = route_spec.get("hostnames") or []
        parent = (route_spec.get("parentRefs") or [{}])[0]
        section = parent.get("sectionName")
        gateway = yaml.safe_load(
            (repo / "platform/edge/prospector-gateway.yaml").read_text()
        )
        listeners = {
            l.get("name"): l for l in (gateway.get("spec") or {}).get("listeners") or []
        }
        listener = listeners.get(section) or {}
        add(
            "route attaches to a declared listener",
            bool(listener),
            f"sectionName={section}",
        )
        add(
            "listener claims the route's hostname",
            bool(listener) and listener.get("hostname") in hosts,
            f"listener={listener.get('hostname')} route={hosts}",
        )
        add(
            "listener terminates TLS with a certificate",
            bool((listener.get("tls") or {}).get("certificateRefs")),
        )
        add(
            "namespace is attachable to the edge",
            labels.get("idp.estate/edge-attach") == "true",
        )
        backend = ((route_spec.get("rules") or [{}])[0].get("backendRefs") or [{}])[0]
        ports = [p.get("port") for p in (service.get("spec") or {}).get("ports") or []]
        add(
            "route backend is the service's port",
            backend.get("port") in ports,
            f"backend={backend.get('port')} service={ports}",
        )

        flows = (
            yaml.safe_load((repo / "platform/ns-fences/allowances.yaml").read_text())
            or {}
        ).get("flows") or {}
        add(
            "edge may reach the site (flows.edge.egress)",
            name in ((flows.get("edge") or {}).get("egress") or []),
        )
        # Two different facts, kept apart on purpose. bin/idp-ns-fence-gen's own one_sided()
        # grader only calls a namespace cut when BOTH halves participate; a namespace with no fence
        # at all is not cut, it is simply unfenced, and it is a separate finding (the next check).
        fenced = name in flows
        add(
            "the site admits edge back (no one-direction cut)",
            (not fenced)
            or "edge" in ((flows.get(name) or {}).get("ingress_from") or []),
            ""
            if not fenced
            else "fenced and does not admit edge: a hang after the TLS handshake",
        )
        fence_file = repo / "platform/ns-fences/network" / f"{name}.yaml"
        add(
            "namespace is fenced from the one input file",
            fenced and fence_file.exists(),
            "no flows entry: nothing denies this namespace, so edge reaches it by accident "
            "rather than by declaration -- add the entry and run bin/idp-ns-fence-gen"
            if not fenced
            else (
                f"run bin/idp-ns-fence-gen to write {fence_file.name}"
                if not fence_file.exists()
                else ""
            ),
        )

    zone = ""
    for doc in _docs(repo / "clusters/oke/estate-config.yaml"):
        zone = (doc.get("data") or {}).get("ESTATE_ZONE") or zone
    literal = [
        f.name for f in sorted(site.glob("*.yaml")) if zone and zone in f.read_text()
    ]
    add(
        f"no literal {zone or 'zone'} in the site's files",
        not literal,
        ", ".join(literal),
    )

    return report(name, results)


def report(name: str, results: list) -> int:
    failed = [r for r in results if not r[1]]
    for label, ok, detail in results:
        if ok:
            print(f"ok   {label}")
        else:
            print(f"FAIL {label}" + (f" -- {detail}" if detail else ""))
    if failed:
        print(
            f"\nREFUSED {name}: {len(failed)} of {len(results)} declarations missing or wrong"
        )
        return 1
    print(f"\nVERIFIED {name}: {len(results)}/{len(results)} declarations present")
    return 0


# --------------------------------------------------------------------------------------------------
# cli


def add_site_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--hostname", default="", help=f"label only; {ZONE} is appended"
    )
    parser.add_argument("--kind", default="website", choices=["website", "api"])
    parser.add_argument("--port", default="8080")
    parser.add_argument("--image", default="")
    parser.add_argument("--replicas", default="2")
    parser.add_argument("--tier", default="founder-facing")
    parser.add_argument("--health-path", default="")
    parser.add_argument("--cpu-request", default="60m")
    parser.add_argument("--memory-request", default="160Mi")
    parser.add_argument("--cpu-limit", default="300m")
    parser.add_argument("--memory-limit", default="384Mi")
    parser.add_argument("--secret-entry", default="")
    parser.add_argument(
        "--contact",
        default="",
        help="telegram: contact form delivers via Otto numun to the founder's chat",
    )
    parser.add_argument("--cert-secret", default="prospector-edge-tls")
    parser.add_argument("--runtime", default="always-on")
    parser.add_argument("--repo", default="")
    parser.add_argument(
        "--force", default="false", help="overwrite an existing platform/<name>"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else ""
    )
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("plan", "write"):
        add_site_args(sub.add_parser(mode))
    checker = sub.add_parser("verify")
    # The same parameters, accepted and ignored: an intent renders one command for every mode, and a
    # verify call that died on "unrecognized arguments" would be a door that only opens if the
    # caller already knew which mode took which flag.
    add_site_args(checker)
    ns = parser.parse_args(argv)
    try:
        repo = find_repo(ns.repo)
        if ns.mode == "verify":
            if not (repo / "platform" / ns.name).exists():
                refuse(
                    f"platform/{ns.name}/ does not exist; run site-onboard write first"
                )
            return verify(repo, ns.name)
        return run(repo, params(ns), write=(ns.mode == "write"))
    except Refused as exc:
        sys.stderr.write(f"REFUSED: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
