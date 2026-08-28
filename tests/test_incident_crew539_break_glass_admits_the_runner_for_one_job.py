"""crew#539, 2026-08-28: the cluster could not heal itself and nobody had a kube path.

coredns died behind the Cilium chain, Flux could not resolve github.com, the merged revert
(idp#514) never reached the cluster. Runners are outside control_plane_allowed_cidrs and the
laptop session token is retired (crew#345). The fix is a break-glass mode on oke-check: the
runner's /32 is admitted through tofu for one job, ONE named playbook runs, the list is restored
on every exit path. These tests run the playbooks against a recording kubectl/flux and read the
rebuild script's break-glass branch for the two properties that make it safe.
"""
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parents[1]
PLAYBOOK = IDP / "bin" / "idp-oke-break-glass"
REBUILD = IDP / "bin" / "idp-oke-rebuild"
WORKFLOW = IDP / ".github" / "workflows" / "oke-check.yml"
MUTATING = re.compile(r"^(kubectl|flux) (delete|apply|rollout|run|reconcile|patch|create|scale|edit|replace)\b")


def _fake_path(tmp_path: Path) -> tuple[Path, Path]:
    log = tmp_path / "calls.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("kubectl", "flux"):
        f = bin_dir / tool
        f.write_text(f'#!/bin/sh\nprintf \'%s %s\\n\' "{tool}" "$*" >> "{log}"\ncat >/dev/null 2>&1 || true\necho ok\n')
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return bin_dir, log


def _run(playbook: str, tmp_path: Path) -> tuple[subprocess.CompletedProcess, list[str]]:
    bin_dir, log = _fake_path(tmp_path)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), playbook], capture_output=True, text=True, env=env)
    calls = log.read_text().splitlines() if log.exists() else []
    return p, calls


