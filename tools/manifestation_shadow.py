#!/usr/bin/env python3
"""Read JSONL obligation events; emit shadow-only recommendations. No write authority."""
import json
import sys

def evaluate(events):
    obligations = {}
    for event in events:
        key = event["id"]
        kind = event["kind"]
        if kind == "concept":
            if key in obligations:
                raise ValueError("duplicate concept")
            obligations[key] = {"opened": int(event["time_ms"]), "settled": False}
        elif kind == "settled":
            if not event.get("verified_receipt"):
                raise ValueError("settlement requires receipt reference")
            obligations[key]["settled"] = True
        else:
            raise ValueError("unknown event")
    pending = sorted((k for k,v in obligations.items() if not v["settled"]),
                     key=lambda k: (obligations[k]["opened"], k))
    return {"authority": "NONE", "deficit": len(pending), "pending": pending,
            "recommendation": pending[0] if pending else None,
            "receipt_authentication": "NOT_IMPLEMENTED"}

if __name__ == "__main__":
    print(json.dumps(evaluate(json.loads(line) for line in sys.stdin if line.strip()), sort_keys=True))
