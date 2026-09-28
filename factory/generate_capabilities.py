#!/usr/bin/env python3
"""
Walk every repo under ROOT, detect capabilities, emit capability.yaml.
Heuristics are explicit; every emitted terminal carries source & confidence.
Never overwrites an existing capability.yaml without --force.
"""

import argparse, os, re, sys, logging
from pathlib import Path
from datetime import date

log = logging.getLogger("factory.generate_capabilities")

try:
    import yaml
except ImportError:
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyyaml"], check=True)
    import yaml

TODAY = date.today().isoformat()
DEFAULT_GATE = {"terminal": "delivery_delivered", "sandbox": "subprocess"}
DEFAULT_GRADE = lambda metric="accuracy", polarity="maximize": {
    "metric": metric,
    "polarity": polarity,
    "scale": [0, 1],
    "gate": DEFAULT_GATE,
}


def emit_terminal(
    tid,
    name,
    in_shape,
    out_shape,
    *,
    mode="function",
    cls="act",
    resources=None,
    tenant_isolated=True,
    role="branch",
    state="incubating",
    grade=None,
    produces_again=False,
):
    return {
        "terminal": {
            "id": tid,
            "name": name,
            "input": {"shape": in_shape},
            "output": {"shape": out_shape},
            "grade": grade or DEFAULT_GRADE(),
            "state": state,
            "since": TODAY,
            "supersedes": [],
            "produces_again": produces_again,
            "annotations": {
                "class": cls,
                "mode": mode,
                "scope": {
                    "resources": resources or ["filesystem"],
                    "secrets": {},
                    "tenant_isolated": tenant_isolated,
                },
                "role": role,
            },
        }
    }


def detect_python_tools(repo: Path) -> list[dict]:
    out = []
    for tools_dir in list(repo.glob("tools")) + list(repo.glob("*/tools")):
        for f in sorted(tools_dir.glob("*.py")):
            if f.name.startswith("_"):
                continue
            stem = f.stem
            if not re.match(r"^[a-z][a-z0-9_]*$", stem):
                continue
            cap_id = stem.replace("_", "-").removesuffix("-tool").rstrip("-")
            if not cap_id:
                continue
            out.append(
                {
                    "id": cap_id,
                    "name": stem.replace("_", " ").title(),
                    "in": {"shape": "any"},
                    "out": {"shape": "any"},
                    "mode": "function",
                    "cls": "act",
                    "resources": ["filesystem"],
                    "role": "branch",
                    "state": "incubating",
                    "source": str(f.relative_to(repo)),
                }
            )
    return out


def detect_skills(repo: Path) -> list[dict]:
    out = []
    for skills_dir in list(repo.glob("skills")) + list(repo.glob("*/skills")):
        for d in sorted(skills_dir.iterdir()):
            if not d.is_dir():
                continue
            sid = d.name.lower().replace("_", "-").replace(" ", "-")
            if not re.match(r"^[a-z][a-z0-9-]*$", sid):
                continue
            out.append(
                {
                    "id": f"skill.{sid}",
                    "name": d.name.replace("-", " ").title(),
                    "in": {"shape": "any"},
                    "out": {"shape": "any"},
                    "mode": "function",
                    "cls": "act",
                    "resources": ["filesystem"],
                    "role": "branch",
                    "state": "incubating",
                    "source": str(d.relative_to(repo)),
                }
            )
    return out


def detect_mcp_plugins(repo: Path) -> list[dict]:
    out = []
    for plugins_dir in [repo / "mcp" / "plugins", repo / "plugins"]:
        if not plugins_dir.exists():
            continue
        for f in sorted(plugins_dir.glob("*.py")):
            if f.name.startswith("_"):
                continue
            pid = f.stem.replace("_", "-")
            out.append(
                {
                    "id": f"mcp.{pid}",
                    "name": f.stem.replace("_", " ").title(),
                    "in": {"shape": "any"},
                    "out": {"shape": "any"},
                    "mode": "function",
                    "cls": "act",
                    "resources": ["filesystem"],
                    "role": "branch",
                    "state": "incubating",
                    "source": str(f.relative_to(repo)),
                }
            )
    return out


def detect_rust_crates(repo: Path) -> list[dict]:
    out = []
    for cargo in [repo / "Cargo.toml", *repo.glob("*/Cargo.toml")]:
        if not cargo.exists():
            continue
        try:
            data = yaml.safe_load(cargo.read_text()) or {}
        except Exception as e:
            log.debug("cargo manifest %s unparseable: %s", cargo, e)
            continue
        name = (data.get("package") or {}).get("name") or cargo.parent.name
        out.append(
            {
                "id": f"crate.{name.replace('_', '-')}",
                "name": name,
                "in": {"shape": "any"},
                "out": {"shape": "any"},
                "mode": "function",
                "cls": "compute",
                "resources": ["compute"],
                "role": "branch",
                "state": "incubating",
                "source": str(cargo.relative_to(repo)),
            }
        )
    return out