def test_diagnose_is_read_only(tmp_path):
    p, calls = _run("diagnose", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert calls, "diagnose read nothing"
    assert [c for c in calls if MUTATING.match(c)] == []


def test_cilium_unchain_removes_the_release_before_the_cni_config_and_ends_with_flux(tmp_path):
    p, calls = _run("cilium-unchain", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    joined = "\n".join(calls)
    order = [
        joined.index("delete helmrelease -n kube-system cilium"),
        joined.index("apply -f -"),                       # the cni-unchain DaemonSet
        joined.index("rollout restart deploy/coredns"),
        joined.index("reconcile source git flux-system"),
        joined.index("reconcile kustomization flux-system"),
    ]
    assert order == sorted(order), calls
    assert "delete ds cni-unchain -n kube-system" in joined, "the privileged helper is not left on the cluster"


def test_cni_cleanup_helper_runs_on_the_host_network():
    """run 33132419902: with the chained config left behind, cilium-cni fails every new sandbox,
    so a helper on the pod network can never start. hostNetwork pods call no CNI."""
    src = PLAYBOOK.read_text()
    helper = src[src.index("name: cni-unchain"):src.index("YAML\n", src.index("name: cni-unchain"))]
    assert "hostNetwork: true" in helper


def test_unknown_playbook_is_refused_and_list_names_both(tmp_path):
    p, _ = _run("rm-rf-everything", tmp_path)
    assert p.returncode == 64
    listed = subprocess.run([str(PLAYBOOK), "--list"], capture_output=True, text=True).stdout.split()
    assert listed == ["diagnose", "cilium-unchain", "helm-retry", "dns-per-node", "dns-per-namespace", "tcp-per-node", "node-drain", "node-uncordon", "chi-resize"]


def test_rebuild_break_glass_restores_the_list_on_every_exit_path():
    src = REBUILD.read_text()
    branch = src[src.index("--break-glass)"):src.index("--teardown-rebuild)")]
    assert 'ORIG_CIDRS="$OKE_ALLOWED_CIDRS"' in branch
    assert "trap bg_revoke EXIT" in branch and 'export OKE_ALLOWED_CIDRS="$ORIG_CIDRS"' in branch
    assert branch.index("trap bg_revoke EXIT") < branch.index('export OKE_ALLOWED_CIDRS="$ORIG_CIDRS, \\"$EGRESS/32\\""')
    assert '[ -n "${OCI_CI:-}" ] ||' in branch, "a laptop must be refused (crew#345)"
    assert "--list | tr ' ' '\\n' | grep -qx \"$PLAYBOOK\"" in branch, "only a named playbook runs"


def test_workflow_offers_break_glass_with_a_named_playbook():
    wf = WORKFLOW.read_text()
    assert "surge-finish, break-glass]" in wf
    assert "options: [diagnose, cilium-unchain, helm-retry, dns-per-node, dns-per-namespace, tcp-per-node, node-drain, node-uncordon, chi-resize]" in wf
    assert "BREAK_GLASS_PLAYBOOK: ${{ inputs.playbook || 'diagnose' }}" in wf


def test_dns_probe_pod_passes_the_cluster_pod_security_policies():
    """runs 33133317589 and 33134611331: the unchain landed but `dns-answers` failed because kyverno
    refused the `kubectl run` probe pod — first require-run-as-nonroot / require-ro-rootfs /
    restrict-seccomp-strict, then disallow-default-namespace / require-pod-probes /
    require-requests-limits. The probe is a full Pod manifest shaped like every platform workload."""
    import yaml
    src = PLAYBOOK.read_text()
    block = src[src.index("apiVersion: v1\nkind: Pod"):src.index("YAML\n", src.index("kind: Pod"))]
    block = block.replace("$pin", "  nodeName: 10.0.0.1").replace("$name", "dns-probe").replace("$fqdn", "github.com").replace("$ns", "kube-system")
    pod = yaml.safe_load(block)
    assert pod["metadata"]["namespace"] == "kube-system"
    assert pod["spec"]["nodeName"] == "10.0.0.1", "the probe can be pinned to a node (dns-per-node)"
    spec = pod["spec"]
    assert spec["securityContext"]["runAsNonRoot"] is True
    assert spec["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
    assert spec["priorityClassName"]
    c = spec["containers"][0]
    assert c["resources"]["requests"]["cpu"] and c["resources"]["limits"]["memory"]
    assert c["readinessProbe"] and c["livenessProbe"]
    assert c["securityContext"]["readOnlyRootFilesystem"] is True
    assert c["securityContext"]["allowPrivilegeEscalation"] is False
    assert c["securityContext"]["capabilities"]["drop"] == ["ALL"]


def test_cilium_unchain_forces_secret_store_after_the_tree_and_removes_the_probe(tmp_path):
    """run 33134611331: the webhooks rolled out, yet `secret-store` still showed the dry-run EOF
    from before the restart — `flux reconcile kustomization flux-system` does not cascade. The
    playbook forces secret-store after the tree, and the probe pod is not left in kube-system."""
    p, calls = _run("cilium-unchain", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    joined = "\n".join(calls)
    assert joined.index("reconcile kustomization flux-system") < joined.index("reconcile kustomization secret-store")
    # review idp#525: a leftover probe (a prior run died before remove, or already Succeeded) makes
    # apply a no-op and dns-answers reads the old verdict; clear it, waiting, before the apply.
    clear = joined.index("delete pod/dns-probe -n kube-system --ignore-not-found --wait=true")
    assert clear < joined.index("apply -f -", joined.index("rollout status deploy/coredns"))
    assert joined.index("wait pod/dns-probe") < joined.index("delete pod/dns-probe", clear + 1)


def test_cilium_unchain_restarts_the_admission_webhooks_after_coredns_and_before_flux(tmp_path):
    """run 33133317589: the chain was removed and coredns rolled out, but the ESO webhook and kyverno
    admission pods rescheduled during the outage stayed in dead sandboxes, so secret-store and its
    dependents failed dry-run with EOF. The playbook restarts them onto fresh sandboxes before Flux."""
    p, calls = _run("cilium-unchain", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    joined = "\n".join(calls)
    order = [
        joined.index("rollout status deploy/coredns"),
        joined.index("rollout restart deploy -n external-secrets"),
        joined.index("rollout restart deploy -n kyverno"),
        joined.index("rollout status deploy -n external-secrets"),
        joined.index("reconcile source git flux-system"),
    ]
    assert order == sorted(order), calls


def test_diagnose_prints_why_a_deployment_stalled_not_only_that_it_did(tmp_path):
    # run 33136391785: three lines said "Deployment/observability/langfuse-web status: Failed", none said why
    p, calls = _run("diagnose", tmp_path)
    assert p.returncode == 0
    assert any("get deploy -A" in c and "Progressing" in c and ".reason" in c for c in calls)
    assert any("get pods -A --field-selector=status.phase!=Running" in c for c in calls)


def test_helm_retry_resets_only_failed_releases_then_refreshes_observability(tmp_path):
    bin_dir, log = _fake_path(tmp_path)
    k = bin_dir / "kubectl"
    k.write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n"
        "case \"$*\" in *helmreleases*jsonpath*) printf 'False observability langfuse\\nTrue observability signoz\\nFalse robusta robusta\\n';; *) echo ok;; esac\n"
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "helm-retry"], capture_output=True, text=True, env=env)
    calls = log.read_text().splitlines()
    assert p.returncode == 0, p.stdout + p.stderr
    resets = [c for c in calls if c.startswith("flux reconcile helmrelease")]
    assert resets == [
        "flux reconcile helmrelease langfuse -n observability --reset --timeout=15m",
        "flux reconcile helmrelease robusta -n robusta --reset --timeout=15m",
    ], "a Ready release is left alone; every Failed one is reset"
    assert calls.index(resets[-1]) < calls.index("flux reconcile kustomization observability -n flux-system --timeout=5m")
    assert [c for c in calls if MUTATING.match(c) and "reconcile" not in c] == [], "helm-retry only reconciles"


def test_diagnose_describes_and_logs_every_unready_and_failed_pod_and_reads_the_newest_warnings(tmp_path):
    # run 33138549588: langfuse-web's new ReplicaSet "timed out progressing", pod Running, reason never printed;
    # 21 descheduler pods in Error; the warnings row showed the oldest 60 events (sorted ascending, head)
    bin_dir, log = _fake_path(tmp_path)
    k = bin_dir / "kubectl"
    k.write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n"
        "case \"$*\" in\n"
        "  *'phase==\"Running\"'*) printf 'False observability langfuse-web-1\\nTrue observability langfuse-worker-1\\n';;\n"
        "  *status.phase=Failed*) printf 'healing descheduler-old\\nhealing descheduler-new\\n';;\n"
        "  *) echo ok;;\nesac\n"
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "diagnose"], capture_output=True, text=True, env=env)
    calls = log.read_text().splitlines()
    assert p.returncode == 0, p.stdout + p.stderr
    assert any("describe pod langfuse-web-1 -n observability" in c for c in calls)
    assert any(c.endswith("logs langfuse-web-1 -n observability --all-containers --tail=30 --prefix") for c in calls)
    assert not any("langfuse-worker-1" in c for c in calls), "a Ready pod is not described"
    assert any("describe pod descheduler-new -n healing" in c for c in calls)
    assert not any("descheduler-old" in c for c in calls), "only the newest Failed pod per namespace"
    assert "--sort-by=.lastTimestamp | tail -60" in PLAYBOOK.read_text()
    assert [c for c in calls if MUTATING.match(c)] == []


def test_diagnose_reads_node_pressure_and_empty_endpoints_before_any_pod(tmp_path):
    # run 33139372173: six pods red on one node, each "not answering on its port"; the node's
    # conditions, usage and allocation, and Services with no ready address, were never printed
    p, calls = _run("diagnose", tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    top = next(i for i, c in enumerate(calls) if c.endswith("top nodes"))
    first_pod = next((i for i, c in enumerate(calls) if "describe pod" in c), len(calls))
    assert top < first_pod, "the node is read before any pod is blamed"
    assert any("describe nodes" in c for c in calls)
    assert any("get nodes -o jsonpath=" in c and "conditions" in c for c in calls)
    assert any("get endpoints -A" in c for c in calls)
    assert "--- node-pressure" in p.stdout and "--- endpoints-empty" in p.stdout
    assert [c for c in calls if MUTATING.match(c)] == []


def test_dns_per_node_pins_an_in_cluster_and_an_external_lookup_to_every_node(tmp_path):
    # run 33140351385: clickhouse "ZooKeeper host ... DNS error", langfuse-web "Can't reach
    # langfuse-postgresql:5432", every Service with endpoints, no node pressure -> resolve per node
    bin_dir, log = _fake_path(tmp_path)
    k = bin_dir / "kubectl"
    k.write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n"
        "case \"$*\" in\n"
        "  *'get nodes -o jsonpath'*) printf '10.0.1.1 10.0.2.2';;\n"
        "  *'apply -f -'*) cat >> \"" + str(log) + ".yaml\"; echo ok;;\n"
        "  *) cat >/dev/null 2>&1; echo ok;;\nesac\n"
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "dns-per-node"], capture_output=True, text=True, env=env)
    calls = log.read_text().splitlines()
    assert p.returncode == 0, p.stdout + p.stderr
    for i in (1, 2):
        assert any(f"wait pod/dns-probe-svc-{i} -n kube-system" in c for c in calls)
        assert any(f"wait pod/dns-probe-ext-{i} -n kube-system" in c for c in calls)
        assert any(f"delete pod/dns-probe-ext-{i} -n kube-system --ignore-not-found --wait=false" in c for c in calls)
    manifests = (log.parent / (log.name + ".yaml")).read_text()
    assert manifests.count("nodeName: 10.0.1.1") == 2 and manifests.count("nodeName: 10.0.2.2") == 2
    assert "kubernetes.default.svc.cluster.local" in manifests and '"github.com"' in manifests
    assert "--- node 10.0.1.1" in p.stdout and "--- node 10.0.2.2" in p.stdout
    assert any("-l k8s-app=kube-dns" in c for c in calls), "coredns itself is read last"


