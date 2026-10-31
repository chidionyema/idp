#!/usr/bin/env python3
"""rust-only-admission: the admission gate for the k3s spine.

THE RULE (founder, 2026-10-31). The Oracle k3s cluster is a strictly governed, Rust-only
environment. A production service that targets the spine is written in Rust. Python does not
reach it: no `.py` in the image, no Python dependency manifest, no Python base image. Legacy
Python services that already run are grandfathered by name in
policy/rust-only-allowlist.json, with an owner, a reason and an expiry -- they are not
rewritten in this change, they are simply not allowed to grow.

WHERE IT SITS. This is the rule engine, and there is exactly one of it. It is called from
three doors, all of which are real admission points:

  1. bin/build-image, before any image is built or pushed -- the estate's one image door (R24).
  2. platform/estate/intents/rust-only.admission.yaml -- so any agent can ask the gate a
     question through the estate's own intent surface (~/.estate/libexec after the runtime
     sync copies it there).
  3. .github/workflows/build-multiarch.yml, over every image bin/dockerfiles lists -- so a
     python service cannot be added to the spine by simply adding a Dockerfile.

HOW IT DECIDES. What is in an image is decided by its Dockerfile, not by the directory that
happens to be the build context: the base image's FROM lines and the files COPY/ADD actually
bring in. A repository-root context that copies one Rust binary is not a python image; a
context that copies `worker.py` is. Reading the Dockerfile is what makes the gate precise
instead of noisy.

THE VERDICT IS THE EXIT CODE. 0 means admitted. 4 means denied, and the first line printed
is exactly:

    ADMISSION DENIED: Services targeting the k3s spine must be written in Rust.

A gate that cannot fail is not a gate, so this ships with its falsifier:
tests/test_rust_only_admission.py drives a known-bad python service (must be denied, with
that exact message) and a known-good rust service (must be admitted) through this engine.

Stdlib only. No network. A finding names the file and the line.
"""

from __future__ import annotations

import argparse
import fnmatch
import glob as globmod
import json
import os
import re
import shlex
import subprocess
import sys

DENY_MESSAGE = "ADMISSION DENIED: Services targeting the k3s spine must be written in Rust."
OK_MESSAGE = "ADMISSION OK"

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_DENIED = 4

PY_SUFFIXES = (".py", ".pyw", ".pyi")
PY_MANIFESTS = {
    "pyproject.toml", "setup.py", "setup.cfg", "pipfile", "pipfile.lock", "poetry.lock",
    "environment.yml", "environment.yaml", "conda.yaml", "conda.yml", "tox.ini",
}
PY_MANIFEST_PREFIXES = ("requirements",)
# A base image whose name is a Python runtime: python:3.12-slim, distroless/python3, pypy:3.10
PY_BASE_IMAGE = re.compile(r"(^|/)(python|pypy|cpython)[0-9]?([.\-]|$)", re.IGNORECASE)

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache"}


def is_python_manifest(name: str) -> bool:
    low = name.lower()
    if low in PY_MANIFESTS:
        return True
    return any(low.startswith(p) and low.endswith(".txt") for p in PY_MANIFEST_PREFIXES)


def python_finding(path: str) -> dict | None:
    base = os.path.basename(path)
    if base.endswith(PY_SUFFIXES):
        return {"kind": "python_source", "path": path, "line": 0, "detail": base}
    if is_python_manifest(base):
        return {"kind": "python_manifest", "path": path, "line": 0, "detail": base}
    return None


def dockerfile_lines(path: str) -> list[tuple[int, str]]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return [(i, l) for i, l in enumerate(fh.readlines(), start=1)]
    except OSError:
        return []


