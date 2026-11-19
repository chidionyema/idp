"""The sandbox lane must consume the admission primitive it ships (#8265).

#8265 landed two separate acts in bin/idp-agent-base-apply.py:
--admit-paths-json serialises the admitted scope, and
--scope-file/--scope-sha256 make submission consume it. A lane that calls the
applicator with --base-file and --patch alone leaves allowed=None, so the
primitive refuses nothing the lane actually reaches.
"""

from __future__ import annotations

from pathlib import Path

WF = Path(__file__).resolve().parents[1] / ".github/workflows/agent-sandbox.yml"


def _lines() -> list[str]:
    return WF.read_text(encoding="utf-8").splitlines()


def _submit() -> list[str]:
    joined = "".join(
        l.rstrip()[:-1] if l.rstrip().endswith("\\") else l + "\n" for l in _lines()
    )
    return [l for l in joined.splitlines() if "idp-agent-base-apply.py" in l]


def test_the_lane_admits_before_it_stages() -> None:
    text = WF.read_text(encoding="utf-8")
    assert "--admit-paths-json" in text, (
        "the lane never serialises an admitted scope (#8265)"
    )


def test_submission_consumes_the_scope_it_admitted() -> None:
    calls = _submit()
    assert calls, "the lane no longer calls the applicator at all"
    for line in calls:
        assert "--admit-paths-json" in line or (
            "--scope-file" in line and "--scope-sha256" in line
        ), f"applicator called without a bound scope: {line.strip()}"
