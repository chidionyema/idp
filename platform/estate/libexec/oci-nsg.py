#!/usr/bin/env python3
"""Open the OKE cluster's API endpoint, and read and write network security group rules.

Why this exists: the estate's OCI CLI is 3.90.3, which has no command that can add NSG
security rules, and the endpoint NSG the cluster's API server sits behind -- `cp-tiafzl` --
has NO rules at all, ingress or egress. That is why `141.147.80.229:6443` answers
TCP_CLOSED, why kubectl cannot reach the cluster, and why the estate's memory door (the
unified memory server, in that cluster) and the cloud router both sit dead behind it.

How it signs: the same scheme OCI's own CLI and SDK use, copied from
`oci/_vendor/httpsig_cffi/utils.py::generate_message` and `oci/signer.py`:

  * the string to sign is the signed header block, one `name: value` per line, in the order
    `date`, `(request-target)`, `host` -- plus `content-length`, `content-type` and
    `x-content-sha256` when the request carries a body -- joined by "\\n" with NO trailing
    newline;
  * the Authorization header is
    `Signature algorithm="rsa-sha256",headers="<the names>",keyId="<t/u/fingerprint>",
     signature="<base64 rsa-pkcs1v15-sha256>",version="1"`;
  * `x-content-sha256` is the base64 of the sha256 digest of the body.

The cluster itself is read and written through OCI's own SDK client, which knows the
container engine's service host and request shapes; the SDK that ships inside the CLI's
venv is used for that (the CLI's own venv is the only place it is installed).

The private key is read from the profile's `key_file`; nothing but the server's own answer
is printed, and no secret value is ever printed.

    python3 oci-nsg.py probe [nsg-ocid]              # read the nsg: proves the signature
    python3 oci-nsg.py cluster                       # the cluster and its endpoint config
    python3 oci-nsg.py create-nsg <rules.json>       # a new nsg carrying the rules
    python3 oci-nsg.py attach <nsg-ocid>             # put it on the cluster's endpoint
"""

from __future__ import annotations

import base64
import configparser
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from email.utils import formatdate

CONFIG = os.path.expanduser("~/.oci/config")
DEFAULT_NSG = "ocid1.networksecuritygroup.oc1.uk-london-1.aaaaaaaaii3pthmob5wnz3gjufri564cfdp47jytvnrjwkxbhinh3gqtu7oa"
COMPARTMENT = "ocid1.compartment.oc1..aaaaaaaaynd3mq5nhnccywzbmwfdevpkmvyzwcsxm7kyevei5s72ikyge5oq"
CLUSTER = "ocid1.cluster.oc1.uk-london-1.aaaaaaaak3vxjechxim2cnrxowiec4jjvagtcbpenob2oj5ftcrq7jwxsjxq"
CLI_VENV = os.path.expanduser("~/.local/share/uv/tools/oci-cli")


def profile(name: str = "agent") -> dict:
    """The profile's own facts: no host, no key, no fingerprint is a literal here."""
    parser = configparser.ConfigParser()
    parser.read(CONFIG)
    section = "profile " + name if parser.has_section("profile " + name) else name
    if not parser.has_section(section):
        raise SystemExit("no profile %r in %s" % (name, CONFIG))
    facts = dict(parser.items(section))
    for key in ("key_file", "fingerprint", "tenancy", "user", "region"):
        if not facts.get(key):
            raise SystemExit("[%s] has no %s" % (section, key))
    return facts


