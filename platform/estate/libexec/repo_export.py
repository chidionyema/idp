#!/usr/bin/env python3
"""repo_export.py -- pack the estate's own code into ONE file for another model's context window.

Usage (via the intent): repo_export.py [path=platform/estate,sovereign,...] [output=/tmp/repo-export/pack.xml]
                        [format=xml] [compress=true] [include=] [ignore=]
                        [max_file_bytes=65536] [token_budget=1000000] [budget_s=80]

WHAT THIS SOLVES (measured 2026-10-31, 4-core laptop under load average 600 -- 13 agents on it):

  * `npx -y repomix@1.18.1` costs 27-34 s per call AND needs the network. The executor's egress
    lock (pf) refuses it, so the intent could never run. The tool is pinned and LOCAL now:
    ~/.cache/estate-tools/repomix (installed by bin/idp-install-deps).
  * repomix walking the working tree crawls 2.9 GB of ignored trees (web/, backstage/, .git):
    167 s for a pack of 9 MB. Nothing to do with the pack's size -- it is the walk.
  * tree-sitter compression of `sovereign/trust/presence_helper.swift` -- ONE 4.5 KB file --
    cost 76 s. The Swift grammar is pathological and 1.18.1 is the latest published repomix,
    so there is no upgrade to wait for. It is excluded, and the exclusion is named.
  * repomix's secretlint scan costs ~12 s over 4.7k files. Kept: a pack that hides a leaked
    credential is worse than one that flags it.

So this script does the part repomix cannot: it decides WHAT goes in, deterministically, from
tracked content only (`git ls-files`), and hands that list to repomix over `--stdin` so repomix
never walks the working tree. It excludes the measured classes, and it says which ones it
excluded and why -- an export nobody can account for is not traceable.

The default scope is the estate's CORE -- the code that runs the estate (platform/estate,
sovereign, mcp, cmd, greenlane) -- not the whole tree. That is deliberate on two measured
grounds: the whole tree compresses to 17.7 MB (~4.4M tokens), which no model's context window
holds, and it costs 110 s on this machine, over the door's 100 s ceiling. A pack nobody's
model can read is not an export. Widen it with path=..., and the token budget refuses a pack
that would not fit the window instead of producing one that is useless.

Every pack comes with a manifest beside it: every path included (with its sha256), every path
excluded (with the reason), the pack's own sha256, the tool version and the measured seconds.
That is what makes the export traceable after the terminal is gone.

THE DOOR IS A HARD CEILING, AND THE MACHINE IS NOT UNDER OUR CONTROL. The 4-core laptop this
estate runs on carried load average 600 on 2026-10-31 (thirteen agents on it), and repomix's
per-file cost is CPU-bound: ~14 s fixed plus ~90 ms a file under that load, ~30 ms a file on an
idle box. A scope measured at 58 s can take 90 s on a busier minute, so a fixed scope is a
promise nobody can keep. Therefore the packer carries its OWN time budget: attempt one gets
`attempt_s` (45 s by default), and if the machine is too busy to finish it, attempt two packs
half the file list with the time that is left. Two attempts, bounded by `budget_s` (80 s), so
the packer returns inside the door's 100 s whatever the load does -- and the manifest names
every file the shrink dropped, so a smaller pack is never a silent one.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

GIT = shutil.which("git") or "/usr/bin/git"
REPOMIX_VERSION = "1.18.1"
DEFAULT_SCOPE = "platform/estate,sovereign,mcp,cmd,greenlane"
DEFAULT_OUTPUT = "/tmp/repo-export/pack.xml"  # noqa: S108 - the pack is a scratch artifact by design
DEFAULT_MAX_FILE_BYTES = 65536
DEFAULT_TOKEN_BUDGET = 1_000_000
DEFAULT_BUDGET_S = 80
DEFAULT_ATTEMPT_S = 45
DEFAULT_FORMAT = "xml"

# The estate's own checkout of the code, when the caller's working directory is not inside a
# repository (the executor runs an intent from wherever it was invoked).
RUNTIME_TREE = "~/.estate/runtime/idp"

# Where the pinned repomix lives. bin/idp-install-deps installs it; CI pins the same version.
TOOL_CANDIDATES = (
    "~/.cache/estate-tools/repomix/node_modules/.bin/repomix",
    "~/.cache/estate-tools/bin/repomix",
)

# Not source: vendored third-party code, minified bundles, archived patches.
VENDORED_MARKERS = ("/vendor/", "/node_modules/", "/.venv/", "/site-packages/")
MINIFIED_SUFFIXES = (".min.js", ".min.css", ".bundle.js")
EXCLUDED_PREFIXES = ("rescued_patches2/",)

# tree-sitter's Swift grammar is pathological: 76 s to compress one 4.5 KB file
# (measured 2026-10-31, repomix 1.18.1). 1.18.1 is the latest published release, so there is no
# upgrade to wait for; the file is excluded from a COMPRESSED pack and kept in a plain one.
PATHOLOGICAL_COMPRESS_SUFFIXES = (".swift",)

# Not context: assets and binaries are bytes, not code.
BINARY_SUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svgz",
    ".pdf",
    ".zip",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".dmg",
    ".iso",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".mp3",
    ".mp4",
    ".mov",
    ".avi",
    ".wav",
    ".webm",
    ".wasm",
    ".so",
    ".dylib",
    ".a",
    ".o",
    ".exe",
    ".bin",
    ".dat",
    ".parquet",
    ".safetensors",
    ".onnx",
    ".pt",
    ".pth",
    ".npy",
    ".npz",
    ".sqlite",
    ".db",
    ".pyc",
    ".jar",
    ".class",
    ".icns",
    ".icns.gz",
)

TOKEN_LINE = re.compile(r"Total Tokens:\s*([0-9,]+)")
FILES_LINE = re.compile(r"Total Files:\s*([0-9,]+)")


class ExportError(Exception):
    """A named failure: the caller gets the reason, not a hang."""


def parse_args(argv):
    """key=value pairs, the estate's libexec convention (see consult_gemini.py)."""
    out = {}
    for a in argv:
        if "=" not in a:
            raise ExportError(f"argument without a value: {a!r} (use key=value)")
        k, v = a.split("=", 1)
        out[k.strip()] = v
    return out


