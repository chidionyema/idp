"""Incident crew#406 row 4, 2026-08-27: the GitHub App behind vault key github-app was never
created, so the github-app ExternalSecret never became Ready; alerts-secret (wait: true) held it,
`alerts` depended on alerts-secret, and the Telegram Provider was never applied. The rule: the
Kustomization that carries the Telegram Provider must not, through any dependsOn edge, wait on a
Kustomization whose path renders an ExternalSecret for the github-app vault key.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLUSTER = ROOT / "clusters" / "oke"


def _flux_kustomizations(files: list[Path]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in files:
        for d in yaml.safe_load_all(f.read_text()):
            if d and d.get("kind") == "Kustomization" and d.get("apiVersion", "").startswith("kustomize.toolkit"):
                out[d["metadata"]["name"]] = d
    return out


def _closure(ks: dict[str, dict], name: str) -> set[str]:
    seen, todo = set(), [name]
    while todo:
        n = todo.pop()
        if n in seen or n not in ks:
            continue
        seen.add(n)
        todo += [d["name"] for d in ks[n]["spec"].get("dependsOn", [])]
    return seen


def _renders_github_app(root: Path, path: str) -> bool:
    for f in (root / path).glob("*.yaml"):
        for d in yaml.safe_load_all(f.read_text()):
            if d and d.get("kind") == "ExternalSecret":
                keys = [x.get("extract", {}).get("key") for x in d["spec"].get("dataFrom", [])]
                keys += [x.get("remoteRef", {}).get("key") for x in d["spec"].get("data", [])]
                if "github-app" in keys:
                    return True
    return False


def _carries_telegram(root: Path, path: str) -> bool:
    return any(
        d and d.get("kind") == "Provider" and d["spec"].get("type") == "telegram"
        for f in (root / path).glob("*.yaml") for d in yaml.safe_load_all(f.read_text())
    )


def waits_on_github_app(root: Path, ks: dict[str, dict]) -> list[str]:
    """Names of Kustomizations that carry the Telegram Provider and wait on the github-app secret."""
    bad = []
    for name, k in ks.items():
        if not _carries_telegram(root, k["spec"]["path"]):
            continue
        for dep in _closure(ks, name) - {name}:
            if _renders_github_app(root, ks[dep]["spec"]["path"]):
                bad.append(f"{name} -> {dep} ({ks[dep]['spec']['path']})")
    return bad


def test_the_telegram_alerts_kustomization_never_waits_on_the_github_app() -> None:
    ks = _flux_kustomizations(sorted(CLUSTER.glob("*.yaml")))
    assert "alerts" in ks and "alerts-github" in ks
    assert _carries_telegram(ROOT, ks["alerts"]["spec"]["path"])
    assert _renders_github_app(ROOT, ks["alerts-github"]["spec"]["path"]), "the ledger's own path holds the App secret"
    assert waits_on_github_app(ROOT, ks) == []


def test_the_rule_refuses_the_chain_that_bit(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir(); (tmp_path / "s").mkdir()
    (tmp_path / "a" / "p.yaml").write_text("kind: Provider\nspec: {type: telegram}\n")
    (tmp_path / "s" / "g.yaml").write_text(
        "kind: ExternalSecret\nspec:\n  dataFrom:\n    - extract: {key: github-app}\n")
    ks = {
        "alerts": {"spec": {"path": "./a", "dependsOn": [{"name": "alerts-secret"}]}},
        "alerts-secret": {"spec": {"path": "./s", "dependsOn": [{"name": "secret-store"}]}},
    }
    assert waits_on_github_app(tmp_path, ks) == ["alerts -> alerts-secret (./s)"]
    ks["alerts"]["spec"]["dependsOn"] = []
    assert waits_on_github_app(tmp_path, ks) == []
