import yaml
from pathlib import Path
from datetime import datetime, timezone
from . import grammar
from .ledger import write as ledger_write


def collect(root: Path) -> dict:
    reg = grammar.bootstrap()
    warnings = []
    seen_repos = 0
    for repo in sorted(root.iterdir()):
        if not repo.is_dir() or repo.name.startswith("."):
            continue
        decl = repo / "capability.yaml"
        if not decl.exists():
            continue
        seen_repos += 1
        try:
            data = yaml.safe_load(decl.read_text())
        except Exception as e:
            warnings.append(f"YAML_ERROR {repo.name}: {e}")
            continue
        if not isinstance(data, dict):
            warnings.append(f"NOT_A_MAPPING {repo.name}")
            continue
        terms = [data["terminal"]] if "terminal" in data else data.get("terminals", [])
        # Unwrap the {terminal: {...}} wrapper if present
        terms = [
            t["terminal"] if isinstance(t, dict) and "terminal" in t else t
            for t in terms
        ]
        for t in terms:
            if not isinstance(t, dict):
                continue
            ids = {x["id"] for x in reg["terminals"]}
            errs = grammar.validate_terminal(t, ids)
            if errs:
                warnings.extend(f"{repo.name}:{t.get('id', '?')}: {e}" for e in errs)
                continue
            t["source_repo"] = repo.name
            reg["terminals"].append(t)
    reg["generated_at"] = datetime.now(timezone.utc).isoformat()
    reg["ttl_seconds"] = 3600
    reg["count"] = len(reg["terminals"])
    reg["repos_seen"] = seen_repos
    reg["warnings"] = warnings
    reg["seed_repo"] = "grammar"
    return reg


def save(reg: dict, path: Path) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg, indent=2, sort_keys=True))
