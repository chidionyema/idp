"""Proof for the Gemini -> Drive -> idp submit lane (claim chidionyema/idp#8702).

Every test drives the REAL compiled verifier (`meridian-outbox-ingest`), real git (a bare local
origin) and the real `platform/meridian-core-engines/scripts/gemini-outbox-pull` pipeline against a fake Drive v3 server that checks
the bearer token, paginates and can inject 503s and upload failures. Each gate has a known-bad
input it must refuse and a known-good one it must accept (AGENTS.md section 9, principle 1).

The binary comes from $MERIDIAN_OUTBOX_INGEST, else is built with cargo; if neither works the
tests FAIL -- a lane test that cannot run its verifier must not look green.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PULL = ROOT / "platform" / "meridian-core-engines" / "scripts" / "gemini-outbox-pull"
WORKSPACE = ROOT / "platform" / "meridian-core-engines"
TOKEN = "test-token-DO-NOT-LEAK-0123456789"  # noqa: S105 -- a fake, asserted never to reach output
FOLDER = "folder-outbox"

_loader = importlib.machinery.SourceFileLoader("gemini_outbox_pull", str(PULL))
_spec = importlib.util.spec_from_loader("gemini_outbox_pull", _loader)
pull = importlib.util.module_from_spec(_spec)
_loader.exec_module(pull)


# ------------------------------------------------------------------ the verifier binary


@pytest.fixture(scope="session")
def ingest_bin() -> pathlib.Path:
    env = os.environ.get("MERIDIAN_OUTBOX_INGEST")
    if env:
        p = pathlib.Path(env)
        assert p.is_file(), f"MERIDIAN_OUTBOX_INGEST={env} is not a file"
        return p
    proc = subprocess.run(
        ["cargo", "build", "--release", "--locked", "-p", "meridian-outbox-ingest"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert proc.returncode == 0, f"cargo build failed:\n{proc.stderr[-2000:]}"
    p = WORKSPACE / "target" / "release" / "meridian-outbox-ingest"
    assert p.is_file(), "built binary missing"
    return p


# ------------------------------------------------------------------ fake Drive v3


class FakeDrive:
    PAGE = 2

    def __init__(self) -> None:
        self.files: Dict[str, Dict[str, Any]] = {}
        self.seq = 0
        self.fail_next = 0  # answer this many requests with 503 first
        self.fail_uploads = False
        self.bad_token_seen = 0
        self.requests: List[Tuple[str, str]] = []
        self.add(
            FOLDER,
            "Meridian-Submit-Outbox",
            [],
            b"",
            "application/vnd.google-apps.folder",
        )

    def add(
        self,
        fid: str,
        name: str,
        parents: List[str],
        data: bytes,
        mime: str = "application/octet-stream",
    ) -> str:
        self.files[fid] = {
            "id": fid,
            "name": name,
            "parents": parents,
            "data": data,
            "mimeType": mime,
        }
        return fid

    def put(self, name: str, data: bytes, parent: str = FOLDER) -> str:
        self.seq += 1
        return self.add(f"f{self.seq}", name, [parent], data)

    def receipts(self) -> Dict[str, Dict[str, Any]]:
        folders = [f["id"] for f in self.files.values() if f["name"] == "receipts"]
        out = {}
        for f in self.files.values():
            if (
                f["parents"]
                and f["parents"][0] in folders
                and f["name"].startswith("RECEIPT_")
            ):
                out[f["name"]] = json.loads(f["data"])
        return out

    @staticmethod
    def _lit(m: "re.Match[str]") -> str:
        return re.sub(r"\\(.)", r"\1", m.group(1))

    def query(self, q: str) -> List[Dict[str, Any]]:
        lit = r"'((?:\\.|[^'\\])*)'"
        out = []
        for f in self.files.values():
            ok = "trashed = false" in q or True
            m = re.search(lit + r" in parents", q)
            if m and self._lit(m) not in f["parents"]:
                ok = False
            m = re.search(r"name = " + lit, q)
            if m and f["name"] != self._lit(m):
                ok = False
            m = re.search(r"name contains " + lit, q)
            if m and self._lit(m) not in f["name"]:
                ok = False
            m = re.search(r"mimeType = " + lit, q)
            if m and f["mimeType"] != self._lit(m):
                ok = False
            m = re.search(r"mimeType != " + lit, q)
            if m and f["mimeType"] == self._lit(m):
                ok = False
            if ok:
                out.append(f)
        return sorted(out, key=lambda f: f["id"])


def make_handler(drive: FakeDrive):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a: Any) -> None:
            pass

        def _auth(self) -> bool:
            drive.requests.append((self.command, self.path.split("?")[0]))
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                drive.bad_token_seen += 1
                self._send(401, b'{"error":"unauthorized"}')
                return False
            if drive.fail_next > 0:
                drive.fail_next -= 1
                self._send(503, b'{"error":"busy"}')
                return False
            return True

        def _send(
            self, code: int, body: bytes, ctype: str = "application/json"
        ) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if not self._auth():
                return
            u = urlparse(self.path)
            qs = parse_qs(u.query)
            m = re.match(r"^/drive/v3/files/([^/]+)$", u.path)
            if m:
                f = drive.files.get(m.group(1))
                if not f or qs.get("alt") != ["media"]:
                    return self._send(404, b"{}")
                return self._send(200, f["data"], "application/octet-stream")
            if u.path == "/drive/v3/files":
                hits = drive.query(qs["q"][0])
                start = int(qs.get("pageToken", ["0"])[0])
                page = hits[start : start + drive.PAGE]
                body: Dict[str, Any] = {
                    "files": [
                        {k: f[k] for k in ("id", "name", "mimeType")} for f in page
                    ]
                }
                if start + drive.PAGE < len(hits):
                    body["nextPageToken"] = str(start + drive.PAGE)
                return self._send(200, json.dumps(body).encode())
            self._send(404, b"{}")

        def do_POST(self) -> None:
            if not self._auth():
                return
            n = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(n)
            u = urlparse(self.path)
            if u.path == "/drive/v3/files":
                meta = json.loads(raw)
                fid = drive.put(meta["name"], b"", meta["parents"][0])
                drive.files[fid]["mimeType"] = meta["mimeType"]
                return self._send(200, json.dumps({"id": fid}).encode())
            if u.path == "/upload/drive/v3/files" and parse_qs(u.query).get(
                "uploadType"
            ) == ["multipart"]:
                if drive.fail_uploads:
                    return self._send(400, b'{"error":"rejected"}')
                boundary = re.search(
                    r"boundary=(\S+)", self.headers["Content-Type"]
                ).group(1)
                parts = [
                    p
                    for p in raw.decode().split(f"--{boundary}")
                    if p.strip() not in ("", "--")
                ]
                meta = json.loads(parts[0].split("\r\n\r\n", 1)[1].strip())
                payload = parts[1].split("\r\n\r\n", 1)[1].rstrip("\r\n")
                fid = drive.put(meta["name"], payload.encode(), meta["parents"][0])
                return self._send(200, json.dumps({"id": fid}).encode())
            self._send(404, b"{}")

    return H


@pytest.fixture()
def drive():
    d = FakeDrive()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(d))
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    d.base = f"http://127.0.0.1:{srv.server_address[1]}"
    yield d
    srv.shutdown()
    srv.server_close()


def source_for(drive: FakeDrive, token: str = TOKEN):
    client = pull.DriveClient(
        token, api=drive.base + "/drive/v3", upload=drive.base + "/upload/drive/v3"
    )
    return pull.DriveSource(client, FOLDER)


# ------------------------------------------------------------------ git origin + repo


@pytest.fixture(autouse=True)
def hermetic_git(monkeypatch):
    """No machine hooks, no global config: the temp repos behave the same everywhere."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GEMINI_PULL_NO_SLEEP", "1")
    for k in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{k}_NAME", "t")
        monkeypatch.setenv(f"GIT_{k}_EMAIL", "t@example.invalid")


