import yaml
from pathlib import Path
from . import metrics

SCHEMAS = Path(__file__).resolve().parent / "schemas"


def bootstrap() -> dict:
    p = SCHEMAS / "grammar.yaml"
    if not p.exists():
        raise RuntimeError("schemas/grammar.yaml missing — cannot bootstrap")
    g = yaml.safe_load(p.read_text())["terminal"]
    if g["id"] != "grammar":
        raise RuntimeError("grammar.yaml is not the grammar")
    return {"terminals": [g], "needs": []}


REQUIRED = ("id", "name", "input", "output", "grade", "state", "since")


def validate_terminal(t: dict, registry_ids: set[str]) -> list[str]:
    errs = []
    for f in REQUIRED:
        if f not in t:
            errs.append(f"missing field: {f}")
    if errs:
        return errs
    if not isinstance(t.get("input"), dict) or "shape" not in t["input"]:
        errs.append("input.shape missing")
    if not isinstance(t.get("output"), dict) or "shape" not in t["output"]:
        errs.append("output.shape missing")
    g = t.get("grade")
    if not isinstance(g, dict):
        errs.append("grade must be an object")
        return errs
    try:
        metrics.validate(g)
    except ValueError as e:
        errs.append(str(e))
    gate = g.get("gate")
    if not isinstance(gate, dict):
        errs.append("grade.gate must be an object (not a raw string)")
    else:
        if (
            gate.get("terminal") not in registry_ids
            and gate.get("terminal") != "grammar.admission_test"
        ):
            errs.append(f"gate terminal not registered: {gate.get('terminal')}")
        if gate.get("sandbox") not in (
            "subprocess",
            "kronos.ring0",
            "kronos.ring1",
            "docker",
        ):
            errs.append(f"sandbox not permitted: {gate.get('sandbox')}")
    ann = t.get("annotations") or {}
    for k, v in (ann.get("scope", {}).get("secrets") or {}).items():
        if not isinstance(v, str) or not v.startswith("vault://"):
            errs.append(f"secret {k} is not a vault:// reference")
    return errs