def sign(string_to_sign: str, key_path: str) -> str:
    """RSA-SHA256 over the string to sign, base64'd. openssl does the crypto, so this script
    needs nothing outside the standard library."""
    proc = subprocess.run(  # noqa: S603 - openssl is the only signer this host has
        ["/usr/bin/openssl", "dgst", "-sha256", "-sign", os.path.expanduser(key_path)],
        input=string_to_sign.encode("ascii"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(
            "openssl refused to sign: %s" % proc.stderr.decode("utf-8", "replace")
        )
    return base64.b64encode(proc.stdout).decode("ascii")


def service_host(path: str, facts: dict) -> str:
    """OCI serves the container engine API on its own host, not on the iaas one.

    The SDK's own endpoint template is `https://containerengine.{region}.oci.{domain}` --
    the extra `.oci.` matters: without it the API answers 404.
    """
    if path.startswith("/20180222"):
        return "containerengine.%s.oci.oraclecloud.com" % facts["region"]
    if path.startswith("/20181025"):
        # The service-limits API has its own host, separate from compute.
        return "limits.%s.oci.oraclecloud.com" % facts["region"]
    if path.startswith("/20160918/availabilityDomains"):
        # The availability-domain list is served from the identity host.
        return "identity.%s.oci.oraclecloud.com" % facts["region"]
    return "iaas.%s.oraclecloud.com" % facts["region"]


def call(method: str, path: str, body: dict, facts: dict) -> tuple:
    """The server's own answer: (status, payload)."""
    host = service_host(path, facts)
    raw = json.dumps(body).encode("utf-8") if body else b""
    # The request-target carries the query string when there is one.
    target = path
    date_value = formatdate(usegmt=True)
    lines = [
        "date: %s" % date_value,
        "(request-target): %s %s" % (method.lower(), target),
        "host: %s" % host,
    ]
    names = ["date", "(request-target)", "host"]
    headers = {"date": date_value, "content-type": "application/json"}
    if raw:
        digest = base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii")
        lines.append("content-length: %d" % len(raw))
        lines.append("content-type: application/json")
        lines.append("x-content-sha256: %s" % digest)
        names += ["content-length", "content-type", "x-content-sha256"]
        headers["content-length"] = str(len(raw))
        headers["x-content-sha256"] = digest
    key_id = "%s/%s/%s" % (facts["tenancy"], facts["user"], facts["fingerprint"])
    authorization = (
        'Signature algorithm="rsa-sha256",headers="%s",keyId="%s",signature="%s",version="1"'
        % (
            " ".join(names),
            key_id,
            sign("\n".join(lines), facts["key_file"]),
        )
    )
    headers["Authorization"] = authorization
    req = urllib.request.Request(
        "https://%s%s" % (host, path), data=raw or None, method=method
    )  # noqa: S310 - the scheme is https by construction
    for name, value in headers.items():
        req.add_header(name, value)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:  # noqa: S310 - the scheme is https by construction
            status = response.status
            text = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        text = exc.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - the caller prints it
        return 0, {"error": "%s: %s" % (type(exc).__name__, exc)}
    if not text.strip():
        return status, {}
    try:
        return status, json.loads(text)
    except ValueError:
        return status, {"error": text[:400]}


def sdk_path() -> str:
    """The CLI's venv site-packages, where OCI's SDK lives."""
    root = os.path.join(CLI_VENV, "lib")
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        candidate = os.path.join(root, name, "site-packages")
        if os.path.isdir(candidate):
            return candidate
    raise SystemExit("no site-packages under %s" % root)


def cluster_client(facts: dict):
    """OCI's own container engine client, built from the profile."""
    sys.path.insert(0, sdk_path())
    from oci.container_engine import ContainerEngineClient  # noqa: PLC0415
    from oci.signer import Signer  # noqa: PLC0415

    signer = Signer(
        facts["tenancy"],
        facts["user"],
        facts["fingerprint"],
        private_key_file_location=os.path.expanduser(facts["key_file"]),
    )
    config = {
        "user": facts["user"],
        "tenancy": facts["tenancy"],
        "fingerprint": facts["fingerprint"],
        "key_file": os.path.expanduser(facts["key_file"]),
        "region": facts["region"],
    }
    return ContainerEngineClient(config, signer=signer)


def the_cluster(client, facts: dict):
    """The estate's one cluster: the one with a public endpoint."""
    clusters = client.list_clusters(COMPARTMENT).data
    if not clusters:
        raise SystemExit("no cluster in the compartment")
    for item in clusters:
        endpoint = endpoint_dict(item)
        if endpoint.get("isPublicIpEnabled"):
            return item
    return clusters[0]


def endpoint_dict(item) -> dict:
    """The endpoint config as the server spells it.

    The model keeps its values behind properties and stores them in underscore-prefixed
    attributes, so the values are read through the properties rather than out of __dict__.
    """
    endpoint = getattr(item, "endpoint_config", None)
    if endpoint is None:
        return {}
    if isinstance(endpoint, dict):
        return endpoint
    return {
        "subnetId": getattr(endpoint, "subnet_id", None),
        "nsgIds": list(getattr(endpoint, "nsg_ids", None) or []),
        "isPublicIpEnabled": getattr(endpoint, "is_public_ip_enabled", None),
        "securityAttributes": getattr(endpoint, "security_attributes", None),
    }


def endpoint_kwargs(model, endpoint: dict, nsg_ids: list) -> dict:
    """Only the fields the SDK's model actually accepts, so a trimmed SDK does not break the
    call; the accepted field names are printed, because a model that has no subnet_id is
    itself a fact worth seeing."""
    accepted = set(getattr(model, "attribute_map", {}) or {})
    print("endpoint model fields: %s" % ", ".join(sorted(accepted)))
    kwargs = {}
    if "nsg_ids" in accepted:
        kwargs["nsg_ids"] = nsg_ids
    if "is_public_ip_enabled" in accepted:
        kwargs["is_public_ip_enabled"] = bool(endpoint.get("isPublicIpEnabled"))
    if "subnet_id" in accepted:
        kwargs["subnet_id"] = endpoint.get("subnetId")
    if "security_attributes" in accepted:
        kwargs["security_attributes"] = endpoint.get("securityAttributes") or {}
    return kwargs


def main(argv: list) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    action = argv[1]
    facts = profile()
    rest = argv[2:]
    # The door passes both the nsg ocid and the rules file; pick them by what they are.
    nsg = next((a for a in rest if a.startswith("ocid1.")), DEFAULT_NSG)
    rules_path = next((a for a in rest if a.endswith(".json")), "")
    # raw-get takes its path in any of the free-form slots; a path is the one argument
    # that starts with a slash and carries no whitespace.
    path_arg = next((a for a in rest if a.startswith("/") and " " not in a), "")
    base = "/20160918/networkSecurityGroups/%s" % nsg
    if action == "probe":
        status, payload = call("GET", base, {}, facts)
        print("GET %s -> %s" % (base, status))
        print(json.dumps(payload)[:400])
        return 0 if status == 200 else 1
    if action == "show":
        status, payload = call("GET", base, {}, facts)
        print("status=%s" % status)
        print(json.dumps(payload, indent=1)[:3000])
        return 0 if status == 200 else 1
    if action == "cluster":
        client = cluster_client(facts)
        item = the_cluster(client, facts)
        print("cluster: %s (%s)" % (item.name, item.id))
        print("  endpoint: %s" % getattr(client, "endpoint", "?"))
        try:
            import oci.container_engine.models as ce_models

            print(
                "  models: %s"
                % ", ".join(
                    sorted(
                        n for n in dir(ce_models) if "Cluster" in n or "Endpoint" in n
                    )
                )
            )
        except Exception as exc:  # noqa: BLE001
            print("  models unavailable: %s" % exc)
        print("  vcnId: %s" % item.vcn_id)
        print("  endpointConfig: %s" % json.dumps(endpoint_dict(item), indent=1))
        return 0
    if action == "create-nsg":
        # A new NSG carrying the rules. The empty NSG the endpoint carries today stays
        # attached: OCI unions the rules of every NSG on the ENI, so adding this one opens
        # the API server without removing anything the estate already declares.
        if len(argv) < 3:
            raise SystemExit("create-nsg needs <rules.json>")
        with open(rules_path, "r", encoding="utf-8") as fh:
            rules = json.load(fh)
        client = cluster_client(facts)
        item = the_cluster(client, facts)
        print("cluster: %s vcnId: %s" % (item.name, item.vcn_id))
        body = {
            "compartmentId": COMPARTMENT,
            "vcnId": item.vcn_id,
            "displayName": "cp-tiafzl-rules",
            "securityGroupRules": rules,
        }
        status, payload = call("POST", "/20160918/networkSecurityGroups", body, facts)
        print("POST networkSecurityGroups -> %s" % status)
        print(json.dumps(payload)[:600])
        if status == 200:
            print("NEW NSG ID: %s" % payload.get("id"))
        return 0 if status == 200 else 1
    if action == "port-check":
        # Prove whether the cluster's API endpoint answers, from this machine.
        host = next(
            (a for a in rest if "." in a and not a.startswith("ocid1.")),
            "141.147.80.229",
        )
        digits = [a for a in rest if a.isdigit()]
        port = digits[-1] if digits else "6443"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(8)
        try:
            sock.connect((host, int(port)))
            print("TCP_OPEN %s:%s" % (host, port))
            return 0
        except Exception as exc:  # noqa: BLE001 - the caller prints it
            print("TCP_CLOSED %s:%s (%s)" % (host, port, exc))
            return 1
        finally:
            sock.close()
    if action == "add-rules":
        # Put the rules on an existing nsg: the estate's tofu owns the endpoint's nsg list,
        # so the rules belong on the nsg the estate already declares.
        if not rules_path:
            raise SystemExit("add-rules needs <rules.json>")
        with open(rules_path, "r", encoding="utf-8") as fh:
            rules = json.load(fh)
        path = "/20160918/networkSecurityGroups/%s/securityRules" % nsg
        status, payload = call("POST", path, {"securityGroupRules": rules}, facts)
        if status not in (200, 201):
            status, payload = call("POST", path, rules, facts)
        print("POST %s -> %s" % (path, status))
        print(json.dumps(payload)[:800])
        got_status, got = call("GET", path, {}, facts)
        print("rules now on %s: %s" % (nsg, json.dumps(got)[:900]))
        return 0 if status in (200, 201) else 1
    if action == "set-rules":
        # Union the nsg's current rules with the ones given, then PUT the whole set back:
        # replacing the set is the only write OCI exposes, so the union is computed first so
        # nothing that was there is lost.
        if not rules_path:
            raise SystemExit("set-rules needs <rules.json>")
        with open(rules_path, "r", encoding="utf-8") as fh:
            wanted = json.load(fh)
        path = "/20160918/networkSecurityGroups/%s/securityRules" % nsg
        status, current = call("GET", path, {}, facts)
        if status != 200:
            print("GET rules -> %s %s" % (status, json.dumps(current)[:300]))
            return 1
        have = (
            current
            if isinstance(current, list)
            else current.get("securityGroupRules") or []
        )
        print("rules before: %d" % len(have))
        for rule in have:
            print("  %s" % json.dumps(rule))

        def key(rule: dict) -> str:
            options = rule.get("tcpOptions") or rule.get("udpOptions") or {}
            ports = options.get("destinationPortRange") or {}
            return json.dumps(
                [
                    rule.get("direction"),
                    str(rule.get("protocol")),
                    rule.get("source"),
                    rule.get("destination"),
                    ports.get("min"),
                    ports.get("max"),
                ],
                sort_keys=True,
            )

        merged = list(have)
        known = {key(rule) for rule in have}
        for rule in wanted:
            if key(rule) not in known:
                merged.append(rule)
                known.add(key(rule))
        print("rules after union: %d" % len(merged))
        status, payload = call("PUT", path, merged, facts)
        print("PUT %s -> %s" % (path, status))
        print(json.dumps(payload)[:600])
        _, after = call("GET", path, {}, facts)
        after_list = (
            after if isinstance(after, list) else after.get("securityGroupRules") or []
        )
        print("rules on the nsg now: %d" % len(after_list))
        for rule in after_list:
            print("  %s" % json.dumps(rule))
        return 0 if status in (200, 201, 202) else 1
    if action == "set-list-rules":
        # The subnet's security list is the other half of the answer: OCI applies the list
        # AND the nsg, so a packet needs both to allow it. The list is replaced wholesale by
        # the update, so the current rules are unioned with the new ones first.
        if not rules_path:
            raise SystemExit("set-list-rules needs <rules.json>")
        with open(rules_path, "r", encoding="utf-8") as fh:
            wanted = json.load(fh)
        client = cluster_client(facts)
        item = the_cluster(client, facts)
        subnet_id = endpoint_dict(item).get("subnetId")
        _, subnet = call("GET", "/20160918/subnets/%s" % subnet_id, {}, facts)
        list_ids = subnet.get("securityListIds") or []
        for list_id in list_ids:
            status, sec = call("GET", "/20160918/securityLists/%s" % list_id, {}, facts)
            if status != 200:
                print("GET security list -> %s %s" % (status, json.dumps(sec)[:200]))
                continue
            ingress = list(sec.get("ingressSecurityRules") or [])
            egress = list(sec.get("egressSecurityRules") or [])

            def key(rule: dict) -> str:
                options = rule.get("tcpOptions") or rule.get("udpOptions") or {}
                ports = options.get("destinationPortRange") or {}
                return json.dumps(
                    [
                        rule.get("direction", "INGRESS"),
                        str(rule.get("protocol")),
                        rule.get("source"),
                        rule.get("destination"),
                        ports.get("min"),
                        ports.get("max"),
                    ],
                    sort_keys=True,
                )

            known = {key(rule) for rule in ingress}
            for rule in wanted:
                rule = dict(rule)
                rule.setdefault("direction", "INGRESS")
                rule.setdefault("isStateless", False)
                if key(rule) not in known:
                    ingress.append(rule)
                    known.add(key(rule))
            body = {
                "ingressSecurityRules": ingress,
                "egressSecurityRules": egress,
            }
            put_status, payload = call(
                "PUT", "/20160918/securityLists/%s" % list_id, body, facts
            )
            print("PUT security list %s -> %s" % (list_id, put_status))
            print(json.dumps(payload)[:400])
            _, after = call("GET", "/20160918/securityLists/%s" % list_id, {}, facts)
            for rule in after.get("ingressSecurityRules") or []:
                options = rule.get("tcpOptions") or rule.get("udpOptions") or {}
                ports = options.get("destinationPortRange") or {}
                print(
                    "  INGRESS %s src=%s %s-%s desc=%s"
                    % (
                        rule.get("protocol"),
                        rule.get("source"),
                        ports.get("min"),
                        ports.get("max"),
                        rule.get("description"),
                    )
                )
            if put_status not in (200, 201, 202):
                return 1
        return 0
    if action == "delete-nsg":
        status, payload = call(
            "DELETE", "/20160918/networkSecurityGroups/%s" % nsg, {}, facts
        )
        print("DELETE nsg %s -> %s" % (nsg, status))
        print(json.dumps(payload)[:300])
        return 0 if status in (200, 202, 204) else 1
    if action == "touch-cluster":
        # A benign cluster update: OKE reconciles the control plane when it is asked for a
        # change, and the tenancy-wide volume allowance now has room for the control plane's
        # own volume. A tag is the smallest change that still asks.
        status, cluster = call("GET", "/20180222/clusters/%s" % CLUSTER, {}, facts)
        if status != 200:
            print("GET cluster -> %s %s" % (status, json.dumps(cluster)[:200]))
            return 1
        tags = dict(cluster.get("freeformTags") or {})
        tags["estate-recovery"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        status, payload = call(
            "PUT", "/20180222/clusters/%s" % CLUSTER, {"freeformTags": tags}, facts
        )
        print("PUT cluster tags -> %s %s" % (status, json.dumps(payload)[:200]))
        return 0 if status in (200, 202) else 1
    if action == "vnic-attachments":
        # Is the cluster endpoint's ENI still attached to anything? A VNIC attachment for
        # the endpoint subnet, or for the cluster's public IP, tells whether the control
        # plane still has a backend on the wire.
        status, payload = call(
            "GET", "/20160918/vnicAttachments?compartmentId=%s" % COMPARTMENT, {}, facts
        )
        print("vnic attachments status=%s" % status)
        if status != 200:
            print("  %s" % json.dumps(payload)[:300])
            return 1
        for item in payload if isinstance(payload, list) else payload.get("data") or []:
            print(
                "  %s state=%s instance=%s subnet=%s vnic=%s"
                % (
                    item.get("id"),
                    item.get("lifecycleState"),
                    item.get("instanceId"),
                    item.get("subnetId"),
                    item.get("vnicId"),
                )
            )
        return 0
    if action == "public-ip":
        # The public IP object and whether anything is listening on it.
        status, payload = call(
            "GET",
            "/20160918/publicIps?compartmentId=%s&scope=REGION" % COMPARTMENT,
            {},
            facts,
        )
        print("public ips status=%s" % status)
        if status != 200:
            print("  %s" % json.dumps(payload)[:300])
        for item in (
            payload if isinstance(payload, list) else (payload.get("data") or [])
        ):
            print(
                "  %s %s state=%s assigned=%s"
                % (
                    item.get("id"),
                    item.get("ipAddress"),
                    item.get("lifecycleState"),
                    (item.get("assignedEntity") or "")[:90],
                )
            )
        host = next(
            (a for a in rest if "." in a and not a.startswith("ocid1.")),
            "141.147.80.229",
        )
        for port in ("443", "6443", "22"):
            sock = socket.socket()
            sock.settimeout(6)
            try:
                sock.connect((host, int(port)))
                print("  port %s: OPEN" % port)
            except Exception as exc:  # noqa: BLE001 - the port's answer is the point
                print("  port %s: %s" % (port, exc.__class__.__name__))
            finally:
                sock.close()
        return 0
    if action == "cluster-state":
        # The cluster's own words about itself: what state, what detail, what endpoints.
        status, cluster = call("GET", "/20180222/clusters/%s" % CLUSTER, {}, facts)
        print("status=%s" % status)
        for field in (
            "name",
            "lifecycleState",
            "lifecycleDetails",
            "kubernetesVersion",
            "endpointConfig",
            "clusterPodNetworkOptions",
            "options",
            "freeformTags",
            "definedTags",
            "metadata",
        ):
            if field in cluster:
                print("%s = %s" % (field, json.dumps(cluster.get(field))[:600]))
        return 0
    if action == "pool-nodes":
        # The pool's own nodes, and what the pool thinks it has: a terminated node still
        # counted against the free tier's nodes-per-pool limit is what keeps the pool from
        # ever serving.
        for pool_id in (
            "ocid1.nodepool.oc1.uk-london-1.aaaaaaaawsykhagdekeqlo7fwpzrsfdrzijay7dzllnwux3nxnul34spge3q",
            "ocid1.nodepool.oc1.uk-london-1.aaaaaaaa4mcndzncxqyjhikhxkyablukiy7vs2d5myz4bewqbn3hi5oqpcjq",
        ):
            status, pool = call("GET", "/20180222/nodePools/%s" % pool_id, {}, facts)
            print(
                "pool %s status=%s state=%s nodeCount=%s"
                % (
                    pool.get("name"),
                    status,
                    pool.get("lifecycleState"),
                    pool.get("nodeCount"),
                )
            )
            for field in ("nodes", "node_ids", "nodeIds"):
                if pool.get(field):
                    print("  pool.%s = %s" % (field, json.dumps(pool.get(field))[:400]))
            status, nodes = call(
                "GET", "/20180222/nodes?nodePoolId=%s" % pool_id, {}, facts
            )
            print("  nodes status=%s" % status)
            if status != 200:
                print("  %s" % json.dumps(nodes)[:300])
                continue
            for node in nodes if isinstance(nodes, list) else nodes.get("data") or []:
                print(
                    "  node %s name=%s lifecycle=%s instance=%s"
                    % (
                        node.get("id"),
                        node.get("name"),
                        node.get("lifecycleState"),
                        node.get("instanceId"),
                    )
                )
        return 0
    if action == "delete-node":
        # Take a node out of the pool so the pool's slot frees: DELETE /20180222/nodes/{id}.
        # The id is the compute instance ocid; the pool is named, because the API needs it.
        node_id = next((a for a in rest if a.startswith("ocid1.instance")), "")
        pool_id = next((a for a in rest if a.startswith("ocid1.nodepool")), "")
        if not node_id or not pool_id:
            raise SystemExit("delete-node needs the node ocid and the pool ocid")
        status, payload = call(
            "DELETE",
            "/20180222/nodePools/%s/node/%s?isDecrementSize=true" % (pool_id, node_id),
            {},
            facts,
        )
        print(
            "DELETE node %s from pool %s -> %s %s"
            % (
                node_id,
                pool_id,
                status,
                json.dumps(payload)[:300],
            )
        )
        return 0 if status in (200, 202, 204) else 1
    if action == "delete-pool":
        # Take the whole pool out: DELETE /20180222/nodePools/{poolId}. A pool whose only node
        # is a terminated instance keeps counting it against the free tier's nodes-per-pool
        # limit, and OKE refuses to shed that node (LimitExceeded), so the pool itself is what
        # has to go -- the next apply creates it again with the shape the estate asks for.
        pool_id = next((a for a in rest if a.startswith("ocid1.nodepool")), "")
        if not pool_id:
            raise SystemExit("delete-pool needs the pool ocid")
        status, payload = call("DELETE", "/20180222/nodePools/%s" % pool_id, {}, facts)
        print("DELETE pool %s -> %s %s" % (pool_id, status, json.dumps(payload)[:300]))
        return 0 if status in (200, 202, 204) else 1
    if action == "reclaim-volumes":
        # The estate's reclaim rule, applied over the fast signed path: a volume is
        # reclaimable when it is AVAILABLE, its only attachments are DETACHED or belong to a
        # TERMINATED instance, its name starts with csi-, it carries the
        # role=persistent_volume tag, it is older than the threshold, and it is not among the
        # oldest kept -- the oldest may back a long-lived PersistentVolume whose data cannot
        # be reproduced from the API.
        keep_oldest = 3
        apply = False
        for arg in rest:
            if arg == "apply":
                apply = True
            elif arg.isdigit() and int(arg) <= 50 and keep_oldest == 3:
                keep_oldest = int(arg)
        _, volumes = call(
            "GET", "/20160918/volumes?compartmentId=%s" % COMPARTMENT, {}, facts
        )
        _, attachments = call(
            "GET",
            "/20160918/volumeAttachments?compartmentId=%s" % COMPARTMENT,
            {},
            facts,
        )
        volume_rows = (
            volumes if isinstance(volumes, list) else volumes.get("data") or []
        )
        attachment_rows = (
            attachments
            if isinstance(attachments, list)
            else attachments.get("data") or []
        )
        live = {}
        for attachment in attachment_rows:
            state = attachment.get("lifecycleState")
            if state in ("ATTACHED", "ATTACHING"):
                live.setdefault(attachment.get("volumeId"), []).append(attachment)
        candidates = []
        for volume in volume_rows:
            if volume.get("lifecycleState") != "AVAILABLE":
                continue
            if not (volume.get("displayName") or "").startswith("csi-"):
                continue
            if live.get(volume.get("id")):
                continue
            tags = (volume.get("definedTags") or {}).get("Oracle-Tags") or {}
            freeform = volume.get("freeformTags") or {}
            role = freeform.get("role") or tags.get("role")
            if role and role != "persistent_volume":
                continue
            candidates.append(volume)
        candidates.sort(key=lambda item: item.get("timeCreated") or "")
        keep = candidates[:keep_oldest]
        chosen = candidates[keep_oldest:]
        print(
            "reclaimable candidates: %d (keeping the %d oldest)"
            % (len(candidates), keep_oldest)
        )
        for volume in keep:
            print(
                "  KEEP  %s %sGB %s"
                % (
                    volume.get("displayName"),
                    volume.get("sizeInGBs"),
                    volume.get("id"),
                )
            )
        for volume in chosen:
            print(
                "  %s %s %sGB %s"
                % (
                    "DELETE" if apply else "WOULD DELETE",
                    volume.get("displayName"),
                    volume.get("sizeInGBs"),
                    volume.get("id"),
                )
            )
        if not apply:
            print("dry run: nothing deleted")
            return 0
        freed = 0
        for volume in chosen:
            status, payload = call(
                "DELETE", "/20160918/volumes/%s" % volume.get("id"), {}, facts
            )
            print(
                "DELETE %s -> %s %s"
                % (volume.get("displayName"), status, json.dumps(payload)[:200])
            )
            if status in (200, 202, 204):
                freed += int(volume.get("sizeInGBs") or 0)
        print("freed %sGB of live storage" % freed)
        return 0
    if action == "volumes-raw":
        # The volume and attachment inventory, read straight from the API, with each
        # attachment's instance state beside it: an attachment to a terminated instance is
        # garbage that still holds the storage allowance.
        for label, path in (
            ("volumes", "/20160918/volumes?compartmentId=%s" % COMPARTMENT),
            (
                "attachments",
                "/20160918/volumeAttachments?compartmentId=%s" % COMPARTMENT,
            ),
        ):
            status, payload = call("GET", path, {}, facts)
            print("%s status=%s" % (label, status))
            if status != 200:
                print("  %s" % json.dumps(payload)[:400])
                continue
            rows = payload if isinstance(payload, list) else payload.get("data") or []
            for item in rows:
                if label == "volumes":
                    print(
                        "  %s %s %sGB state=%s"
                        % (
                            item.get("displayName"),
                            item.get("id"),
                            item.get("sizeInGBs"),
                            item.get("lifecycleState"),
                        )
                    )
                else:
                    print(
                        "  volume=%s instance=%s state=%s type=%s"
                        % (
                            item.get("volumeId"),
                            item.get("instanceId"),
                            item.get("lifecycleState"),
                            item.get("attachmentType"),
                        )
                    )
        return 0
    if action == "storage":
        # What is holding the storage allowance, and is it attached to anything alive?
        sys.path.insert(0, sdk_path())
        from oci.core import ComputeClient  # noqa: PLC0415
        from oci.signer import Signer  # noqa: PLC0415

        signer = Signer(
            facts["tenancy"],
            facts["user"],
            facts["fingerprint"],
            private_key_file_location=os.path.expanduser(facts["key_file"]),
        )
        config = {
            "user": facts["user"],
            "tenancy": facts["tenancy"],
            "fingerprint": facts["fingerprint"],
            "key_file": os.path.expanduser(facts["key_file"]),
            "region": facts["region"],
        }
        compute = ComputeClient(config, signer=signer)
        engine = cluster_client(facts)
        print("node pools:")
        for pool in engine.list_node_pools(COMPARTMENT).data:
            print(
                "  %s %s state=%s nodes=%s"
                % (
                    pool.name,
                    pool.id,
                    pool.lifecycle_state,
                    getattr(pool, "node_count", None)
                    or getattr(pool, "nodeCount", None),
                )
            )
        print("instances:")
        for instance in compute.list_instances(COMPARTMENT).data:
            print(
                "  %s %s state=%s ad=%s"
                % (
                    instance.display_name,
                    instance.id,
                    instance.lifecycle_state,
                    getattr(instance, "availability_domain", None),
                )
            )
        print("volumes:")
        for volume in compute.list_volumes(COMPARTMENT).data:
            print(
                "  %s %s %sGB state=%s ad=%s"
                % (
                    volume.display_name,
                    volume.id,
                    getattr(volume, "size_in_gbs", None)
                    or getattr(volume, "sizeInGBs", None),
                    volume.lifecycle_state,
                    getattr(volume, "availability_domain", None),
                )
            )
        print("volume attachments:")
        for attachment in compute.list_volume_attachments(COMPARTMENT).data:
            print(
                "  %s volume=%s instance=%s state=%s type=%s"
                % (
                    attachment.id,
                    attachment.volume_id,
                    attachment.instance_id,
                    attachment.lifecycle_state,
                    attachment.attachment_type,
                )
            )
        return 0
    if action == "endpoint-state":
        # Is the public endpoint still attached, and is the control plane serving?
        status, ips = call(
            "GET",
            "/20160918/publicIps?compartmentId=%s" % COMPARTMENT,
            {},
            facts,
        )
        print("public ips status=%s" % status)
        for item in ips if isinstance(ips, list) else ips.get("data") or []:
            print(
                "  %s %s state=%s assignment=%s"
                % (
                    item.get("id"),
                    item.get("ipAddress"),
                    item.get("lifecycleState"),
                    (item.get("assignedEntity") or "")[:80],
                )
            )
        status, pools = call(
            "GET",
            "/20180222/nodePools?compartmentId=%s" % COMPARTMENT,
            {},
            facts,
        )
        print("node pools status=%s" % status)
        for item in pools if isinstance(pools, list) else pools.get("data") or []:
            print(
                "  %s %s state=%s nodes=%s"
                % (
                    item.get("id"),
                    item.get("name"),
                    item.get("lifecycleState"),
                    item.get("node_count"),
                )
            )
        status, cluster = call("GET", "/20180222/clusters/%s" % CLUSTER, {}, facts)
        print(
            "cluster status=%s lifecycle=%s" % (status, cluster.get("lifecycleState"))
        )
        print("  endpoints: %s" % json.dumps(cluster.get("endpoints")))
        return 0
    if action == "diagnose":
        # Where is the packet dropped? An nsg rule is only half the answer: the subnet's
        # security lists apply too, and the cluster's public endpoint has its own lifecycle.
        client = cluster_client(facts)
        item = the_cluster(client, facts)
        status, cluster = call("GET", "/20180222/clusters/%s" % item.id, {}, facts)
        print("cluster status=%s" % status)
        for key in sorted(cluster):
            if (
                "endpoint" in key.lower()
                or "lifecycle" in key.lower()
                or "public" in key.lower()
            ):
                print("  %s: %s" % (key, json.dumps(cluster[key])[:400]))
        subnet_id = endpoint_dict(item).get("subnetId")
        status, subnet = call("GET", "/20160918/subnets/%s" % subnet_id, {}, facts)
        print("subnet status=%s" % status)
        list_ids = subnet.get("securityListIds") or []
        print("securityListIds: %s" % list_ids)
        for list_id in list_ids:
            list_status, sec = call(
                "GET", "/20160918/securityLists/%s" % list_id, {}, facts
            )
            print(
                "security list %s status=%s name=%s"
                % (list_id, list_status, sec.get("displayName"))
            )
            for rule in sec.get("ingressSecurityRules") or []:
                options = rule.get("tcpOptions") or rule.get("udpOptions") or {}
                ports = options.get("destinationPortRange") or {}
                print(
                    "   INGRESS %s src=%s %s-%s desc=%s"
                    % (
                        rule.get("protocol"),
                        rule.get("source"),
                        ports.get("min"),
                        ports.get("max"),
                        rule.get("description"),
                    )
                )
        return 0
    if action == "rules-try":
        # Which path holds an nsg's rules? The CLI's own client is not installed, so the
        # candidates are tried and the server's answer names the right one.
        client = cluster_client(facts)
        item = the_cluster(client, facts)
        print("cluster endpointConfig: %s" % json.dumps(endpoint_dict(item)))
        candidates = [
            "/20160918/networkSecurityGroups/%s/networkSecurityGroupSecurityRules"
            % nsg,
            "/20160918/networkSecurityGroups/%s/securityRules" % nsg,
            "/20160918/networkSecurityGroups/%s/networkSecurityGroupSecurityRules?limit=50"
            % nsg,
            "/20160918/networkSecurityGroupSecurityRules?networkSecurityGroupId=%s"
            % nsg,
        ]
        for path in candidates:
            status, payload = call("GET", path, {}, facts)
            print("GET %s -> %s %s" % (path, status, json.dumps(payload)[:200]))
        return 0
    if action == "run-command":
        # Run a script ON an instance that has no public IP and no SSH door. The OCI CLI
        # 3.90.3 has no `compute instance run-command` command and the SDK 2.184.2 has no
        # run_command API, so this is the only way in: the instance agent's own plugin
        # ("Compute Instance Run Command", ENABLED on the recovery host) accepts a TEXT
        # source. The script is read from a file, never from a shell fragment.
        instance = next((a for a in rest if a.startswith("ocid1.instance.")), "")
        script_path = next((a for a in rest if a.endswith(".sh")), "")
        if not instance or not script_path:
            raise SystemExit("run-command needs <instance-ocid> <script.sh>")
        with open(script_path, "r", encoding="utf-8") as fh:
            script = fh.read()
        body = {
            "compartmentId": COMPARTMENT,
            "displayName": "estate-diag",
            "source": {"sourceType": "TEXT", "text": script},
            "timeoutInSeconds": 120,
        }
        path = "/20160918/instances/%s/actions/runCommand" % instance
        status, payload = call("POST", path, body, facts)
        print("POST runCommand -> %s" % status)
        if status not in (200, 202):
            print(json.dumps(payload)[:800])
            return 1
        command_id = payload.get("id", "")
        print("command: %s" % command_id)
        # The agent runs the script and writes the answer back; the command's own output
        # is the fact. Poll, bounded: the executor's ceiling is 100s.
        for _ in range(10):
            status, payload = call(
                "GET",
                "/20160918/instances/%s/commands/%s" % (instance, command_id),
                {},
                facts,
            )
            state = payload.get("lifecycleState", "")
            if state in ("SUCCEEDED", "FAILED", "CANCELED", "TIMED_OUT"):
                print("state: %s" % state)
                out = payload.get("output", "")
                if out:
                    try:
                        out = base64.b64decode(out).decode("utf-8", "replace")
                    except Exception:  # noqa: BLE001, S110 - the output may be plain text already
                        pass
                print(out[:8000])
                log_id = payload.get("logId", "")
                if log_id:
                    print("logId: %s" % log_id)
                return 0 if state == "SUCCEEDED" else 1
            time.sleep(4)
        print("the command has not finished yet; state=%s" % state)
        return 1
    if action == "raw-get":
        # A read-only GET against any OCI path, so a fact can be measured directly from the
        # API instead of inferred. The path is data, not a shell fragment: it is split on
        # whitespace and nothing is interpreted.
        if not path_arg:
            raise SystemExit("raw-get needs <path>")
        status, payload = call("GET", path_arg, {}, facts)
        print("GET %s -> %s" % (path_arg, status))
        print(json.dumps(payload, indent=1)[:8000])
        return 0 if status == 200 else 1
    if action == "survival":
        # Which volume does each backup come from, and does that volume still exist?
        # This is the map the recovery plan is written against: a backup is only a
        # recovery path if its SOURCE volume survives, because the backup is a point in
        # time, not the live data.
        def _get(path, query=None):
            full = path + ("?" + query if query else "")
            status, payload = call("GET", full, {}, facts)
            if status != 200:
                raise SystemExit("GET %s -> %s" % (full, status))
            return payload

        def _items(payload):
            # The API answers a list on some paths and an object on others.
            if isinstance(payload, list):
                return payload
            return payload.get("items", []) if isinstance(payload, dict) else []

        vols = _items(
            _get(
                "/20160918/volumes",
                "compartmentId="
                + COMPARTMENT
                + "&availabilityDomain="
                + "lPOl:UK-LONDON-1-AD-1",
            )
        )
        by_ocid = {v["id"]: v for v in vols}
        print("=== volumes in AD-1 (%d) ===" % len(vols))
        for v in sorted(vols, key=lambda x: x.get("timeCreated", "")):
            tags = v.get("systemTags") or {}
            interesting = {
                k: val
                for k, val in tags.items()
                if "csi" in k.lower()
                or "pvc" in k.lower()
                or "kubernetes" in k.lower()
                or "estate" in k.lower()
                or "claim" in k.lower()
            }
            print(
                "  %-12s %5sGB  %s  %s"
                % (
                    v.get("lifecycleState"),
                    v.get("sizeInGBs"),
                    v.get("displayName"),
                    v["id"],
                )
            )
            if interesting:
                for k, val in sorted(interesting.items()):
                    print("        %s = %s" % (k, val))
            print("        freeformTags = %s" % json.dumps(v.get("freeformTags") or {}))

        backups = _items(
            _get(
                "/20160918/volumeBackups",
                "compartmentId=" + COMPARTMENT,
            )
        )
        print(
            "\n=== volume backups (%d): does the SOURCE volume survive? ==="
            % len(backups)
        )
        alive = 0
        dead = 0
        seen = set()
        for b in sorted(backups, key=lambda x: x.get("timeCreated", "")):
            src = b.get("volumeId")
            v = by_ocid.get(src)
            state = "SURVIVES" if v else "SOURCE-GONE"
            tags = b.get("freeformTags") or {}
            ident = "%s/%s" % (tags.get("namespace", "?"), tags.get("claim", "?"))
            if ident in seen:
                continue  # one line per workload, not per backup
            seen.add(ident)
            if v:
                alive += 1
            else:
                dead += 1
            print(
                "  %-12s %-46s %-42s unique=%sGB %s"
                % (
                    state,
                    ident,
                    b.get("displayName"),
                    b.get("uniqueSizeInGBs"),
                    b.get("timeCreated"),
                )
            )
        print(
            "\nsummary: %d workload(s) whose source volume survives, %d whose source is gone"
            % (alive, dead)
        )
        total_unique = sum(int(b.get("uniqueSizeInGBs") or 0) for b in backups)
        print(
            "unique bytes across all %d backups: %s GB" % (len(backups), total_unique)
        )
        return 0
    if action == "cli":
        # Read-only OCI CLI commands, run with the agent profile. The CLI knows the
        # endpoint, the signing and the query shape for the service-limits API, which the
        # signed REST door does not; the arguments are data, never a shell fragment.
        import shlex  # noqa: PLC0415
        import subprocess  # noqa: PLC0415

        # The intent passes seven fixed slots and the command words last, so the command
        # is the final slot. It arrives as one string, so it is split on whitespace here:
        # the words are data, and nothing is interpreted.
        words = shlex.split(rest[-1]) if rest else []
        if not words:
            raise SystemExit("cli needs <oci arguments>")
        # A filter word keeps a jq expression out of the command line: the shell would
        # split it, and the estate's own rule is that nothing is interpreted here.
        want = ""
        keep = []
        for w in words:
            if w.startswith("@filter:"):
                want = w.split(":", 1)[1]
            else:
                keep.append(w)
        words = keep
        proc = subprocess.run(  # noqa: S603 - the estate's own OCI CLI, with its own arguments
            [os.path.expanduser("~/.local/share/uv/tools/oci-cli/bin/oci")] + words,
            capture_output=True,
            text=True,
            timeout=90,
        )
        print("oci %s -> %s" % (" ".join(words), proc.returncode))
        if want and proc.returncode == 0 and proc.stdout.strip().startswith("{"):
            try:
                doc = json.loads(proc.stdout)
            except ValueError:
                doc = {}
            rows = [r for r in doc.get("data", []) if want in str(r.get("name", ""))]
            print(json.dumps({"data": rows}, indent=2))
            return 0
        print(proc.stdout[:8000])
        if proc.stderr.strip():
            print("stderr: %s" % proc.stderr[:2000])
        return proc.returncode
    if action == "ingress":
        # The two ways back in: the load balancer that is still ACTIVE, and the vault that
        # still holds the provider credentials. Both are read; nothing is written.
        status, payload = call(
            "GET", "/20170115/loadBalancers?compartmentId=%s" % COMPARTMENT, {}, facts
        )
        for item in payload if isinstance(payload, list) else payload.get("data") or []:
            print(
                "load-balancer %s state=%s"
                % (item.get("displayName"), item.get("lifecycleState"))
            )
            print("  ipAddresses: %s" % item.get("ipAddresses"))
            print("  shape: %s" % item.get("shape"))
            print("  isPrivate: %s" % item.get("isPrivate"))
            print("  subnetIds: %s" % item.get("subnetIds"))
            print("  presigned: %s" % item.get("presignedUrl"))
            for name in (
                "listenerIds",
                "backendSetIds",
                "networkSecurityGroupIds",
                "routeTableId",
            ):
                print("  %s: %s" % (name, item.get(name)))
        for label, path in (
            (
                "listeners",
                "/20170115/loadBalancerListeners?compartmentId=%s" % COMPARTMENT,
            ),
            (
                "backend-sets",
                "/20170115/loadBalancerBackendSets?compartmentId=%s" % COMPARTMENT,
            ),
        ):
            status, payload = call("GET", path, {}, facts)
            print("%s status=%s" % (label, status))
            for item in (
                payload if isinstance(payload, list) else payload.get("data") or []
            ):
                print(
                    "  %s state=%s port=%s protocol=%s"
                    % (
                        item.get("displayName"),
                        item.get("lifecycleState"),
                        item.get("port"),
                        item.get("protocol"),
                    )
                )
                for key in (
                    "defaultBackendSetId",
                    "backendSets",
                    "isTlsEnabled",
                    "certificateName",
                    "connectionIdleTimeoutInSeconds",
                    "idleTimeoutInSeconds",
                    "pathRoutings",
                ):
                    value = item.get(key)
                    if value:
                        print("    %s: %s" % (key, value))
        return 0
    if action == "vault":
        # The vault's secret NAMES only. A secret value is never printed; the name is
        # enough to decide whether the recovery host can obtain the credential itself.
        sys.path.insert(0, sdk_path())
        from oci.signer import Signer  # noqa: PLC0415

        signer = Signer(
            facts["tenancy"],
            facts["user"],
            facts["fingerprint"],
            private_key_file_location=os.path.expanduser(facts["key_file"]),
        )
        config = {
            "user": facts["user"],
            "tenancy": facts["tenancy"],
            "fingerprint": facts["fingerprint"],
            "key_file": os.path.expanduser(facts["key_file"]),
            "region": facts["region"],
        }
        try:
            from oci.secrets_manager import SecretsManagerClient  # noqa: PLC0415
        except Exception as exc:  # noqa: BLE001
            print("secrets manager unavailable: %s" % exc)
            return 1
        client = SecretsManagerClient(config, signer=signer)
        try:
            vaults = client.list_secrets_vaults(COMPARTMENT).data
        except Exception as exc:  # noqa: BLE001
            print("list_secrets_vaults failed: %s" % exc)
            return 1
        for vault in vaults:
            print("vault %s state=%s" % (vault.id, vault.lifecycle_state))
            try:
                secrets = client.list_secrets(vault.id).data
            except Exception as exc:  # noqa: BLE001
                print("  list_secrets failed: %s" % exc)
                continue
            for secret in secrets:
                print(
                    "  secret %-44s state=%s version=%s"
                    % (
                        secret.name,
                        secret.lifecycle_state,
                        getattr(secret, "currentVersionNumber", "?"),
                    )
                )
        return 0
    if action == "capacity":
        # Everything the router recovery plan turns on, measured rather than assumed:
        # the account tier, the shape each availability domain actually offers, which
        # surviving volume holds which database (through the backup that names the PVC),
        # and the load balancer the public entry points point at.
        status, payload = call(
            "GET", "/20160918/subscriptions?compartmentId=%s" % COMPARTMENT, {}, facts
        )
        print("subscriptions status=%s" % status)
        for item in payload if isinstance(payload, list) else payload.get("data") or []:
            print(
                "  %s tier=%s status=%s"
                % (
                    item.get("displayName"),
                    item.get("lifecycleState"),
                    item.get("timeCreated"),
                )
            )
            for key, value in sorted(item.items()):
                if any(
                    word in key.lower() for word in ("tier", "plan", "quota", "entitle")
                ):
                    print("    %s: %s" % (key, value))
        for domain in (
            "lPOl:UK-LONDON-1-AD-1",
            "lPOl:UK-LONDON-1-AD-2",
            "lPOl:UK-LONDON-1-AD-3",
        ):
            status, payload = call(
                "GET",
                "/20160918/shapes?compartmentId=%s&availabilityDomain=%s"
                % (COMPARTMENT, domain),
                {},
                facts,
            )
            rows = payload if isinstance(payload, list) else payload.get("data") or []
            names = sorted({r.get("shape") for r in rows if r.get("shape")})
            print(
                "AD %s status=%s shapes=%d A1.Flex=%s"
                % (domain, status, len(names), "VM.Standard.A1.Flex" in names)
            )
            for row in rows:
                if row.get("shape") == "VM.Standard.A1.Flex":
                    print(
                        "  A1.Flex ocpus=%s memory=%s"
                        % (row.get("ocpus"), row.get("memory"))
                    )
        # Which surviving volume holds which database. The backup names the PVC it came
        # from, and the backup names its source volume, so the pair identifies the volume.
        status, payload = call(
            "GET", "/20160918/volumeBackups?compartmentId=%s" % COMPARTMENT, {}, facts
        )
        rows = payload if isinstance(payload, list) else payload.get("data") or []
        print("volume backups: %d" % len(rows))
        for item in rows:
            source = ""
            for _key, value in item.items():
                if isinstance(value, str) and value.startswith("ocid1.volume."):
                    source = value
                if isinstance(value, dict):
                    for inner in value.values():
                        if isinstance(inner, str) and inner.startswith("ocid1.volume."):
                            source = inner
            print("  %-72s source=%s" % (item.get("displayName"), source or "?"))
        for label, path in (
            (
                "load-balancers",
                "/20170115/loadBalancers?compartmentId=%s" % COMPARTMENT,
            ),
            (
                "public-ips",
                "/20160918/publicIps?compartmentId=%s&scope=REGION" % COMPARTMENT,
            ),
            ("subnets", "/20160918/subnets?compartmentId=%s" % COMPARTMENT),
            ("vcns", "/20160918/vcns?compartmentId=%s" % COMPARTMENT),
            ("nat-gateways", "/20160918/natGateways?compartmentId=%s" % COMPARTMENT),
        ):
            status, payload = call("GET", path, {}, facts)
            print("%s status=%s" % (label, status))
            for item in (
                payload if isinstance(payload, list) else payload.get("data") or []
            ):
                if label == "load-balancers":
                    print(
                        "  %s state=%s ip=%s"
                        % (
                            item.get("displayName"),
                            item.get("lifecycleState"),
                            item.get("ipAddresses"),
                        )
                    )
                elif label == "public-ips":
                    print(
                        "  %s state=%s assigned=%s"
                        % (
                            item.get("ipAddress"),
                            item.get("lifecycleState"),
                            (item.get("assignedEntity") or "")[:60],
                        )
                    )
                elif label == "subnets":
                    print(
                        "  %s cidr=%s vcn=%s public=%s"
                        % (
                            item.get("displayName"),
                            item.get("cidrBlock"),
                            (item.get("vcnId") or "")[-12:],
                            item.get("prohibitPublicIpOnVnic"),
                        )
                    )
                elif label == "vcns":
                    print(
                        "  %s cidr=%s"
                        % (item.get("displayName"), item.get("cidrBlock"))
                    )
                else:
                    print(
                        "  %s state=%s"
                        % (item.get("displayName"), item.get("lifecycleState"))
                    )
        return 0
    if action == "limits":
        # The service limits, found by trying the versions and service names OCI actually
        # serves. A 404 here is not a fact about the allowance, only about the URL, so the
        # candidates are tried and the answer that comes back is printed.
        for path in (
            "/20181025/limits/values?compartmentId=%s&serviceName=container-engine"
            % COMPARTMENT,
            "/20180401/limits/values?compartmentId=%s&serviceName=container-engine"
            % COMPARTMENT,
            "/20181025/limits/values?compartmentId=%s&serviceName=blockstorage"
            % COMPARTMENT,
            "/20181025/limits/values?compartmentId=%s&serviceName=volume-backup"
            % COMPARTMENT,
        ):
            status, payload = call("GET", path, {}, facts)
            print("GET %s -> %s" % (path, status))
            if status != 200:
                print("  %s" % json.dumps(payload)[:200])
                continue
            for item in (
                payload if isinstance(payload, list) else payload.get("data") or []
            ):
                print(
                    "  %-38s value=%s limit=%s"
                    % (item.get("name"), item.get("value"), item.get("limit"))
                )
        return 0
    if action == "sdk-facts":
        # The facts the recovery plan turns on, read through OCI's own SDK clients rather
        # than by guessing REST URLs: the service limits that decide what may be created,
        # the shapes each availability domain actually offers, and the load balancer the
        # public entry points point at.
        sys.path.insert(0, sdk_path())
        from oci.core import ComputeClient  # noqa: PLC0415
        from oci.limits import LimitsClient  # noqa: PLC0415
        from oci.signer import Signer  # noqa: PLC0415

        signer = Signer(
            facts["tenancy"],
            facts["user"],
            facts["fingerprint"],
            private_key_file_location=os.path.expanduser(facts["key_file"]),
        )
        config = {
            "user": facts["user"],
            "tenancy": facts["tenancy"],
            "fingerprint": facts["fingerprint"],
            "key_file": os.path.expanduser(facts["key_file"]),
            "region": facts["region"],
        }
        limits = LimitsClient(config, signer=signer)
        for service in (
            "container-engine",
            "blockstorage",
            "volume-backup",
            "objectstorage",
        ):
            try:
                values = limits.list_resource_limits(
                    COMPARTMENT, service_name=service
                ).data
            except Exception as exc:  # noqa: BLE001
                print("limits %s -> unavailable (%s)" % (service, exc))
                continue
            print("limits %s:" % service)
            for item in values:
                print(
                    "  %-38s value=%s limit=%s"
                    % (
                        getattr(item, "name", "?"),
                        getattr(item, "value", None),
                        getattr(item, "limit_value", None),
                    )
                )
        compute = ComputeClient(config, signer=signer)
        for domain in (
            "lPOl:UK-LONDON-1-AD-1",
            "lPOl:UK-LONDON-1-AD-2",
            "lPOl:UK-LONDON-1-AD-3",
        ):
            status, payload = call(
                "GET",
                "/20160918/shapes?compartmentId=%s&availabilityDomain=%s"
                % (COMPARTMENT, domain),
                {},
                facts,
            )
            rows = payload if isinstance(payload, list) else payload.get("data") or []
            names = sorted({r.get("shape") for r in rows if r.get("shape")})
            print(
                "  AD %s status=%s shapes=%d A1.Flex=%s"
                % (domain, status, len(rows), "VM.Standard.A1.Flex" in names)
            )
        print("load balancers:")
        for item in compute.list_load_balancers(COMPARTMENT).data:
            print(
                "  %s state=%s ip=%s"
                % (item.display_name, item.lifecycle_state, item.ip_addresses)
            )
        print("boot volumes:")
        for item in compute.list_boot_volumes(COMPARTMENT).data:
            print(
                "  %s %sGB ad=%s state=%s"
                % (
                    item.display_name,
                    item.size_in_gbs,
                    item.availability_domain,
                    item.lifecycle_state,
                )
            )
        return 0
    if action == "entitlement":
        # What the account is actually allowed to do right now, and what it is already
        # spending it on. The Always Free allowance is a set of LIMITS, not a shape name:
        # cluster-count = 0 means the control plane is gone for good, whatever shape a
        # cluster would have used. So the limits are read, and the resources that count
        # against them are counted, before anything is declared.
        limits = {}
        for label, path in (
            (
                "limits-ce",
                "/20181025/limits/values?compartmentId=%s&serviceName=container-engine"
                % COMPARTMENT,
            ),
            (
                "limits-bv",
                "/20181025/limits/values?compartmentId=%s&serviceName=blockstorage"
                % COMPARTMENT,
            ),
            (
                "limits-vb",
                "/20181025/limits/values?compartmentId=%s&serviceName=volume-backup"
                % COMPARTMENT,
            ),
            (
                "volume-backups",
                "/20160918/volumeBackups?compartmentId=%s" % COMPARTMENT,
            ),
            ("instances", "/20160918/instances?compartmentId=%s" % COMPARTMENT),
            ("boot-volumes", "/20160918/bootVolumes?compartmentId=%s" % COMPARTMENT),
            (
                "load-balancers",
                "/20160918/loadBalancers?compartmentId=%s" % COMPARTMENT,
            ),
        ):
            status, payload = call("GET", path, {}, facts)
            print("%s status=%s" % (label, status))
            rows = payload if isinstance(payload, list) else payload.get("data") or []
            if label.startswith("limits-"):
                for item in rows:
                    print(
                        "  %-34s value=%s limit=%s"
                        % (item.get("name"), item.get("value"), item.get("limit"))
                    )
                continue
            if label == "volume-backups":
                print("  backups: %d" % len(rows))
                for item in rows:
                    print(
                        "    %s %s state=%s size=%sGB"
                        % (
                            item.get("displayName"),
                            item.get("id"),
                            item.get("lifecycleState"),
                            item.get("sizeInGBs"),
                        )
                    )
                continue
            if label == "instances":
                for item in rows:
                    print(
                        "  instance %s shape=%s ad=%s state=%s"
                        % (
                            item.get("displayName"),
                            item.get("shape"),
                            item.get("availabilityDomain"),
                            item.get("lifecycleState"),
                        )
                    )
                continue
            if label == "boot-volumes":
                for item in rows:
                    print(
                        "  boot-volume %s %sGB ad=%s state=%s"
                        % (
                            item.get("displayName"),
                            item.get("sizeInGBs"),
                            item.get("availabilityDomain"),
                            item.get("lifecycleState"),
                        )
                    )
                continue
            if label == "load-balancers":
                for item in rows:
                    print(
                        "  load-balancer %s state=%s ip=%s"
                        % (
                            item.get("displayName"),
                            item.get("lifecycleState"),
                            (item.get("ipAddresses") or ""),
                        )
                    )
                continue
        # The A1 Flex shape, and whether the domain offers it today. Always Free capacity is
        # not offered in every availability domain, and Oracle moves it. The domain names
        # carry a prefix ("lPOl:UK-LONDON-1-AD-1"), so they are read rather than guessed.
        status, payload = call(
            "GET",
            "/20160918/availabilityDomains?compartmentId=%s" % COMPARTMENT,
            {},
            facts,
        )
        ads = []
        for item in payload if isinstance(payload, list) else payload.get("data") or []:
            ads.append(item.get("name"))
            print("  AD %s" % item.get("name"))
        for ad in ads:
            status, payload = call(
                "GET",
                "/20160918/shapes?compartmentId=%s&availabilityDomain=%s"
                % (COMPARTMENT, ad),
                {},
                facts,
            )
            rows = payload if isinstance(payload, list) else payload.get("data") or []
            names = sorted({r.get("shape") for r in rows if r.get("shape")})
            print(
                "  %s shapes=%d A1.Flex=%s"
                % (ad, len(rows), "VM.Standard.A1.Flex" in names)
            )
        return 0
    if action == "raw-cluster":
        client = cluster_client(facts)
        item = the_cluster(client, facts)
        status, payload = call("GET", "/20180222/clusters/%s" % item.id, {}, facts)
        print("raw GET cluster -> %s" % status)
        print(json.dumps(payload, indent=1)[:6000])
        return 0 if status == 200 else 1
    if action == "attach":
        # Put the new NSG on the cluster's endpoint, keeping the one already there.
        if not nsg:
            raise SystemExit("attach needs <nsg-ocid>")
        client = cluster_client(facts)
        item = the_cluster(client, facts)
        endpoint = endpoint_dict(item)
        nsg_ids = list(endpoint.get("nsgIds") or [])
        if nsg not in nsg_ids:
            nsg_ids.append(nsg)
        endpoint["nsgIds"] = nsg_ids
        status, payload = call(
            "PUT",
            "/20180222/clusters/%s" % item.id,
            {"endpointConfig": endpoint},
            facts,
        )
        print("PUT cluster -> %s" % status)
        print(json.dumps(payload)[:600])
        if status in (200, 202):
            print(
                "endpointConfig.nsgIds requested: %s" % (endpoint.get("nsgIds") or [])
            )
            return 0
        return 1
    print("unknown action %r" % action)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
