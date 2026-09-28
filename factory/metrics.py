import yaml
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def _registry():
    p = Path(__file__).resolve().parent / "schemas" / "metrics.yaml"
    data = yaml.safe_load(p.read_text())["metric_registry"]
    return {f["name"]: f for f in data["families"]}


def family(name: str) -> dict:
    f = _registry().get(name)
    if f is None:
        raise ValueError(f"metric not registered: {name}")
    return f


def comparable(a: str, b: str) -> bool:
    return b in family(a)["comparable_with"]


def validate(grade: dict) -> None:
    f = family(grade["metric"])
    if grade.get("polarity") != f["polarity"]:
        raise ValueError(f"polarity mismatch for {grade['metric']}")
