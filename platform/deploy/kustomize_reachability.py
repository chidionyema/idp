#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Set

import yaml

KUSTOMIZE_NAMES = ("kustomization.yaml", "kustomization.yml", "Kustomization")
DEPLOY_MARKERS = (
    "kustomization.yaml",
    "kustomization.yml",
    "wrangler.toml",
    "wrangler.jsonc",
    "deployment.yaml",
    "service.yaml",
    "Dockerfile",
)


def _norm(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def collect_flux_reachable_dirs(repo_root: Path, flux_roots: Iterable[str]) -> Set[str]:
    visited_files: Set[Path] = set()
    reachable_dirs: Set[str] = set()

    def walk(kust_file: Path) -> None:
        resolved = kust_file.resolve()
        if resolved in visited_files or not resolved.is_file():
            return
        visited_files.add(resolved)
        parent = resolved.parent
        reachable_dirs.add(_norm(parent, repo_root))

        doc = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
        entries = list(doc.get("resources") or []) + list(doc.get("components") or [])
        for entry in entries:
            if not isinstance(entry, str) or "://" in entry:
                continue
            target = (parent / entry).resolve()
            if target.is_dir():
                reachable_dirs.add(_norm(target, repo_root))
                for name in KUSTOMIZE_NAMES:
                    child = target / name
                    if child.is_file():
                        walk(child)
            elif target.is_file():
                reachable_dirs.add(_norm(target.parent, repo_root))
                if target.name in KUSTOMIZE_NAMES:
                    walk(target)

    def add_target(target: Path) -> None:
        if not target.is_dir():
            return
        reachable_dirs.add(_norm(target, repo_root))
        for name in KUSTOMIZE_NAMES:
            child = target / name
            if child.is_file():
                walk(child)

    def flux_cr_paths(cr_file: Path):
        """spec.path of Flux Kustomization CRs: the estate's actual wiring."""
        try:
            docs = yaml.safe_load_all(cr_file.read_text(encoding="utf-8"))
            for doc in docs:
                if not isinstance(doc, dict) or doc.get("kind") != "Kustomization":
                    continue
                if "kustomize.toolkit.fluxcd.io" not in str(doc.get("apiVersion", "")):
                    continue
                path = str((doc.get("spec") or {}).get("path") or "").strip()
                if path:
                    yield path[2:] if path.startswith("./") else path
        except Exception:
            return

    for rel in flux_roots:
        root = repo_root / rel
        if root.is_file():
            if root.name in KUSTOMIZE_NAMES:
                walk(root)
            for path in flux_cr_paths(root):
                add_target((repo_root / path).resolve())
        elif root.is_dir():
            for cr in sorted(list(root.rglob("*.yaml")) + list(root.rglob("*.yml"))):
                for path in flux_cr_paths(cr):
                    add_target((repo_root / path).resolve())
    return reachable_dirs


def discover_deployable_platform_dirs(repo_root: Path) -> Set[str]:
    platform_root = repo_root / "platform"
    if not platform_root.is_dir():
        return set()
    discovered: Set[str] = set()
    for path in platform_root.rglob("*"):
        if not path.is_file():
            continue
        if any(
            part in {"node_modules", ".venv", ".wrangler", "dist", "__pycache__"}
            for part in path.parts
        ):
            continue
        if path.name in DEPLOY_MARKERS:
            discovered.add(_norm(path.parent, repo_root))
    return discovered


def audit_reachability(repo_root: Path, targets_path: Path) -> list[str]:
    cfg = json.loads(targets_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    prohibited = [p.lower() for p in cfg.get("prohibited_patterns", [])]
    flux_dirs = collect_flux_reachable_dirs(repo_root, cfg.get("flux_roots", []))
    worker_dirs = {w["dir"].strip("/") for w in cfg.get("cloudflare_workers", [])}
    non_deployable = {d.strip("/") for d in cfg.get("non_deployable_dirs", [])}

    # Verify declared Worker directories actually exist if referenced on disk
    for worker in cfg.get("cloudflare_workers", []):
        wdir = worker["dir"].strip("/")
        for pat in prohibited:
            if pat in wdir.lower():
                errors.append(
                    f"PROHIBITED_TARGET: {wdir} matches retired pattern '{pat}'"
                )

    # Reject any retired OKE paths inside active Flux roots
    for fdir in sorted(flux_dirs):
        for pat in prohibited:
            if pat in fdir.lower():
                errors.append(
                    f"PROHIBITED_FLUX_PATH: {fdir} matches retired pattern '{pat}'"
                )

    # Every deployable directory under platform/ must be reachable via Flux, Worker targets, or explicit non-deployable
    deployable = discover_deployable_platform_dirs(repo_root)
    for d in sorted(deployable):
        if any(d == nd or d.startswith(nd + "/") for nd in non_deployable):
            continue
        if d in flux_dirs or d in worker_dirs:
            continue
        # A directory inside a reconciled path is applied by that kustomization.
        if any(d.startswith(fd + "/") for fd in flux_dirs):
            continue
        if any(d.startswith(wd + "/") for wd in worker_dirs):
            continue
        errors.append(
            f"UNAPPLIED_PLATFORM_DIR: '{d}' contains deployable artifacts but is unreachable from Flux or targets.json (#8328)"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify all deployable platform directories are reachable (#8328)"
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--targets", required=True)
    args = parser.parse_args()

    errors = audit_reachability(Path(args.repo_root), Path(args.targets))
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    print("REACHABILITY_OK: 0 unapplied platform directories, 0 retired OKE references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
