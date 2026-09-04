"""crew#740: the founder asked at the start of the cloud migration for one inventory of everything
the estate runs that can never be out of sync, and on 2026-08-31 the sessions could not say
whether LiteLLM was in the estate. The blueprint (his doc 2026-08-31T11:55Z): read the control
planes, never git; four verdicts; a plane that cannot be read is UNKNOWN, never a green zero.

These pin the shape without a cloud: the grader on a cluster dump on disk, the four verdicts and
no fifth, the read-only workflow with its cron on the drill catalogue, and the query files the
SaaS planes run. Proved red first: a dump with an undeclared Deployment reads ORPHAN, a
Kustomization whose inventory names a missing object reads GHOST, a not-Ready one DRIFTED."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin/idp-inventory"
WORKFLOW = ROOT / ".github/workflows/estate-inventory.yml"
FIXTURE = ROOT / "tests/fixtures/inventory-kube-dump.json"
CLEAN = ROOT / "tests/fixtures/inventory-kube-dump-clean.json"


def grade(tmp_path: Path, fixture: Path = FIXTURE) -> dict:
    p = subprocess.run(
        [sys.executable, str(TOOL), "--fixture", str(fixture), "--out", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    return json.loads((tmp_path / "inventory.json").read_text())


def by_id(doc: dict) -> dict:
    return {r["id"]: r for r in doc["rows"]}


def test_the_four_verdicts_come_from_the_dump_and_nothing_is_a_fifth(tmp_path):
    doc = grade(tmp_path)
    rows = by_id(doc)
    assert rows["llm/Deployment/litellm"]["verdict"] == "MANAGED"
    assert (
        rows["llm/Deployment/litellm"]["declared_in"] == "Kustomization flux-system/llm"
    )
    assert rows["llm/Deployment/by-hand"]["verdict"] == "ORPHAN"
    assert rows["llm/Deployment/gone"]["verdict"] == "GHOST"
    assert rows["flux-system/Kustomization/tailscale"]["verdict"] == "DRIFTED"
    assert (
        rows["observability/Service/signoz"]["declared_in"]
        == "HelmRelease observability/signoz"
    )
    assert rows["tools/Deployment/plain-helm"]["verdict"] == "ORPHAN"
    assert rows["kube-system/ConfigMap/coredns"]["verdict"] == "MANAGED"
    assert {r["verdict"] for r in doc["rows"]} <= {
        "MANAGED",
        "DRIFTED",
        "ORPHAN",
        "GHOST",
    }


def test_cluster_noise_is_not_an_orphan(tmp_path):
    """A ReplicaSet, the root CA ConfigMap and a Helm release Secret are made by the cluster for
    something declared; listing them ORPHAN is the noise a reviewer stops reading."""
    ids = set(by_id(grade(tmp_path)))
    assert "llm/ReplicaSet/litellm-abc" not in ids
    assert "llm/ConfigMap/kube-root-ca.crt" not in ids
    assert "llm/Secret/sh.helm.release.v1.x" not in ids


def test_the_table_lists_every_red_row_and_the_counts(tmp_path):
    doc = grade(tmp_path)
    table = (tmp_path / "inventory.md").read_text()
    assert "| kubernetes | " in table
    for rid in (
        "llm/Deployment/by-hand",
        "llm/Deployment/gone",
        "flux-system/Kustomization/tailscale",
    ):
        assert rid in table
    c = doc["counts"]["kubernetes"]
    assert (c["MANAGED"], c["DRIFTED"], c["ORPHAN"], c["GHOST"]) == (4, 1, 2, 1)


def test_strict_is_the_red_gate_and_audit_mode_is_not(tmp_path):
    p = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--fixture",
            str(FIXTURE),
            "--out",
            str(tmp_path),
            "--strict",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert p.returncode == 1 and "not MANAGED" in p.stdout


def test_nothing_in_the_tool_lists_git_to_decide_what_exists():
    """The blueprint's first law: inventory from the control planes, never from git. The only git
    read is the Mac plane's 'is this plist tracked' on the declared side."""
    text = TOOL.read_text()
    before, _, after = text.partition("def tracked_files")
    body, _, rest = after.partition("\ndef ")
    # the token, not a phrase: a subprocess call spells it ["git", ..., "ls-files"]
    assert "ls-files" not in before and "ls-files" not in rest
    assert body.count("ls-files") == 1
    assert "glob(" not in text.replace('QUERIES.glob(f"{plane}-*.sql")', "")