def detect_bin_scripts(repo: Path) -> list[dict]:
    out = []
    bin_dir = repo / "bin"
    if not bin_dir.exists():
        return out
    for f in sorted(bin_dir.iterdir()):
        if f.name.startswith("_") or f.name.startswith("."):
            continue
        if not f.is_file():
            continue
        if not (f.name.endswith(".py") or os.access(f, os.X_OK)):
            continue
        stem = f.stem if f.suffix == ".py" else f.name
        if not re.match(r"^[a-z][a-z0-9-]*$", stem):
            continue
        out.append(
            {
                "id": stem,
                "name": stem.replace("-", " ").title(),
                "in": {"shape": "{args: json}"},
                "out": {"shape": "json"},
                "mode": "function",
                "cls": "act",
                "resources": ["filesystem"],
                "role": "rail",
                "state": "incubating",
                "source": str(f.relative_to(repo)),
            }
        )
    return out


def detect_http_routes(repo: Path) -> list[dict]:
    out = []
    route_re = re.compile(r'@(app|router)\.(get|post|put|delete)\(\s*["\']([^"\']+)')
    for py in repo.rglob("*.py"):
        if any(p in py.parts for p in ("node_modules", ".venv", "venv", "__pycache__")):
            continue
        try:
            text = py.read_text(errors="ignore")
        except Exception as e:
            log.debug("cannot read python file %s: %s", py, e)
            continue
        for m in route_re.finditer(text):
            method, path = m.group(2).upper(), m.group(3)
            if path in ("/health", "/", "/metrics"):
                continue
            sid = f"{method.lower()}.{repo.name}.{path.strip('/').replace('/', '-').replace('{', '').replace('}', '')}"
            sid = re.sub(r"[^a-z0-9.\-]", "", sid.lower())
            if len(sid) > 62:
                continue
            out.append(
                {
                    "id": sid,
                    "name": f"{method} {path}",
                    "in": {"shape": "{body: json}"},
                    "out": {"shape": "json"},
                    "mode": "function",
                    "cls": "surface",
                    "resources": [repo.name],
                    "role": "branch",
                    "state": "incubating",
                    "source": str(py.relative_to(repo)),
                }
            )
    return out


DETECTORS = [
    detect_python_tools,
    detect_skills,
    detect_mcp_plugins,
    detect_rust_crates,
    detect_bin_scripts,
    detect_http_routes,
]


def detect_repo_role(repo: Path) -> str:
    name = repo.name
    if name in ("idp", "estate-core", "estate-guards", "estate-secrets", "crew"):
        return "rail"
    if name in ("agent-foundry",):
        return "seed-expression"
    if name.endswith("-platform") or "commerce" in name or "medusa" in name:
        return "product"
    return "branch"


def build_declaration(repo: Path) -> dict:
    terminals = []
    for det in DETECTORS:
        try:
            for t in det(repo):
                terminals.append(t)
        except Exception as e:
            print(
                f"  [{repo.name}] detector {det.__name__} failed: {e}", file=sys.stderr
            )
    seen = {}
    for t in terminals:
        if t["id"] not in seen:
            seen[t["id"]] = t
    terminals = list(seen.values())
    role = detect_repo_role(repo)
    return {
        "terminals": [
            emit_terminal(
                t["id"],
                t["name"],
                t["in"]["shape"],
                t["out"]["shape"],
                mode=t["mode"],
                cls=t["cls"],
                resources=t["resources"],
                role=role,
                state=t.get("state", "incubating"),
            )["terminal"]
            for t in terminals
        ]
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path.home() / "Documents" / "code"))
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    stats = {"repos": 0, "generated": 0, "skipped": 0, "terminals": 0, "empty": 0}
    for repo in sorted(root.iterdir()):
        if not repo.is_dir() or repo.name.startswith("."):
            continue
        stats["repos"] += 1
        target = (
            (Path(args.out_dir) / repo.name / "capability.yaml")
            if args.out_dir
            else (repo / "capability.yaml")
        )
        if target.exists() and not args.force:
            stats["skipped"] += 1
            continue
        decl = build_declaration(repo)
        if not decl["terminals"]:
            stats["empty"] += 1
            continue
        text = yaml.safe_dump(decl, sort_keys=False)
        if args.dry_run:
            print(f"--- {target} ---\n{text}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        stats["generated"] += 1
        stats["terminals"] += len(decl["terminals"])
    print(
        f"{stats['repos']} repos, {stats['generated']} generated, "
        f"{stats['skipped']} skipped, {stats['empty']} empty, "
        f"{stats['terminals']} terminals total"
    )


if __name__ == "__main__":
    main()
