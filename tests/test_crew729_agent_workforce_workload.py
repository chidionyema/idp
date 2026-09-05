"""crew#729 step 3: the agent workforce is a cluster workload with no cluster hand.

Rung 2 over the manifests, the Flux row, the catalogue and the drill; rung 4 for the drill
reader, driven with a fake `gh` and a local Langfuse stand-in (no network socket leaves the
machine). The rules:

  1. the crew's ServiceAccount is named by no Role, RoleBinding or ClusterRoleBinding anywhere
     under platform/, and its token is never mounted -- no agent touches the cluster again
     (founder 2026-09-01);
  2. every secret reaches the pod as a file (Kyverno refuses secret env vars); the crew's
     NAME_FILE variables all point into the one read-only projected directory;
  3. the memory volume is a PersistentVolumeClaim, never an emptyDir (idp#365's lesson);
  4. the laws init container produces exactly the four names the crew's knowledge base expects,
     from the repositories that version them, with the owner substituted from estate-config;
  5. the Flux row substitutes from estate-config and the github-app Secret, waits on the rows it
     reads from, and carries no health check (a CronJob has no readiness to check);
  6. the catalogue Component, the drill row and the runbook exist and agree on the names;
  7. the drill reader grades the property that breaks: a queued ticket left unplanned is red, a
     plan with no trace is red, a planned ticket with a trace is green, and a surface it cannot
     read is BLIND, never green.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "platform" / "agent-workforce"
LAW_FILES = {"AGENTS.md", "AGENTS-FULL.md", "STANDARDS.md", "definition-of-done.md"}


def _docs(name: str) -> list[dict]:
    return [d for d in yaml.safe_load_all((DIR / name).read_text()) if d]


def _cronjob() -> dict:
    (cj,) = [d for d in _docs("cronjob.yaml") if d["kind"] == "CronJob"]
    return cj


def _pod() -> dict:
    return _cronjob()["spec"]["jobTemplate"]["spec"]["template"]["spec"]


def _crew() -> dict:
    (c,) = [c for c in _pod()["containers"] if c["name"] == "crew"]
    return c


def _every_platform_doc():
    for path in sorted((ROOT / "platform").rglob("*.yaml")):
        try:
            for d in yaml.safe_load_all(path.read_text()):
                if isinstance(d, dict) and "kind" in d:
                    yield path, d
        except yaml.YAMLError:
            continue


def test_the_crew_has_no_cluster_hand():
    pod = _pod()
    assert pod["serviceAccountName"] == "agent-workforce"
    assert pod["automountServiceAccountToken"] is False
    (sa,) = [d for d in _docs("cronjob.yaml") if d["kind"] == "ServiceAccount"]
    assert sa["automountServiceAccountToken"] is False
    for path, d in _every_platform_doc():
        if d["kind"] in {"RoleBinding", "ClusterRoleBinding"}:
            for s in d.get("subjects") or []:
                assert not (
                    s.get("kind") == "ServiceAccount"
                    and s.get("name") == "agent-workforce"
                    and s.get("namespace", "agent-workforce") == "agent-workforce"
                ), (
                    f"{path} binds the crew's ServiceAccount: the crew has a cluster hand"
                )
        if d["kind"] in {"Role", "ClusterRole"}:
            assert d["metadata"]["name"] != "agent-workforce", (
                f"{path}: a Role named for the crew"
            )


def test_every_secret_is_a_file_in_one_readonly_directory():
    crew = _crew()
    assert "envFrom" not in crew
    env = {e["name"]: e.get("value") for e in crew["env"]}
    assert not [e for e in crew["env"] if "valueFrom" in e]
    files = {k: v for k, v in env.items() if k.endswith("_FILE")}
    assert set(files) == {
        "AGENT_WORKFORCE_GITHUB_TOKEN_FILE",
        "LITELLM_API_KEY_FILE",
        "LANGFUSE_PUBLIC_KEY_FILE",
        "LANGFUSE_SECRET_KEY_FILE",
    }
    mounts = {m["mountPath"]: m for m in crew["volumeMounts"]}
    (secret_dir,) = {os.path.dirname(p) for p in files.values()}
    assert mounts[secret_dir]["readOnly"] is True
    vols = {v["name"]: v for v in _pod()["volumes"]}
    sources = vols[mounts[secret_dir]["name"]]["projected"]["sources"]
    projected = {s["secret"]["name"] for s in sources}
    externals = {
        d["spec"]["target"]["name"]
        for d in _docs("external-secret.yaml")
        if d["kind"] == "ExternalSecret"
    }
    assert projected <= externals, projected - externals
    for key in ("KEY", "TOKEN", "PASSWORD", "SECRET"):
        assert not [n for n in env if n.endswith(key)], (
            "a secret named as a plain env value"
        )


def test_the_github_token_is_minted_in_cluster_on_the_agent_workforce_lane():
    docs = _docs("external-secret.yaml")
    (gen,) = [d for d in docs if d["kind"] == "GithubAccessToken"]
    assert gen["spec"]["appID"] == "${githubAppIDQuoted}"
    assert gen["spec"]["installID"] == "${githubAppInstallationIDQuoted}"
    perms = gen["spec"]["permissions"]
    assert perms == {
        "metadata": "read",
        "contents": "write",
        "pull_requests": "write",
        "issues": "write",
        "actions": "read",
        "checks": "read",
    }
    assert "workflows" not in perms and "administration" not in perms
    (es,) = [
        d
        for d in docs
        if d["kind"] == "ExternalSecret"
        and d["metadata"]["name"] == "agent-workforce-github"
    ]
    (src,) = es["spec"]["dataFrom"]
    assert src["sourceRef"]["generatorRef"]["name"] == gen["metadata"]["name"]
    assert es["spec"]["refreshInterval"] == "10m"


def test_memory_outlives_the_pod_and_laws_are_fetched_from_git():
    crew = _crew()
    env = {e["name"]: e.get("value") for e in crew["env"]}
    mounts = {m["mountPath"]: m["name"] for m in crew["volumeMounts"]}
    vols = {v["name"]: v for v in _pod()["volumes"]}
    (pvc,) = [d for d in _docs("cronjob.yaml") if d["kind"] == "PersistentVolumeClaim"]
    assert (
        vols[mounts[env["AGENT_WORKFORCE_STORAGE_DIR"]]]["persistentVolumeClaim"][
            "claimName"
        ]
        == pvc["metadata"]["name"]
    )
    (laws,) = _pod()["initContainers"]
    script = laws["args"][0]
    for name in LAW_FILES:
        assert f'"{name}"' in script, f"the laws step does not produce {name}"
    assert "claude-guards" in script and "docs/STANDARDS.md" in script
    assert "docs/reference/policy/definition-of-done.md" in script
    assert (ROOT / "docs/reference/policy/definition-of-done.md").is_file()
    laws_env = {e["name"]: e.get("value") for e in laws["env"]}
    assert laws_env["LAWS_OWNER"] == "${ESTATE_GITHUB_OWNER}"
    assert env["AGENT_WORKFORCE_REPO_OWNER"] == "${ESTATE_GITHUB_OWNER}"
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "${OTLP_ENDPOINT}"
    cfg = yaml.safe_load((ROOT / "clusters/oke/estate-config.yaml").read_text())["data"]
    assert cfg["ESTATE_GITHUB_OWNER"] and "/" not in cfg["ESTATE_GITHUB_OWNER"]
    assert env["AGENT_WORKFORCE_MODEL"] != env["AGENT_WORKFORCE_VERIFIER_MODEL"], (
        "the verifier grades with the builder's brain"
    )
    assert env["CREWAI_DISABLE_TELEMETRY"] == "true"
    assert not crew.get("args"), (
        "an argument pins one ticket; the workload takes the queue"
    )


def test_the_cronjob_is_one_at_a_time_batch_and_restricted():
    cj = _cronjob()
    assert cj["spec"]["schedule"] == "*/15 * * * *"
    assert cj["spec"]["concurrencyPolicy"] == "Forbid"
    assert cj["metadata"]["labels"]["backstage.io/kubernetes-id"] == "agent-workforce"
    pod = _pod()
    assert pod["priorityClassName"] == "platform-batch"
    for c in pod["containers"] + pod["initContainers"]:
        sc = c["securityContext"]
        assert sc["runAsUser"] == 10001 and sc["readOnlyRootFilesystem"] is True
        assert sc["capabilities"] == {"drop": ["ALL"]}
    ns = _docs("namespace.yaml")[0]
    assert (
        ns["metadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted"
    )
    assert (
        ns["metadata"]["annotations"]["kustomize.toolkit.fluxcd.io/prune"] == "disabled"
    )


def test_the_flux_row_waits_on_what_it_reads_and_checks_no_health():
    rows = [
        d
        for d in yaml.safe_load_all((ROOT / "clusters/oke/platform.yaml").read_text())
        if d
    ]
    (row,) = [r for r in rows if r["metadata"]["name"] == "agent-workforce"]
    spec = row["spec"]
    assert spec["path"] == "./platform/agent-workforce"
    subs = {(s["kind"], s["name"]) for s in spec["postBuild"]["substituteFrom"]}
    assert subs == {("ConfigMap", "estate-config"), ("Secret", "github-app")}
    deps = {d["name"] for d in spec["dependsOn"]}
    assert {"scheduling", "secret-store", "alerts-github", "llm"} <= deps
    assert spec["wait"] is True
    assert "healthChecks" not in spec, (
        "a CronJob has no readiness; the drill is the proof"
    )


def test_catalogue_drill_and_runbook_agree():
    cat = (ROOT / "backstage/platform/catalog-info.yaml").read_text()
    assert "name: layer-agent-workforce" in cat
    assert "kustomize.toolkit.fluxcd.io/name=agent-workforce" in cat
    drills = yaml.safe_load((ROOT / "drills/catalogue.yaml").read_text())["drills"]
    (drill,) = [d for d in drills if d["name"] == "agent-workforce"]
    assert drill["workflow"] == "oke-check.yml" and drill["job"] == "agent-workforce"
    assert not drill.get("pending")
    wf = yaml.safe_load((ROOT / ".github/workflows/oke-check.yml").read_text())
    assert "agent-workforce" in wf["jobs"]
    assert drill["schedule"] == wf[True]["schedule"][0]["cron"]
    runbook = (ROOT / "docs/runbooks/agent-workforce.md").read_text()
    for word in (
        "Suspend",
        "agents_enabled",
        "suspend: true",
        "lane:platform",
        "agent-workforce.run",
    ):
        assert word in runbook, f"the runbook does not say {word!r}"


# ---- rung 4: the drill reader, driven with a fake gh and a Langfuse stand-in --------------------

NOW = datetime.now(timezone.utc)


def _stamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class _Langfuse(BaseHTTPRequestHandler):
    traces = 1

    def do_GET(self):  # noqa: N802 - http.server's name
        body = json.dumps({"data": [{"id": "t"}] * self.traces, "meta": {}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def _langfuse(traces: int) -> str:
    _Langfuse.traces = traces
    srv = HTTPServer(("127.0.0.1", 0), _Langfuse)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_port}"


def _fake_gh(tmp: Path, issues: list[dict], comments: dict[int, list[dict]]) -> Path:
    bindir = tmp / "bin"
    bindir.mkdir()
    (tmp / "issues.json").write_text(json.dumps(issues))
    (tmp / "comments.json").write_text(
        json.dumps({str(k): v for k, v in comments.items()})
    )
    gh = bindir / "gh"
    gh.write_text(
        "#!/usr/bin/env python3\n"
        "import json, re, sys\n"
        "from datetime import datetime, timezone\n"
        "from email.utils import format_datetime\n"
        f"root = {str(tmp)!r}\n"
        "path = sys.argv[-1]\n"
        "m = re.search(r'/issues/(\\d+)/comments', path)\n"
        "if path == 'rate_limit':\n"
        "    # the drill reads GitHub's clock off this header (crew#583); the stand-in serves one\n"
        "    print('Date: ' + format_datetime(datetime.now(timezone.utc), usegmt=True))\n"
        "    print()\n"
        "    print('{}')\n"
        "elif m:\n"
        "    print(json.dumps(json.load(open(root + '/comments.json')).get(m.group(1), [])))\n"
        "else:\n"
        "    print(json.dumps(json.load(open(root + '/issues.json'))))\n"
    )
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    return bindir


def _run(tmp: Path, issues, comments, traces=1, keys=True):
    bindir = _fake_gh(tmp, issues, comments)
    env = dict(
        os.environ, PATH=f"{bindir}:{os.environ['PATH']}", AGENT_WORKFORCE_BOARD="owner/crew"
    )
    env["LANGFUSE_HOST"] = _langfuse(traces)
    if keys:
        env["LANGFUSE_PUBLIC_KEY"], env["LANGFUSE_SECRET_KEY"] = "pk", "sk"
    else:
        env.pop("LANGFUSE_PUBLIC_KEY", None)
        env.pop("LANGFUSE_SECRET_KEY", None)
    r = subprocess.run(
        [str(ROOT / "bin/idp-agent-workforce-drill")],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return r.returncode, r.stdout.strip()


def _issue(n: int, age: timedelta, state="open") -> dict:
    return {"number": n, "state": state, "created_at": _stamp(NOW - age)}


def _plan(age: timedelta) -> dict:
    return {"body": "plan\n\nOptimised: 12 -> 4 steps", "created_at": _stamp(NOW - age)}


def test_a_queued_ticket_left_unplanned_is_red(tmp_path):
    rc, out = _run(tmp_path, [_issue(41, timedelta(hours=3))], {})
    assert rc == 1 and out.startswith("FAIL") and "#41" in out, out


def test_a_fresh_ticket_inside_the_grace_period_is_not_yet_red(tmp_path):
    rc, out = _run(tmp_path, [_issue(41, timedelta(minutes=20))], {})
    assert rc == 0 and out.startswith("ok") and "queue empty" in out, out


def test_a_planned_ticket_with_a_trace_is_green(tmp_path):
    rc, out = _run(
        tmp_path,
        [_issue(41, timedelta(hours=3))],
        {41: [_plan(timedelta(hours=2))]},
        traces=1,
    )
    assert rc == 0 and out.startswith("ok") and "#41" in out, out


def test_a_plan_with_no_trace_behind_it_is_red(tmp_path):
    rc, out = _run(
        tmp_path,
        [_issue(41, timedelta(hours=3))],
        {41: [_plan(timedelta(hours=2))]},
        traces=0,
    )
    assert rc == 1 and "no trace" in out, out


def test_a_plan_the_drill_cannot_confirm_is_blind_never_green(tmp_path):
    rc, out = _run(
        tmp_path,
        [_issue(41, timedelta(hours=3))],
        {41: [_plan(timedelta(hours=2))]},
        keys=False,
    )
    assert rc == 2 and out.startswith("BLIND"), out


def test_a_board_that_cannot_be_read_is_blind(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text("#!/bin/sh\nexit 1\n")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    env = dict(
        os.environ, PATH=f"{bindir}:{os.environ['PATH']}", AGENT_WORKFORCE_BOARD="owner/crew"
    )
    r = subprocess.run(
        [str(ROOT / "bin/idp-agent-workforce-drill")],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert r.returncode == 2 and r.stdout.startswith("BLIND"), r.stdout