def from_findings(dockerfile: str, rel_to: str) -> list[dict]:
    """Python base images, named with the file and the line."""
    out = []
    for i, line in dockerfile_lines(dockerfile):
        stripped = line.strip()
        if not stripped.upper().startswith("FROM "):
            continue
        parts = stripped[5:].split()
        if not parts:
            continue
        image = parts[0]
        if PY_BASE_IMAGE.search(image):
            out.append({"kind": "python_base_image", "path": rel_to, "line": i, "detail": image})
    return out


def copy_sources(dockerfile: str) -> list[tuple[str, int]]:
    """The paths a Dockerfile brings into the image: (source, line)."""
    out = []
    for i, line in dockerfile_lines(dockerfile):
        stripped = line.strip()
        if not re.match(r"^(COPY|ADD)\s+", stripped, re.IGNORECASE):
            continue
        try:
            tokens = shlex.split(stripped, posix=True)
        except ValueError:
            tokens = stripped.split()
        tokens = [t for t in tokens[1:] if not t.startswith("--")]
        if any(t.startswith("--from=") for t in tokens):
            continue          # a stage copy: that stage's own sources are counted already
        if len(tokens) < 2:
            continue
        for src in tokens[:-1]:          # the last token is the destination
            if "$" in src:
                continue                # an env-dependent source: not resolvable, not counted
            out.append((src, i))
    return out


def scan_source(context: str, src: str) -> list[str]:
    """Every python artifact under one COPY/ADD source, as paths relative to the context."""
    out = []
    full = os.path.join(context, src)
    if any(ch in src for ch in "*?["):
        matches = globmod.glob(full, recursive=True)
    elif os.path.isdir(full):
        matches = []
        for root, dirs, files in os.walk(full):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                matches.append(os.path.join(root, f))
    elif os.path.isfile(full):
        matches = [full]
    else:
        matches = []
    for m in matches:
        if os.path.isdir(m):
            continue
        if python_finding(m):
            out.append(os.path.relpath(m, context))
    return out


def image_findings(dockerfile: str, context: str, repo_root: str) -> list[dict]:
    """What this image would contain that Python wrote."""
    out = []
    df_rel = os.path.relpath(dockerfile, repo_root) if os.path.isabs(dockerfile) else dockerfile
    if dockerfile and os.path.isfile(dockerfile):
        out.extend(from_findings(dockerfile, df_rel))
        for src, line in copy_sources(dockerfile):
            for rel in scan_source(context, src):
                out.append({"kind": "python_source", "path": f"{df_rel} -> {rel}", "line": line,
                            "detail": os.path.basename(rel)})
    elif context and os.path.isdir(context):
        # no Dockerfile to read: the whole context is the image (a conservative reading)
        for root, dirs, files in os.walk(context):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                finding = python_finding(os.path.join(root, f))
                if finding:
                    finding["path"] = os.path.relpath(os.path.join(root, f), context)
                    out.append(finding)
    return out


def load_allowlist(path: str) -> list[dict]:
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return []
    allow = doc.get("allow")
    return allow if isinstance(allow, list) else []


def allowed_for(image: str, allow: list[dict]) -> dict | None:
    """An entry grandfathers an image. An entry without a reason is not an entry."""
    for entry in allow:
        if not isinstance(entry, dict):
            continue
        pattern = entry.get("image") or ""
        if not pattern or not entry.get("reason"):
            continue
        if fnmatch.fnmatch(image, pattern) or image == pattern or \
                fnmatch.fnmatch(os.path.basename(image), pattern):
            return entry
    return None


def check_images(images: list[dict], allow: list[dict], repo_root: str) -> tuple[list[dict], list[dict]]:
    """images: [{"name","dockerfile","context"}]. Returns (admitted, denied)."""
    admitted, denied = [], []
    for img in images:
        name = img.get("name") or "?"
        entry = allowed_for(name, allow)
        findings = image_findings(img.get("dockerfile", ""), img.get("context", "."), repo_root)
        if findings:
            denied.append({"image": name, "findings": findings,
                           "grandfathered": entry.get("reason") if entry else None})
        else:
            admitted.append({"image": name, "grandfathered": entry.get("reason") if entry else None})
    return admitted, denied


