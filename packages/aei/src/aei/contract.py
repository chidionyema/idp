"""Validate mandatory component observability manifests against a strict schema."""

import argparse
import json
from pathlib import Path
from .core import FAMILIES

REQUIRED = (
    "schema",
    "component",
    "version",
    "owner",
    "dependencies",
    "events",
    "metrics",
    "correlation",
    "visualisations",
    "acceptance",
)
VIEWS = {
    "waterfall",
    "problem_graph",
    "comparison",
    "waste",
    "scorecard",
    "optimisation_map",
}


def validate_manifest(d):
    if not isinstance(d, dict):
        raise ValueError("manifest must be object")
    for k in REQUIRED:
        if k not in d:
            raise ValueError(f"missing {k}")
    if d["schema"] != "aei.manifest.v1":
        raise ValueError("unsupported manifest")
    for k in ("component", "version", "owner"):
        if not isinstance(d[k], str) or not d[k].strip():
            raise ValueError(f"invalid {k}")
    for k in ("dependencies", "events", "metrics", "visualisations", "acceptance"):
        if not isinstance(d[k], list) or not d[k]:
            raise ValueError(f"empty {k}")
    if not set(d["events"]).issubset(FAMILIES):
        raise ValueError("unknown event family")
    if not isinstance(d["correlation"], dict) or not set(
        ("run_id", "task_id", "trace_id")
    ).issubset(d["correlation"]):
        raise ValueError("missing correlation keys")
    for m in d["metrics"]:
        if not isinstance(m, dict) or not set(
            ("name", "unit", "source", "reliability")
        ).issubset(m):
            raise ValueError("metric provenance incomplete")
    for v in d["visualisations"]:
        if (
            not isinstance(v, dict)
            or v.get("type") not in VIEWS
            or not v.get("evidence_field")
        ):
            raise ValueError("visualisation lacks evidence link")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("paths", nargs="+")
    args = p.parse_args()
    for path in args.paths:
        validate_manifest(json.loads(Path(path).read_text()))
        print("PASS", path)


if __name__ == "__main__":
    main()
