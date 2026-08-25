"""Properties of the intake pipeline that survive a rewrite.

Rung 2 (properties) where hypothesis is installed, rung 4 (one incident test
per rule) otherwise. No vision model is ever called: every case goes through
the `vision=` seam with a stub.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from sovereign.intake import vision
from sovereign.intake.pipeline import IntakeRefused, IntakeRequest, intake, receipt_line

try:
    from hypothesis import given, settings
    from hypothesis import strategies as st
except ImportError:  # pragma: no cover
    given = None  # type: ignore[assignment]


def _stub(markdown: str, slug: str, tags: list[str]):
    def _call(model: str, messages) -> str:
        return json.dumps({"markdown": markdown, "slug": slug, "tags": tags, "title": slug})

    return _call


def test_property_slug_is_always_a_safe_filename() -> None:
    """sanitize_slug never yields a path separator, whitespace or an
    over-long name, whatever the model returned."""
    samples = ["Hello World", "../../etc/passwd", "a/b\\c", "x" * 500, "  ", "Ünïcödé slug", "a:b|c"]
    if given is not None:
        @given(st.text())
        @settings(max_examples=300)
        def prop(raw: str) -> None:
            s = vision.sanitize_slug(raw)
            assert "/" not in s and "\\" not in s and " " not in s
            assert len(s) <= 60
            assert s == s.lower()
        prop()
    for raw in samples:
        s = vision.sanitize_slug(raw)
        assert "/" not in s and "\\" not in s and " " not in s and len(s) <= 60


def test_property_receipt_line_is_one_line_and_names_the_commit() -> None:
    line = receipt_line("docs/a_b_c.md", "8f2a1b3c" + "0" * 32, ("ml", "governance"), 200)
    assert "\n" not in line
    assert line == "[✓] DOC_COMMIT | file:docs/a_b_c.md | hash:8f2a1b3c | tags:#ml,#governance | budget:-200"


def test_parse_refuses_anything_but_the_strict_object() -> None:
    for bad in ("not json", "[1,2]", '{"markdown": "x"}', '{"slug": "x", "tags": []}'):
        with pytest.raises(vision.ExtractionError):
            vision.parse(bad, "alias")
    fenced = "```json\n" + json.dumps({"markdown": "m", "slug": "A B", "tags": "ml, ops"}) + "\n```"
    ex = vision.parse(fenced, "alias")
    assert ex.slug == "a_b" and ex.tags == ("ml", "ops")


def test_incident_budget_zero_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Spec 4.3: at zero, hard halt. A refused intake leaves no file, no
    commit and no receipt."""
    repo = tmp_path / "r"
    repo.mkdir()
    env = {**os.environ, "GIT_CONFIG_GLOBAL": str(tmp_path / "gc"), "GIT_CONFIG_SYSTEM": os.devnull}
    subprocess.run(["git", "init", "-q", repo], check=True, env=env)
    calls: list[str] = []

    def spy(model, messages):
        calls.append(model)
        return "{}"

    req = IntakeRequest(image=b"x", caption="c", repo=repo, source="t", channel="t", budget_remaining=0)
    with pytest.raises(IntakeRefused):
        intake(req, vision=spy)
    assert calls == [], "the model was called even though the budget refused the op"
    assert not (repo / "docs").exists()


def test_incident_not_a_repo_is_refused_before_the_model(tmp_path: Path) -> None:
    calls: list[str] = []
    req = IntakeRequest(image=b"x", caption="c", repo=tmp_path, source="t", channel="t")
    with pytest.raises(IntakeRefused):
        intake(req, vision=lambda m, ms: calls.append(m) or "{}")
    assert calls == []