def test_dns_per_namespace_resolves_every_headless_service_from_inside_the_failing_namespace(tmp_path):
    # run 33141542523: DNS answers on every node, yet clickhouse cannot resolve its ZooKeeper
    # headless name and coredns says NXDOMAIN for its per-replica Service -> ask from inside the ns
    bin_dir, log = _fake_path(tmp_path)
    k = bin_dir / "kubectl"
    k.write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n"
        "case \"$*\" in\n"
        "  *'get helmreleases -A -o jsonpath'*) printf 'False observability\\nTrue keda\\nFalse observability\\nFalse robusta\\n';;\n"
        "  *'get svc -n observability -o jsonpath'*) printf 'signoz-zookeeper-headless signoz-clickhouse-headless ';;\n"
        "  *'get svc -n robusta -o jsonpath'*) printf '';;\n"
        "  *'apply -f -'*) cat >> \"" + str(log) + ".yaml\"; echo ok;;\n"
        "  *) cat >/dev/null 2>&1; echo ok;;\nesac\n"
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "dns-per-namespace"], capture_output=True, text=True, env=env)
    calls = log.read_text().splitlines()
    assert p.returncode == 0, p.stdout + p.stderr
    assert "--- namespace observability" in p.stdout and "--- namespace robusta" in p.stdout
    assert "--- namespace keda" not in p.stdout, "a Ready namespace is not probed"
    assert any("get svc,endpointslices -n observability" in c for c in calls)
    assert [c for c in calls if MUTATING.match(c) and "dns-probe-ns-" not in c] == [], "only the probe pods are written"
    manifests = (log.parent / (log.name + ".yaml")).read_text()
    assert manifests.count("namespace: observability") == 2, "one probe per headless Service, inside the namespace"
    assert '"signoz-zookeeper-headless.observability.svc.cluster.local"' in manifests
    assert '"signoz-clickhouse-headless.observability.svc.cluster.local"' in manifests
    assert any("wait pod/dns-probe-ns-1 -n observability" in c for c in calls)
    assert any("delete pod/dns-probe-ns-2 -n observability --ignore-not-found --wait=false" in c for c in calls)
    assert any("-l k8s-app=kube-dns" in c for c in calls), "coredns is read per namespace"


