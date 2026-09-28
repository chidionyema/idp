"""A proposal the execution stage accepts, so a sealed claim may leave.

All three stages run: these bytes compile (structural), the declared guard contract is
satisfiable (symbolic), and this exits 0 from the sterile tree the execution stage
builds (execution). Only then is an attestation minted, and its subject is the SHA-256
of these exact bytes -- not of a filename, not of a patch that once looked like this.

The gate then proves the seal is bound to content by presenting a different subject
and reading the refusal.
"""

import sys


def main() -> int:
    # The claim the proposal carries is the one its execution stage proves.
    return 0


if __name__ == "__main__":
    sys.exit(main())
