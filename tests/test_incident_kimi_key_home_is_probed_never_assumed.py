"""Incident, 2026-09-03 (apply run 33696669868, job 100467823768; then the founder's aider session):
the founder's Kimi key read `refused by https://api.moonshot.ai/v1/models: HTTP 401 Incorrect API key`
and the router lane `kimi` answered every caller with the same words. The key was not dead. A Kimi
key has one of three homes (the open platform's global host, the Kimi Code membership host, the
open platform's China host) and answers only at its own; the vendor's FAQ says so. Our probe asked
one host and called the answer a bad key: the fix-proved-on-the-wrong-surface class.

Now the registry lists every home, the probe walks them, and the host that accepts the key is
written beside it as MOONSHOT_API_BASE, which LiteLLM's moonshot adapter reads from the
environment. Nobody is asked where the key was made, and a refusal names every host's answer.
"""

import importlib.util
import pathlib

_sibling = pathlib.Path(__file__).with_name(
    "test_incident_crew66_vendor_roots_are_named_secrets.py"
)
_spec = importlib.util.spec_from_file_location("vendor_roots_harness", _sibling)
_h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_h)

KIMI = _h.REG["kimi"]

# the global host refuses the key, the membership host accepts it, the China host is never asked
_SHIM = (
    "import urllib.request, urllib.error, io\n"
    "class _R(io.BytesIO):\n"
    "    status = 200\n"
    "    def __enter__(self): return self\n"
    "    def __exit__(self, *a): return False\n"
    "def _open(req, timeout=30):\n"
    "    url = req.full_url\n"
    "    open({verify_log!r}, 'a').write(url.split('?')[0] + '\\n')\n"
    "    if 'api.moonshot.ai' in url or 'api.moonshot.cn' in url:\n"
    "        raise urllib.error.HTTPError(url, 401, 'Unauthorized', {{}},\n"
    '            io.BytesIO(b\'{{"error":{{"message":"Incorrect API key provided"}}}}\'))\n'
    "    return _R(b'{{}}')\n"
    "urllib.request.urlopen = _open\n"
)


def test_the_registry_names_every_home_a_kimi_key_can_have():
    assert KIMI["bases"] == [
        "https://api.moonshot.ai/v1",
        "https://api.kimi.com/coding/v1",
        "https://api.moonshot.cn/v1",
    ], KIMI["bases"]
    assert KIMI["verify"]["url"].startswith("{base}/"), KIMI["verify"]["url"]
    derived = [t for t in KIMI["targets"] if t.get("derived") == "base"]
    assert derived == [
        {"entry": "litellm-upstream", "field": "MOONSHOT_API_BASE", "derived": "base"}
    ], KIMI["targets"]


def test_a_key_refused_at_one_home_is_tried_at_the_next_and_its_home_is_written(
    tmp_path,
):
    idp, log, site = _h._tree(tmp_path)
    verify_log = tmp_path / "verify.log"
    (site / "sitecustomize.py").write_text(_SHIM.format(verify_log=str(verify_log)))
    r = _h._run(
        idp, site, {"SEED_KIMI_API_KEY": _h.FAKE["SEED_KIMI_API_KEY"]}, "--only", "kimi"
    )
    assert r.returncode == 0, r.stdout + r.stderr
    line = next(ln for ln in r.stdout.splitlines() if " kimi " in ln)
    assert line.startswith("ok"), line
    assert "verified at https://api.kimi.com/coding/v1" in line, line
    asked = verify_log.read_text().splitlines()
    assert asked == [
        "https://api.moonshot.ai/v1/models",
        "https://api.kimi.com/coding/v1/models",
    ], asked
    puts = log.read_text().splitlines()
    assert (
        f"put --merge litellm-upstream MOONSHOT_API_KEY=V_KEY {_h.FAKE['SEED_KIMI_API_KEY']}"
        in puts
    ), puts
    assert (
        "put --merge litellm-upstream MOONSHOT_API_BASE=V_KEY https://api.kimi.com/coding/v1"
        in puts
    ), puts
    assert _h.FAKE["SEED_KIMI_API_KEY"] not in r.stdout, "a root reached stdout"


def test_a_key_refused_at_every_home_names_every_answer(tmp_path):
    idp, log, site = _h._tree(tmp_path)
    verify_log = tmp_path / "verify.log"
    shim = _SHIM.replace(
        "'api.moonshot.ai' in url or 'api.moonshot.cn' in url", "'api.' in url"
    )
    (site / "sitecustomize.py").write_text(shim.format(verify_log=str(verify_log)))
    r = _h._run(
        idp, site, {"SEED_KIMI_API_KEY": _h.FAKE["SEED_KIMI_API_KEY"]}, "--only", "kimi"
    )
    assert r.returncode == 1, r.stdout + r.stderr
    line = next(ln for ln in r.stdout.splitlines() if " kimi " in ln)
    assert line.startswith("FAIL"), line
    for home in KIMI["bases"]:
        assert f"({home})" in line, line
    assert "HTTP 401" in line and "does not accept this key" in line, line
    assert not log.exists() or "MOONSHOT" not in log.read_text(), (
        "a refused key was written"
    )
