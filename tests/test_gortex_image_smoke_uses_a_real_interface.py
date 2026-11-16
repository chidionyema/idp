"""The gortex image smoke step must call an interface the CLI actually has.

build-multiarch run 43774918311 on main died on BOTH arches at `gortex --version`
("unknown flag: --version"), reddening every main build. A Dockerfile cannot be
built on a laptop without docker, so the regression is caught statically: the
smoke step must invoke `--help` (an interface the usage text itself prints) and
must not invoke `--version`.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _shell_lines() -> str:
    """The Dockerfile without its comments: a comment may NAME the bad flag."""
    return "\n".join(
        line
        for line in (ROOT / "gortex-engine.Dockerfile").read_text().splitlines()
        if not line.lstrip().startswith("#")
    )


def test_smoke_step_does_not_pass_version_flag() -> None:
    text = _shell_lines()
    assert "gortex --version" not in text, (
        "the CLI has no --version flag (measured run 43774918311)"
    )


def test_smoke_step_invokes_help() -> None:
    text = _shell_lines()
    assert "gortex --help" in text, "the smoke step must prove the binary runs"
