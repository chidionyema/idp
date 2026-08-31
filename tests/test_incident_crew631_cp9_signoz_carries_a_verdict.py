"""crew#631 CP9: SigNoz, the third surface, carries a verdict -- L1 + L2 + L3 + a negative control.

The mistake class this pins (crew#631 CP1 and CP2 taught it): a surface "with a verdict" that is
green over a login screen, a route opened to a program that quietly exposes more than the one
path, and a key minter that prints the value it minted. Each row below is a property that breaks:

  1. the probe's negative control turns red when SigNoz answers a caller holding no key;
  2. bin/idp-prove names signoz, the hourly workflow runs it, the catalogue and the dispatcher
     carry it, and the portal has its button;
  3. the signoz-api route exposes /api/v2/dashboards alone, and the front-door gate refuses the
     same annotation on any other path;
  4. bin/idp-signoz-key mints through the vendor's endpoints, keeps a key SigNoz still accepts,
     rotates on SIGNOZ_ROTATE, and never prints the value;
  5. the front-door assertions grade a walk: reached and signed-in are two different facts.
"""

from __future__ import annotations

import http.server
import json
import os
import re
import stat
import subprocess
import sys
import threading
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from probes import front_door, signoz  # noqa: E402

ANNOTATION = "signoz-service-account-key"


def _get(status: int, doc: object):
    def get(url, **kw):
        get.calls.append((url, kw))
        return status, json.dumps(doc)

    get.calls = []
    return get


# --- 1. the probe --------------------------------------------------------------------------------


def test_l2_reads_dashboards_with_the_key_header_and_the_negative_control_holds() -> (
    None
):
    get = _get(200, {"data": []})
    rows = signoz.l2_machine("https://signoz.example", "k", get)
    assert {r["name"] for r in rows} == {
        "l2.dashboards.status_200_json",
        "l2.dashboards.data_is_a_list",
    }
    assert all(r["ok"] for r in rows)
    assert get.calls[0][1]["headers"] == {signoz.KEY_HEADER: "k"}
    assert signoz.KEY_HEADER == "SIGNOZ-API-KEY"

    (refused,) = signoz.negative_no_key(
        "https://signoz.example", _get(401, {"error": "unauthorized"})
    )
    assert refused["name"] == "l2.NEGATIVE.no_key_is_refused" and refused["ok"]


def test_negative_control_turns_red_when_the_dashboards_answer_a_caller_holding_no_key() -> (
    None
):
    (open_door,) = signoz.negative_no_key(
        "https://signoz.example", _get(200, {"data": [{"id": 1}]})
    )
    assert not open_door["ok"], (
        "SigNoz handed dashboards to a caller with no key and the row stayed green"
    )


def test_probe_with_no_key_is_l1_and_negative_only() -> None:
    rows = signoz.probe("https://signoz.example", None, _get(401, {}))
    names = {r["name"] for r in rows}
    assert "l2.NEGATIVE.no_key_is_refused" in names
    assert not any(n.startswith("l2.dashboards") for n in names)


# --- 2. wired: prover, workflow, catalogue, dispatcher, button -----------------------------------


def test_bin_idp_prove_names_signoz_as_a_target() -> None:
    src = (ROOT / "bin" / "idp-prove").read_text()
    assert re.search(r'"signoz":\s*prove_signoz', src)
    assert "bin/idp-prove signoz" in src.split("import", 1)[0], (
        "usage banner does not list signoz"
    )


def test_the_hourly_workflow_runs_the_signoz_prover_and_reports_verify_signoz() -> None:
    wf = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "verdict-signoz.yml").read_text()
    )
    on = wf.get("on") or wf.get(True)
    assert on["schedule"][0]["cron"] == "47 * * * *"
    assert "workflow_dispatch" in on and "lookup_trace" not in (
        on["workflow_dispatch"] or {}
    ).get("inputs", {})
    text = (ROOT / ".github" / "workflows" / "verdict-signoz.yml").read_text()
    assert "bin/idp-prove signoz" in text and "name=verify/signoz" in text
    assert "IDP_PROVE_LOOKUP_TRACE" not in text
    assert "bin/idp-signoz-key" in on["push"]["paths"]


