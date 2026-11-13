"""bin/idp-otto-homes resolve_account: where the lifeboat Worker deploys. Total over every case,
including the two-account stitch (idp#7814) that failed runs 42385416630/42489994627/42602043437."""
import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

loader = importlib.machinery.SourceFileLoader("otto_homes", str(Path(__file__).resolve().parents[1] / "bin/idp-otto-homes"))
spec = importlib.util.spec_from_loader("otto_homes", loader)
oh = importlib.util.module_from_spec(spec)
loader.exec_module(oh)

ZONE = "https://api.cloudflare.com/client/v4/zones?name=example.com"
ACCTS = "https://api.cloudflare.com/client/v4/accounts"


def fake(zone_body, accounts_body):
    calls = []

    def get(url, token):
        calls.append((url, token))
        return {ZONE: zone_body, ACCTS: accounts_body}.get(url)
    get.calls = calls
    return get


def test_zone_readable_deploys_on_the_zone_route():
    get = fake({"result": [{"account": {"id": "acct-zone"}}]}, None)
    assert oh.resolve_account("example.com", "reader", "workers", get) == ("acct-zone", "zone")
    assert get.calls == [(ZONE, "reader")], "the accounts list is not read when the zone answers"


@pytest.mark.parametrize("zone_body", [None, {}, {"result": []}, {"result": [{"account": {}}]}, {"result": "x"}])
def test_zone_in_another_account_falls_back_to_the_single_workers_account(zone_body):
    get = fake(zone_body, {"result": [{"id": "acct-own"}]})
    assert oh.resolve_account("example.com", "reader", "workers", get) == ("acct-own", "workers.dev")
    assert (ACCTS, "workers") in get.calls, "the account is read with the Workers token"


def test_no_reader_token_skips_the_zone_read():
    get = fake({"result": [{"account": {"id": "never"}}]}, {"result": [{"id": "acct-own"}]})
    assert oh.resolve_account("example.com", "", "workers", get) == ("acct-own", "workers.dev")
    assert all(u != ZONE for u, _ in get.calls)


@pytest.mark.parametrize("accounts_body", [None, {}, {"result": []}, {"result": [{"name": "no-id"}]}])
def test_no_visible_account_refuses(accounts_body):
    with pytest.raises(SystemExit, match="sees no account"):
        oh.resolve_account("example.com", "reader", "workers", fake(None, accounts_body))


def test_several_accounts_refuse_rather_than_guess():
    with pytest.raises(SystemExit, match="sees 2 accounts; refusing to guess"):
        oh.resolve_account("example.com", "reader", "workers", fake(None, {"result": [{"id": "a"}, {"id": "b"}]}))
