"""crew#612 CP5: "every entity page carries content ... no empty tab." Measured 2026-08-29 in
node_modules/@backstage/plugin-techdocs/dist/alpha.esm.js: the TechDocs entity content has no
filter, so all 338 entities showed a TechDocs tab while 4 carry backstage.io/techdocs-ref; the
api-docs "APIs" content filters on kind=component only, and no Component provides an API.

Rule: backstage/app-config.yaml carries a predicate for each of those two contents, and the
predicate, evaluated the way @backstage/filter-predicates evaluates it, shows the tab on a
founder surface only when the surface has something for it. Rung 4, incident test.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_CONFIG = ROOT / "backstage" / "app-config.yaml"
FOUNDER = ROOT / "backstage" / "founder" / "catalog-info.yaml"


def _at(value, path):
    """Port of filter-predicates getJsonValueAtPath: a key may itself contain dots."""
    if not path or not isinstance(value, dict):
        return None
    for k, v in value.items():
        if k == path and v is not None:
            return v
        if path.startswith(k + "."):
            found = _at(v, path[len(k) + 1:])
            if found is not None:
                return found
    return None


def _value(flt, value):
    if not isinstance(flt, dict):
        return value == flt
    if "$contains" in flt:
        return isinstance(value, list) and any(_pred(flt["$contains"], v) for v in value)
    if "$exists" in flt:
        return (value is not None) if flt["$exists"] else (value is None)
    if "$in" in flt:
        return value in flt["$in"]
    return False


def _pred(pred, value):
    if not isinstance(pred, dict):
        return value == pred
    if "$all" in pred:
        return all(_pred(f, value) for f in pred["$all"])
    if "$any" in pred:
        return any(_pred(f, value) for f in pred["$any"])
    if "$not" in pred:
        return not _pred(pred["$not"], value)
    return all(_value(f, _at(value, k)) for k, f in pred.items())


def _extension_config():
    app = yaml.safe_load(APP_CONFIG.read_text())
    out = {}
    for item in app["app"]["extensions"]:
        if isinstance(item, dict):
            (name, body), = item.items()
            out[name] = (body or {}).get("config") or {}
    return out


def _founder_surfaces():
    docs = [d for d in yaml.safe_load_all(FOUNDER.read_text()) if d]
    return [d for d in docs if (d.get("spec") or {}).get("type") == "founder-surface"]


def test_docs_tab_shows_only_where_docs_exist_and_is_called_docs():
    cfg = _extension_config()["entity-content:techdocs"]
    assert cfg["title"] == "Docs"
    surfaces = _founder_surfaces()
    shown = [d["metadata"]["name"] for d in surfaces if _pred(cfg["filter"], d)]
    with_docs = [d["metadata"]["name"] for d in surfaces
                 if "backstage.io/techdocs-ref" in (d["metadata"].get("annotations") or {})]
    assert shown == with_docs and with_docs, (shown, with_docs)


def test_apis_tab_shows_only_where_an_api_relation_exists():
    cfg = _extension_config()["entity-content:api-docs/apis"]
    surfaces = _founder_surfaces()
    assert not [d["metadata"]["name"] for d in surfaces if _pred(cfg["filter"], d)]
    with_api = dict(surfaces[0], relations=[{"type": "providesApi", "targetRef": "api:default/x"}])
    assert _pred(cfg["filter"], with_api)


def test_the_port_matches_the_library_on_dotted_annotation_keys():
    entity = {"metadata": {"annotations": {"backstage.io/techdocs-ref": "dir:."}}}
    assert _pred({"metadata.annotations.backstage.io/techdocs-ref": {"$exists": True}}, entity)
    assert not _pred({"metadata.annotations.backstage.io/techdocs-ref": {"$exists": True}}, {"metadata": {}})