def test_catalogue_and_dispatcher_carry_verdict_signoz_and_verdict_backstage() -> None:
    cat = yaml.safe_load((ROOT / "drills" / "catalogue.yaml").read_text())
    rows = {d["name"]: d for d in cat["drills"]}
    assert (
        rows["verdict-signoz"]["workflow"] == "verdict-signoz.yml"
        and rows["verdict-signoz"]["schedule"] == "47 * * * *"
    )
    assert (
        rows["verdict-backstage"]["workflow"] == "verdict-backstage.yml"
        and rows["verdict-backstage"]["schedule"] == "43 * * * *"
    )
    disp = (ROOT / "platform" / "drills" / "drill-dispatcher.yaml").read_text()
    assert (
        "verdict-signoz.yml=47_*_*_*_*" in disp
        and "verdict-backstage.yml=43_*_*_*_*" in disp
    )


def test_the_portal_has_a_button_for_the_signoz_prover() -> None:
    assert (
        ROOT
        / "backstage"
        / "templates"
        / "founder-actions"
        / "verdict-signoz"
        / "template.yaml"
    ).is_file()


def test_root_trust_register_names_the_signoz_prover_key() -> None:
    reg = (ROOT / "docs" / "reference" / "policy" / "root-trust.md").read_text()
    assert re.search(r"^\| `signoz-prover` \|.*bin/idp-signoz-key", reg, re.M)


# --- 3. the route and the gate -------------------------------------------------------------------


def _routes():
    return [
        d
        for d in yaml.safe_load_all(
            (ROOT / "platform" / "observability" / "httproute.yaml").read_text()
        )
        if d
    ]


def test_signoz_api_route_exposes_the_dashboards_prefix_alone() -> None:
    (route,) = [r for r in _routes() if r["metadata"]["name"] == "signoz-api"]
    assert route["metadata"]["annotations"]["idp.estate/auth"] == ANNOTATION
    paths = [m["path"] for rule in route["spec"]["rules"] for m in rule["matches"]]
    assert paths == [{"type": "PathPrefix", "value": "/api/v2/dashboards"}]
    assert route["spec"]["rules"][0]["backendRefs"] == [
        {"name": "signoz", "port": 8080}
    ]
    assert route["spec"]["parentRefs"][0]["sectionName"] == "https-signoz"
    (login_route,) = [r for r in _routes() if r["metadata"]["name"] == "signoz"]
    assert "idp.estate/auth" not in (
        login_route["metadata"].get("annotations") or {}
    ), "the login route must stay behind oauth2-proxy"


def test_the_gate_refuses_the_annotation_on_any_other_path() -> None:
    import importlib

    gate = importlib.import_module(
        "test_front_door_every_route_is_behind_the_one_login"
    )
    (route,) = [r for r in _routes() if r["metadata"]["name"] == "signoz-api"]
    gate.test_every_route_outside_identity_is_behind_forward_auth(
        "fixture", route
    )  # the real one passes
    wide = json.loads(json.dumps(route))
    wide["spec"]["rules"][0]["matches"][0]["path"]["value"] = "/api/"
    with pytest.raises(AssertionError, match="other than /api/v2/dashboards"):
        gate.test_every_route_outside_identity_is_behind_forward_auth("fixture", wide)
    extra = json.loads(json.dumps(route))
    extra["spec"]["rules"].append(
        {
            "matches": [
                {"path": {"type": "PathPrefix", "value": "/api/v1/service_accounts"}}
            ],
            "backendRefs": [{"name": "signoz", "port": 8080}],
        }
    )
    with pytest.raises(AssertionError, match="other than /api/v2/dashboards"):
        gate.test_every_route_outside_identity_is_behind_forward_auth("fixture", extra)


# --- 4. the key minter ---------------------------------------------------------------------------


