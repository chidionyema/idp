"""crew#631 CP9, the security-surface change: the catalogue API lets a Bearer token past the
browser login. Graded on the shapes that would open the door: a rule with no Authorization match,
an unanchored regular expression, a missing externalAccess block, and the prover workflow that
must exist to run the NEGATIVE control hourly."""

import pathlib

import yaml

import tests.test_front_door_every_route_is_behind_the_one_login as FD

IDP = pathlib.Path(__file__).resolve().parents[1]
ROUTE = IDP / "platform" / "backstage" / "overlays" / "oke" / "httproute.yaml"
WORKFLOW = IDP / ".github" / "workflows" / "verdict-backstage.yml"


def _rules():
    for d in yaml.safe_load_all(ROUTE.read_text()):
        if d and d.get("kind") == "HTTPRoute":
            return d["spec"]["rules"]
    raise AssertionError("no HTTPRoute in the catalogue overlay")


def _bearer_rule():
    for r in _rules():
        if any(m.get("headers") for m in r.get("matches") or []):
            return r
    raise AssertionError("no Bearer-gated rule on the catalogue route")


def _names(rule):
    return [
        f["extensionRef"]["name"]
        for f in rule.get("filters", [])
        if f.get("type") == "ExtensionRef"
    ]


def test_the_bearer_rule_skips_the_login_only_for_the_catalogue_api_with_a_token():
    r = _bearer_rule()
    assert "login-forward-auth" not in _names(r)
    assert [m["path"] for m in r["matches"]] == [
        {"type": "PathPrefix", "value": "/api/catalog/"}
    ]
    ok, why = FD.bearer_gated_ok(
        r, (IDP / "backstage" / "app-config.container.yaml").read_text()
    )
    assert ok, why
    assert [b["name"] for b in r["backendRefs"]] == ["catalogue"]


def test_the_catch_all_rule_still_carries_the_login():
    last = _rules()[-1]
    assert "matches" not in last and "login-forward-auth" in _names(last)


def test_the_gate_refuses_every_shape_that_opens_the_door():
    good = _bearer_rule()
    cfg = "backend:\n  auth:\n    externalAccess: []\n"
    assert FD.bearer_gated_ok(good, cfg)[0]
    path = good["matches"][0]["path"]
    no_header = {"matches": [{"path": path}]}
    assert not FD.bearer_gated_ok(no_header, cfg)[0]
    loose = {
        "matches": [
            {
                "path": path,
                "headers": [
                    {
                        "type": "RegularExpression",
                        "name": "Authorization",
                        "value": "Bearer",
                    }
                ],
            }
        ]
    }
    assert not FD.bearer_gated_ok(loose, cfg)[0]
    exact = {
        "matches": [
            {
                "path": path,
                "headers": [
                    {"type": "Exact", "name": "Authorization", "value": "^Bearer .+"}
                ],
            }
        ]
    }
    assert not FD.bearer_gated_ok(exact, cfg)[0]
    assert not FD.bearer_gated_ok(good, "backend:\n  auth: {}\n")[0]
    assert not FD.bearer_gated_ok({"matches": []}, cfg)[0]


def test_the_prover_workflow_runs_the_negative_control_hourly():
    w = yaml.safe_load(WORKFLOW.read_text())
    assert w[True]["schedule"][0]["cron"].split()[1] == "*", (
        "the catalogue prover is hourly"
    )
    steps = "\n".join(s.get("run", "") for s in w["jobs"]["prove"]["steps"])
    assert "bin/idp-prove backstage --out" in steps and "verify/backstage" in steps
    assert "bin/idp-verdict store" in steps, "the verdict row lands in the table"
    assert "playwright" not in WORKFLOW.read_text(), (
        "no browser: the machine door is the point"
    )


def test_idp_prove_reads_the_token_from_the_vault_entry_never_the_environment():
    src = (IDP / "bin" / "idp-prove").read_text()
    assert 'vault("backstage-env")' in src and '.get("PROVER_TOKEN")' in src
    assert 'environ.get("PROVER_TOKEN' not in src and 'environ["PROVER_TOKEN' not in src
    assert '"backstage": prove_backstage' in src