def test_every_saas_plane_has_a_query_file_that_names_type_id_and_name():
    q = ROOT / "platform/inventory/queries"
    for plane in ("github", "cloudflare", "tailscale"):
        files = sorted(q.glob(f"{plane}-*.sql"))
        assert files, plane
        for f in files:
            sql = f.read_text().lower()
            assert (
                " as type" in sql
                and re.search(r"\bid\b", sql)
                and re.search(r"\bname\b", sql)
            ), f


def test_the_workflow_is_read_only_scheduled_and_on_the_drill_catalogue():
    wf = yaml.safe_load(WORKFLOW.read_text())
    on = wf.get(True) or wf.get("on")
    cron = on["schedule"][0]["cron"]
    rows = yaml.safe_load((ROOT / "drills/catalogue.yaml").read_text())["drills"]
    row = next(r for r in rows if r["workflow"] == "estate-inventory.yml")
    assert row["schedule"] == cron and row["owner"]
    assert wf["permissions"]["contents"] == "read"
    # the job that reads the planes holds no write scope; the one write is the Ops tile's data
    # (docs/inventory.{json,md} on state/live-diagram) in its own job, never on a pull request
    assert "permissions" not in wf["jobs"]["inventory"]
    pub = wf["jobs"]["publish-to-state-branch"]
    assert pub["permissions"] == {"contents": "write"} and pub["needs"] == "inventory"
    assert "pull_request" in pub["if"]
    text = WORKFLOW.read_text()
    assert "HEAD:refs/heads/state/live-diagram" in text
    assert "git add docs/inventory.json docs/inventory.md" in text
    assert "--strict" not in text, "audit mode until E1 flips the red gate on"
    assert "tofu apply" not in text and "kubectl apply" not in text
    # steampipe comes from a pinned vendor release, checksum verified; the setup action
    # pages GitHub's API with no token and 403s on hosted runners
    assert "uses: turbot/steampipe-action-setup" not in text
    assert re.search(r"releases/download/\$v/steampipe_linux_amd64\.tar\.gz", text)
    assert "sha256sum -c" in text and re.search(r"sum=[0-9a-f]{64}", text)