def _int(args, key, default):
    raw = args.get(key, "")
    if raw in (None, ""):
        return default
    try:
        return int(str(raw).strip())
    except ValueError as exc:
        raise ExportError(f"{key} must be a whole number, got {raw!r}") from exc


def _bool(args, key, default):
    raw = str(args.get(key, "")).strip().lower()
    if raw == "":
        return default
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    raise ExportError(f"{key} must be true or false, got {raw!r}")


def resolve_repo(value):
    """The repo root: an explicit path, else the git root above the working directory, else the
    estate's runtime checkout. An export of "the estate's code" must not depend on where the
    caller happened to be standing."""
    if value:
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        if candidate.is_file():
            candidate = candidate.parent
        if not candidate.is_dir():
            raise ExportError(f"repo path does not exist: {candidate}")
        for parent in [candidate, *candidate.parents]:
            if (parent / ".git").exists():
                return parent
        raise ExportError(f"no git repository at or above {candidate}")
    for start in (Path.cwd(), Path(RUNTIME_TREE).expanduser()):
        for parent in [start, *start.parents]:
            if (parent / ".git").exists():
                return parent
    raise ExportError(
        f"no git repository at or above {Path.cwd()} and no runtime checkout at {RUNTIME_TREE}; "
        "pass repo=<path>"
    )


def tracked_files(repo, scope):
    """Every tracked path under the scope, from git -- so the pack never walks the worktree."""
    roots = [s.strip() for s in scope.split(",") if s.strip()]
    cmd = [GIT, "-C", str(repo), "ls-files", "-z"]
    if roots and roots != ["."]:
        cmd += ["--", *roots]
    proc = subprocess.run(cmd, capture_output=True, check=False)  # noqa: S603
    if proc.returncode != 0:
        raise ExportError(
            f"git ls-files failed in {repo}: {proc.stderr.decode(errors='replace').strip()[:200]}"
        )
    return [p.decode(errors="replace") for p in proc.stdout.split(b"\0") if p]


def _matches(path, patterns):
    """Glob match on the full path and on the basename, the way a user writes them."""
    import fnmatch

    for pattern in patterns:
        pattern = pattern.strip()
        if not pattern:
            continue
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, f"*/{pattern}"):
            return True
        if fnmatch.fnmatch(Path(path).name, pattern):
            return True
    return False