def test_tcp_per_node_connects_from_inside_the_failing_namespace_pinned_to_every_node(tmp_path):
    # run 33143467334: langfuse-web on 10.0.148.221 got P1001 to langfuse-postgresql:5432 while the
    # postgres pod was Running with endpoints and every name resolved (33142680663); dns-per-node
    # only proved UDP to a ClusterIP a node can answer locally -> prove TCP through a ClusterIP
    # from every node, inside the namespace whose NetworkPolicies apply
    bin_dir, log = _fake_path(tmp_path)
    k = bin_dir / "kubectl"
    k.write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n"
        "case \"$*\" in\n"
        "  *'get helmreleases -A -o jsonpath'*) printf 'False observability\\nTrue keda\\n';;\n"
        "  *'get svc -n observability -o jsonpath'*) printf 'langfuse-postgresql.observability.svc.cluster.local:5432 langfuse-redis.observability.svc.cluster.local:6379 ';;\n"
        "  *'get nodes -o jsonpath'*) printf '10.0.148.221 10.0.159.197';;\n"
        "  *'apply -f -'*) cat >> \"" + str(log) + ".yaml\"; echo ok;;\n"
        "  *) cat >/dev/null 2>&1; echo ok;;\nesac\n"
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "tcp-per-node"], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    pods = (log.parent / (log.name + ".yaml")).read_text()
    assert pods.count("kind: Pod") == 2, pods
    assert "nodeName: 10.0.148.221" in pods and "nodeName: 10.0.159.197" in pods
    assert "namespace: observability" in pods and "namespace: kube-system" not in pods
    assert "nc -z -w3" in pods
    assert "langfuse-postgresql.observability.svc.cluster.local:5432" in pods
    assert "langfuse-redis.observability.svc.cluster.local:6379" in pods
    assert "--- from node 10.0.148.221 into observability" in p.stdout
    assert "get pods -n observability -o wide" in log.read_text()
    assert "networkpolicies" in log.read_text()


