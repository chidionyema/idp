"""Incident, measured on apply runs 33681830297 and 33685104831 (2026-09-02): three vendor keys the
founder had funded that day read `refused by <url>; revoke it and make one that works`, and one read
`does not match the registry shape`. The probe swallowed the vendor's HTTP status, so a dead key, an
empty balance, a wrong probe URL on our side and a rate limit were one word, and the advice was
wrong for three of the four. MiniMax's key never reached the vendor at all: a JSON-web-token regex
nobody had a source for refused it first. Now the FAIL line carries the vendor's status and body
head, names whose fault it is, and the MiniMax shape refuses only an empty or malformed paste.
"""

import importlib.util
import pathlib

_sibling = pathlib.Path(__file__).with_name(
    "test_incident_crew66_vendor_roots_are_named_secrets.py"
)
_spec = importlib.util.spec_from_file_location("vendor_roots_harness", _sibling)
_h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_h)

_SHIM = (
    "import urllib.request, urllib.error, io\n"
    "class _R(io.BytesIO):\n"
    "    status = 200\n"
    "    def __enter__(self): return self\n"
    "    def __exit__(self, *a): return False\n"
    "def _open(req, timeout=30):\n"
    "    url = req.full_url\n"
    "    open({verify_log!r}, 'a').write(url.split('?')[0] + '\\n')\n"
    "    if 'api.deepseek.com' in url:\n"
    "        raise urllib.error.HTTPError(url, 402, 'Payment Required', {{}},\n"
    '            io.BytesIO(b\'{{"error":{{"message":"Insufficient Balance"}}}}\'))\n'
    "    if 'api.moonshot.ai' in url:\n"
    "        raise urllib.error.HTTPError(url, 404, 'Not Found', {{}}, io.BytesIO(b'no route'))\n"
    "    if 'api.minimax.io' in url:\n"
    "        key = req.get_header('Authorization').split(' ', 1)[1]\n"
    "        raise urllib.error.HTTPError(url, 401, 'Unauthorized', {{}},\n"
    "            io.BytesIO(('bad key ' + key).encode()))\n"
    "    return _R(b'{{}}')\n"
    "urllib.request.urlopen = _open\n"
)


def test_the_fail_line_carries_the_vendors_status_and_names_whose_fault_it_is(tmp_path):
    idp, log, site = _h._tree(tmp_path)
    verify_log = tmp_path / "verify.log"
    (site / "sitecustomize.py").write_text(_SHIM.format(verify_log=str(verify_log)))
    r = _h._run(idp, site, _h.FAKE)
    assert r.returncode == 1, r.stdout + r.stderr
    lines = {ln.split()[1]: ln for ln in r.stdout.splitlines() if ln.startswith("FAIL")}
    # no balance is the vendor's verdict on the account, not on the key
    assert "HTTP 402" in lines["deepseek"], lines["deepseek"]
    assert "Insufficient Balance" in lines["deepseek"], lines["deepseek"]
    assert "reports no balance" in lines["deepseek"], lines["deepseek"]
    # a 404 is our probe URL, and the line says so instead of blaming the key
    assert "HTTP 404" in lines["kimi"], lines["kimi"]
    assert "our probe URL is wrong" in lines["kimi"], lines["kimi"]
    # a 401 is the vendor refusing the key
    assert "HTTP 401" in lines["minimax"], lines["minimax"]
    assert "does not accept this key" in lines["minimax"], lines["minimax"]
    # the old one-word verdict and its wrong advice are gone
    assert "revoke it and make one that works" not in r.stdout
    # a vendor echoing the key back never reaches the log: the body head is scrubbed
    for value in _h.FAKE.values():
        assert value not in r.stdout and value not in r.stderr, "a root reached stdout"
    assert "bad key ***" in lines["minimax"], lines["minimax"]


def test_a_minimax_key_that_is_not_a_json_web_token_reaches_the_vendor(tmp_path):
    idp, log, site = _h._tree(tmp_path)
    verify_log = tmp_path / "verify.log"
    (site / "sitecustomize.py").write_text(_SHIM.format(verify_log=str(verify_log)))
    r = _h._run(idp, site, {**_h.FAKE, "SEED_MINIMAX_API_KEY": "sk-api-" + "q" * 40})
    # the shape no longer decides; the vendor's answer does
    assert "does not match the registry shape" not in r.stdout, r.stdout
    assert "https://api.minimax.io/v1/models" in verify_log.read_text()