def load_tool():
    import importlib.util
    from importlib.machinery import SourceFileLoader

    spec = importlib.util.spec_from_loader(
        "idp_inventory", SourceFileLoader("idp_inventory", str(TOOL))
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_clean_dump_is_all_managed_and_strict_exits_zero(tmp_path):
    """The gate proved both ways: the same dump with every red object removed exits 0."""
    p = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--fixture",
            str(CLEAN),
            "--out",
            str(tmp_path),
            "--strict",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    counts = json.loads((tmp_path / "inventory.json").read_text())["counts"][
        "kubernetes"
    ]
    assert counts["MANAGED"] >= 1
    assert counts["DRIFTED"] == counts["ORPHAN"] == counts["GHOST"] == 0
    assert counts["read"] == "yes"


def test_a_plane_that_cannot_be_read_is_blind_and_never_a_green_zero(tmp_path):
    """No steampipe on PATH: the github plane is UNKNOWN, a BLIND line prints, exit 2."""
    env = {"PATH": str(tmp_path / "empty-bin"), "HOME": str(tmp_path)}
    (tmp_path / "empty-bin").mkdir()
    p = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--planes",
            "github",
            "--no-drift",
            "--out",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert p.returncode == 2, p.stdout + p.stderr
    assert "BLIND   inventory  github  UNKNOWN" in p.stdout
    assert "ok      inventory  github" not in p.stdout
    table = (tmp_path / "out/inventory.md").read_text()
    assert "| github | 0 | 0 | 0 | 0 | UNKNOWN |" in table


def test_a_half_read_plane_is_partial_never_ok():
    """One row read and one kind unread: PARTIAL, and strict refuses it."""
    mod = load_tool()
    rows = [
        mod.row(
            "kubernetes",
            "Deployment",
            "a/Deployment/x",
            "x",
            "Kustomization a/b",
            "MANAGED",
        )
    ]
    blind = ["kubernetes: get deployments.apps: timed out after 300s"]
    counts = mod.summarise(rows, ["kubernetes"], blind)
    assert counts["kubernetes"]["read"] == "PARTIAL"
    assert counts["kubernetes"]["UNKNOWN"] is False
    assert mod.summarise(rows, ["kubernetes"], [])["kubernetes"]["read"] == "yes"
    assert mod.summarise([], ["kubernetes"], blind)["kubernetes"]["read"] == "UNKNOWN"


def test_no_ghost_is_graded_for_a_kind_kubectl_could_not_list():
    """A failed `kubectl get deployments` removes Deployments from the live set; without the
    unreadable list every Kustomization entry of that kind would be a fabricated GHOST."""
    mod = load_tool()
    items = json.loads(FIXTURE.read_text())["items"]
    items = [i for i in items if i.get("kind") != "Deployment"]
    ghosts = [r for r in mod.classify_kube(items) if r["verdict"] == "GHOST"]
    assert {r["name"] for r in ghosts} == {"litellm", "gone"}  # the fabrication, proved
    ghosts = [
        r
        for r in mod.classify_kube(items, ["deployments.apps"])
        if r["verdict"] == "GHOST"
    ]
    assert ghosts == []


def test_secret_payloads_never_reach_the_raw_dump_or_the_registry():
    mod = load_tool()
    items = [
        {
            "kind": "Secret",
            "metadata": {"name": "s"},
            "data": {"k": "aGVsbG8="},
            "stringData": {"p": "x"},
        }
    ]
    out = mod.redact_secrets(items)[0]
    assert "aGVsbG8=" not in json.dumps(out) and "redacted" in out["data"]["k"]
    wf = WORKFLOW.read_text()
    assert '--path="$RUNNER_TEMP/publish"' in wf
    assert '--path="$RUNNER_TEMP/inventory"' not in wf


def test_the_render_carries_the_inventory_forward_and_the_tile_reads_the_same_path():
    """bin/catalog-render force-pushes state/live-diagram from origin/main; without the carry the
    inventory the workflow put there would vanish on the next render, and the Ops tile would read
    a 404. The tile's path and the render's path are the same two files."""
    render = (ROOT / "bin/catalog-render").read_text()
    assert 'CARRIED = ["docs/inventory.json", "docs/inventory.md"]' in render
    assert (
        'f"origin/{BRANCH}", "--", f' in render and '["git", "add", *carried]' in render
    )
    home = ROOT / "backstage/packages/app/src/modules/home"
    tile = (home / "inventory.ts").read_text()
    assert "INVENTORY_JSON = '/estate-state/docs/inventory.json'" in tile
    ops = (home / "Ops.tsx").read_text()
    # The page must still read the inventory. How it labels the unread case is look and feel,
    # and LAW 53 keeps test ids out of tests: the shared page shell (modules/shell) carries the
    # unread state now, so the id is a prop on a component and not a literal in this file.
    assert "useInventory()" in ops
    proxy = (ROOT / "backstage/app-config.yaml").read_text()
    assert "state/live-diagram" in proxy.split("'/estate-state':")[1][:400]
