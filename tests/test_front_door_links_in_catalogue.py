"""crew#269 row 2 (founder, 2026-08-25: "how do i know what the backstage url is"). Property:
every HTTPRoute hostname under platform/** appears in the generated catalogue as a Component with
an `Open` link on the estate zone, with no unsubstituted variable; and a checkout that publishes
routes without declaring a zone is refused, never silently linkless."""
import os
import pathlib
import shutil
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "catalog-gen"
FIX = ROOT / "tests" / "fixtures" / "inventory.json"


def _run(tmp_path, root):
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    return subprocess.run([str(GEN)], env={**os.environ, "INV": str(FIX), "OUT": str(out), "ESTATE_ENV": "dev",
                                           "CATALOG_GEN_ROOT": str(root)}, capture_output=True, text=True), out


def _hostnames(root):
    for f in sorted((root / "platform").rglob("*.yaml")):
        for d in yaml.safe_load_all(f.read_text()):
            if d and d.get("kind") == "HTTPRoute":
                yield from d["spec"].get("hostnames", [])


def _zone(root):
    zones = set()
    for f in (root / "clusters").glob("*/estate-config.yaml"):
        zones.update(yaml.safe_load(f.read_text())["data"]["ESTATE_ZONE"] for _ in [0])
    assert len(zones) == 1, zones
    return zones.pop()


def test_every_published_hostname_is_an_open_link_on_the_zone(tmp_path):
    hosts = list(_hostnames(ROOT))
    assert hosts, "no HTTPRoute under platform/**"
    r, out = _run(tmp_path, ROOT)
    assert r.returncode == 0, r.stderr
    docs = [d for d in yaml.safe_load_all((out / "catalog-info.yaml").read_text()) if d]
    links = {l["url"] for d in docs for l in d["metadata"].get("links", [])}
    zone = _zone(ROOT)
    for h in hosts:
        assert f"https://{h.replace('${ESTATE_ZONE}', zone)}" in links, (h, sorted(links))
    assert not [u for u in links if "${" in u], links


def test_routes_without_a_zone_are_refused(tmp_path):
    fake = tmp_path / "root"
    shutil.copytree(ROOT / "platform", fake / "platform")
    (fake / "clusters").mkdir()
    r, _ = _run(tmp_path, fake)
    assert r.returncode != 0 and "refusing" in (r.stderr + r.stdout), (r.returncode, r.stderr[-300:])