def sh(*args: str, cwd: pathlib.Path) -> str:
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    assert p.returncode == 0, f"{args} -> {p.stderr}"
    return p.stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    origin = tmp_path / "origin.git"
    sh("git", "init", "--bare", "-q", "-b", "main", str(origin), cwd=tmp_path)
    seed = tmp_path / "seed"
    sh("git", "clone", "-q", str(origin), str(seed), cwd=tmp_path)
    (seed / "README.md").write_text("seed\n")
    sh("git", "add", "-A", cwd=seed)
    sh("git", "commit", "-q", "-m", "seed", cwd=seed)
    sh("git", "push", "-q", "origin", "HEAD:refs/heads/main", cwd=seed)
    work = tmp_path / "work"
    sh("git", "clone", "-q", str(origin), str(work), cwd=tmp_path)
    return work


def branches(repo: pathlib.Path) -> List[str]:
    out = sh("git", "ls-remote", "--heads", "origin", cwd=repo)
    return sorted(line.split("refs/heads/")[1] for line in out.splitlines())


# ------------------------------------------------------------------ packet helpers


def zip_bytes(members: Dict[str, str], symlink: Optional[str] = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, body in members.items():
            zf.writestr(name, body)
        if symlink:
            zi = zipfile.ZipInfo(symlink)
            zi.external_attr = 0o120777 << 16
            zf.writestr(zi, "/etc/passwd")
    return buf.getvalue()


def now_utc(minutes_ago: int = 0) -> str:
    return (
        dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def packet(pid: str, arts: List[Tuple[str, bytes, str]], **over: Any) -> Dict[str, Any]:
    p = {
        "schema": "meridian.gemini-packet.v1",
        "packet_id": pid,
        "created_utc": now_utc(),
        "source_surface": "gemini-web",
        "target_repo": "chidionyema/idp",
        "target_branch_prefix": "submit/gemini-",
        "claim_issue": "chidionyema/idp#8702",
        "ship_contract_accept_url": "https://llm.meridianlabs.cloud/health",
        "artifacts": [
            {
                "filename": n,
                "sha256": hashlib.sha256(b).hexdigest(),
                "bytes": len(b),
                "target_subdir": sub,
            }
            for n, b, sub in arts
        ],
    }
    p.update(over)
    return p


def seed(drive: FakeDrive, pkt: Dict[str, Any], blobs: Dict[str, bytes]) -> None:
    drive.put(f"PACKET_{pkt['packet_id']}.json", json.dumps(pkt).encode())
    for n, b in blobs.items():
        drive.put(n, b)


GOOD_ZIP = zip_bytes({"crates/demo/src/lib.rs": "pub fn ok() -> u8 { 1 }\n"})


def good_packet(
    drive: FakeDrive, pid: str = "20261128-lane-ok", **over: Any
) -> Dict[str, Any]:
    art = f"{pid}.zip"  # unique per packet: two Drive files with one name are refused as ambiguous
    pkt = packet(pid, [(art, GOOD_ZIP, "intake/demo")], **over)
    seed(drive, pkt, {art: GOOD_ZIP})
    return pkt


def run(drive, ingest_bin, repo, push=True, only=""):
    return pull.run(source_for(drive), ingest_bin, repo, push, only)


# ------------------------------------------------------------------ the tests


def test_drive_ingest_pushes_submit_branch_and_uploads_receipt(
    drive, ingest_bin, repo, capsys
):
    good_packet(drive)
    main_before = sh("git", "rev-parse", "origin/main", cwd=repo)
    assert run(drive, ingest_bin, repo) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["results"][0]["verdict"] == "INGESTED_READY_FOR_SUBMIT"

    assert branches(repo) == ["main", "submit/gemini-20261128-lane-ok"]
    sha = sh(
        "git",
        "ls-remote",
        "origin",
        "refs/heads/submit/gemini-20261128-lane-ok",
        cwd=repo,
    ).split()[0]
    sh("git", "fetch", "-q", "origin", "submit/gemini-20261128-lane-ok", cwd=repo)
    msg = sh("git", "log", "-1", "--format=%B", sha, cwd=repo).splitlines()
    assert "Claim: chidionyema/idp#8702" in msg and "Agent: gemini-outbox" in msg
    files = sh("git", "ls-tree", "-r", "--name-only", sha, cwd=repo).splitlines()
    assert (
        "intake/demo/crates/demo/src/lib.rs" in files
        and "intake/demo/20261128-lane-ok.zip" in files
    )
    assert sh(
        "git", "diff", "--name-only", "origin/main", sha, cwd=repo
    ).splitlines() == sorted(f for f in files if f.startswith("intake/"))
    assert (
        sh("git", "ls-remote", "origin", "refs/heads/main", cwd=repo).split()[0]
        == main_before
    )

    rcpt = drive.receipts()["RECEIPT_20261128-lane-ok.json"]
    assert rcpt["verdict"] == "INGESTED_READY_FOR_SUBMIT" and rcpt["commit_sha"] == sha
    assert (
        rcpt["verified_artifacts"][0]["landed_sha256"]
        == hashlib.sha256(GOOD_ZIP).hexdigest()
    )
    assert drive.bad_token_seen == 0


def test_second_run_is_already_ingested_with_no_duplicate_branch(
    drive, ingest_bin, repo, capsys
):
    good_packet(drive)
    assert run(drive, ingest_bin, repo) == 0
    capsys.readouterr()
    sha1 = sh(
        "git",
        "ls-remote",
        "origin",
        "refs/heads/submit/gemini-20261128-lane-ok",
        cwd=repo,
    ).split()[0]
    uploads_before = sum(1 for m, p in drive.requests if m == "POST")
    assert run(drive, ingest_bin, repo) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["results"][0]["verdict"] == "ALREADY_INGESTED"
    assert branches(repo) == ["main", "submit/gemini-20261128-lane-ok"]
    assert (
        sh(
            "git",
            "ls-remote",
            "origin",
            "refs/heads/submit/gemini-20261128-lane-ok",
            cwd=repo,
        ).split()[0]
        == sha1
    )
    assert sum(1 for m, p in drive.requests if m == "POST") == uploads_before


def test_failed_receipt_upload_is_retried_without_a_second_push(
    drive, ingest_bin, repo, capsys
):
    good_packet(drive)
    drive.fail_uploads = True
    assert run(drive, ingest_bin, repo) == 3  # transport failure: nothing receipted
    capsys.readouterr()
    sha1 = sh(
        "git",
        "ls-remote",
        "origin",
        "refs/heads/submit/gemini-20261128-lane-ok",
        cwd=repo,
    ).split()[0]
    assert drive.receipts() == {}
    drive.fail_uploads = False
    assert run(drive, ingest_bin, repo) == 0
    assert (
        sh(
            "git",
            "ls-remote",
            "origin",
            "refs/heads/submit/gemini-20261128-lane-ok",
            cwd=repo,
        ).split()[0]
        == sha1
    )
    assert drive.receipts()["RECEIPT_20261128-lane-ok.json"]["commit_sha"] == sha1


def _expect_rejected(drive, ingest_bin, repo, capsys, pid, reason_prefix):
    assert run(drive, ingest_bin, repo) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["results"][0]["verdict"] == "REJECTED", out
    assert out["results"][0]["reason"].startswith(reason_prefix), out
    assert branches(repo) == ["main"], "a rejected packet must never create a branch"
    assert drive.receipts()[f"RECEIPT_{pid}.json"]["verdict"] == "REJECTED"


def test_tampered_artifact_is_rejected(drive, ingest_bin, repo, capsys):
    pkt = packet("20261128-bad-sha", [("demo.zip", GOOD_ZIP, "intake/demo")])
    pkt["artifacts"][0]["sha256"] = "0" * 64
    seed(drive, pkt, {"demo.zip": GOOD_ZIP})
    _expect_rejected(
        drive, ingest_bin, repo, capsys, "20261128-bad-sha", "LANDED_DIGEST_MISMATCH"
    )


def test_zip_slip_is_rejected_before_any_staging(
    drive, ingest_bin, repo, capsys, tmp_path
):
    evil = zip_bytes({"../escape.txt": "boom"})
    pkt = packet("20261128-evil", [("evil.zip", evil, "intake/evil")])
    seed(drive, pkt, {"evil.zip": evil})
    _expect_rejected(
        drive, ingest_bin, repo, capsys, "20261128-evil", "ZIP_SLIP_OR_SPECIAL_MEMBER"
    )
    assert not (tmp_path / "escape.txt").exists()


def test_zip_symlink_member_is_rejected(drive, ingest_bin, repo, capsys):
    link = zip_bytes({"ok.txt": "x"}, symlink="evil-link")
    pkt = packet("20261128-link", [("link.zip", link, "intake/link")])
    seed(drive, pkt, {"link.zip": link})
    _expect_rejected(
        drive, ingest_bin, repo, capsys, "20261128-link", "ZIP_SLIP_OR_SPECIAL_MEMBER"
    )


def test_later_bad_artifact_leaves_nothing_from_earlier_ones(
    drive, ingest_bin, repo, capsys
):
    evil = zip_bytes({"../x": "y"})
    pkt = packet(
        "20261128-mixed",
        [("demo.zip", GOOD_ZIP, "intake/ok"), ("evil.zip", evil, "intake/evil")],
    )
    seed(drive, pkt, {"demo.zip": GOOD_ZIP, "evil.zip": evil})
    _expect_rejected(
        drive, ingest_bin, repo, capsys, "20261128-mixed", "ZIP_SLIP_OR_SPECIAL_MEMBER"
    )


def test_proxy_green_accept_url_is_rejected(drive, ingest_bin, repo, capsys):
    pkt = packet(
        "20261128-proxy",
        [("demo.zip", GOOD_ZIP, "intake/demo")],
        ship_contract_accept_url="https://api.github.com/repos/chidionyema/idp/commits/main",
    )
    seed(drive, pkt, {"demo.zip": GOOD_ZIP})
    _expect_rejected(
        drive, ingest_bin, repo, capsys, "20261128-proxy", "PROXY_GREEN_URL_REJECTED"
    )


@pytest.mark.parametrize(
    "sub", [".github/workflows", "bin", "platform/estate/intents", "intake/../bin"]
)
def test_target_outside_intake_is_rejected(drive, ingest_bin, repo, capsys, sub):
    pkt = packet("20261128-escape", [("demo.zip", GOOD_ZIP, sub)])
    seed(drive, pkt, {"demo.zip": GOOD_ZIP})
    _expect_rejected(
        drive, ingest_bin, repo, capsys, "20261128-escape", "UNSAFE_OR_FORBIDDEN_PATH"
    )


def test_wrong_target_repo_is_rejected(drive, ingest_bin, repo, capsys):
    pkt = packet(
        "20261128-repo",
        [("demo.zip", GOOD_ZIP, "intake/demo")],
        target_repo="someone/else",
    )
    seed(drive, pkt, {"demo.zip": GOOD_ZIP})
    _expect_rejected(
        drive, ingest_bin, repo, capsys, "20261128-repo", "TARGET_REPO_MISMATCH"
    )


def test_missing_artifact_waits_while_fresh_then_is_rejected(
    drive, ingest_bin, repo, capsys
):
    pkt = packet(
        "20261128-late", [("demo.zip", GOOD_ZIP, "intake/demo")]
    )  # artifact not uploaded yet
    seed(drive, pkt, {})
    assert run(drive, ingest_bin, repo) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["results"][0]["verdict"] == "PENDING_ARTIFACTS"
    assert drive.receipts() == {} and branches(repo) == ["main"]

    stale = packet(
        "20261128-stale",
        [("demo.zip", GOOD_ZIP, "intake/demo")],
        created_utc=now_utc(minutes_ago=120),
    )
    seed(drive, stale, {})
    assert run(drive, ingest_bin, repo) == 1
    capsys.readouterr()
    assert drive.receipts()["RECEIPT_20261128-stale.json"]["reason"].startswith(
        "MISSING_ARTIFACT"
    )


def test_duplicate_artifact_name_in_drive_is_never_ingested(
    drive, ingest_bin, repo, capsys
):
    pkt = packet(
        "20261128-dupe",
        [("demo.zip", GOOD_ZIP, "intake/demo")],
        created_utc=now_utc(minutes_ago=120),
    )
    seed(drive, pkt, {"demo.zip": GOOD_ZIP})
    drive.put("demo.zip", b"different bytes")
    assert run(drive, ingest_bin, repo) == 1
    assert branches(repo) == ["main"]


def test_pagination_and_503_retry(drive, ingest_bin, repo, capsys):
    for i in range(5):
        good_packet(drive, pid=f"20261128-page-{i}")
        drive.put(f"PACKET_noise_{i}.txt", b"x")
    drive.fail_next = 2
    assert run(drive, ingest_bin, repo) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["processed"] == 5
    assert sorted(branches(repo)) == ["main"] + [
        f"submit/gemini-20261128-page-{i}" for i in range(5)
    ]


def test_unauthorised_is_a_transport_failure_not_a_rejection(
    drive, ingest_bin, repo, capsys
):
    good_packet(drive)
    wrong = source_for(drive, token="wrong")  # noqa: S106 -- a fake, the server must refuse it
    code = pull.run(wrong, ingest_bin, repo, True, "")
    assert code == 3
    assert drive.receipts() == {} and branches(repo) == ["main"]


def test_token_never_appears_in_output(drive, ingest_bin, repo, capsys):
    good_packet(drive)
    run(drive, ingest_bin, repo)
    drive.fail_uploads = True
    good_packet(drive, pid="20261128-other")
    run(drive, ingest_bin, repo)
    cap = capsys.readouterr()
    assert TOKEN not in cap.out and TOKEN not in cap.err


def test_without_push_flag_nothing_is_pushed_or_receipted(
    drive, ingest_bin, repo, capsys
):
    good_packet(drive)
    assert run(drive, ingest_bin, repo, push=False) == 0
    assert (
        json.loads(capsys.readouterr().out)["results"][0]["verdict"]
        == "VERIFIED_NOT_SUBMITTED"
    )
    assert branches(repo) == ["main"] and drive.receipts() == {}


def test_cli_refuses_missing_credentials_and_missing_binary(tmp_path):
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GOOGLE_OAUTH_ACCESS_TOKEN", "GDRIVE_OUTBOX_FOLDER_ID")
    }
    fake_bin = tmp_path / "bin"
    fake_bin.write_text("#!/bin/sh\nexit 0\n")
    fake_bin.chmod(0o755)
    p = subprocess.run(
        [
            sys.executable,
            str(PULL),
            "--mode",
            "drive-api",
            "--ingest-bin",
            str(fake_bin),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert p.returncode == 3 and "GOOGLE_OAUTH_ACCESS_TOKEN" in p.stdout
    p = subprocess.run(
        [
            sys.executable,
            str(PULL),
            "--mode",
            "drive-api",
            "--ingest-bin",
            str(tmp_path / "nope"),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert p.returncode == 3 and "ingest-bin" in p.stdout


def test_verifier_that_lies_or_crashes_fails_closed(drive, repo, tmp_path, capsys):
    good_packet(drive)
    liar = tmp_path / "liar"
    liar.write_text('#!/bin/sh\necho \'{"verdict":"REJECTED"}\'\nexit 0\n')
    liar.chmod(0o755)
    assert run(drive, liar, repo) == 3
    junk = tmp_path / "junk"
    junk.write_text("#!/bin/sh\necho not-json\nexit 0\n")
    junk.chmod(0o755)
    assert run(drive, junk, repo) == 3
    assert branches(repo) == ["main"] and drive.receipts() == {}


def test_local_mount_source_shares_the_same_pipeline(
    ingest_bin, repo, tmp_path, capsys
):
    box = tmp_path / "Meridian-Submit-Outbox"
    box.mkdir()
    pkt = packet("20261128-local", [("demo.zip", GOOD_ZIP, "intake/local")])
    (box / "PACKET_20261128-local.json").write_text(json.dumps(pkt))
    (box / "demo.zip").write_bytes(GOOD_ZIP)
    assert pull.run(pull.LocalMountSource(box), ingest_bin, repo, True, "") == 0
    assert "submit/gemini-20261128-local" in branches(repo)
    assert (box / "receipts" / "RECEIPT_20261128-local.json").is_file()
    capsys.readouterr()
    assert pull.run(pull.LocalMountSource(box), ingest_bin, repo, True, "") == 0
    assert (
        json.loads(capsys.readouterr().out)["results"][0]["verdict"]
        == "ALREADY_INGESTED"
    )
