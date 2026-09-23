"""Incident, measured on apply run 33677001751 (2026-09-02): the deepseek key was refused
by its vendor API and bin/idp-bootstrap-vendors exited on the spot, so the apprise
telegram pair five vendors later -- the exact entry the notify stack was waiting on --
was never seeded. One dead vendor key must not block every vendor behind it: a FAIL is
recorded, the loop finishes, the exit is still 1 and the summary still names the count,
so nothing reads green that is not.
"""

import importlib.util
import pathlib

_sibling = pathlib.Path(__file__).with_name(
    "test_incident_crew66_vendor_roots_are_named_secrets.py"
)
_spec = importlib.util.spec_from_file_location("vendor_roots_harness", _sibling)
_h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_h)


def test_one_refused_vendor_still_seeds_every_vendor_behind_it(tmp_path):
    idp, log, site = _h._tree(tmp_path)
    # the sibling's shim answers 200 to everything; this one refuses deepseek only,
    # the same way the vendor API refused the real key
    (site / "sitecustomize.py").write_text(
        "import urllib.request, urllib.error, io\n"
        "class _R(io.BytesIO):\n"
        "    status = 200\n"
        "    def __enter__(self): return self\n"
        "    def __exit__(self, *a): return False\n"
        "def _open(req, timeout=30):\n"
        "    url = req.full_url\n"
        "    if 'api.deepseek.com' in url:\n"
        "        raise urllib.error.HTTPError(url, 401, 'refused', {}, io.BytesIO(b''))\n"
        "    return _R(b'{}')\n"
        "urllib.request.urlopen = _open\n"
    )
    r = _h._run(idp, site, _h.FAKE)
    # the failure is still loud: exit 1, the vendor named, the summary counting it
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL    deepseek" in r.stdout, r.stdout
    assert "1 failed" in r.stdout, r.stdout
    # and every vendor behind the dead one was still handled: the apprise pair -- the
    # entry the notify stack reads -- reached the vault writer
    puts = log.read_text()
    assert "put --merge notify-apprise-founder-telegram token" in puts, puts
    assert "put --merge notify-apprise-founder-telegram chat" in puts, puts
    # no value leaked on the way through
    for value in _h.FAKE.values():
        assert value not in r.stdout and value not in r.stderr, "a root reached stdout"
