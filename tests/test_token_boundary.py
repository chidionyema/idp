"""The token door's boundary must read the SEED mint, not only the OCI mint.

Run 44078567589: app.seed outcome=success, yet assert_boundary read
steps.mint.outputs.token (the skipped OCI path) and failed
GITHUB_APP_TOKEN_EMPTY_AT_BOUNDARY. The boundary may never ignore a live mint.
"""

from pathlib import Path

ACTION = (
    Path(__file__).resolve().parents[1] / ".github/actions/github-app-token/action.yml"
)
WANT = "MINTED: ${{ steps.seed.outputs.token || steps.mint.outputs.token }}"


def test_boundary_reads_the_seed_mint():
    assert WANT in ACTION.read_text()
