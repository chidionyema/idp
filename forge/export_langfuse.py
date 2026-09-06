"""Langfuse dataset name in, dataset.jsonl with a deterministic 80/20 split out."""

import json
import os
import sys

from langfuse import Langfuse

from common import split


def main() -> None:
    lf = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ["LANGFUSE_HOST"],
    )
    name = os.environ.get("DATASET_NAME", "voice-gate")
    out = os.environ.get("DATASET_OUT", "dataset.jsonl")
    ds = lf.get_dataset(name)
    records = [
        {
            "input": item.input.get("text", ""),
            "output": str(item.expected_output.get("label", "")).strip(),
        }
        for item in ds.items
    ]
    rows = split(records)
    with open(out, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    n_train = sum(1 for r in rows if r["split"] == "train")
    print(
        f"exported {n_train} train, {len(rows) - n_train} eval to {out}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
