#!/usr/bin/env python3
"""Drop-in CLI gate for bin/pre-push-wall.py, Lane 3 GitHub Actions, and Lane 2 OCI.

Exit codes:
  0  - Gate passed
  42 - Epistemic defect detected (fail-closed)
  2  - Usage / input error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from epistemic_kernel import EpistemicKernel, SignedReceipt


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Meridian Epistemic Falsification Gate")
    parser.add_argument("--mode", choices=["diagnosis", "operational"], required=True)
    parser.add_argument("--input", required=True, help="Path to envelope/contract JSON")
    parser.add_argument("--receipts", required=True, help="Path to signed receipts JSON array")
    parser.add_argument(
        "--authorities",
        default=os.environ.get("EPISTEMIC_TRUSTED_AUTHORITIES", "gh-actions-prober,cloudflare-prober,oci-blackbox-prober"),
        help="Comma-separated trusted non-agent capture authorities",
    )
    parser.add_argument("--max-age", type=int, default=3600)
    parser.add_argument("--min-fence", type=int, default=1)
    args = parser.parse_args(argv)

    secret = os.environ.get("ESTATE_RECEIPT_KEY", "")
    if not secret:
        print(json.dumps({"allowed": False, "verdict": "REJECTED_MISSING_KEY", "error_codes": ["ERR_MISSING_ESTATE_RECEIPT_KEY"]}))
        return 42

    payload = load_json(args.input)
    raw_receipts = load_json(args.receipts)
    receipts = [SignedReceipt(**item) for item in raw_receipts]
    authorities = [a.strip() for a in args.authorities.split(",") if a.strip()]

    kernel = EpistemicKernel(
        secret_key=secret.encode("utf-8"),
        trusted_authorities=authorities,
        max_receipt_age_seconds=args.max_age,
    )

    if args.mode == "diagnosis":
        decision = kernel.evaluate_diagnosis(payload, receipts, min_fencing_token=args.min_fence)
    else:
        decision = kernel.evaluate_operational_transition(payload, receipts, min_fencing_token=args.min_fence)

    print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
    return 0 if decision.allowed else 42


if __name__ == "__main__":
    sys.exit(main())