def _dockerfiles_json(repo_root: str, extra: list[str]) -> list[dict]:
    script = os.path.join(repo_root, "bin", "dockerfiles")
    if not os.path.isfile(script):
        return []
    try:
        p = subprocess.run([script, "--json", *extra], cwd=repo_root, capture_output=True,
                           text=True, timeout=90)
        if p.returncode != 0:
            return []
        data = json.loads(p.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    out = []
    for item in data if isinstance(data, list) else []:
        if isinstance(item, dict):
            out.append({"name": item.get("name") or item.get("image") or "?",
                        "dockerfile": item.get("dockerfile") or "",
                        "context": item.get("context") or "."})
        elif isinstance(item, (list, tuple)) and len(item) >= 3:
            out.append({"name": item[0], "dockerfile": item[1], "context": item[2]})
    return out


def images_from_dockerfiles(repo_root: str) -> list[dict]:
    """Every image the estate builds (R24's one list)."""
    return _dockerfiles_json(repo_root, [])


def images_from_changed(repo_root: str, base: str) -> list[dict]:
    """Only the images a diff against <ref> reaches."""
    return _dockerfiles_json(repo_root, ["--changed-since", base])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Rust-only admission gate for the k3s spine")
    ap.add_argument("--repo-root", default=os.getcwd(),
                    help="repository root (default: the current directory)")
    ap.add_argument("--context", default="", help="scan one build context")
    ap.add_argument("--dockerfile", default="", help="the Dockerfile that builds that context")
    ap.add_argument("--image", default="", help="the image name the context builds")
    ap.add_argument("--allowlist", default="", help="policy/rust-only-allowlist.json")
    ap.add_argument("--base", default="", help="scan only the images a diff against <ref> reaches")
    ap.add_argument("--json", action="store_true", help="print the verdict as JSON")
    args = ap.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)
    allowlist = args.allowlist or os.path.join(repo_root, "policy", "rust-only-allowlist.json")
    allow = load_allowlist(allowlist)

    if args.context:
        images = [{"name": args.image or os.path.basename(os.path.abspath(args.context)),
                   "dockerfile": args.dockerfile,
                   "context": args.context}]
    elif args.base:
        images = images_from_changed(repo_root, args.base)
        if not images:
            print(f"{OK_MESSAGE}: no image is reached by the diff against {args.base}; nothing to admit")
            return EXIT_OK
    else:
        images = images_from_dockerfiles(repo_root)
        if not images:
            print(f"{OK_MESSAGE}: no image list found (bin/dockerfiles); nothing to admit")
            return EXIT_OK

    admitted, denied = check_images(images, allow, repo_root)
    hard_denied = [d for d in denied if not d.get("grandfathered")]

    if args.json:
        print(json.dumps({
            "verdict": "DENIED" if hard_denied else "ADMITTED",
            "message": DENY_MESSAGE if hard_denied else OK_MESSAGE,
            "admitted": admitted,
            "denied": denied,
        }, indent=2))
        return EXIT_DENIED if hard_denied else EXIT_OK

    if hard_denied:
        print(DENY_MESSAGE)
        for d in hard_denied:
            print(f"  image {d['image']}:")
            for f in d["findings"]:
                where = f"{f['path']}:{f['line']}" if f.get("line") else f["path"]
                print(f"    {f['kind']}: {where} ({f.get('detail', '')})")
        print(f"  {len(hard_denied)} image(s) refused; "
              f"{len(denied) - len(hard_denied)} grandfathered legacy image(s) admitted")
        return EXIT_DENIED

    for d in denied:
        print(f"  grandfathered: {d['image']} -- {d['grandfathered']}")
    print(f"{OK_MESSAGE}: {len(admitted)} image(s) admitted, {len(denied)} grandfathered "
          f"({len(hard_denied)} refused)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
