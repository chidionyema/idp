"""crew#562 path 2 (ADR 0009 decision founder-screen-access): the estate Mac's screen in the browser.

The shape a buyer's engineer would take apart, refused here so no later edit reopens it:
  1. no password for the app anywhere: the seed deletes the schema's default `guacadmin`, the
     front door (header extension) is the only login, and no VNC password is stored -- Guacamole
     prompts for it (the seed sets hostname/port only);
  2. the Mac is reached only through the tailnet egress Service on the estate-config row, and the
     vault entry is on the root-trust register with a bootstrapper;
  3. the surface is routed behind the one login on the existing catalogue listener, listed as a
     founder surface, and probed.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIR = ROOT / "platform" / "guacamole"


def _docs(name):
    return [d for d in yaml.safe_load_all((DIR / name).read_text()) if d]


def _seed_sql():
    cm = next(d for d in _docs("guacamole.yaml") if d["kind"] == "ConfigMap")
    return cm["data"]["seed.sql"]


def test_no_password_exists_for_the_app():
    sql = _seed_sql()
    assert re.search(r"DELETE FROM guacamole_entity WHERE name = 'guacadmin'", sql), "the default admin must go"
    assert "'password'" not in sql and "'username'" not in sql, "the VNC login is typed at connect time, never seeded"
    env = next(d for d in _docs("env.yaml") if d["kind"] == "ConfigMap")["data"]
    assert env["HEADER_ENABLED"] == "true" and env["HTTP_AUTH_HEADER"] == "X-Auth-Request-Email"
    assert env["POSTGRESQL_AUTO_CREATE_ACCOUNTS"] == "true"
    dep = next(d for d in _docs("guacamole.yaml") if d["kind"] == "Deployment")
    for c in dep["spec"]["template"]["spec"]["containers"] + dep["spec"]["template"]["spec"]["initContainers"]:
        for e in c.get("env", []):
            assert "secretKeyRef" not in str(e.get("valueFrom", {})), f"{c['name']}: secrets are mounted files, never env"


def test_the_mac_is_reached_only_over_the_tailnet_egress():
    svc = next(d for d in _docs("mac-egress.yaml") if d["kind"] == "Service")
    assert svc["metadata"]["annotations"]["tailscale.com/tailnet-ip"] == "${FOUNDER_MAC_TS_IP}"
    assert svc["spec"]["type"] == "ExternalName" and svc["spec"]["ports"][0]["port"] == 5900
    sql = _seed_sql()
    assert "('hostname', 'founder-mac-vnc')" in sql and "('port', '5900')" in sql
    assert not re.search(r"\b100\.\d+\.\d+\.\d+\b", (DIR / "guacamole.yaml").read_text() + sql), "no tailnet IP literal (LAW 46)"


def test_the_vault_entry_is_born_by_a_bootstrapper():
    es = [d for d in _docs("external-secret.yaml") if d["kind"] == "ExternalSecret"]
    keys = {r["remoteRef"]["key"] for d in es for r in d["spec"]["data"]}
    assert keys == {"guacamole", "langfuse-init-user-email"}
    assert re.search(r"^guacamole\s+postgres-password\s+hex32$", (ROOT / "bin" / "idp-estate-seed").read_text(), re.M)
    register = (ROOT / "docs" / "reference" / "policy" / "root-trust.md").read_text()
    assert re.search(r"^\| `guacamole` \(`postgres-password`\) \|.*\| MEETS \| `bin/idp-estate-seed` \|$", register, re.M)


def test_the_surface_is_behind_the_one_login_listed_and_probed():
    route = next(d for d in _docs("httproute.yaml") if d["kind"] == "HTTPRoute")
    assert route["spec"]["hostnames"] == ["catalogue.${ESTATE_ZONE}"]
    assert route["spec"]["parentRefs"][0]["sectionName"] == "https-catalogue"
    rule = route["spec"]["rules"][0]
    assert rule["matches"][0]["path"] == {"type": "PathPrefix", "value": "/screen/"}
    assert any(f.get("extensionRef", {}).get("name") == "login-forward-auth" for f in rule["filters"])
    ns = next(d for d in _docs("namespace.yaml") if d["kind"] == "Namespace")
    assert ns["metadata"]["labels"]["idp.estate/edge-attach"] == "true", "the catalogue listener selects on this label"
    surfaces = [d for d in yaml.safe_load_all((ROOT / "backstage" / "founder" / "catalog-info.yaml").read_text())
                if d and d["metadata"]["name"] == "founder-screen"]
    assert surfaces and surfaces[0]["metadata"]["links"][0]["url"] == "https://catalogue.${ESTATE_ZONE}/screen/"
    probe = (ROOT / "platform" / "monitoring" / "rules" / "founder-surfaces-probe.yaml").read_text()
    assert "- https://catalogue.${ESTATE_ZONE}/screen/" in probe
    flux = (ROOT / "clusters" / "oke" / "platform.yaml").read_text()
    assert "path: ./platform/guacamole" in flux


def test_a_first_time_user_is_told_the_one_prerequisite_and_the_estate_measures_it():
    """Founder, 2026-08-28: "how will a first time user know this" -- the card says it, the probe measures it."""
    card = next(d for d in yaml.safe_load_all((ROOT / "backstage" / "founder" / "catalog-info.yaml").read_text())
                if d and d["metadata"]["name"] == "founder-screen")
    assert "System Settings > General > Sharing > Screen Sharing" in card["metadata"]["description"]
    probe = next(d for d in yaml.safe_load_all((ROOT / "platform" / "monitoring" / "rules" / "founder-mac-screen-sharing-probe.yaml").read_text()) if d)
    assert probe["spec"]["module"] == "mac_screen_sharing"
    assert probe["spec"]["targets"]["staticConfig"]["static"] == ["founder-mac-vnc.guacamole.svc.cluster.local:5900"]
    bb = (ROOT / "platform" / "monitoring" / "blackbox.yaml").read_text()
    assert re.search(r"mac_screen_sharing:\n\s+prober: tcp", bb)
    rules = (ROOT / "platform" / "monitoring" / "rules" / "estate.yaml").read_text()
    assert 'probe_success{job="founder-mac-screen-sharing"} == 0' in rules
    assert "Sharing > Screen Sharing on" in rules, "the alert names the one switch in plain English"
    assert "founder-mac-screen-sharing-probe.yaml" in (ROOT / "platform" / "monitoring" / "rules" / "kustomization.yaml").read_text()
