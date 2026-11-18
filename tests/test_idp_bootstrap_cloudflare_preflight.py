"""The Cloudflare preflight must measure the road the live run takes (idp#8202).

THE DEFECT. `bin/idp-bootstrap-cloudflare --preflight` probed the DASHBOARD
(`https://dash.cloudflare.com/profile/api-tokens`) and nothing else. The live run does not use
the dashboard: on road a (R52) the standing root token comes from the environment and no
browser is driven at all. So the preflight answered a question the door never asks, and on the
CI runner -- where the dashboard answers 403 because it is behind the founder's login -- it
answered FAIL while saying nothing about the credential the live run would use.

Measured 2026-11-17 with the standing root: the estate's Cloudflare account
(4912457480997df81450b3ea614ccf3c) holds `mumchimp.com` only, and
`GET /zones?name=meridianlabs.cloud` answered `count: 0`. The zone the estate declares was not
a zone of the account the token names -- and the preflight said "console answers 403". An
operator reading that could not tell a broken credential path from a wrong account, and the
live path's own refusal ("$ZONE is not a zone of this account") was never reached.

THE FIX. On road a the preflight measures the API the door will use: the root token verifies,
and the account is asked whether it holds the declared zone. If it does not, the preflight
names the zones the account DOES hold -- and says so as a FAIL, because a zone that is not in
the account cannot be minted for. On road b (no root token in the environment) the console is
the road -- the root is born there -- so the console probe stays.

THE FALSIFIER. This test builds a synthetic tree (the real script, stub OCI/vault doors), a fake
Cloudflare API and a fake console that answers 403, and runs the real script against it:

  1. the account HOLDS the zone   -> exit 0, the zone named   (the old script: FAIL, "403")
  2. the account does NOT hold it  -> exit 1, "not a zone of this account", and the zones the
     account DOES hold are named -- never "answers 403"
  3. no root token in the env     -> the console is still the road: "answers 403"

Case 1 fails on the pre-fix tree, which is what makes this a falsifier rather than a
description.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "bin" / "idp-bootstrap-cloudflare"
ZONE = "meridianlabs.cloud"


# --------------------------------------------------------------------------- the fake provider


class _Provider:
    """A Cloudflare-shaped API and a console that answers 403."""

    def __init__(self, zones: list[dict]) -> None:
        self.zones = zones
        self.server = HTTPServer(("127.0.0.1", 0), self._handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def _handler(self):  # noqa: ANN202 -- a class factory
        zones = self.zones

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:  # silence the stderr spam
                return

            def _send(self, code: int, body: dict) -> None:
                raw = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:  # noqa: N802 -- http.server's name
                path = self.path
                if path.startswith("/client/v4/user/tokens/verify"):
                    self._send(200, {"success": True, "result": {"status": "active"}})
                    return
                if path.startswith("/client/v4/zones"):
                    name = ""
                    if "name=" in path:
                        name = path.split("name=", 1)[1].split("&", 1)[0]
                    found = [z for z in zones if not name or z["name"] == name]
                    self._send(200, {"success": True, "result": found})
                    return
                # The console: login-gated, exactly as the runner sees it.
                self._send(403, {"success": False, "errors": [{"code": 9109}]})

        return Handler


# --------------------------------------------------------------------------- the synthetic tree


def _tree(tmp: Path) -> Path:
    """A tree where the real script runs against stub OCI and vault doors."""
    root = tmp / "idp"
    (root / "bin").mkdir(parents=True)
    shutil.copy2(SCRIPT, root / "bin" / "idp-bootstrap-cloudflare")
    os.chmod(root / "bin" / "idp-bootstrap-cloudflare", 0o755)

    (root / "bin" / "idp-oci-whoami").write_text(
        "#!/bin/sh\necho estate\n", encoding="utf-8"
    )
    (root / "bin" / "idp-vault-put").write_text(
        "#!/bin/sh\necho 'ok vault reachable'\nexit 0\n", encoding="utf-8"
    )
    for stub in ("idp-oci-whoami", "idp-vault-put"):
        os.chmod(root / "bin" / stub, 0o755)

    cfg = root / "clusters" / "oke"
    cfg.mkdir(parents=True)
    (cfg / "estate-config.yaml").write_text(
        "data:\n  ESTATE_ZONE: " + ZONE + "\n", encoding="utf-8"
    )

    # The browser road's driver: a fake venv python so no test ever installs playwright.
    venv = tmp / "home" / "bootstrap-venv" / "bin"
    venv.mkdir(parents=True)
    fake = venv / "python"
    fake.write_text(
        "#!/bin/sh\ncase \"$*\" in\n"
        "  *importlib*) echo '0.0.0-fake' ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    os.chmod(fake, 0o755)
    return root


def _run(root: Path, home: Path, provider: _Provider, root_token: str | None):
    env = dict(os.environ)
    env["ESTATE_HOME"] = str(home)
    env["CLOUDFLARE_API_URL"] = f"{provider.base}/client/v4"
    env["CLOUDFLARE_CONSOLE_URL"] = f"{provider.base}/console"
    env.pop("CLOUDFLARE_ROOT_TOKEN", None)
    if root_token is not None:
        env["CLOUDFLARE_ROOT_TOKEN"] = root_token
    done = subprocess.run(
        ["bash", str(root / "bin" / "idp-bootstrap-cloudflare"), "--preflight"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return done


# --------------------------------------------------------------------------- the three cases


def test_the_account_holding_the_zone_passes_even_though_the_console_answers_403(tmp_path):
    provider = _Provider(
        [{"id": "zone-id-1", "name": ZONE, "account": {"id": "acct-1"}}]
    )
    try:
        root = _tree(tmp_path)
        done = _run(root, tmp_path / "home", provider, "root-token")
    finally:
        provider.stop()
    out = done.stdout + done.stderr
    assert done.returncode == 0, f"the preflight refused a zone it can reach:\n{out}"
    assert f"zone {ZONE} is a zone of this account" in out, out
    assert "answers 403" not in out, (
        "the preflight still judges the dashboard, which the live road never opens:\n" + out
    )


def test_a_zone_the_account_does_not_hold_is_a_fail_naming_the_zones_it_does_hold(tmp_path):
    provider = _Provider(
        [{"id": "zone-id-2", "name": "mumchimp.com", "account": {"id": "acct-1"}}]
    )
    try:
        root = _tree(tmp_path)
        done = _run(root, tmp_path / "home", provider, "root-token")
    finally:
        provider.stop()
    out = done.stdout + done.stderr
    assert done.returncode == 1, f"a missing zone must fail, not pass:\n{out}"
    assert f"{ZONE} is not a zone of this account" in out, out
    assert "mumchimp.com" in out, f"the preflight must name what the account DOES hold:\n{out}"
    assert "answers 403" not in out, (
        "the verdict must be about the zone, not about a console:\n" + out
    )


def test_without_a_root_token_the_console_is_still_the_road(tmp_path):
    """Road b: the root is born in the dashboard, so the dashboard is what is measured."""
    provider = _Provider(
        [{"id": "zone-id-1", "name": ZONE, "account": {"id": "acct-1"}}]
    )
    try:
        root = _tree(tmp_path)
        done = _run(root, tmp_path / "home", provider, None)
    finally:
        provider.stop()
    out = done.stdout + done.stderr
    assert done.returncode == 1, f"an unreachable console must fail:\n{out}"
    assert "answers 403" in out, out