def exclusion_reason(rel, size, compress, max_file_bytes, include, ignore):
    """Why this file is not in the pack, or None when it is."""
    if ignore and _matches(rel, ignore.split(",")):
        return "ignored by --ignore"
    if include and not _matches(rel, include.split(",")):
        return "not matched by --include"
    if rel.startswith(EXCLUDED_PREFIXES):
        return "archived patch, not source"
    if any(marker in f"/{rel}" for marker in VENDORED_MARKERS):
        return "vendored third-party code"
    if rel.endswith(MINIFIED_SUFFIXES):
        return "minified bundle"
    if rel.endswith(BINARY_SUFFIXES):
        return "binary or asset"
    if compress and rel.endswith(PATHOLOGICAL_COMPRESS_SUFFIXES):
        return (
            "tree-sitter cannot compress this file in time (measured 76s for one file)"
        )
    if size is not None and size > max_file_bytes:
        return f"larger than max_file_bytes ({size} > {max_file_bytes})"
    return None


def resolve_repomix():
    """The pinned, local repomix. Never npx: that needs the network the door closes."""
    override = os.environ.get("REPO_EXPORT_REPOMIX", "").strip()
    if override:
        if not Path(override).exists():
            raise ExportError(f"REPO_EXPORT_REPOMIX points at nothing: {override}")
        return Path(override)
    for candidate in TOOL_CANDIDATES:
        path = Path(candidate).expanduser()
        if path.exists():
            return path
    found = shutil.which("repomix")
    if found:
        return Path(found)
    raise ExportError(
        "repomix is not installed. Run bin/idp-install-deps (it installs the pinned "
        f"{REPOMIX_VERSION} into ~/.cache/estate-tools/repomix), or point REPO_EXPORT_REPOMIX at "
        "a local repomix binary."
    )


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv):
    args = parse_args(argv)
    scope = args.get("path", "").strip() or DEFAULT_SCOPE
    output = Path(args.get("output", "").strip() or DEFAULT_OUTPUT).expanduser()
    fmt = args.get("format", "").strip() or DEFAULT_FORMAT
    compress = _bool(args, "compress", True)
    include = args.get("include", "").strip()
    ignore = args.get("ignore", "").strip()
    max_file_bytes = _int(args, "max_file_bytes", DEFAULT_MAX_FILE_BYTES)
    token_budget = _int(args, "token_budget", DEFAULT_TOKEN_BUDGET)
    budget_s = _int(args, "budget_s", DEFAULT_BUDGET_S)
    attempt_s = min(_int(args, "attempt_s", DEFAULT_ATTEMPT_S), budget_s)
    repo = resolve_repo(
        args.get("repo", "").strip() or os.environ.get("REPO_EXPORT_REPO", "").strip()
    )

    repomix = resolve_repomix()

    included, excluded = [], {}
    for rel in tracked_files(repo, scope):
        path = repo / rel
        try:
            size = path.stat().st_size
        except OSError:
            excluded[rel] = "not present in the working tree"
            continue
        reason = exclusion_reason(rel, size, compress, max_file_bytes, include, ignore)
        if reason:
            excluded[rel] = reason
        else:
            included.append(rel)

    if not included:
        raise ExportError(
            "nothing to pack: the scope matched no file that survives the exclusions. "
            f"scope={scope!r} tracked={len(tracked_files(repo, scope))}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    list_path = output.parent / (output.name + ".filelist")

    cmd = [
        str(repomix),
        "--stdin",
        "--style",
        fmt,
        "--output",
        str(output),
        "--no-git-sort-by-changes",
        "--no-file-summary",
        "--no-directory-structure",
        "--truncate-base64",
        "--parsable-style",
    ]
    if compress:
        cmd.append("--compress")
    if token_budget > 0:
        cmd += ["--token-budget", str(token_budget)]

    # The packer carries its own budget: two attempts, bounded, so the door is met whatever the
    # machine's load does. A timed-out attempt is a measurement, not a failure.
    deadline = time.monotonic() + budget_s
    started = time.monotonic()
    packing = list(included)
    dropped_by_budget = []
    attempt = 0
    proc = None
    while True:
        attempt += 1
        left = deadline - time.monotonic()
        if left <= 0.5:
            raise ExportError(
                f"the time budget ({budget_s}s) ran out before a pack was produced; "
                f"narrow the scope with path=... and try again"
            )
        list_path.write_text("\n".join(packing) + "\n")
        if output.exists():
            output.unlink()
        with open(list_path, encoding="utf-8") as handle:
            try:
                proc = subprocess.run(  # noqa: S603
                    cmd,
                    stdin=handle,
                    capture_output=True,
                    text=True,
                    timeout=max(1.0, min(float(attempt_s), left)),
                    cwd=str(repo),
                    check=False,
                )
            except subprocess.TimeoutExpired:
                proc = None
        if proc is not None and proc.returncode == 0 and output.exists():
            break
        if attempt >= 2 or len(packing) < 2:
            if proc is not None and proc.returncode != 0:
                if proc.stdout.strip():
                    print(proc.stdout.strip())
                if proc.stderr.strip():
                    print(proc.stderr.strip()[-2000:], file=sys.stderr)
                raise ExportError(
                    f"repomix exited {proc.returncode} after {time.monotonic() - started:.1f}s "
                    f"(token_budget={token_budget}); see the summary above for the measured tokens"
                )
            raise ExportError(
                f"repomix did not finish {len(packing)} files inside the time budget "
                f"({budget_s}s, attempt timeout {attempt_s}s); narrow the scope with path=..."
            )
        half = len(packing) // 2
        dropped_by_budget = packing[half:]
        packing = packing[:half]
        print(
            f"repo-export: the machine was too busy for {len(packing) + len(dropped_by_budget)} "
            f"files in {attempt_s}s; retrying with the first {len(packing)}"
        )
    elapsed = time.monotonic() - started

    if proc.stdout.strip():
        print(proc.stdout.strip())
    if not output.exists() or output.stat().st_size == 0:
        raise ExportError(f"repomix wrote no pack at {output}")

    included = packing
    for rel in dropped_by_budget:
        excluded[rel] = "dropped by the time budget (the machine was too busy)"

    tokens = TOKEN_LINE.search(proc.stdout)
    tokens = int(tokens.group(1).replace(",", "")) if tokens else 0
    packed_bytes = output.stat().st_size
    pack_sha = _sha256(output)

    manifest = output.with_suffix(output.suffix + ".manifest.txt")
    head = subprocess.run(  # noqa: S603
        [GIT, "-C", str(repo), "rev-parse", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    dirty = subprocess.run(  # noqa: S603
        [GIT, "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [
        f"# repo-export manifest -- {output}",
        f"generated_at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"repo: {repo}",
        f"git_head: {head.stdout.strip() or 'unknown'}",
        f"dirty_paths: {len([l for l in dirty.stdout.splitlines() if l.strip()])}",
        f"scope: {scope}",
        f"format: {fmt} compress: {compress}",
        f"repomix: {repomix} (pinned {REPOMIX_VERSION})",
        f"files: {len(included)}",
        f"bytes: {packed_bytes}",
        f"tokens: {tokens}",
        f"seconds: {elapsed:.1f}",
        f"pack_sha256: {pack_sha}",
        "",
        "## included",
    ]
    for rel in included:
        try:
            digest = _sha256(repo / rel)
        except OSError:
            digest = "unreadable"
        lines.append(f"{digest}  {rel}")
    lines += ["", "## excluded"]
    for rel, reason in sorted(excluded.items()):
        lines.append(f"{reason}  {rel}")
    manifest.write_text("\n".join(lines) + "\n")

    print(
        f"verdict: repo-export packed {len(included)} files ({packed_bytes} bytes, {tokens} tokens) "
        f"in {elapsed:.1f}s -> {output}"
    )
    print(f"verdict: repo {repo} (head {head.stdout.strip()[:12] or 'unknown'})")
    print(
        f"verdict: excluded {len(excluded)} files (vendored, minified, binary, oversized)"
    )
    print(f"verdict: manifest {manifest} (pack sha256 {pack_sha[:16]})")
    print(
        json.dumps(
            {
                "files": len(included),
                "bytes": packed_bytes,
                "tokens": tokens,
                "seconds": round(elapsed, 1),
                "output": str(output),
                "manifest": str(manifest),
                "sha256": pack_sha,
                "repo": str(repo),
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except ExportError as exc:
        print(f"repo-export: {exc}", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print(
            "repo-export: timed out -- the scope is too large for the door. Narrow it with "
            "path=... and try again.",
            file=sys.stderr,
        )
        sys.exit(124)
