from datetime import datetime, timezone
from .shapes import subsumes


class Refuse(Exception):
    pass


def _check_ttl(registry: dict) -> None:
    gen = registry.get("generated_at")
    ttl = registry.get("ttl_seconds", 3600)
    if not gen:
        raise Refuse("registry missing generated_at")
    age = (
        datetime.now(timezone.utc) - datetime.fromisoformat(gen.replace("Z", "+00:00"))
    ).total_seconds()
    if age > ttl:
        raise Refuse(f"registry stale: age={age:.0f}s > ttl={ttl}s")


def resolve(order: dict, registry: dict) -> dict:
    _check_ttl(registry)
    index = {}
    for t in registry["terminals"]:
        index.setdefault(t["id"], []).append(t)

    resolved, unresolved = [], []
    for req in order["capabilities"]:
        req_id = req["id"]
        candidates = index.get(req_id, [])
        if req.get("shape"):
            candidates = [
                t
                for t in registry["terminals"]
                if t.get("state") == "current"
                and subsumes(t["output"]["shape"], req["shape"])
            ]
        current = [t for t in candidates if t.get("state") == "current"]
        if not current:
            unresolved.append({"id": req_id, "reason": "NOT_FOUND_OR_NOT_CURRENT"})
            continue
        if len(current) > 1 and not req.get("shape"):
            unresolved.append({"id": req_id, "reason": "AMBIGUOUS"})
            continue
        chosen = current[0]
        ann = chosen.get("annotations", {})
        if order["tenant_id"].startswith("ten_") and not ann.get("scope", {}).get(
            "tenant_isolated", False
        ):
            unresolved.append({"id": req_id, "reason": "TENANT_BOUNDARY_VIOLATION"})
            continue
        if req.get("mode") and ann.get("mode") and ann["mode"] != req["mode"]:
            unresolved.append({"id": req_id, "reason": "MODE_MISMATCH"})
            continue
        resolved.append(
            {
                "id": chosen["id"],
                "source_repo": chosen.get("source_repo", "unknown"),
                "state": chosen["state"],
                "input_shape": chosen["input"]["shape"],
                "output_shape": chosen["output"]["shape"],
                "grade": chosen["grade"],
                "annotations": ann,
            }
        )

    chain_errors = []
    # py3.9 runtime target cannot use zip(..., strict=); the offset pairing below
    # is deliberate (resolved[i] feeds resolved[i+1]), so B905's truncation
    # concern does not apply.
    for a, b in zip(resolved, resolved[1:]):  # noqa: B905
        if not subsumes(a["output_shape"], b["input_shape"]):
            chain_errors.append(
                {
                    "from": a["id"],
                    "to": b["id"],
                    "reason": f"{a['output_shape']} does not subsume {b['input_shape']}",
                }
            )

    return {
        "order_id": order["order_id"],
        "tenant_id": order["tenant_id"],
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "resolved": resolved,
        "unresolved": unresolved,
        "chain_errors": chain_errors,
    }
