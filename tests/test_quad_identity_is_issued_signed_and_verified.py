"""idp#8336: an agent's identity is issued by the estate, signed by its session, checked by the door.

Before: identity was a hand-typed `Agent:` line; 0 of the last 100 idp main commits carried one
anyone could verify. Each case builds a real git commit and a real RSA issuer key; every test
fails on main, where bin/quad does not exist.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
QUAD = ROOT / "bin" / "quad"
_loader = importlib.machinery.SourceFileLoader("quad_mod", str(QUAD))
_spec = importlib.util.spec_from_loader("quad_mod", _loader)
quad = importlib.util.module_from_spec(_spec)
_loader.exec_module(quad)


def _run(*args: str, cwd: Path, stdin: bytes | None = None) -> str:
    return subprocess.run(
        list(args), cwd=cwd, input=stdin, capture_output=True, check=True
    ).stdout.decode()


@pytest.fixture()
def world(tmp_path: Path):
    issuer = tmp_path / "issuer.pem"
    _run("openssl", "genrsa", "-out", str(issuer), "2048", cwd=tmp_path)
    pub = _run("openssl", "rsa", "-in", str(issuer), "-pubout", cwd=tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _run("git", "init", "-q", cwd=repo)
    _run("git", "config", "user.email", "a@b", cwd=repo)
    _run("git", "config", "user.name", "agent", cwd=repo)
    (repo / "f.txt").write_text("one\n")
    _run("git", "add", "f.txt", cwd=repo)
    _run("git", "commit", "-q", "-m", "base", cwd=repo)
    key = tmp_path / "session.key"
    pubkey = _run("python3", str(QUAD), "keygen", "--out", str(key), cwd=repo).strip()
    cert = tmp_path / "cert.json"
    cert.write_text(
        _run(
            "python3",
            str(QUAD),
            "issue",
            "--agent",
            "agent-x",
            "--model",
            "m-1",
            "--pubkey",
            pubkey,
            "--session",
            "s-1",
            "--key",
            str(issuer),
            cwd=repo,
        )
    )
    return {"repo": repo, "key": key, "cert": cert, "pub": pub}


def _commit(w, subject: str, sign: bool = True) -> str:
    repo = w["repo"]
    (repo / "f.txt").write_text((repo / "f.txt").read_text() + subject + "\n")
    _run("git", "add", "f.txt", cwd=repo)
    msg = repo.parent / "msg.txt"
    msg.write_text(f"{subject}\n\nAgent: agent-x\n")
    if sign:
        _run(
            "python3",
            str(QUAD),
            "sign-message",
            str(msg),
            "--key",
            str(w["key"]),
            "--cert",
            str(w["cert"]),
            cwd=repo,
        )
    _run("git", "commit", "-q", "-F", str(msg), cwd=repo)
    return _run("git", "rev-parse", "HEAD", cwd=repo).strip()


def _verdict(w, sha: str, pub: str | None = None) -> dict:
    issuer = w["repo"].parent / "issuer.pub.pem"
    issuer.write_text(pub or w["pub"])
    out = _run(
        "python3", str(QUAD), "verify", sha, "--issuer", str(issuer), cwd=w["repo"]
    )
    return json.loads(out)


def test_an_issued_signed_commit_is_verified_with_its_identity(world):
    v = _verdict(world, _commit(world, "work"))
    assert v["verdict"] == "verified", v
    assert (v["agent"], v["model"], v["session"]) == ("agent-x", "m-1", "s-1")


def test_a_typed_agent_line_is_not_an_identity(world):
    assert (
        _verdict(world, _commit(world, "typed", sign=False))["verdict"]
        == "unidentified"
    )


def test_a_certificate_from_another_issuer_is_forged(world, tmp_path):
    other = tmp_path / "other.pem"
    _run("openssl", "genrsa", "-out", str(other), "2048", cwd=tmp_path)
    other_pub = _run("openssl", "rsa", "-in", str(other), "-pubout", cwd=tmp_path)
    v = _verdict(world, _commit(world, "work"), pub=other_pub)
    assert v["verdict"] == "forged" and "issuer" in v["reason"]


def test_a_signature_moved_to_other_content_is_forged(world):
    sha = _commit(world, "work")
    repo = world["repo"]
    msg = _run("git", "log", "-1", "--format=%B", sha, cwd=repo)
    (repo / "f.txt").write_text("tampered\n")
    _run("git", "add", "f.txt", cwd=repo)
    _run("git", "commit", "-q", "-m", msg, cwd=repo)
    tampered = _run("git", "rev-parse", "HEAD", cwd=repo).strip()
    v = _verdict(world, tampered)
    assert v["verdict"] == "forged" and "session" in v["reason"]


def test_an_edited_certificate_is_forged(world):
    packed = json.loads(world["cert"].read_text())
    packed["cert"]["agent"] = "someone-else"
    world["cert"].write_text(json.dumps(packed))
    assert _verdict(world, _commit(world, "work"))["verdict"] == "forged"


def test_the_estate_hook_trailers_do_not_break_the_proof(world):
    sha = _commit(world, "work")
    repo = world["repo"]
    msg = _run("git", "log", "-1", "--format=%B", sha, cwd=repo) + "X-Idp-Signed: abc\n"
    _run("git", "commit", "-q", "--amend", "-m", msg, cwd=repo)
    head = _run("git", "rev-parse", "HEAD", cwd=repo).strip()
    assert _verdict(world, head)["verdict"] == "verified"


def test_ed25519_matches_rfc_8032_vector_1():
    seed = bytes.fromhex(
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
    )
    assert quad.ed_public(seed).hex() == (
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    )
    assert quad.ed_verify(quad.ed_public(seed), b"", quad.ed_sign(seed, b""))


def test_the_estate_issues_and_the_door_checks_without_refusing_yet():
    import yaml

    issue = (ROOT / ".github/workflows/quad-issue.yml").read_text()
    flow = yaml.safe_load(issue)
    on = flow.get("on", flow.get(True))
    assert set(on["workflow_dispatch"]["inputs"]) == {
        "agent",
        "model",
        "session",
        "pubkey",
    }
    assert "refs/quad/certs/" in issue and "refs/quad/by-key/" in issue
    assert 'rm -f "$RUNNER_TEMP/issuer.pem"' in issue, (
        "the issuer key never outlives the step"
    )
    door = yaml.safe_load((ROOT / ".github/workflows/submit-gate.yml").read_text())
    ident = door["jobs"]["identity"]
    script = "\n".join(s.get("run", "") for s in ident["steps"])
    assert "bin/quad verify" in script
    assert "exit 1" not in script, "phase 1 reports; phase 2 refuses"
    assert door["jobs"]["promote"]["needs"] == "gate", (
        "identity does not gate promotion yet"
    )