class _SigNoz(http.server.BaseHTTPRequestHandler):
    """The five vendor endpoints, as SigNoz v0.138.0's own integration tests describe them."""

    state: dict = {}

    def log_message(self, *a):  # noqa: D102
        pass

    def _send(self, status, doc):
        body = json.dumps(doc).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        s = self.state
        s.setdefault("log", []).append(("GET", self.path))
        if self.path.startswith("/api/v2/dashboards"):
            key = self.headers.get("SIGNOZ-API-KEY")
            return (
                self._send(200, {"data": []})
                if key in s["keys"]
                else self._send(401, {"error": "unauthorized"})
            )
        if self.path.startswith("/api/v2/sessions/context"):
            return self._send(200, {"data": {"orgs": [{"id": "org-1"}]}})
        if self.headers.get("Authorization") != "Bearer tok":
            return self._send(401, {"error": "unauthorized"})
        if self.path == "/api/v1/roles":
            return self._send(
                200,
                {
                    "data": [
                        {"id": "r-admin", "name": "signoz-admin"},
                        {"id": "r-view", "name": "signoz-viewer"},
                    ]
                },
            )
        if self.path == "/api/v1/service_accounts":
            return self._send(
                200, {"data": [{"id": i, "name": n} for i, n in s["accounts"].items()]}
            )
        self._send(404, {})

    def do_POST(self):  # noqa: N802
        s = self.state
        body = json.loads(
            self.rfile.read(int(self.headers.get("Content-Length", 0)) or b"{}")
        )
        s.setdefault("log", []).append(("POST", self.path, body))
        if self.path == "/api/v2/sessions/email_password":
            ok = body == {
                "email": "root@example",
                "password": "hunter2",
                "orgId": "org-1",
            }
            return (
                self._send(200, {"data": {"accessToken": "tok"}})
                if ok
                else self._send(401, {"error": "bad login"})
            )
        if self.headers.get("Authorization") != "Bearer tok":
            return self._send(401, {"error": "unauthorized"})
        if self.path == "/api/v1/service_accounts":
            sid = f"sa-{len(s['accounts']) + 1}"
            s["accounts"][sid] = body["name"]
            return self._send(201, {"data": {"id": sid}})
        if self.path == "/api/v1/service_account_roles":
            s.setdefault("roles", []).append(body)
            return self._send(201, {"data": {}})
        m = re.fullmatch(r"/api/v1/service_accounts/([^/]+)/keys", self.path)
        if m and m.group(1) in s["accounts"] and body.get("expiresAt") == 0:
            key = f"minted-{len(s['keys']) + 1}"
            s["keys"].append(key)
            return self._send(201, {"data": {"key": key}})
        self._send(404, {})


@pytest.fixture
def fake_signoz():
    _SigNoz.state = {"keys": [], "accounts": {}, "log": []}
    srv = http.server.HTTPServer(("127.0.0.1", 0), _SigNoz)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_port}", _SigNoz.state
    finally:
        srv.shutdown()


def _fakes(tmp_path: Path, held: str | None):
    """A fake bin/idp-cloud (secret get) and bin/idp-vault-put that record what they were asked."""
    vault = {"signoz-root-email": "root@example", "signoz-root-password": "hunter2"}
    if held is not None:
        vault["signoz-prover"] = held
    (tmp_path / "vault.json").write_text(json.dumps(vault))
    cloud = tmp_path / "cloud"
    cloud.write_text(
        "#!/usr/bin/env python3\nimport json,sys\n"
        f"v=json.load(open({str(tmp_path / 'vault.json')!r}))\n"
        "assert sys.argv[1:3]==['secret','get']\n"
        "n=sys.argv[3]\n"
        "sys.exit(0 if n in v and not print(v[n]) else 1)\n"
    )
    put = tmp_path / "vault-put"
    put.write_text(
        "#!/usr/bin/env python3\nimport os,sys\n"
        f"open({str(tmp_path / 'put.log')!r},'a').write(' '.join(sys.argv[1:])+'\\n')\n"
        f"open({str(tmp_path / 'put.env')!r},'w').write(open(os.environ['ESTATE_ENV_FILE']).read())\n"
    )
    for f in (cloud, put):
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return cloud, put