def test_diagnose_prints_the_clickhouse_limit_at_every_link_and_the_cronjobs(tmp_path):
    # run 33144117286: signoz.v40 carried the 4Gi limit and the clickhouse pod kept "maximum: 1.80
    # GiB"; the link that did not roll has to be named from the CHI, the StatefulSet and the pod.
    # Run 33145711762: `-l app=clickhouse-operator` matched nothing; the operator is found by name.
    bin_dir, log = _fake_path(tmp_path)
    (bin_dir / "kubectl").write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n"
        "case \"$*\" in\n"
        "  *'get pods -A --no-headers'*) printf 'kube-system coredns-1 1/1 Running 0 1h\\nobservability signoz-clickhouse-operator-9946d55c-n8z7q 2/2 Running 1 2h\\n';;\n"
        "  *) cat >/dev/null 2>&1; echo ok;;\nesac\n")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "diagnose"], capture_output=True, text=True, env=env)
    calls = log.read_text().splitlines()
    assert p.returncode == 0, p.stdout + p.stderr
    assert "--- clickhouse-installation" in p.stdout
    assert "--- clickhouse-operator-log" in p.stdout
    assert "--- cronjobs" in p.stdout
    joined = "\n".join(calls)
    assert "get chi -A -o jsonpath" in joined
    assert "get sts -A -l clickhouse.altinity.com/chi" in joined
    assert "get pods -A -l clickhouse.altinity.com/chi" in joined
    assert "get pods -A --no-headers" in joined
    assert "logs -n observability signoz-clickhouse-operator-9946d55c-n8z7q --all-containers --tail=40" in joined
    assert "get cronjobs,jobs -A" in joined


