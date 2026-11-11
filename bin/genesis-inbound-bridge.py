#!/usr/bin/env python3
"""Gmail Drafts / Drive [GENESIS-OUTBOX] -> repo-local GitHub issue intake.

Only the authenticated Google account's drafts and an explicitly configured
Drive folder are sources. Inbound text is unverified data, not shell commands,
signed Git instructions or production release authority. Run on GitHub Actions.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

PREFIX = "[GENESIS-OUTBOX]"
REPOS = {"chidionyema/argon", "chidionyema/idp", "chidionyema/hermes-agent",
         "chidionyema/hermes-config", "chidionyema/hermes-operator"}
MAX_BODY = 30000


class BridgeError(Exception):
    pass


def api(url, token, method="GET", body=None):
    payload = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=payload, method=method, headers={
        "Authorization": "Bearer " + token, "User-Agent": "genesis-inbound-bridge/1",
        "Accept": "application/json", **({"Content-Type": "application/json"} if payload else {})})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            raw = response.read(500000)
    except urllib.error.HTTPError as error:
        raise BridgeError("API returned HTTP " + str(error.code)) from None
    except (urllib.error.URLError, TimeoutError):
        raise BridgeError("API could not be reached") from None
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise BridgeError("API returned invalid JSON") from None


def oauth():
    names = ("GENESIS_GOOGLE_CLIENT_ID", "GENESIS_GOOGLE_CLIENT_SECRET",
             "GENESIS_GOOGLE_REFRESH_TOKEN")
    if any(not os.environ.get(name) for name in names):
        raise BridgeError("Google OAuth credentials are missing; intake NOT ACTIVE")
    data = urllib.parse.urlencode({
        "client_id": os.environ[names[0]], "client_secret": os.environ[names[1]],
        "refresh_token": os.environ[names[2]], "grant_type": "refresh_token"}).encode()
    request = urllib.request.Request("https://oauth2.googleapis.com/token", data=data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            token = json.load(response).get("access_token")
    except (ValueError, urllib.error.HTTPError, urllib.error.URLError):
        raise BridgeError("Google OAuth exchange failed") from None
    if not token:
        raise BridgeError("Google did not issue an access token")
    return token


def gmail_body(part):
    mime = part.get("mimeType", "")
    if mime.startswith("multipart/"):
        return next((value for child in part.get("parts", [])
                     if (value := gmail_body(child))), "")
    if mime not in ("", "text/plain", "application/json"):
        return ""
    raw = part.get("body", {}).get("data", "")
    if not raw:
        return ""
    try:
        return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        raise BridgeError("Gmail draft body is not valid UTF-8") from None


def gmail_drafts(token):
    root = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
    next_page = None
    scanned = 0
    while True:
        params = {"maxResults": 100}
        if next_page:
            params["pageToken"] = next_page
        result = api(root + "?" + urllib.parse.urlencode(params), token)
        for record in result.get("drafts", []):
            scanned += 1
            if scanned > 1000:
                raise BridgeError("Gmail pagination exceeded bounded scan")
            draft = api(root + "/" + urllib.parse.quote(record["id"], safe="") + "?format=full", token)
            message = draft.get("message", {})
            if "DRAFT" not in message.get("labelIds", []):
                continue
            payload = message.get("payload", {})
            headers = {h.get("name", "").lower(): h.get("value", "")
                       for h in payload.get("headers", [])}
            name = headers.get("subject", "")
            if name.startswith(PREFIX):
                yield "gmail:" + record["id"], name, gmail_body(payload)
        next_page = result.get("nextPageToken")
        if not next_page:
            return


def download(url, token):
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read(MAX_BODY + 1)
    except (urllib.error.HTTPError, urllib.error.URLError):
        raise BridgeError("Drive outbox item could not be downloaded") from None
    if len(raw) > MAX_BODY:
        raise BridgeError("Drive outbox item exceeds size limit")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise BridgeError("Drive outbox item is not UTF-8") from None


def drive_docs(token, folder):
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", folder):
        raise BridgeError("Drive folder ID missing or invalid")
    root = "https://www.googleapis.com/drive/v3/files"
    next_page = None
    scanned = 0
    while True:
        params = {"q": "'" + folder + "' in parents and trashed = false",
                  "pageSize": 100, "fields": "nextPageToken,files(id,name,mimeType)"}
        if next_page:
            params["pageToken"] = next_page
        result = api(root + "?" + urllib.parse.urlencode(params), token)
        for item in result.get("files", []):
            scanned += 1
            if scanned > 1000:
                raise BridgeError("Drive pagination exceeded bounded scan")
            name = item.get("name", "")
            if not name.startswith(PREFIX):
                continue
            file_id = urllib.parse.quote(item["id"], safe="")
            mime = item.get("mimeType", "")
            if mime == "application/vnd.google-apps.document":
                url = root + "/" + file_id + "/export?mimeType=text%2Fplain"
            elif mime in ("text/plain", "application/json", "application/octet-stream"):
                url = root + "/" + file_id + "?alt=media"
            else:
                raise BridgeError("unsupported MIME type in outbox")
            yield "drive:" + item["id"], name, download(url, token)
        next_page = result.get("nextPageToken")
        if not next_page:
            return


def parse_dispatch(subject, raw, repo):
    if not subject.startswith(PREFIX) or not raw.strip() or len(raw.encode()) > MAX_BODY:
        raise BridgeError("empty, oversized or unmarked dispatch")
    try:
        envelope = json.loads(raw)
    except ValueError:
        tag = re.search(r"\[(argon|idp|hermes-agent|hermes-config|hermes-operator)\]", subject)
        if not tag:
            raise BridgeError("plain text requires [repo] tag in the subject")
        envelope = {"v": 1, "repo": "chidionyema/" + tag.group(1),
                    "title": subject.replace(PREFIX, "").strip(), "body": raw.strip()}
    if not isinstance(envelope, dict) or envelope.get("v") != 1 or envelope.get("repo") not in REPOS:
        raise BridgeError("invalid version or unauthorized repo")
    if envelope["repo"] != repo:
        return None
    # IDP / Hermes repositories are public. No private dispatch is published to them.
    if repo != "chidionyema/argon" and envelope.get("public") is not True:
        raise BridgeError("public repository requires explicit public=true")
    title, body = envelope.get("title"), envelope.get("body")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 140:
        raise BridgeError("invalid title")
    if not isinstance(body, str) or not 1 <= len(body.strip().encode()) <= MAX_BODY:
        raise BridgeError("invalid body")
    if "\x00" in title + body:
        raise BridgeError("NUL content refused")
    return {"title": title.strip(), "body": body.strip(),
            "instruction_id": str(envelope.get("instruction_id", "unspecified"))[:128]}


def previous_ids(gh, repo):
    found = set()
    for page in range(1, 11):
        query = urllib.parse.urlencode({"state": "all", "labels": "genesis-inbound",
                                        "per_page": 100, "page": page})
        rows = api("https://api.github.com/repos/" + repo + "/issues?" + query, gh)
        if not isinstance(rows, list):
            raise BridgeError("GitHub issue inventory not a list")
        for row in rows:
            marker = re.search(r"^GENESIS-INBOUND-ID: ([0-9a-f]{64})$",
                               row.get("body") or "", re.MULTILINE)
            if marker:
                found.add(marker.group(1))
        if len(rows) < 100:
            return found
    raise BridgeError("inbound receipt inventory too large to deduplicate safely")


def ensure_label(gh, repo):
    root = "https://api.github.com/repos/" + repo + "/labels"
    try:
        api(root + "/genesis-inbound", gh)
    except BridgeError as error:
        if "HTTP 404" not in str(error):
            raise
        api(root, gh, "POST", {"name": "genesis-inbound", "color": "54617d",
                              "description": "Unverified Google outbox instruction, not operational proof"})


def publish(gh, repo, key, entry, source):
    quoted = "\n".join("> " + line for line in entry["body"].splitlines())
    body = ("GENESIS-INBOUND-ID: " + key + "\n\n"
            "State: RECEIVED_UNVERIFIED. No execution, approval, or deployment asserted.\n\n"
            "Instruction: " + entry["instruction_id"] + "\n"
            "Source-kind: " + source.split(":")[0] + "\n\n"
            "### Untrusted dispatch data\n\n" + quoted)
    api("https://api.github.com/repos/" + repo + "/issues", gh, "POST",
        {"title": "[GENESIS-INBOUND] " + entry["title"][:110], "body": body,
         "labels": ["genesis-inbound"]})


def run(repo):
    if repo not in REPOS:
        raise BridgeError("unapproved repository")
    gh = os.environ.get("GH_TOKEN", "")
    if not gh:
        raise BridgeError("GitHub token missing")
    folder = os.environ.get("GENESIS_DRIVE_FOLDER_ID", "")
    gmail = os.environ.get("GENESIS_GMAIL_DRAFTS") == "true"
    if not folder and not gmail:
        raise BridgeError("no Gmail/Drive outbox selected")
    token = oauth()
    receipts = previous_ids(gh, repo)
    ensure_label(gh, repo)
    streams = [gmail_drafts(token)] if gmail else []
    if folder:
        streams.append(drive_docs(token, folder))
    count = 0
    for stream in streams:
        for source, title, body in stream:
            entry = parse_dispatch(title, body, repo)
            if not entry:
                continue
            key = hashlib.sha256((source + "\0" + title + "\0" + body).encode()).hexdigest()
            if key in receipts:
                continue
            publish(gh, repo, key, entry, source)
            receipts.add(key)
            count += 1
    print("genesis-inbound-bridge: RECEIVED_UNVERIFIED=%d target=%s" % (count, repo))


def selftest():
    assert parse_dispatch("[GENESIS-OUTBOX][argon] Test", "body", "chidionyema/argon")
    assert parse_dispatch("[GENESIS-OUTBOX][idp] Test", "body", "chidionyema/argon") is None
    try:
        parse_dispatch("[GENESIS-OUTBOX][idp] Test", "body", "chidionyema/idp")
    except BridgeError:
        pass
    else:
        raise BridgeError("public repository privacy guard not enforced")
    print("genesis-inbound-bridge: core negative tests PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        selftest() if args.self_test else run(args.repo)
    except BridgeError as error:
        print("genesis-inbound-bridge: FAILED: " + str(error), file=sys.stderr)
        sys.exit(2)