def _run(tmp_path, base, held=None, rotate=False):
    cloud, put = _fakes(tmp_path, held)
    env = dict(
        os.environ,
        SIGNOZ_URL=base,
        IDP_CLOUD=str(cloud),
        IDP_VAULT_PUT=str(put),
        IDP_KUBE="/nonexistent/kubectl",
    )
    env.pop("SIGNOZ_ROTATE", None)
    if rotate:
        env["SIGNOZ_ROTATE"] = "1"
    return subprocess.run(
        [sys.executable, str(ROOT / "bin" / "idp-signoz-key")],
        env=env,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_minter_creates_the_viewer_service_account_mints_a_key_and_writes_it_unprinted(
    fake_signoz, tmp_path
) -> None:
    base, state = fake_signoz
    p = _run(tmp_path, base)
    assert p.returncode == 0, p.stdout + p.stderr
    assert state["accounts"] == {"sa-1": "estate-prover"}
    assert state["roles"] == [{"serviceAccountId": "sa-1", "roleId": "r-view"}], (
        "the account must carry signoz-viewer, not admin"
    )
    assert state["keys"] == ["minted-1"]
    assert (
        tmp_path / "put.log"
    ).read_text().strip() == "--merge signoz-prover key=SIGNOZ_PROVER_KEY"
    assert (tmp_path / "put.env").read_text() == "SIGNOZ_PROVER_KEY=minted-1\n"
    assert "minted-1" not in p.stdout + p.stderr, "the key value reached stdout"
    assert "hunter2" not in p.stdout + p.stderr


def test_minter_keeps_a_held_key_signoz_still_accepts_and_rotates_only_on_request(
    fake_signoz, tmp_path
) -> None:
    base, state = fake_signoz
    state["keys"].append("held-1")
    p = _run(tmp_path, base, held=json.dumps({"key": "held-1"}))
    assert p.returncode == 0 and "kept" in p.stdout, p.stdout + p.stderr
    assert not (tmp_path / "put.log").exists() and state["accounts"] == {}
    p = _run(tmp_path, base, held=json.dumps({"key": "held-1"}), rotate=True)
    assert p.returncode == 0 and state["keys"] == ["held-1", "minted-2"], (
        p.stdout + p.stderr
    )
    assert (tmp_path / "put.env").read_text() == "SIGNOZ_PROVER_KEY=minted-2\n"


def test_minter_mints_anew_when_the_held_key_is_refused(fake_signoz, tmp_path) -> None:
    base, state = fake_signoz
    p = _run(tmp_path, base, held=json.dumps({"key": "revoked"}))
    assert p.returncode == 0 and state["keys"] == ["minted-1"], p.stdout + p.stderr


def test_minter_is_blind_with_no_root_login_and_fails_on_a_refused_login(
    fake_signoz, tmp_path
) -> None:
    base, _ = fake_signoz
    cloud, put = _fakes(tmp_path, None)
    (tmp_path / "vault.json").write_text(
        json.dumps({"signoz-root-email": "root@example"})
    )
    env = dict(
        os.environ, SIGNOZ_URL=base, IDP_CLOUD=str(cloud), IDP_VAULT_PUT=str(put)
    )
    p = subprocess.run(
        [sys.executable, str(ROOT / "bin" / "idp-signoz-key")],
        env=env,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert p.returncode == 2 and "BLIND" in p.stdout
    (tmp_path / "vault.json").write_text(
        json.dumps(
            {"signoz-root-email": "root@example", "signoz-root-password": "wrong"}
        )
    )
    p = subprocess.run(
        [sys.executable, str(ROOT / "bin" / "idp-signoz-key")],
        env=env,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert p.returncode == 1 and "FAIL" in p.stdout and "wrong" not in p.stdout


def test_the_seed_runs_the_minter_as_step_4_and_lists_it_in_preflight() -> None:
    seed = (ROOT / "bin" / "idp-estate-seed").read_text()
    assert "SIGNOZ_KEY=${IDP_SIGNOZ_KEY:-$IDP/bin/idp-signoz-key}" in seed
    assert "# --- 4. the SigNoz prover key" in seed
    assert "bl signoz-prover" in seed and "fail signoz-prover" in seed
    assert 'say "" signoz-prover "key <- SigNoz service-account key' in seed
    assert os.access(ROOT / "bin" / "idp-signoz-key", os.X_OK)


# --- 5. the front-door assertions ----------------------------------------------------------------


def test_front_door_reached_and_signed_in_are_two_facts() -> None:
    def names(rows):
        return {r["name"]: r["ok"] for r in rows}

    home = names(
        front_door.assertions("signoz", "signoz.z", "signoz.z", "/", 0, 200, "login.z")
    )
    assert home == {
        "l3.front_door.signoz.reached_host": True,
        "l3.front_door.signoz.signed_in": True,
    }
    login = names(
        front_door.assertions(
            "signoz", "signoz.z", "signoz.z", "/login", 1, 200, "login.z"
        )
    )
    assert (
        login["l3.front_door.signoz.reached_host"]
        and not login["l3.front_door.signoz.signed_in"]
    )
    stuck = names(
        front_door.assertions("signoz", "signoz.z", "login.z", "/", 0, 200, "login.z")
    )
    assert (
        not stuck["l3.front_door.signoz.reached_host"]
        and not stuck["l3.front_door.signoz.signed_in"]
    )
    error = names(
        front_door.assertions("signoz", "signoz.z", "signoz.z", "/", 0, 502, "login.z")
    )
    assert not error["l3.front_door.signoz.reached_host"]