def test_no_logs_call_carries_all_namespaces():
    # idp#538 review: `kubectl logs -A` is not a flag (v1.36.4: unknown shorthand flag 'A'); the
    # row printed the error and PASSed
    import re
    src = PLAYBOOK.read_text()
    offenders = [a for a in re.findall(r"\$K logs ([^|;\n]*)", src) if re.search(r"(^|\s)-A(\s|$)", a)]
    assert offenders == [], offenders


def test_probe_log_prints_every_target_line_not_only_the_last(tmp_path):
    # run 33144789785: the probe measured langfuse-postgresql:5432 and langfuse-redis:6379 but the
    # log row went through step(), which keeps the last line -> only signoz-zookeeper-metrics
    # survived and the answer the run existed for was thrown away. The log is the receipt: every
    # line of it is printed.
    bin_dir, log = _fake_path(tmp_path)
    k = bin_dir / "kubectl"
    k.write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n"
        "case \"$*\" in\n"
        "  *'get helmreleases -A -o jsonpath'*) printf 'False observability\\n';;\n"
        "  *'get svc -n observability -o jsonpath'*) printf 'a.observability.svc.cluster.local:5432 b.observability.svc.cluster.local:6379 ';;\n"
        "  *'get nodes -o jsonpath'*) printf '10.0.148.221';;\n"
        "  *'logs pod/tcp-probe-1'*) printf 'FAIL a.observability.svc.cluster.local:5432\\nok b.observability.svc.cluster.local:6379\\n';;\n"
        "  *) cat >/dev/null 2>&1; echo ok;;\nesac\n"
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "tcp-per-node"], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "FAIL a.observability.svc.cluster.local:5432" in p.stdout, p.stdout
    assert "ok b.observability.svc.cluster.local:6379" in p.stdout, p.stdout


def _node_drain_kubectl(bin_dir: Path, log: Path, pods: str, nodes: str = "10.0.148.221 True \\n10.0.159.197 True \\n") -> None:
    (bin_dir / "kubectl").write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n"
        "case \"$*\" in\n"
        "  *'get pods -A -o jsonpath'*) printf '" + pods + "';;\n"
        "  *'get nodes -o jsonpath'*) printf '" + nodes + "';;\n"
        "  *) cat >/dev/null 2>&1; echo ok;;\nesac\n"
    )


def test_node_drain_retires_the_node_carrying_the_crashing_pods_and_only_that_node(tmp_path):
    # crew#539 5448912676: clickhouse, langfuse-web and langfuse-worker all crashed on 10.0.148.221,
    # each timing out to a Service whose backend was on that same node; the replica on 10.0.159.197
    # ran. The node is picked from the pods, never typed; it is cordoned before it is drained; the
    # drain keeps DaemonSets and lets emptyDir go so the autoscaler can remove the empty node.
    bin_dir, log = _fake_path(tmp_path)
    _node_drain_kubectl(bin_dir, log,
        "10.0.148.221 observability/langfuse-web-a Running false \\n"
        "10.0.148.221 observability/langfuse-worker-a Running false \\n"
        "10.0.148.221 observability/chi-0 Running false \\n"
        "10.0.159.197 observability/langfuse-web-b Running true \\n"
        "10.0.159.197 observability/migrator Succeeded false \\n"
        "10.0.159.197 healing/descheduler-1 Failed false \\n"
        "10.0.159.197 healing/descheduler-2 Failed false \\n"
        "10.0.159.197 healing/descheduler-3 Failed false \\n"
        "10.0.159.197 healing/descheduler-4 Failed false \\n"
        "10.0.159.197 healing/descheduler-5 Failed false \\n")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "node-drain"], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    calls = log.read_text().splitlines()
    assert "--- target 10.0.148.221" in p.stdout, p.stdout
    cordon = [i for i, c in enumerate(calls) if c.endswith("cordon 10.0.148.221")]
    drain = [i for i, c in enumerate(calls) if "drain 10.0.148.221 --ignore-daemonsets --delete-emptydir-data --timeout=600s" in c]
    assert cordon and drain and cordon[0] < drain[0], calls
    assert not any("10.0.159.197" in c for c in calls if "cordon" in c or "drain" in c), calls
    assert "observability/langfuse-web-a" in p.stdout and "observability/migrator" not in p.stdout
    assert "healing/descheduler-1" not in p.stdout   # five Failed job pods on .197 do not out-vote three crashers on .221


