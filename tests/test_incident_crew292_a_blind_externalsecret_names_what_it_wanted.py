"""crew#292: `BLIND receipt not-ready ExternalSecret tailscale/tailscale-operator-secret: could
not get secret data from provider` -- verify-drill run 33176874659, 2026-08-28T13:46Z.

That sentence is ESO's own, and it is the whole receipt. It names neither the store it asked nor
the key it wanted, so three different faults print identically:

  * the vault entry was never written  (the actual cause: no SEED_TAILSCALE_OAUTH_CLIENT_ID /
    SEED_TAILSCALE_OAUTH_CLIENT_SECRET repository secret on chidionyema/idp, so vault-seed.yml
    had nothing to seed the `tailscale-operator` entry from)
  * the store is unreachable or its auth expired
  * the key is right and the `property` under it is misspelled

An operator reading the receipt cannot tell which, and the run that printed it exited 1 with no
way forward. This is the same class as bin/idp-cloud's swallowed create-kubeconfig stderr and
bin/idp-ci's `grep -E '^(FAIL|      )'` on the kyverno judge: an instrument that destroys the
cause of the failure it reports (LAW 28), which nobody can attribute from (LAW 29). Fourth
instance found, same branch.

Rules this file holds:
  1. A not-ready ExternalSecret row names the store it asked and every remote key it wanted.
  2. ESO's own message is kept, never replaced -- the fix adds cause, it does not swap one
     partial receipt for another.
  3. A ready row is not annotated: the clause is for the reader of a failure, and a row that is
     fine stays as short as it was.
  4. Every shape the spec can take reaches the clause -- `data` with and without `property`,
     `dataFrom.extract`, `dataFrom.find` -- because a shape that silently contributes nothing is
     how an allow-list drops a case with no test failing.
  5. A spec that declares no keys at all says so, rather than printing an empty list that reads
     as "nothing was wanted".

The function and the row-building loop are lifted out of the deployed ConfigMap by ast and
executed. Nothing here asserts on the text of the source.
"""
import ast
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"

# the live spec, verbatim from platform/tailscale/external-secret.yaml
LIVE_SPEC = {
    "secretStoreRef": {"name": "estate-vault", "kind": "ClusterSecretStore"},
    "data": [
        {"secretKey": "client_id",
         "remoteRef": {"key": "tailscale-operator", "property": "client_id"}},
        {"secretKey": "client_secret",
         "remoteRef": {"key": "tailscale-operator", "property": "client_secret"}},
    ],
}
# the message ESO actually printed in run 33176874659
ESO_MESSAGE = "could not get secret data from provider"


def _collect() -> str:
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    return next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]


def _wanted_from():
    """The real helper out of the manifest the cluster runs, executed, not string-matched."""
    tree = ast.parse(_collect())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "wanted_from")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "collect.py", "exec"), ns)
    return ns["wanted_from"]


def _rows(*secrets):
    """Run collect.py's real flux loop over these ExternalSecrets and return the rows it built.

    The loop is module-level code, not a function, so it is lifted as the `for` statement it is
    and executed with the helpers it calls and a `get` that hands it these objects. The row this
    asserts on is the row the cluster's collector builds.
    """
    tree = ast.parse(_collect())
    loop = next(n for n in tree.body
                if isinstance(n, ast.For) and getattr(n.iter, "id", "") == "FLUX")
    wanted = {"refresh_seconds", "stale_sync", "flux_message", "helm_last_attempt", "wanted_from"}
    helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    assert {h.name for h in helpers} == wanted, wanted - {h.name for h in helpers}
    ns = {"re": re, "datetime": datetime, "timezone": timezone, "flux": [],
          "FLUX": [("ExternalSecret", "/apis/external-secrets.io/v1/externalsecrets")],
          "get": lambda _path: {"items": list(secrets)}}
    exec(compile(ast.Module(body=helpers + [loop], type_ignores=[]), "collect.py", "exec"), ns)
    return ns["flux"]


def _es(spec, ready, message, ns="tailscale", name="tailscale-operator-secret"):
    return {"metadata": {"namespace": ns, "name": name},
            "spec": dict(spec, refreshInterval="1h"),
            "status": {"refreshTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "conditions": [{"type": "Ready",
                                       "status": "True" if ready else "False",
                                       "message": message,
                                       "lastTransitionTime": "2026-08-28T13:00:00Z"}]}}


def test_the_live_blind_row_now_names_the_store_and_both_keys_it_wanted():
    """Rule 1, on the exact row that was blind in run 33176874659."""
    row = _rows(_es(LIVE_SPEC, False, ESO_MESSAGE))[0]
    assert row["ready"] is False
    assert "ClusterSecretStore/estate-vault" in row["message"]
    assert "tailscale-operator[client_id]" in row["message"]
    assert "tailscale-operator[client_secret]" in row["message"]


