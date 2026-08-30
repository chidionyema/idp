"""crew#561, founder 2026-08-30: "OTTO CLAIMS NO ACCESS TO GITHUB OR MAC".

otto-parity had passed (run 33285885139) while the agent in Telegram said it had no access: the
playbook graded what an operator could exec (ssh key, mac-run), not what the agent's own tools
see. The image had no `gh`, and no skill named `mac-run` (hermes-v2#56). The playbook now grades
both, and this test refuses a playbook that drops any of the three rows.
"""

from pathlib import Path

PLAYBOOK = Path(__file__).resolve().parents[1] / "bin" / "idp-oke-break-glass"


def _parity_block() -> str:
    text = PLAYBOOK.read_text()
    start = text.index("step mac-run-hostname")
    return text[start : text.index("show model-lane", start)]


def test_parity_runs_gh_inside_the_gateway_container():
    block = _parity_block()
    assert "step gh-installed" in block and "gh --version" in block
    assert "step gh-token-works" in block and "gh api user" in block


def test_parity_checks_the_rendered_founder_mac_skill():
    block = _parity_block()
    assert "step founder-mac-skill" in block
    assert "/data/skills/founder-mac/SKILL.md" in block
    assert "mac-run hostname" in block