def test_node_drain_reads_every_container_not_only_the_first(tmp_path):
    # idp#540 review: a 2/3 pod whose third container crashes is sick; $4 alone missed it
    bin_dir, log = _fake_path(tmp_path)
    _node_drain_kubectl(bin_dir, log,
        "10.0.159.197 observability/operator Running true true false \\n"
        "10.0.148.221 a/ok Running true true true \\n")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "node-drain"], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "--- target 10.0.159.197" in p.stdout, p.stdout


def test_node_drain_touches_nothing_when_every_pod_runs(tmp_path):
    bin_dir, log = _fake_path(tmp_path)
    _node_drain_kubectl(bin_dir, log, "10.0.148.221 a/b Running true \\n10.0.159.197 a/c Succeeded false \\n")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "node-drain"], capture_output=True, text=True, env=env)
    assert p.returncode == 0 and "nothing to drain" in p.stdout, p.stdout + p.stderr
    assert not any(("cordon" in c or "drain" in c) for c in log.read_text().splitlines())


def test_node_uncordon_is_the_undo(tmp_path):
    bin_dir, log = _fake_path(tmp_path)
    (bin_dir / "kubectl").write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n"
        "case \"$*\" in\n  *'get nodes -o jsonpath'*) printf '10.0.148.221 ';;\n  *) echo ok;;\nesac\n")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "node-uncordon"], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "kubectl --request-timeout=60s uncordon 10.0.148.221" in log.read_text()


def test_node_drain_never_picks_a_node_that_is_not_ready(tmp_path):
    # a NotReady node carries every pod the scheduler gave up on; it is the cloud layer's to replace
    bin_dir, log = _fake_path(tmp_path)
    _node_drain_kubectl(bin_dir, log,
        "10.0.1.1 a/x Running false \\n10.0.1.1 a/y Running false \\n10.0.1.1 a/z Pending \\n"
        "10.0.148.221 observability/langfuse-web-a Running false \\n10.0.159.197 a/ok Running true \\n",
        nodes="10.0.1.1 False \\n10.0.148.221 True \\n10.0.159.197 True \\n")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "node-drain"], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "--- target 10.0.148.221" in p.stdout, p.stdout
    assert not any("10.0.1.1" in c for c in log.read_text().splitlines() if "cordon" in c or "drain" in c)


def test_node_drain_refuses_the_only_ready_node(tmp_path):
    bin_dir, log = _fake_path(tmp_path)
    _node_drain_kubectl(bin_dir, log, "10.0.148.221 a/x Running false \\n",
                        nodes="10.0.148.221 True \\n10.0.159.197 False \\n")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "node-drain"], capture_output=True, text=True, env=env)
    assert p.returncode == 1 and "only Ready node; refusing" in p.stdout, p.stdout + p.stderr
    assert not any(("cordon" in c or "drain" in c) for c in log.read_text().splitlines())


