"""The delegate-build loads the estate's artifact policy from the installed layout.

2026-10-24: the policy was staged into the router's modules dir only. The installed
delegate-build (~/.estate/libexec/delegate-build.py) looks next to itself -- ~/.estate/llm --
and found nothing, so every delegated plan died before it made a model call. The router and the
delegator must read the same bytes, so the installed copy wins over a stale checkout.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "platform/estate/libexec/delegate-build.py"
)


def _installed(tmp_path: Path):
    """A copy of the script in the installed layout, with the installed policy beside it."""
    home = tmp_path / ".estate"
    (home / "libexec").mkdir(parents=True)
    (home / "llm").mkdir(parents=True)
    installed = home / "libexec/delegate-build.py"
    shutil.copy2(SCRIPT, installed)
    (home / "llm/artifact_tier.py").write_text(
        "def default_policy():\n    return {'loaded': 'installed'}\n"
    )
    spec = importlib.util.spec_from_file_location("delegate_build_installed", installed)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_installed_policy_is_the_one_that_routes(tmp_path):
    mod = _installed(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    # The repo argument is a checkout with no policy in it -- the installed copy must win.
    assert mod.artifact_policy(str(repo)) == {"loaded": "installed"}


def test_the_checkout_policy_is_used_when_nothing_is_installed(tmp_path):
    mod = _installed(tmp_path)
    (tmp_path / ".estate/llm/artifact_tier.py").unlink()
    repo = tmp_path / "repo"
    (repo / "platform/llm").mkdir(parents=True)
    (repo / "platform/llm/artifact_tier.py").write_text(
        "def default_policy():\n    return {'loaded': 'checkout'}\n"
    )
    assert mod.artifact_policy(str(repo)) == {"loaded": "checkout"}


def test_a_missing_policy_is_an_error_not_a_guess(tmp_path):
    mod = _installed(tmp_path)
    (tmp_path / ".estate/llm/artifact_tier.py").unlink()
    repo = tmp_path / "repo"
    repo.mkdir()
    try:
        mod.artifact_policy(str(repo))
    except RuntimeError as exc:
        assert "artifact routing policy" in str(exc)
    else:
        raise AssertionError("a missing policy must not be silently defaulted")
