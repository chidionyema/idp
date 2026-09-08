"""The JIT token broker: an agent asks, the founder taps once, the access expires by itself.

Founder's specification, 2026-09-07, in
`~/.claude/docs/founder/2026-09-07T1606Z-ok-lets-add-these-also-ign-the-proof-c2f0f9be.md`:

    You want the agent to operate autonomously where safe, hit a wall, ask for a temporary
    key, do the job, and have the key vanish into thin air without you ever cleaning up
    behind it.

Why this exists rather than Teleport or Vault: both were named and rejected in that same
message as setup bloat for a one-founder estate. Everything below is thin glue over two
primitives that are already installed -- the Kubernetes TokenRequest API, which mints a
token that carries its own expiry in its signature, and Telegram, which is already how this
estate talks to its founder.

The guarantee is cryptographic, not procedural. A token minted with a ten minute duration
stops being accepted by the API server at ten minutes and one second because the signature
says so. No cleanup job has to run. A crashed broker, a partitioned network and a rogue
agent all fail closed, which is the property no revocation-list design has.

Four rules hold the security, and each is a function below:

1. A grant is CHOSEN, never composed (`_load_grant`). The agent names an id from
   platform/jit/grants.yaml and fills in declared parameters. It cannot describe the access
   it wants, because a request body an agent writes is a request body an agent can widen.

2. The approval is SIGNED and the agent never sees the channel (`_sign`, `_verify`). The
   Telegram callback carries an HMAC over the whole request taken with a key that lives only
   in the broker. An agent that could forge a callback would not need the founder.

3. An approval is spent once (`_consume`). The same tap replayed is refused, so a captured
   callback is not a second grant.

4. Two modes, because Kubernetes permissions have no field-level scope (`_execute`). If a
   token can `patch` a Deployment then its holder can rewrite `serviceAccountName` and keep
   access after the token dies. So anything touching a pod spec is `broker-applies`: the
   broker performs the exact approved change and the agent never holds the verb at all.
   `bin/idp-jit-grants` refuses a catalogue that gets this wrong, and CI runs it.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import yaml

#: Ten minutes is the founder's example and the catalogue's ceiling is thirty. The
#: TokenRequest API will not mint below its own floor, so a shorter ask is honoured as
#: whatever the API server is willing to sign and the real expiry is read back from the
#: token, never assumed.
TTL = re.compile(r"^(\d+)([smh])$")
_SECONDS = {"s": 1, "m": 60, "h": 3600}

#: A quantity like 512Mi or 2Gi. Parsed, not trusted: the catalogue declares a maximum and
#: a request above it is refused before the founder is ever asked, so his phone does not
#: buzz for something that was never going to be allowed.
_QUANTITY = re.compile(r"^(\d+(?:\.\d+)?)(Ki|Mi|Gi|Ti|K|M|G|T)?$")
_SCALE = {
    None: 1,
    "K": 10**3,
    "M": 10**6,
    "G": 10**9,
    "T": 10**12,
    "Ki": 2**10,
    "Mi": 2**20,
    "Gi": 2**30,
    "Ti": 2**40,
}

#: A Kubernetes object name. Anything else is an injection attempt against the shell-free
#: argv we hand kubectl, or a typo; both are refused the same way.
_NAME = re.compile(r"^[a-z0-9]([-a-z0-9.]{0,61}[a-z0-9])?$")

#: An image tag. The catalogue marks rollback's tag `must_be_previously_deployed`, and that
#: is checked against the workload's own rollout history rather than trusted, because a
#: rollback to a tag this cluster has never run is not a rollback -- it is a deploy wearing
#: the word rollback, and it would arrive on the founder's phone under the wrong sentence.
_TAG = re.compile(r"^[\w][\w.-]{0,127}$")
_RRTYPE = re.compile(r"^[A-Za-z]{1,10}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]{1,39}/[A-Za-z0-9_.-]{1,100}$")
# A vault secret is not a Kubernetes object: OCI names them with underscores, and the estate's
# own seed entries (estate_seed_keys, agent_foundry_runner) are spelled that way. Grading them
# with _NAME refused every real one.
_VAULT_NAME = re.compile(r"^[A-Za-z0-9_-]{1,255}$")


def ttl_seconds(v: str) -> int | None:
    m = TTL.match(str(v or ""))
    return int(m.group(1)) * _SECONDS[m.group(2)] if m else None


def quantity_bytes(v: str) -> int | None:
    m = _QUANTITY.match(str(v or "").strip())
    return int(float(m.group(1)) * _SCALE[m.group(2)]) if m else None


class Refused(Exception):
    """The request does not become a question for the founder. He is only asked things
    that are allowed to happen; everything else is answered here, with the reason."""


@dataclass
class Request:
    id: str
    grant_id: str
    params: dict[str, str]
    why: str
    ttl: str
    asked_by: str
    asked_at: float
    state: str = "pending"
    reason: str = ""
    result: dict[str, Any] = field(default_factory=dict)


class Ledger:
    """Append-only, and provably so.

    The founder, on the first pass of this design: "Append-only by convention isn't
    tamper-proof either." So each line carries the hash of the line before it and an HMAC
    over both. Removing or editing any line breaks every hash after it, and `verify()`
    says which line. Convention is not doing the work; the chain is.
    """

    def __init__(self, path: str, key: bytes, sink=None):
        self.path, self.key = path, key
        # WJ.7: where the record goes to survive this node. broker/collector.py ships each
        # line to the estate collector; None means the file is the only copy, which is what a
        # unit test and a laptop run get. The file is written first either way, so a sink that
        # is down costs delivery, never the record.
        self.sink = sink

    def _tail_hash(self) -> str:
        prev = "0" * 64
        if os.path.exists(self.path):
            with open(self.path) as fh:
                for line in fh:
                    if line.strip():
                        prev = json.loads(line)["this"]
        return prev

    def append(self, event: str, **fields: Any) -> dict:
        prev = self._tail_hash()
        body = {"at": time.time(), "event": event, "prev": prev, **fields}
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
        body["this"] = hashlib.sha256((prev + payload).encode()).hexdigest()
        body["sig"] = hmac.new(
            self.key, body["this"].encode(), hashlib.sha256
        ).hexdigest()
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a") as fh:
            fh.write(json.dumps(body, sort_keys=True) + "\n")
            # The record is worthless if the process dies between write and disk, and this is
            # the one write in the broker where that matters: everything else can be redone,
            # an account of who was given write access cannot.
            fh.flush()
            os.fsync(fh.fileno())
        if self.sink is not None:
            # Deliberately after the file, and deliberately swallowing everything: a broker that
            # refuses a 3am approval because a metrics pipeline is unreachable has turned an
            # observability outage into an access outage. OTLPSink already returns False rather
            # than raising for a network fault; this catch is what makes that a property of the
            # ledger rather than a promise the next sink has to keep. The record is on disk and
            # fsynced above, so the only thing lost here is delivery.
            try:
                self.sink(dict(body))
            except Exception as boom:  # noqa: BLE001
                print(
                    f"warn   jit-ledger: sink refused the record: {boom}",
                    file=sys.stderr,
                )
        return body

    def verify(self) -> tuple[bool, str]:
        prev = "0" * 64
        if not os.path.exists(self.path):
            return True, "empty"
        with open(self.path) as fh:
            for n, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("prev") != prev:
                    return False, f"line {n} does not follow the line before it"
                body = {k: v for k, v in rec.items() if k not in ("this", "sig")}
                payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
                want = hashlib.sha256((prev + payload).encode()).hexdigest()
                if want != rec.get("this"):
                    return False, f"line {n} has been edited since it was written"
                if not hmac.compare_digest(
                    hmac.new(self.key, want.encode(), hashlib.sha256).hexdigest(),
                    rec.get("sig", ""),
                ):
                    return False, f"line {n} is not signed by this broker"
                prev = rec["this"]
        return True, "intact"


class Broker:
    #: The read-only identity every agent in this estate runs as. platform/rbac/agent-reader.yaml
    #: is the object; naming it here means the broker and bin/idp-kube cannot drift apart on the
    #: string, which is the whole reason the door exists.
    AGENT_SA = "agent-reader"
    AGENT_NS = "agents"
    #: An hour, matching what bin/idp-kube already asked the API server for. Long enough that a
    #: session is not re-authenticating between commands, short enough that a copied token is
    #: worthless by morning.
    AGENT_TTL_SECONDS = 3600
    #: Identities are not grants and are never approved, so the only thing bounding them is this.
    #: A handful of sessions refreshing hourly sits far below it; a leaked bootstrap key being
    #: replayed does not.
    AGENT_IDENTITIES_PER_HOUR = 60

    #: Where the cluster publishes its own address and certificate, for exactly this purpose.
    #: kubeadm writes it and OKE keeps it; `system:public-info-viewer` makes it readable by
    #: anyone, authenticated or not, because a client needs it *before* it has a credential.
    CLUSTER_INFO_NS = "kube-public"
    CLUSTER_INFO_CM = "cluster-info"

    def __init__(
        self,
        catalogue: str,
        key: bytes,
        ledger_path: str,
        notify: Callable[[Request, str], None] | None = None,
        kube: Callable[..., tuple[int, str]] | None = None,
        killswitch: Callable[[], str | None] | None = None,
        now: Callable[[], float] = time.time,
        providers: dict[str, Callable[[list[str]], tuple[int, str]]] | None = None,
        agent_key: bytes | None = None,
        ledger_sink=None,
        executor: Callable[[str, str, dict], dict] | None = None,
    ):
        self.catalogue_path = catalogue
        self.key = key
        self.ledger = Ledger(ledger_path, key, sink=ledger_sink)
        self.notify = notify or (lambda r, t: None)
        self.kube = kube or _kubectl
        self.killswitch = killswitch or (lambda: None)
        # WJ.15. One runner per layer below Kubernetes, injected the same way the cluster is,
        # so a test can read the exact argv the broker would run without a tenancy, a zone or
        # a GitHub App anywhere near it.
        self.providers = dict(PROVIDER_COMMANDS if providers is None else providers)
        # Decision 0027. Below Kubernetes the broker ships no tooling and holds no cloud
        # credential (platform/jit/Dockerfile, deployment.yaml), so it cannot run an OCI/DNS/
        # GitHub act itself. On an approved ask it hands the signed grant and the exact
        # parameters to this executor -- None is a broker that refuses those layers loudly
        # rather than pretending it performed them.
        self.executor = executor
        self.now = now
        self.pending: dict[str, Request] = {}
        self.spent: set[str] = set()
        self.history: list[tuple[float, str]] = []
        # Empty on a broker that has not been given one, which is a broker that cannot
        # identify anybody -- `identity()` refuses rather than defaulting open.
        self.agent_key = agent_key or b""

    # ---------------------------------------------------------------- the catalogue

    def _load_grant(self, grant_id: str) -> dict:
        with open(self.catalogue_path) as fh:
            cat = yaml.safe_load(fh) or {}
        for g in cat.get("grants") or []:
            if g.get("id") == grant_id:
                return g
        raise Refused(
            f"no grant called {grant_id!r}. The broker mints only what "
            f"{os.path.basename(self.catalogue_path)} already describes, and adding to that "
            f"file is a change to the estate's security boundary, not a request"
        )

    def _check_implemented(self, grant: dict) -> None:
        """A grant the broker cannot perform never reaches the phone.

        The catalogue and the code that performs it are two files, and until 2026-09-08 nothing
        held them together: `oci-vault-write` shipped in the catalogue with no step in this file
        and passed `bin/idp-jit-grants`, because that gate asks whether a grant can become
        standing access and never asked whether the broker can do it at all. So the ask was
        real, the button was real, the tap was real, and the act was not.

        Refusing here rather than in `_apply` is the difference between an agent being told no
        and the founder being woken to approve nothing. `bin/idp-jit-grants` now grades the same
        two sets at merge time, so this branch is the belt and that gate is the braces.
        """
        provider = str(grant.get("provider") or "kubernetes").lower()
        if grant.get("mode") != "broker-applies":
            return
        known = KUBERNETES_APPLIES if provider == "kubernetes" else set(APPLIES)
        if grant["id"] not in known:
            raise Refused(
                f"grant {grant['id']} is broker-applies and the broker has no step for it. "
                f"An ask nobody can perform is refused before it is shown to anyone"
            )

    def _check_params(self, grant: dict, params: dict[str, str]) -> None:
        declared = grant.get("parameters") or {}
        for name in declared:
            if declared[name].get("required") and not params.get(name):
                raise Refused(
                    f"grant {grant['id']} needs {name!r} and it was not given"
                )
        for name, value in params.items():
            if name not in declared:
                raise Refused(f"grant {grant['id']} takes no parameter {name!r}")
            spec = declared[name]
            kind = spec.get("type")
            if kind in ("name", "namespace") and not _NAME.match(str(value)):
                raise Refused(f"{name}={value!r} is not a Kubernetes object name")
            if kind == "image_tag":
                if not _TAG.match(str(value)):
                    raise Refused(f"{name}={value!r} is not an image tag")
                if spec.get("must_be_previously_deployed") and not self._was_deployed(
                    params.get("namespace", ""), params.get("workload", ""), str(value)
                ):
                    raise Refused(
                        f"this cluster has no record of {params.get('workload')} running "
                        f"{value}. That is a deploy, not a rollback, and it is not what the "
                        f"founder would be approving"
                    )
            if kind == "vault_secret_name" and not _VAULT_NAME.match(str(value)):
                raise Refused(f"{name}={value!r} is not a vault secret name")
            if kind == "base64_blob":
                # The value is the secret, so it is never quoted back -- only its shape is.
                # Checked here rather than at the provider because a bad-request echo from a
                # cloud CLI is one of the ways a secret reaches a log (LAW 21).
                try:
                    raw = base64.b64decode(str(value), validate=True)
                except (binascii.Error, ValueError):
                    raise Refused(f"{name} is not base64") from None
                cap = int(spec.get("max_bytes", 65536))
                if len(raw) > cap:
                    raise Refused(
                        f"{name} is {len(raw)} bytes, above the {cap} this grant allows"
                    )
            if kind == "repository" and not _REPO.match(str(value)):
                raise Refused(f"{name}={value!r} is not an owner/repository")
            if kind == "record_type" and not _RRTYPE.match(str(value)):
                raise Refused(f"{name}={value!r} is not a DNS record type")
            if kind == "integer":
                try:
                    got = int(str(value))
                except ValueError:
                    raise Refused(f"{name}={value!r} is not a whole number") from None
                cap = spec.get("max")
                if cap is not None and got > int(cap):
                    raise Refused(f"{name}={got} is above the {cap} this grant allows")
                floor = spec.get("min")
                if floor is not None and got < int(floor):
                    raise Refused(
                        f"{name}={got} is below the {floor} this grant allows. Taking a node "
                        f"pool below its floor is an eviction, and an eviction is an outage "
                        f"decision rather than a ten-minute one"
                    )
                if got < 0:
                    raise Refused(f"{name}={got} is negative")
            if kind == "quantity":
                got, cap = quantity_bytes(value), quantity_bytes(spec.get("max", ""))
                if got is None:
                    raise Refused(f"{name}={value!r} is not a quantity")
                if cap is not None and got > cap:
                    raise Refused(
                        f"{name}={value} is above the {spec['max']} this grant allows. "
                        f"A bigger ceiling is a capacity decision, not a ten-minute one"
                    )
        # Every layer bounds itself by the same shape: the grant names the things it reaches,
        # and a parameter that is not one of them is refused before the founder is ever shown
        # it. Kubernetes bounds by namespace; DNS by record; GitHub by repository (WJ.15).
        for param, allow_field, noun in (
            ("namespace", "namespaces", "namespace"),
            ("record", "records", "DNS record"),
            ("repository", "repositories", "repository"),
            ("secret_name", "secrets", "vault secret"),
        ):
            got = params.get(param)
            allowed = [str(a) for a in grant.get(allow_field) or []]
            if (
                got
                and allowed
                and str(got) not in allowed
                and str(got) not in [a.rsplit("/", 1)[-1] for a in allowed]
            ):
                raise Refused(f"grant {grant['id']} does not reach the {noun} {got!r}")
        rtype = params.get("record_type")
        types = [str(t).upper() for t in grant.get("record_types") or []]
        if rtype and types and str(rtype).upper() not in types:
            raise Refused(
                f"grant {grant['id']} does not write {str(rtype).upper()} records"
            )

    def _was_deployed(self, ns: str, workload: str, tag: str) -> bool:
        """Ask the cluster, not the agent. A Deployment keeps its old ReplicaSets, and each
        one carries the image it ran, so the rollout history is the record of what this
        workload has actually served."""
        rc, out = self.kube(
            [
                "get",
                "replicaset",
                "-n",
                ns,
                "-l",
                f"app.kubernetes.io/name={workload}",
                "-o",
                "jsonpath={.items[*].spec.template.spec.containers[*].image}",
            ]
        )
        if rc != 0:
            return False
        return any(img.rsplit(":", 1)[-1] == tag for img in out.split())

    def _check_rate(self, grant: dict) -> None:
        """One raise is a fix; forty in an hour is an incident nobody is watching.

        The founder, first pass: "Nothing bounds the rate". So every grant declares one and
        it is counted here, against approvals rather than asks -- a refused ask costs
        nothing and should not lock out a real one.
        """
        cap = int(grant.get("rate_per_hour") or 0)
        cutoff = self.now() - 3600
        used = sum(1 for at, gid in self.history if gid == grant["id"] and at > cutoff)
        if cap and used >= cap:
            raise Refused(
                f"grant {grant['id']} has been used {used} times in the last hour and its "
                f"limit is {cap}. Something is looping, or this is not a ten-minute problem"
            )

    # ------------------------------------------------- the agent's own identity

    def _check_identity_rate(self) -> None:
        cutoff = self.now() - 3600
        used = sum(1 for at, what in self.history if what == "identity" and at > cutoff)
        if used >= self.AGENT_IDENTITIES_PER_HOUR:
            raise Refused(
                f"{used} identities have been minted in the last hour and the limit is "
                f"{self.AGENT_IDENTITIES_PER_HOUR}. Either something is looping or this key "
                f"is being replayed by somebody who is not an agent of this estate"
            )

    def authenticate(self, presented: str) -> None:
        """Prove the caller is an agent of this estate, or refuse.

        Factored out of `identity()` so the `/ask` door can stand behind the same check.
        Until it did,
        `asked_by` was a string in the request body and nothing else: anything that could open
        a socket to port 8080 -- any pod in any namespace the fence let through, a compromised
        sidecar, a mistyped port-forward -- could put a name on an ask and make the founder's
        phone buzz with it. The founder still taps every one, so the hole was never standing
        access; it was provenance, which is worse in one specific way. The whole design rests
        on him reading an ask and deciding, and a name he cannot trust is a name that makes
        every future ask worth less than the one before it.

        One key covers every agent, so what this proves is "an agent of this estate", not
        which one. `asked_by` stays a label, and the ledger now records that it was attested
        rather than merely asserted. Per-agent keys are WJ.13's problem, not this door's.
        """
        if not self.agent_key:
            raise Refused(
                "this broker holds no agent key, so it cannot identify anyone. "
                "platform/jit/deployment.yaml is where JIT_AGENT_KEY arrives"
            )
        if not hmac.compare_digest(presented or "", self.agent_key.decode()):
            # No ledger line, and for the reason the Telegram path already gives: this door is
            # reachable from outside the cluster, so a line per refusal is a way for a stranger
            # to fill the ledger volume. The ledger records what the broker did, and it did
            # nothing. compare_digest because a byte-at-a-time comparison leaks the key to
            # whoever can time it.
            raise Refused("not an agent of this estate")

    def identity(self, presented: str) -> dict:
        """Mint the read-only identity an agent runs as, for a caller that proves it is one.

        WJ.1 ends "`bin/idp-kube` stops minting the founder's OCI principal." Until this door
        existed it could not. Measured 2026-09-08 at bin/idp-kube:84: the downgrade ran
        `kubectl create token agent-reader -n agents` under $KC, a kubeconfig whose user is an
        `exec` credential calling `oci generate-token` -- the founder's own OCI principal, on
        his laptop. The identity every agent runs as was therefore minted, every hour, by an
        administrator credential that existed on exactly one machine. `auth whoami` answering
        `agent-reader` was true and hid that: the downgrade was real, the thing performing it
        was not an agent.

        This is deliberately not a grant and never reaches the founder's phone. agent-reader
        holds reads and nothing else -- it is the floor every agent already stands on, not an
        elevation above it -- so there is nothing to approve. What the door changes is which
        credential a device must hold in order to become an agent: an agent's own, scoped to
        reads and revocable by itself, instead of the founder's, scoped to the tenancy.

        The bootstrap key is still a secret on a device, and no amount of design removes that
        -- something has to be the root. The difference worth the code is what that root can
        do when the device is lost: read this cluster for an hour, rather than administer the
        tenancy until somebody notices.
        """
        stopped = self.killswitch()
        if stopped:
            raise Refused(f"the broker is stopped: {stopped}")
        self.authenticate(presented)
        self._check_identity_rate()
        rc, out = self.kube(
            [
                "create",
                "token",
                self.AGENT_SA,
                "-n",
                self.AGENT_NS,
                f"--duration={self.AGENT_TTL_SECONDS}s",
            ]
        )
        if rc != 0:
            raise Refused(
                f"the API server would not mint the identity: {out.strip()[:200]}"
            )
        self.history.append((self.now(), "identity"))
        # WJ.7: the issuance is on the record, the token is not. A ledger that holds the
        # credential it recorded is a second copy of every credential the broker ever made.
        self.ledger.append(
            "identity",
            subject=f"{self.AGENT_NS}:{self.AGENT_SA}",
            ttl=self.AGENT_TTL_SECONDS,
        )
        return {
            "token": out.strip(),
            "expires_in": self.AGENT_TTL_SECONDS,
            "subject": f"system:serviceaccount:{self.AGENT_NS}:{self.AGENT_SA}",
            **self._cluster_address(),
        }

    def _cluster_address(self) -> dict:
        """Where the cluster is and the certificate that proves it, read from the cluster.

        A token alone does not let a device reach the API server: it also needs the address
        and the CA. Until this method the only thing on any device that knew either was the
        kubeconfig `bin/idp-cloud cluster kubeconfig` mints, which requires the `oci` CLI and
        the founder's own login -- so handing back a token and nothing else would have left
        the Mac exactly as load-bearing as before, with an extra door.

        The obvious fix was to write the endpoint into clusters/oke/estate-config.yaml and
        plumb it here through Flux substitution. That was not needed. Measured 2026-09-08:
        `kube-public/cluster-info` exists on this cluster and holds both values, and it read
        clean as `agent-reader`, so the read floor already permits it. This is what that
        ConfigMap is for -- kubeadm publishes it, and `system:public-info-viewer` makes it
        world-readable, precisely because a joining client needs the address and the CA
        before it holds any credential at all. So the estate keeps one copy of a machine
        fact, in the cluster, and no file names it (LAW 46).
        """
        rc, out = self.kube(
            [
                "get",
                "configmap",
                self.CLUSTER_INFO_CM,
                "-n",
                self.CLUSTER_INFO_NS,
                "-o",
                "jsonpath={.data.kubeconfig}",
            ]
        )
        if rc != 0:
            raise Refused(
                f"the cluster does not publish its own address at "
                f"{self.CLUSTER_INFO_NS}/{self.CLUSTER_INFO_CM}: {out.strip()[:200]}"
            )
        try:
            cluster = yaml.safe_load(out)["clusters"][0]["cluster"]
            server, authority = cluster["server"], cluster["certificate-authority-data"]
        except (yaml.YAMLError, KeyError, IndexError, TypeError) as exc:
            raise Refused(
                f"{self.CLUSTER_INFO_NS}/{self.CLUSTER_INFO_CM} is not a kubeconfig: {exc}"
            ) from None
        # OKE publishes `server: <host>:6443` with no scheme, and kubectl refuses a server
        # that has none. Measured 2026-09-08: the value in this cluster's ConfigMap is bare.
        server = str(server)
        if not server.startswith(("http://", "https://")):
            server = "https://" + server
        return {"server": server, "ca": authority}

    # ---------------------------------------------------------------- the ask

    def ask(
        self,
        grant_id: str,
        params: dict[str, str],
        why: str,
        ttl: str,
        asked_by: str,
        attested: bool = False,
    ) -> Request:
        """`attested` is the door's word that the caller proved the estate's agent key.

        The check itself is at the door and not here on purpose: anything holding a reference
        to this object is already inside the process that holds the key, so a second check
        here would defend against nothing and would only make the record less honest by
        being unfalsifiable. What travels is the verdict, and the ledger keeps it either way
        -- an in-process caller writes `attested: false`, which is exactly what it is.
        """
        stopped = self.killswitch()
        if stopped:
            raise Refused(f"the broker is stopped: {stopped}")
        grant = self._load_grant(grant_id)
        self._check_implemented(grant)
        self._check_params(grant, params)
        self._check_rate(grant)

        want, cap = ttl_seconds(ttl), ttl_seconds(grant.get("max_ttl", "10m"))
        if want is None:
            raise Refused(f"{ttl!r} is not a duration")
        if cap is not None and want > cap:
            raise Refused(
                f"grant {grant_id} lives at most {grant['max_ttl']}, and {ttl} was asked for"
            )
        if not (why or "").strip():
            raise Refused(
                "every ask carries why, because the founder is answering it on a phone"
            )

        req = Request(
            uuid.uuid4().hex,
            grant_id,
            dict(params),
            why.strip(),
            ttl,
            asked_by,
            self.now(),
        )
        self.pending[req.id] = req
        self.ledger.append(
            "asked",
            request=req.id,
            grant=grant_id,
            params=params,
            why=req.why,
            ttl=ttl,
            asked_by=asked_by,
            # The name is still self-declared -- one key covers every agent -- but a reader of
            # the ledger can now tell an ask whose caller proved the estate's agent key from
            # one that merely reached the port, which before this field no reader could.
            attested=attested,
        )
        self.notify(req, self._sign(req.id, "approve"))
        return req

    # ---------------------------------------------------------------- the approval

    def _sign(self, request_id: str, verdict: str) -> str:
        return hmac.new(
            self.key, f"{request_id}:{verdict}".encode(), hashlib.sha256
        ).hexdigest()

    def _verify(self, request_id: str, verdict: str, sig: str) -> bool:
        return hmac.compare_digest(self._sign(request_id, verdict), sig or "")

    def _consume(self, request_id: str) -> None:
        if request_id in self.spent:
            raise Refused("that approval has already been used once")
        self.spent.add(request_id)

    #: Telegram gives a button 64 bytes of callback_data and no more, so the signature
    #: travels truncated. 24 hex characters is 96 bits, which is far past forging for a
    #: value that is single-use (`_consume`), rate limited, and accepted from exactly one
    #: chat -- an attacker gets one guess, not the offline grind that would need the full
    #: 256. The request id is shortened for the same reason and resolved by prefix.
    SIG_CHARS = 24
    ID_CHARS = 12

    def callback_data(self, request_id: str, verdict: str) -> str:
        return (
            f"j:{request_id[: self.ID_CHARS]}:{verdict[0]}"
            f":{self._sign(request_id, verdict)[: self.SIG_CHARS]}"
        )

    def decide_callback(self, data: str) -> Request:
        """Verdict straight off a button press. Everything in `data` came back from
        Telegram and is treated as hostile input: the id is looked up rather than trusted,
        and the signature is compared in constant time before any state moves."""
        try:
            tag, short_id, verdict_char, sig = data.split(":", 3)
        except ValueError:
            raise Refused("that is not a broker button") from None
        if tag != "j" or verdict_char not in ("a", "d"):
            raise Refused("that is not a broker button")
        verdict = "approve" if verdict_char == "a" else "deny"
        matches = [r for r in self.pending if r.startswith(short_id)]
        if len(matches) != 1:
            raise Refused("no such request")
        want = self._sign(matches[0], verdict)[: self.SIG_CHARS]
        if not hmac.compare_digest(want, sig):
            self.ledger.append("forged", request=matches[0], verdict=verdict)
            raise Refused("that approval is not signed by this broker")
        return self.decide(matches[0], verdict, self._sign(matches[0], verdict))

    def expire_stale(self, after_s: int = 900) -> list[Request]:
        """WJ.3: "a silent no-answer is a deny -- the request expires on its own." So a
        request nobody answers is not a request that waits forever for a tap that might
        come at 3am from someone holding his phone."""
        gone = []
        for req in self.pending.values():
            if req.state == "pending" and self.now() - req.asked_at > after_s:
                req.state = "expired"
                self.ledger.append("expired", request=req.id)
                gone.append(req)
        return gone

    def decide(self, request_id: str, verdict: str, sig: str) -> Request:
        req = self.pending.get(request_id)
        if req is None:
            raise Refused("no such request")
        # Without this the expiry above is decoration: a request that timed out at
        # midnight would still be sitting in his chat at 3am, one tap from live, for
        # whoever is holding the phone. A verdict is only ever spent on a live ask.
        if req.state != "pending":
            raise Refused(f"that request is already {req.state}")
        if not self._verify(request_id, verdict, sig):
            self.ledger.append("forged", request=request_id, verdict=verdict)
            raise Refused("that approval is not signed by this broker")
        self._consume(request_id)
        if verdict != "approve":
            req.state = "denied"
            self.ledger.append("denied", request=request_id)
            return req
        grant = self._load_grant(req.grant_id)
        self.history.append((self.now(), req.grant_id))
        try:
            req.result = self._execute(grant, req)
            req.state = "granted"
            self.ledger.append(
                "granted",
                request=request_id,
                mode=grant.get("mode"),
                expires_at=req.result.get("expires_at"),
            )
        except Exception as exc:  # noqa: BLE001 -- the agent must see it
            req.state, req.reason = "failed", str(exc)
            self.ledger.append("failed", request=request_id, reason=str(exc))
        return req

    # ---------------------------------------------------------------- doing the thing

    def _execute(self, grant: dict, req: Request) -> dict:
        """WJ.15. Which layer the grant acts on decides who performs it, and only Kubernetes
        can hand anything over: below it there is no credential that is both scoped to what
        the founder approved and self-expiring, so the broker performs the act and the agent
        is told the outcome. bin/idp-jit-grants refuses `mode: token` on those providers, so
        the branch below can never be reached with one.
        """
        provider = str(grant.get("provider") or "kubernetes").lower()
        mode = grant.get("mode")
        if provider != "kubernetes":
            if mode != "broker-applies":
                raise Refused(
                    f"grant {grant['id']} is mode {mode!r} on {provider}, and nothing below "
                    f"Kubernetes hands over a credential"
                )
            # Decision 0027. Below Kubernetes the broker ships no tooling and holds no cloud
            # credential, so it does not run the act itself: when an executor is configured it
            # hands the exact approved grant and parameters there. An executor performs it
            # under its own (narrow) identity and returns the outcome, which becomes this
            # request's result.
            if self.executor is not None:
                return self.executor(req.id, grant["id"], dict(req.params))
            # No executor yet -- fall back to the legacy local-provider path (argv-bounds
            # tests, and a production default whose missing binary stays fail-closed), never
            # a broker that reports done for a layer it cannot reach.
            runner = self.providers.get(provider)
            if runner is None:
                raise Refused(
                    f"the broker has no way to act on {provider!r}. A provider it cannot "
                    f"reach is refused here rather than reported as done"
                )
            return self._apply_below(provider, runner, grant, req)
        if mode == "broker-applies":
            return self._apply(grant, req)
        if mode == "token":
            return self._mint(grant, req)
        raise Refused(f"grant {grant['id']} has no mode the broker knows")

    def _apply_below(self, provider, runner, grant: dict, req: Request) -> dict:
        """The step this grant names, run by the provider's own command. Nothing here is
        composed from agent text: the step comes out of APPLIES, keyed by the grant id, and
        every value has already been checked against what that grant declares.

        Keyed by the grant and not by the provider, and that is the whole repair. It used to
        be `BELOW[provider]`, so every OCI grant ran the one OCI step that existed -- the node
        pool resize. On 2026-09-08 a second OCI grant landed (`oci-vault-write`, #2496) with no
        step of its own, and this line would have handed its approved vault write to the node
        pool resizer, which then looked for a `node_pool` parameter that grant does not declare.
        A founder tap, and a crash in the shape of a different act. Founder, that morning:
        "and also wtf is this" (~/.claude/docs/founder/
        2026-09-08T0953Z-and-also-wtf-is-this-4991d777.md). A grant now reaches its own step or
        it reaches none, and `_check_implemented` refuses it before the phone ever buzzes.
        """
        handler = APPLIES.get(grant["id"])
        if handler is None:
            raise Refused(
                f"grant {grant['id']} names an act the broker has no step for. It is refused "
                f"here rather than run as some other grant's step"
            )
        return handler(grant, req, runner, provider)

    def _mint(self, grant: dict, req: Request) -> dict:
        """A token bound to a Role that exists only for this request.

        The Role is deleted on the way out, but that deletion is housekeeping, not the
        guarantee: the token stops working on its own. This is the whole reason the design
        survives the broker crashing halfway through.
        """
        ns, sec = req.params["namespace"], ttl_seconds(req.ttl)
        sa = f"jit-{req.id[:12]}"
        rules = [
            {
                "apiGroups": grant.get("apiGroups", [""]),
                "resources": grant.get("resources", []),
                "verbs": grant.get("verbs", []),
                "resourceNames": [
                    v for k, v in req.params.items() if k not in ("namespace",)
                ],
            }
        ]
        self._kube_step("create", "serviceaccount", sa, "-n", ns)
        self._kube_step(
            "apply",
            "-f",
            "-",
            stdin=yaml.safe_dump(
                {
                    "apiVersion": "rbac.authorization.k8s.io/v1",
                    "kind": "Role",
                    "metadata": {"name": sa, "namespace": ns},
                    "rules": rules,
                }
            ),
        )
        self._kube_step(
            "create",
            "rolebinding",
            sa,
            f"--role={sa}",
            f"--serviceaccount={ns}:{sa}",
            "-n",
            ns,
        )
        rc, out = self.kube(["create", "token", sa, "-n", ns, f"--duration={sec}s"])
        if rc != 0:
            raise Refused(
                f"the API server would not mint the token: {out.strip()[:200]}"
            )
        token = out.strip()
        return {
            "mode": "token",
            "token": token,
            "namespace": ns,
            "serviceaccount": sa,
            "expires_at": _token_expiry(token) or self.now() + sec,
        }

    def _apply(self, grant: dict, req: Request) -> dict:
        """The broker performs the approved change. The agent is told what happened and
        never holds a credential, which is the only way to grant `patch` on a pod spec
        without also granting the ability to keep the access."""
        ns = req.params["namespace"]
        if grant["id"] == "raise-memory-limit":
            patch = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": req.params["workload"],
                                    "resources": {
                                        "limits": {"memory": req.params["memory"]}
                                    },
                                }
                            ]
                        }
                    }
                }
            }
            args = [
                "patch",
                "deployment",
                req.params["workload"],
                "-n",
                ns,
                "--type=strategic",
                "-p",
                json.dumps(patch),
            ]
        elif grant["id"] == "rollback-image":
            rc, cur = self.kube(
                [
                    "get",
                    "deployment",
                    req.params["workload"],
                    "-n",
                    ns,
                    "-o",
                    "jsonpath={.spec.template.spec.containers[0].image}",
                ]
            )
            if rc != 0:
                raise Refused(f"cannot read the current image: {cur.strip()[:200]}")
            repo = cur.rsplit(":", 1)[0]
            args = [
                "set",
                "image",
                f"deployment/{req.params['workload']}",
                f"{req.params['workload']}={repo}:{req.params['tag']}",
                "-n",
                ns,
            ]
        else:
            raise Refused(
                f"grant {grant['id']} is broker-applies but the broker has no step for it"
            )
        rc, out = self.kube(args)
        if rc != 0:
            raise Refused(
                f"the change was approved and then failed: {out.strip()[:300]}"
            )
        return {
            "mode": "broker-applies",
            "applied": " ".join(args[:4]),
            "output": out.strip()[:400],
        }

    def _kube_step(self, *args: str, stdin: str | None = None) -> None:
        """One step of the setup. `already exists` is not an error: a retried request must
        land on the same Role rather than half a Role, so every step is idempotent."""
        rc, out = (
            self.kube(list(args), stdin) if stdin is not None else self.kube(list(args))
        )
        if rc != 0 and "already exists" not in out:
            raise Refused(out.strip()[:200])


def _token_expiry(token: str) -> float | None:
    """Read the expiry out of the token the API server actually signed.

    The founder's guarantee is "at exactly 10 minutes and 1 second, the cryptography
    invalidates". That claim is only true of the number in the signed token, so it is read
    back rather than assumed: the API server has a floor and will hand back a longer life
    than was asked for, and the agent is told the real one.
    """
    try:
        import base64

        body = token.split(".")[1]
        body += "=" * (-len(body) % 4)
        return float(json.loads(base64.urlsafe_b64decode(body))["exp"])
    except Exception:  # noqa: BLE001
        return None


def _kubectl(args: list[str], stdin: str | None = None) -> tuple[int, str]:
    """Every cluster call in this estate goes through bin/idp-kube, which holds the
    kubeconfig and the audit line; the broker is not an exception to that."""
    idp = os.environ.get("IDP_ROOT") or os.getcwd()
    p = subprocess.run(  # noqa: S603 -- argv is a list built from the catalogue and validated parameters; no shell
        [os.path.join(idp, "bin", "idp-kube"), *args],
        input=stdin,
        capture_output=True,
        text=True,
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ------------------------------------------------------------------ WJ.15, below Kubernetes
#
# Three layers the estate also runs on, each reached through the tool that already owns it, and
# each doing exactly one thing. There is no general "run an OCI command" here on purpose: the
# operation is a constant in this file, and only its parameters come from the request, so a grant
# cannot be talked into a different act than the one on the founder's phone.


def _oci_args(grant: dict, req: "Request") -> list[str]:
    """Resize a node pool, between the floor and the ceiling the grant declares. The floor is
    what stops this being a way to evict every workload on the cluster: `size: 0` is refused by
    _check_params before the founder is ever shown it."""
    return [
        "ce",
        "node-pool",
        "update",
        "--node-pool-id",
        req.params["node_pool"],
        "--size",
        str(int(req.params["size"])),
        "--wait-for-state",
        "SUCCEEDED",
    ]


def _dns_args(grant: dict, req: "Request") -> list[str]:
    """Point one record at one target. The record, its type and the zone are all checked
    against the grant before this is built."""
    return [
        "dns",
        "record",
        "rrset",
        "update",
        "--domain",
        req.params["record"],
        "--rtype",
        str(req.params["record_type"]).upper(),
        "--items",
        json.dumps(
            [
                {
                    "domain": req.params["record"],
                    "rtype": str(req.params["record_type"]).upper(),
                    "rdata": req.params["target"],
                    "ttl": 300,
                }
            ]
        ),
        "--force",
    ]


def _github_args(grant: dict, req: "Request") -> list[str]:
    """Re-run the jobs that failed on a workflow run. It runs the workflow the merged commit
    already carries and cannot introduce one, which is why this is the only GitHub act in the
    catalogue."""
    return [
        "api",
        "--method",
        "POST",
        f"repos/{req.params['repository']}/actions/runs/{int(req.params['run_id'])}/rerun-failed-jobs",
    ]


def _oci_vault_write(grant: dict, req: "Request", run, provider: str) -> dict:
    """Write one vault value the estate bootstrap needs, under a name the grant allows.

    Two calls and not one, because the OCI CLI addresses an existing secret by OCID and a new
    one by name: the list resolves the name the founder approved into the id, and the write is
    a create when the list finds nothing. Both calls carry the compartment the broker is
    configured with, never one out of the request, so a name the grant permits can still only
    be written in the one compartment this broker holds.

    The three OCIDs come from the broker's own environment (JIT_OCI_COMPARTMENT_ID,
    JIT_OCI_VAULT_ID, JIT_OCI_KEY_ID) and are refused when absent. A broker with no vault
    configured says so instead of failing halfway through an approved change.

    The value never appears in the record. `contents_b64` is the secret itself, so it is kept
    out of the argv summary, and the provider's own error text is scrubbed of it before it is
    quoted anywhere -- a bad-request echo is the classic way a secret reaches a log (LAW 21).
    """
    compartment = os.environ.get("JIT_OCI_COMPARTMENT_ID", "").strip()
    vault = os.environ.get("JIT_OCI_VAULT_ID", "").strip()
    key = os.environ.get("JIT_OCI_KEY_ID", "").strip()
    missing = [
        n
        for n, v in (
            ("JIT_OCI_COMPARTMENT_ID", compartment),
            ("JIT_OCI_VAULT_ID", vault),
            ("JIT_OCI_KEY_ID", key),
        )
        if not v
    ]
    if missing:
        raise Refused(
            f"this broker has no vault configured ({', '.join(missing)} unset), so it cannot "
            f"perform a vault write it was approved for"
        )

    name = req.params["secret_name"]
    blob = req.params["contents_b64"]

    def scrub(text: str) -> str:
        return text.replace(blob, "<contents>") if blob else text

    rc, out = run(
        ["vault", "secret", "list", "--compartment-id", compartment, "--name", name]
    )
    if rc != 0 and "NotAuthorizedOrNotFound" not in out:
        raise Refused(f"cannot read the vault: {scrub(out).strip()[:300]}")
    try:
        found = (json.loads(out or "{}").get("data") or []) if rc == 0 else []
    except json.JSONDecodeError:
        found = []
    live = [d for d in found if str(d.get("lifecycle-state", "")).upper() != "DELETED"]

    if live:
        args = [
            "vault",
            "secret",
            "update-base64",
            "--secret-id",
            str(live[0]["id"]),
            "--secret-content-content",
            blob,
            "--force",
        ]
        did = "updated"
    else:
        args = [
            "vault",
            "secret",
            "create-base64",
            "--compartment-id",
            compartment,
            "--vault-id",
            vault,
            "--key-id",
            key,
            "--secret-name",
            name,
            "--secret-content-content",
            blob,
        ]
        did = "created"

    rc, out = run(args)
    if rc != 0:
        raise Refused(
            f"the vault write was approved and then failed: {scrub(out).strip()[:300]}"
        )
    return {
        "mode": "broker-applies",
        "provider": provider,
        "applied": f"vault secret {did} {name}",
        "output": f"{did} {name}",
    }


def _argv_step(build) -> Callable[..., dict]:
    """The three original acts, each still one argv and one run.

    The wrapper exists so APPLIES holds one shape -- a step that takes the grant, the request
    and the runner -- whether the act is a single command or, as with the vault write, a
    resolve and then a write.
    """

    def step(grant: dict, req: "Request", run, provider: str) -> dict:
        args = build(grant, req)
        rc, out = run(args)
        if rc != 0:
            raise Refused(
                f"the change was approved and then failed on {provider}: {out.strip()[:300]}"
            )
        return {
            "mode": "broker-applies",
            "provider": provider,
            "applied": " ".join(args[:5]),
            "output": out.strip()[:400],
        }

    return step


# Every act the broker can perform below Kubernetes, keyed by the grant that names it. This
# table and the non-Kubernetes rows of platform/jit/grants.yaml must be the same set;
# bin/idp-jit-grants fails the build when they are not.
APPLIES = {
    "oci-scale-node-pool": _argv_step(_oci_args),
    "oci-vault-write": _oci_vault_write,
    "dns-point-record": _argv_step(_dns_args),
    "github-rerun-failed-checks": _argv_step(_github_args),
}

# The same set for Kubernetes, where the act is a branch of Broker._apply rather than a row
# here. A `mode: token` grant needs no entry: minting is generic, and the Role it cuts is the
# grant itself.
KUBERNETES_APPLIES = {"raise-memory-limit", "rollback-image"}


def _provider_runner(binary: str) -> Callable[[list[str]], tuple[int, str]]:
    """Run one provider's own CLI. The binary is a constant, the argv is a list, and there is
    no shell -- so nothing in a request can become a second command."""

    def run(args: list[str]) -> tuple[int, str]:
        p = subprocess.run(  # noqa: S603 -- constant binary, argv is a list built in this file from validated parameters; no shell
            [binary, *args], capture_output=True, text=True
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")

    return run


PROVIDER_COMMANDS = {
    "oci": _provider_runner("oci"),
    "dns": _provider_runner("oci"),
    "github": _provider_runner("gh"),
}
