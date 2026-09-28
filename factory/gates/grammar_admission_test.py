from pathlib import Path
import yaml


def run() -> int:
    root = Path(__file__).resolve().parents[2] / "schemas"
    for name in ("shapes.yaml", "metrics.yaml", "grammar.yaml"):
        p = root / name
        if not p.exists():
            return 1
        try:
            yaml.safe_load(p.read_text())
        except Exception:
            return 2
    return 0