def test_node_uncordon_uncordons_every_cordoned_node_and_nothing_else(tmp_path):
    bin_dir, log = _fake_path(tmp_path)
    (bin_dir / "kubectl").write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n"
        "case \"$*\" in\n  *'get nodes -o jsonpath'*) printf '10.0.148.221 10.0.1.1 ';;\n  *) echo ok;;\nesac\n")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "node-uncordon"], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    calls = [c for c in log.read_text().splitlines() if "uncordon" in c]
    assert sorted(calls) == sorted(["kubectl --request-timeout=60s uncordon 10.0.148.221", "kubectl --request-timeout=60s uncordon 10.0.1.1"]), calls
    assert not any("drain" in c or " cordon " in c for c in log.read_text().splitlines())


def _chi_kubectl(bin_dir: Path, log: Path, values: str, chis: str = "observability/signoz-clickhouse ") -> None:
    (bin_dir / "kubectl").write_text(
        "#!/bin/sh\nprintf '%s %s\\n' kubectl \"$*\" >> \"" + str(log) + "\"\n"
        "case \"$*\" in\n"
        "  *'get configmap signoz-values -n observability'*) printf '" + values + "';;\n"
        "  *'get chi -A -o jsonpath={range .items[*]}{.metadata.namespace}/{.metadata.name}{\" \"}{end}'*) printf '" + chis + "';;\n"
        "  *) cat >/dev/null 2>&1; echo ok;;\nesac\n"
    )


def test_chi_resize_patches_the_installation_to_what_the_values_configmap_declares(tmp_path):
    # run 33147086133: signoz.v41 upgrade to 4Gi failed on its pre-upgrade migrator Job, whose init
    # containers wait for a ClickHouse that exits 137 at 2Gi. The value is read from the ConfigMap
    # the HelmRelease already consumes, the CHI is patched to it, and the StatefulSet roll is waited on.
    bin_dir, log = _fake_path(tmp_path)
    _chi_kubectl(bin_dir, log, "clickhouse:\\n  resources:\\n    requests: {cpu: 1000m, memory: 4Gi}\\n    limits: {cpu: 1000m, memory: 4Gi}\\n")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "chi-resize"], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    calls = log.read_text().splitlines()
    patch = [c for c in calls if "patch chi signoz-clickhouse -n observability --type=json" in c]
    assert len(patch) == 1, calls
    assert '"memory":"4Gi"' in patch[0] and "/spec/templates/podTemplates/0/spec/containers/0/resources" in patch[0], patch
    assert '"requests":{"cpu":"1000m","memory":"4Gi"}' in patch[0], patch   # requests == limits stays (Guaranteed QoS)
    assert any("rollout status sts -n observability -l clickhouse.altinity.com/chi=signoz-clickhouse --timeout=600s" in c for c in calls), calls
    assert calls.index(patch[0]) < [i for i, c in enumerate(calls) if "rollout status" in c][0]
    assert "--- want " in p.stdout and "--- chi-before" in p.stdout and "--- chi-after" in p.stdout, p.stdout


def test_chi_resize_refuses_when_the_values_declare_no_resources(tmp_path):
    # a typed fallback would be the hardcode LAW 46 forbids: no declared value, no patch
    bin_dir, log = _fake_path(tmp_path)
    _chi_kubectl(bin_dir, log, "clickhouse:\\n  persistence: {size: 20Gi}\\n")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    p = subprocess.run([str(PLAYBOOK), "chi-resize"], capture_output=True, text=True, env=env)
    assert p.returncode != 0 and "no clickhouse.resources" in p.stdout, p.stdout + p.stderr
    assert not any("patch" in c for c in log.read_text().splitlines())


def test_chi_resize_is_listed_and_wired():
    assert "chi-resize" in subprocess.run([str(PLAYBOOK), "--list"], capture_output=True, text=True).stdout.split()
    wf = (PLAYBOOK.parent.parent / ".github" / "workflows" / "oke-check.yml").read_text()
    assert "chi-resize" in wf
