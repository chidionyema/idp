#!/usr/bin/env python3
"""Zero-router web-agent intake. Source manifests are data, never authority.

Founder kit SHA256: 7faf705031dfeafbc129fa0a5967f64906ebd235a23da8248d8520ae76fa8e4d.
Use an existing authorized claim and exact public-release envelope; route only
through the established submit gate. No force, workflow edits or browser secrets.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

REPO = "chidionyema/idp"
MAX_ARCHIVE = 2 * 1024 * 1024
MAX_FILE = 256 * 1024
MAX_FILES = 5
ROOTS = {"src", "tests", "packages", "platform", "docs", "bin", "scripts", "ops", "catalog"}
DENIED = {
    ".git", ".github", ".githooks", ".ssh", ".env", "node_modules",
    "secrets", "secret", "credentials", "credential", "private", ".vault",
}
PROTECTED = {
    "bin/idp-auth", "bin/idp-guarded-paths", "bin/idp-ci-guarded-paths",
    "catalog/dof-registry.json", "catalog/genesis-protocols.json",
    "platform/edge/otel-endpoint-exception.yaml",
    "platform/edge/inject-otel-endpoint.yaml",
    "platform/edge/require-otel-endpoint.yaml",
}
MOCKS = ("generalPurposePersonaData.ts", "physicalEstateData.ts", "INITIAL_SPECIALIST_FLEET")
SECRET = re.compile(
    r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{12,}|"
    r"\bgh[pousr]_[A-Za-z0-9]{16,}|\bsk-[A-Za-z0-9_-]{16,}|"
    r"\bAIza[A-Za-z0-9_-]{30,}|\bAKIA[A-Z0-9]{16}",
    re.I,
)


class BridgeError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, code):
    if not condition:
        raise BridgeError(code)


def safe_path(path):
    require(isinstance(path, str) and re.fullmatch(r"[A-Za-z0-9._/-]{1,200}", path), "PATH")
    parts = path.split("/")
    require(len(parts) >= 2 and parts[0] in ROOTS, "PATH_ROOT")
    require(
        all(p not in ("", ".", "..") and p.lower() not in DENIED
            and not p.lower().startswith(".env") for p in parts),
        "PATH_SEGMENT",
    )
    require(path not in PROTECTED and not path.startswith("platform/policies/kyverno/"), "GUARDED_PATH")
    require(not re.search(r"\.(pem|key|p12|pfx|age|kdbx|sqlite|db|env)(\.|$)", path, re.I), "SECRET_PATH")
    require(not any(m in path for m in MOCKS), "MOCK_FIXTURE")
    return path


def approval(raw):
    require(isinstance(raw, dict) and raw.get("public_release") is True, "PUBLIC_RELEASE_NOT_AUTHORIZED")
    require(raw.get("repo") == REPO, "REPOSITORY")
    require(isinstance(raw.get("base_sha"), str) and re.fullmatch(r"[0-9a-f]{40}", raw["base_sha"]), "BASE")
    require(raw.get("source") in ("drive", "github"), "SOURCE")
    field = "archive_sha256" if raw["source"] == "drive" else "source_commit"
    length = 64 if field == "archive_sha256" else 40
    require(isinstance(raw.get(field), str) and re.fullmatch(r"[0-9a-f]{%d}" % length, raw[field]), "SOURCE_DIGEST")
    paths = raw.get("paths")
    require(isinstance(paths, list) and 0 < len(paths) <= MAX_FILES, "SCOPE")
    require(len(set(safe_path(p) for p in paths)) == len(paths), "DUPLICATE_SCOPE")
    require(type(raw.get("claim_issue")) is int and raw["claim_issue"] > 0, "CLAIM")
    require(isinstance(raw.get("agent"), str) and re.fullmatch(r"[A-Za-z0-9_-]{3,64}", raw["agent"]), "AGENT")
    if raw["source"] == "drive":
        require(isinstance(raw.get("drive_file_id"), str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", raw["drive_file_id"]), "DRIVE_FILE")
    return raw


def source_key(release):
    return release.get("archive_sha256") if release["source"] == "drive" else release["source_commit"]


def validate_file(raw):
    require(len(raw) <= MAX_FILE, "FILE_SIZE")
    text = raw.decode("utf-8")
    require("\x00" not in text and not SECRET.search(text), "SECRET_OR_BINARY")


def validate_zip(data, release):
    require(len(data) <= MAX_ARCHIVE and digest(data) == release["archive_sha256"], "ARCHIVE_DIGEST")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        infos = zf.infolist()
        names = [x.filename for x in infos]
        require(len(names) <= MAX_FILES + 1 and len(set(names)) == len(names), "ZIP_ENTRIES")
        require(set(names) == set(release["paths"]) | {"DROP_MANIFEST.json"}, "ZIP_SCOPE")
        for info in infos:
            require(info.file_size <= MAX_FILE and not info.is_dir(), "ZIP_SIZE")
            require(not stat.S_ISLNK(info.external_attr >> 16), "ZIP_SYMLINK")
        manifest = json.loads(zf.read("DROP_MANIFEST.json"))
        require(isinstance(manifest, dict), "MANIFEST")
        specs = manifest.get("files")
        require(isinstance(specs, list) and len(specs) == len(release["paths"]), "MANIFEST_SCOPE")
        result = {}
        for spec in specs:
            require(isinstance(spec, dict), "FILE_SPEC")
            path = safe_path(spec.get("path"))
            require(path in release["paths"] and path not in result, "FILE_SCOPE")
            raw = zf.read(path)
            require(digest(raw) == spec.get("sha256"), "FILE_DIGEST")
            validate_file(raw)
            require(type(spec.get("executable", False)) is bool, "FILE_MODE")
            result[path] = (raw, spec.get("executable", False))
        require(set(result) == set(release["paths"]), "FILE_COVERAGE")
        return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BridgeError("PROVIDER_REDIRECT_REFUSED")


def request(url, *, token=None, form=None, limit=MAX_ARCHIVE):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    body = urllib.parse.urlencode(form).encode() if form else None
    if form:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, headers=headers, data=body)  # noqa: S310 -- fixed HTTPS provider endpoints
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=20) as response:
            data = response.read(limit + 1)
    except urllib.error.HTTPError as exc:
        raise BridgeError(f"PROVIDER_HTTP_{exc.code}") from None
    require(len(data) <= limit, "RESPONSE_SIZE")
    return data


def fetch(release, env):
    folder = env.get("WEB_AGENT_DRIVE_FOLDER_ID", "")
    require(re.fullmatch(r"[A-Za-z0-9_-]{1,128}", folder), "DRIVE_FOLDER")
    keys = ("GDRIVE_CLIENT_ID", "GDRIVE_CLIENT_SECRET", "GDRIVE_REFRESH_TOKEN")
    require(all(env.get(k) for k in keys), "DRIVE_OAUTH_MISSING")
    auth = json.loads(request("https://oauth2.googleapis.com/token", form={
        "client_id": env[keys[0]], "client_secret": env[keys[1]],
        "refresh_token": env[keys[2]], "grant_type": "refresh_token",
    }, limit=65536))
    token = auth.get("access_token")
    require(isinstance(token, str) and token, "DRIVE_ACCESS_TOKEN")
    url = "https://www.googleapis.com/drive/v3/files/" + release["drive_file_id"]
    meta = json.loads(request(url + "?fields=id,parents,trashed,size&supportsAllDrives=true", token=token, limit=65536))
    require(meta.get("id") == release["drive_file_id"] and folder in meta.get("parents", [])
            and meta.get("trashed") is False, "DRIVE_CUSTODY")
    require(int(meta.get("size", MAX_ARCHIVE + 1)) <= MAX_ARCHIVE, "DRIVE_SIZE")
    data = request(url + "?alt=media&supportsAllDrives=true", token=token)
    validate_zip(data, release)
    return data


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])  # noqa: S603,S607 -- fixed git argv, no shell


def read_commit(root, commit, release):
    require(re.fullmatch(r"[0-9a-f]{40}", commit), "COMMIT")
    parents = git(root, "rev-list", "--parents", "-n", "1", commit).decode().split()
    require(parents == [commit, release["base_sha"]], "PARENT")
    paths = git(root, "diff", "--no-renames", "--name-only", "-z", release["base_sha"], commit).decode().split("\0")
    require(set(filter(None, paths)) == set(release["paths"]), "COMMIT_SCOPE")
    result = {}
    for path in release["paths"]:
        mode = git(root, "ls-tree", commit, "--", path).split()[0]
        require(mode in (b"100755", b"100644"), "COMMIT_MODE")
        raw = git(root, "show", f"{commit}:{path}")
        validate_file(raw)
        result[path] = (raw, mode == b"100755")
    return result


def expected_files(root, archive, release):
    if release["source"] == "github":
        return read_commit(root, release["source_commit"], release)
    with archive.open("rb") as handle:
        return validate_zip(handle.read(MAX_ARCHIVE + 1), release)


def stage(root, files, release):
    require(git(root, "rev-parse", "HEAD").decode().strip() == release["base_sha"], "STALE_BASE")
    require(not git(root, "status", "--porcelain"), "DIRTY_BASE")
    for name, (data, executable) in files.items():
        path = root
        for part in name.split("/")[:-1]:
            path = path / part
            require(not path.is_symlink(), "SYMLINK_PARENT")
            path.mkdir(exist_ok=True)
        path = root / name
        require(not path.is_symlink() and (not path.exists() or path.is_file()), "SYMLINK_TARGET")
        path.write_bytes(data)
        path.chmod(0o755 if executable else 0o644)
        git(root, "add", "--", name)


def verify_commit(root, commit, files, release):
    require(read_commit(root, commit, release) == files, "COMMIT_BYTES")
    message = git(root, "show", "-s", "--format=%B", commit).decode()
    for line in (
        f"Claim: #{release['claim_issue']}", f"Agent: {release['agent']}",
        f"Drop-Source: {source_key(release)}",
    ):
        require(message.splitlines().count(line) == 1, "COMMIT_TRAILER")
    require(re.search(r"^X-Idp-Signed: [0-9a-f]{64}$", message, re.M), "HOOK_STAMP_MISSING")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("fetch", "stage", "verify"))
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--root", default=Path.cwd(), type=Path)
    parser.add_argument("--commit")
    args = parser.parse_args()
    try:
        release = approval(json.loads(os.environ["WEB_AGENT_RELEASE_JSON"]))
        if args.command == "fetch":
            args.archive.write_bytes(fetch(release, os.environ) if release["source"] == "drive" else b"")
        else:
            files = expected_files(args.root, args.archive, release)
            if args.command == "stage":
                stage(args.root, files, release)
            else:
                verify_commit(args.root, args.commit or "", files, release)
        print("WEB_AGENT_BRIDGE_OK", args.command)
        return 0
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        # No provider response bodies, tokens or source bytes in public logs.
        print("WEB_AGENT_BRIDGE_REFUSED", str(exc) if isinstance(exc, BridgeError) else type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
