"""crew#684 CP4, founder 2026-08-30: "I need to see everything": open FOUNDER ACTION items and the
last receipts as tiles on the Ops page. Incident class (crew#412, R38): the founder asked for his
view three times in 24 hours and got a typed answer from a session's memory each time. Guard: the
tiles read docs/founder.json, which bin/estate-founder writes from GitHub beside FOUNDER.md on the
render schedule and bin/catalog-render stages; the page reaches it through the backend's proxy
plugin (app-config proxy.endpoints./estate-state), never a host typed in the page and never a
session's memory. Fault class: process.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin" / "estate-founder"
HOME = ROOT / "backstage" / "packages" / "app" / "src" / "modules" / "home"
NOW = "2026-08-30T03:00Z"


def _fixtures(tmp: Path) -> dict[str, Path]:
    merged = [
        {
            "repo": "chidionyema/idp",
            "url": "https://github.com/chidionyema/idp/pull/918",
            "number": 918,
            "title": "Ops page",
            "body": "Built: the Ops page.\nUse: open the portal, sidebar Ops\nExpect: numbers",
            "merged_at": "2026-08-30T02:40:00Z",
            "created_at": "2026-08-30T01:00:00Z",
        },
        {
            "repo": "chidionyema/idp",
            "url": "https://github.com/chidionyema/idp/pull/921",
            "number": 921,
            "title": "register",
            "body": "no use line here",
            "merged_at": "2026-08-30T02:50:00Z",
            "created_at": "2026-08-30T02:00:00Z",
        },
    ]
    issues = [
        {
            "number": 693,
            "url": "https://github.com/chidionyema/crew/issues/693",
            "body": "- [ ] CP1 Founder replies APPROVE: crew#693 (his decision)\n- [ ] CP2 image automation\n",
            "labels": [],
        }
    ]
    paths = {}
    for name, data in {"merged": merged, "open": [], "issues": issues}.items():
        paths[name] = tmp / f"{name}.json"
        paths[name].write_text(json.dumps(data))
    return paths


def test_estate_founder_writes_founder_json_beside_the_page(tmp_path: Path) -> None:
    p = _fixtures(tmp_path)
    r = subprocess.run(
        [
            sys.executable,
            str(BIN),
            "--merged",
            str(p["merged"]),
            "--open",
            str(p["open"]),
            "--issues",
            str(p["issues"]),
            "--out",
            str(tmp_path / "FOUNDER.md"),
            "--now",
            NOW,
            "--taken",
            NOW,
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads((tmp_path / "founder.json").read_text())
    assert data["taken"] == NOW
    assert [w["issue"] + 0 for w in data["waiting"]] == [693] and data["waiting"][0][
        "cp"
    ] == "CP1"
    assert [x["number"] for x in data["receipts"]] == [918], (
        "only pull requests with a Use: line are receipts"
    )
    assert data["receipts"][0]["use"] == "open the portal, sidebar Ops"


def test_the_render_driver_stages_the_sidecar_and_the_proxy_serves_the_state_branch() -> (
    None
):
    render = (ROOT / "bin" / "catalog-render").read_text()
    assert 'FOUNDER_JSON = "docs/founder.json"' in render
    assert render.count("FOUNDER, FOUNDER_JSON]") == 2, (
        "founder.json must be in the diff and the stage lists"
    )
    cfg = yaml.safe_load((ROOT / "backstage" / "app-config.yaml").read_text())
    ep = cfg["proxy"]["endpoints"]["/estate-state"]
    assert ep["target"].endswith("/chidionyema/idp/state/live-diagram")
    assert ep["allowedMethods"] == ["GET"]
