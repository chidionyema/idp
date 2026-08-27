"""crew#503: the GitHub App JWT is signed by openssl, never by a gh extension.

Incident: oke-check apply 33094153967, step `bin/idp-github-app installation`, printed
`unknown command "token" for "gh"`. The script minted the App JWT with `gh token generate`,
which is the Link-/gh-token extension; it was installed on the laptop and on no runner, so
every CI path through `token` and `installation` died after the founder's Install tap.

Guard: no `gh token` anywhere in bin/, and app_jwt() signs a JWT that openssl verifies with the
matching public key and whose claims name the App. No network: the key is minted here.
"""
import base64
import json
import pathlib
import re
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-github-app"


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def test_no_bin_file_calls_the_gh_token_extension():
    hits = [
        p.name
        for p in (ROOT / "bin").iterdir()
        if p.is_file() and re.search(r"\bgh token\b", p.read_text(errors="ignore"))
    ]
    assert hits == [], f"gh extensions do not exist on runners: {hits}"


def test_app_jwt_is_rs256_signed_and_verifies_with_openssl(tmp_path):
    key = tmp_path / "k.pem"
    pub = tmp_path / "k.pub"
    subprocess.run(["openssl", "genrsa", "-out", str(key), "2048"], check=True, capture_output=True)
    subprocess.run(["openssl", "rsa", "-in", str(key), "-pubout", "-out", str(pub)], check=True, capture_output=True)
    pem_b64 = base64.b64encode(key.read_bytes()).decode()
    # source only the helper functions (everything above the `case`), then call app_jwt
    src = SCRIPT.read_text().split("\ncase ", 1)[0]
    src = "\n".join(l for l in src.splitlines() if not l.startswith(("set -", "IDP=", "MAIN=", "D=", "cmd=")))
    out = subprocess.run(
        ["bash", "-c", src + '\napp_jwt "$1" "$2"', "_", "4740261", pem_b64],
        check=True, capture_output=True, text=True,
    ).stdout
    h, p, sig = out.split(".")
    assert json.loads(_b64url_decode(h)) == {"alg": "RS256", "typ": "JWT"}
    claims = json.loads(_b64url_decode(p))
    assert claims["iss"] == "4740261"
    now = int(time.time())
    assert now - 120 <= claims["iat"] <= now and now + 400 <= claims["exp"] <= now + 600
    (tmp_path / "sig").write_bytes(_b64url_decode(sig))
    (tmp_path / "hp").write_text(f"{h}.{p}")
    v = subprocess.run(
        ["openssl", "dgst", "-sha256", "-verify", str(pub), "-signature", str(tmp_path / "sig"), str(tmp_path / "hp")],
        capture_output=True, text=True,
    )
    assert v.returncode == 0 and "Verified OK" in v.stdout, v.stdout + v.stderr
    assert not list(tmp_path.glob("tmp.*")), "the decoded key file must not survive the call"