def test_the_message_eso_printed_is_kept_not_replaced():
    """Rule 2. Adding a cause must not cost the reader the symptom."""
    row = _rows(_es(LIVE_SPEC, False, ESO_MESSAGE))[0]
    assert ESO_MESSAGE in row["message"]
    assert row["message"].index(ESO_MESSAGE) < row["message"].index("wanted ")


def test_a_ready_row_is_not_annotated():
    """Rule 3. The clause is for the reader of a failure."""
    row = _rows(_es(LIVE_SPEC, True, "secret synced"))[0]
    assert row["ready"] is True
    assert "wanted " not in row["message"]


def test_a_row_with_no_ready_condition_at_all_still_names_what_it_wanted():
    """The blindest row of all is the one ESO never got far enough to grade."""
    o = _es(LIVE_SPEC, False, "")
    o["status"]["conditions"] = []
    row = _rows(o)[0]
    assert "no Ready condition yet" in row["message"]
    assert "tailscale-operator[client_id]" in row["message"]


def test_a_stale_row_names_which_key_stopped_refreshing():
    """The crew#387 staleness message says the interval; it never said the key."""
    o = _es(LIVE_SPEC, True, "secret synced")
    o["status"]["refreshTime"] = "2026-01-01T00:00:00Z"
    row = _rows(o)[0]
    assert row["ready"] is False
    assert "older than 2x refreshInterval" in row["message"]
    assert "tailscale-operator[client_id]" in row["message"]


@pytest.mark.parametrize("spec,expected", [
    ({"data": [{"remoteRef": {"key": "plain"}}]}, "plain"),
    ({"data": [{"remoteRef": {"key": "k", "property": "p"}}]}, "k[p]"),
    ({"dataFrom": [{"extract": {"key": "whole-entry"}}]}, "whole-entry"),
    ({"dataFrom": [{"find": {"key": "by-pattern"}}]}, "by-pattern"),
    ({"data": [{"remoteRef": {"key": "a"}}],
      "dataFrom": [{"extract": {"key": "b"}}]}, "a, b"),
])
def test_every_shape_a_spec_can_declare_a_key_in_reaches_the_clause(spec, expected):
    """Rule 4. A shape that contributes nothing is how an allow-list drops a case in silence."""
    assert _wanted_from()(spec).startswith(f"wanted {expected} from ")


def test_a_key_wanted_twice_is_named_once():
    """Two secretKeys off one vault entry is the common shape; the clause must not stutter."""
    spec = {"data": [{"remoteRef": {"key": "e", "property": "p"}},
                     {"remoteRef": {"key": "e", "property": "p"}}]}
    assert _wanted_from()(spec) == "wanted e[p] from SecretStore/?"


def test_a_spec_that_declares_no_keys_says_so_rather_than_printing_an_empty_list():
    """Rule 5. An empty list reads as 'nothing was wanted', which is never the truth."""
    assert "no keys declared in spec" in _wanted_from()({"secretStoreRef": {"name": "v"}})


def test_a_missing_store_ref_does_not_crash_the_whole_snapshot():
    """A collector that raises here loses every row after it, not just this one."""
    for spec in ({}, None, {"secretStoreRef": None}, {"data": None}, {"data": [{}]}):
        assert _wanted_from()(spec).startswith("wanted ")


def test_the_store_kind_is_named_because_a_namespaced_store_is_a_different_object():
    """A namespaced SecretStore and a ClusterSecretStore of the same name are two
    different places to look, so the kind is part of the answer."""
    f = _wanted_from()
    assert "ClusterSecretStore/estate-vault" in f({"secretStoreRef": {"name": "estate-vault",
                                                                  "kind": "ClusterSecretStore"}})
    assert "SecretStore/estate-vault" in f({"secretStoreRef": {"name": "estate-vault"}})


def test_the_declaration_this_incident_was_found_on_still_reads_the_way_the_test_assumes():
    """If the live spec changes shape, this file is stale and must say so rather than pass."""
    docs = [d for d in yaml.safe_load_all(
        (ROOT / "platform/tailscale/external-secret.yaml").read_text()) if d]
    es = next(d for d in docs if d["kind"] == "ExternalSecret")
    keys = {(d["remoteRef"]["key"], d["remoteRef"].get("property")) for d in es["spec"]["data"]}
    assert keys == {("tailscale-operator", "client_id"), ("tailscale-operator", "client_secret")}
    # The store is asserted too, not just the keys. This file first shipped with LIVE_SPEC naming
    # `oci-vault` while the manifest said `estate-vault`, and every test still passed because
    # nothing here ever compared the two: a fixture graded against itself (peer review, session
    # 78caaa17 on idp#602). A row that sends the reader to a store that does not exist is worse
    # than the six words it replaced.
    assert es["spec"]["secretStoreRef"] == {"kind": "ClusterSecretStore", "name": "estate-vault"}
    assert LIVE_SPEC["secretStoreRef"] == es["spec"]["secretStoreRef"]
    assert _wanted_from()(es["spec"]) == (
        "wanted tailscale-operator[client_id], tailscale-operator[client_secret] "
        "from ClusterSecretStore/estate-vault")
