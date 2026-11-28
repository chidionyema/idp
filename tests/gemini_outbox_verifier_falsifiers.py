"""Optimus measure: gemini_outbox.verifier_falsifiers_declared.

Prints `optimus.gemini_outbox.verifier_falsifiers_declared=<n>`: the number of `#[test]`
falsifiers declared in the Gemini outbox verifier crate
(platform/meridian-core-engines/crates/meridian-outbox-ingest). 0 when the crate is absent.

What this measures and what it does not. It COUNTS declared tests; it does not run them, because
the Greenlane judge is not promised a Rust toolchain and a measure must need no cluster or
secret. That the tests PASS is proved by `cargo test --workspace --locked` in
.github/workflows/meridian-core-engines.yml, which runs on every change to the crate. Read this
number as "the falsifier set exists and has not shrunk", never as "the verifier is green".

Stdlib only.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
CRATE = (
    ROOT / "platform" / "meridian-core-engines" / "crates" / "meridian-outbox-ingest"
)
# `#[test]` at the start of a line (after indentation): not a mention in a comment or a string.
TEST_ATTR = re.compile(r"^\s*#\[test\]\s*$", re.MULTILINE)


def declared_falsifiers(crate: pathlib.Path = CRATE) -> int:
    total = 0
    for sub in ("src", "tests"):
        base = crate / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.rs")):
            total += len(
                TEST_ATTR.findall(path.read_text(encoding="utf-8", errors="replace"))
            )
    return total


def main() -> int:
    print(f"optimus.gemini_outbox.verifier_falsifiers_declared={declared_falsifiers()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
