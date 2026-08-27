"""crew#401 (founder, 2026-08-27): "i didnt ask i would not have known this. all founder interfaces
need to be highly accessible to founder else it's a void ... tell me how you guarantee i would
never have to wonder where anything is."

The guarantee is a gate, not a promise. backstage/founder/catalog-info.yaml is the one list of
places the founder looks, rendered by the portal at
catalogue.<zone>/catalog?filters[kind]=component&filters[type]=founder-surface. Rules (rung 2,
properties over the checkout; rung 4 for the incident itself):

  1. every public hostname (HTTPRoute under platform/**) is an Open link on a founder surface;
  2. every workflow a person can press (workflow_dispatch) is a link on a founder surface;
  3. every founder surface says what it is for, who updates it, and has at least one link;
     no link carries an unsubstituted variable; names and URLs are unique;
  4. the portal loads the file (app-config.yaml location) and the image carries it (Dockerfile).

Proved both ways: the checkout passes; a copy with one extra route or one extra button fails.
"""
import pathlib
import re
import shutil

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
FOUNDER = "backstage/founder/catalog-info.yaml"


def _zone(root):
    zones = {yaml.safe_load(f.read_text())["data"]["ESTATE_ZONE"] for f in (root / "clusters").glob("*/estate-config.yaml")}
    assert len(zones) == 1, zones
    return zones.pop()


def _hostnames(root):
    zone = _zone(root)
    for f in sorted((root / "platform").rglob("*.yaml")):
        for d in yaml.safe_load_all(f.read_text()):
            if d and d.get("kind") == "HTTPRoute":
                for h in d["spec"].get("hostnames", []):
                    yield re.sub(r"\$\{ESTATE_ZONE[^}]*\}", zone, h)


def _buttons(root):
    for f in sorted((root / ".github/workflows").glob("*.yml")):
        on = yaml.safe_load(f.read_text()).get(True) or yaml.safe_load(f.read_text()).get("on") or {}
        if "workflow_dispatch" in on:
            yield f.name


def _surfaces(root):
    docs = [d for d in yaml.safe_load_all((root / FOUNDER).read_text()) if d]
    assert docs, FOUNDER
    return docs


def missing(root) -> list[str]:
    """Every rule, as a list of violations; empty means the founder can find everything."""
    zone = _zone(root)
    out = []
    surfaces = _surfaces(root)
    urls, names = [], []
    for d in surfaces:
        m, name = d["metadata"], d["metadata"]["name"]
        names.append(name)
        if d.get("kind") != "Component" or d.get("spec", {}).get("type") != "founder-surface":
            out.append(f"{name}: not a Component of type founder-surface")
        if not m.get("description", "").strip():
            out.append(f"{name}: no description (what is it for?)")
        if not (m.get("annotations") or {}).get("idp/updated-by", "").strip():
            out.append(f"{name}: no idp/updated-by annotation (who keeps it current?)")
        links = m.get("links") or []
        if not links:
            out.append(f"{name}: no links")
        for l in links:
            u = l["url"].replace("${ESTATE_ZONE}", zone)
            if "${" in u or not re.match(r"https?://", u):
                out.append(f"{name}: link {l['url']} is not an address a person can open")
            urls.append(u)
    for dup in {x for x in names if names.count(x) > 1}:
        out.append(f"duplicate surface name {dup}")
    for dup in {x for x in urls if urls.count(x) > 1}:
        out.append(f"duplicate link {dup}")
    hosts = {re.match(r"https?://([^/]+)", u).group(1) for u in urls if re.match(r"https?://", u)}
    for h in _hostnames(root):
        if h not in hosts:
            out.append(f"public hostname {h} has no founder surface")
    for wf in _buttons(root):
        if not any(u.endswith(f"/actions/workflows/{wf}") for u in urls):
            out.append(f"workflow button {wf} has no founder surface link")
    app = yaml.safe_load((root / "backstage/app-config.yaml").read_text())
    if not any(loc.get("target", "").endswith("founder/catalog-info.yaml") for loc in app["catalog"]["locations"]):
        out.append("app-config.yaml does not load the founder location")
    if "COPY --chown=node:node founder ./founder" not in (root / "backstage/Dockerfile").read_text():
        out.append("Dockerfile does not copy founder/ into the image")
    return out


def test_incident_crew401_the_checkout_lists_every_founder_surface():
    assert missing(ROOT) == []


def _copy(tmp_path):
    fake = tmp_path / "root"
    for p in ("platform", "clusters", ".github/workflows", "backstage/founder"):
        shutil.copytree(ROOT / p, fake / p)
    for p in ("backstage/app-config.yaml", "backstage/Dockerfile"):
        shutil.copy(ROOT / p, fake / p)
    return fake


def test_incident_crew401_an_unlisted_hostname_is_refused(tmp_path):
    fake = _copy(tmp_path)
    (fake / "platform/nowhere.yaml").write_text(
        "apiVersion: gateway.networking.k8s.io/v1\nkind: HTTPRoute\nmetadata: {name: x}\nspec:\n  hostnames: ['void.${ESTATE_ZONE}']\n")
    assert [m for m in missing(fake) if "void." in m], "a route with no founder surface must fail"


def test_incident_crew401_an_unlisted_button_is_refused(tmp_path):
    fake = _copy(tmp_path)
    (fake / ".github/workflows/void.yml").write_text("name: void\non:\n  workflow_dispatch: {}\njobs: {}\n")
    assert [m for m in missing(fake) if "void.yml" in m], "a button with no founder surface must fail"


@pytest.mark.parametrize("field", ["description", "links"])
def test_incident_crew401_a_surface_without_purpose_or_link_is_refused(tmp_path, field):
    fake = _copy(tmp_path)
    docs = _surfaces(fake)
    docs[0]["metadata"].pop(field)
    (fake / FOUNDER).write_text(yaml.safe_dump_all(docs))
    assert [m for m in missing(fake) if docs[0]["metadata"]["name"] in m]
