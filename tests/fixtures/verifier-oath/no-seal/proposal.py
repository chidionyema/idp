"""A proposal whose execution stage refuses.

The structural stage passes -- these bytes compile -- and that is the point: a
proposal can be perfectly valid Python and still carry no proof. The execution stage
runs it in a sterile tree and reads the exit code, which is 1. So the claim is
refused and no attestation is minted.

This is the fixture the founder's sentence describes: "the fact u are able toi lie
eans he his rules isnt operation al". Valid syntax is not evidence.
"""

import sys


def main() -> int:
    # The proof the proposal claims to carry does not hold.
    return 1


if __name__ == "__main__":
    sys.exit(main())
