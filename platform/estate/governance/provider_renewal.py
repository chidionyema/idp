"""Governance bound to the model provider: repeated violations end the subscription.

THE FOUNDER'S RULE (2026-10-29): "bind the governance and enforcement to the model provider so
that repeated violations by a model provider means that provider's estate subscription is not
renewed".

So the provider is not a detail of a violation record, it is the thing that pays for it. A
provider whose sessions keep breaking the estate's laws loses its lanes: the rendered router
configuration drops its models, so the estate stops paying for it and stops routing to it.

THE STATE. Two copies, both machine-readable:

    platform/vendors/renewals.yaml       the committed record (the renderer's source of truth)
    ~/.estate/state/provider-renewals.json the live copy the local router reads

THE THRESHOLD. Two violations of any class from one provider end the renewal. One is noise;
two is a pattern. The founder's words: "repeated violations".

THE EFFECT. bin/idp-vendor-render drops every model of a denied provider when it renders the
router config, and the rendered config is what the estate actually routes through. A denial
that only lives in a report is not a denial; a denial that removes the lane is.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from . import ledger

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RENEWAL_FILE = os.path.join(REPO_ROOT, "platform", "vendors", "renewals.yaml")
RUNTIME_FILE = os.path.join(ledger.state_home(), "provider-renewals.json")

THRESHOLD = 2

HEADER = """# Provider renewals: the committed record of who the estate still pays for.
#
# A model provider whose sessions keep breaking the estate's laws loses its renewal, and a
# provider without a renewal has no lanes: bin/idp-vendor-render drops its models from the
# rendered router configuration, which is what the estate routes through.
#
#   renewals:
#     <provider>:
#       status: granted | denied
#       violations: <count>
#       threshold: <count at which the renewal is denied>
#       evidence: [<iso ts>, ...]
#       decided_at: <iso ts>
#
# The threshold is 2 violations of any class from one provider: one is noise, two is a
# pattern. The live copy the local router reads is ~/.estate/state/provider-renewals.json.
# The record is written by bin/estate-provider-renewal; it is never edited by hand, so a
# verdict always carries the evidence that produced it.
"""


def _load_yaml(path: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def evaluate(threshold: int = THRESHOLD) -> Dict[str, Any]:
    """The provider's violation counts, and the verdict that follows from them."""
    counts = ledger.provider_counts()
    rows = []
    for provider, count in sorted(counts.items()):
        rows.append(
            {
                "provider": provider,
                "violations": count,
                "status": "denied" if count >= threshold else "granted",
                "threshold": threshold,
                "evidence": [
                    v.get("ts") for v in ledger.violations(provider=provider)[-5:]
                ],
            }
        )
    return {
        "renewals": rows,
        "denied": [r["provider"] for r in rows if r["status"] == "denied"],
        "threshold": threshold,
        "ts": ledger.now(),
    }


def write_yaml(report: Dict[str, Any], path: str = RENEWAL_FILE) -> str:
    """Write the committed record. The format is the same yaml the renderer reads."""
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pyyaml is required to write the renewal record") from exc
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = {
        "renewals": {
            row["provider"]: {
                "status": row["status"],
                "violations": row["violations"],
                "threshold": row["threshold"],
                "evidence": row["evidence"],
                "decided_at": report.get("ts"),
            }
            for row in report.get("renewals", [])
        }
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(HEADER)
        yaml.safe_dump(body, f, sort_keys=True, default_flow_style=False)
    os.replace(tmp, path)
    return path


def write_runtime(report: Dict[str, Any], path: str = RUNTIME_FILE) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    os.replace(tmp, path)
    return path


def denied_providers(path: str = RENEWAL_FILE) -> List[str]:
    """The providers whose renewal is denied, read from the committed record."""
    data = _load_yaml(path)
    rows = data.get("renewals") or {}
    out = []
    for provider, body in rows.items():
        if isinstance(body, dict) and body.get("status") == "denied":
            out.append(provider)
    return sorted(out)


def status(path: str = RENEWAL_FILE) -> Dict[str, Any]:
    data = _load_yaml(path)
    return data.get("renewals") or {}


def apply(report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Evaluate, write both records, and say what the renderer will now drop."""
    report = report or evaluate()
    written = []
    try:
        written.append(write_yaml(report))
    except RuntimeError:
        pass
    written.append(write_runtime(report))
    return {
        "denied": report.get("denied", []),
        "written": written,
        "renewals": report.get("renewals", []),
    }
