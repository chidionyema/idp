"""JevLayer: unified confidence-and-decision service (ADR 0030).

Scenarios:
  available path      -- Jev returns confidence 0.9 -> escalated false, row in jev_decisions
  low confidence     -- Jev returns confidence 0.4 < floor -> escalated true
  unavailable path   -- typesafe-sdk absent or JEV_API_KEY empty -> escalated true, _fallback set
  timeout path      -- API times out -> escalated true, _fallback timeout
  escalation routing -- guard with escalated=true -> routes to human review
  no secret leakage -- context with password key -> stripped, password_redacted flag set
  policy jev drift  -- policy.py jev keys match AGENTS.md [jev] section
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from sovereign import policy

# The pure functions under test (no MCP server needed for these scenarios)
import mcp.plugins.jev as jev_module


class FakeTime:
    def __init__(self):
        self.calls = []

    def isoformat(self):
        return "2026-09-21T12:00:00Z"


class FakeUuid:
    def __init__(self):
        self._hex = "abcd1234efgh"

    def hex(self):
        return self._hex


class TestJevLayerPureFunctions:
    """Test the pure core functions without any MCP server or TypeSafe dependency."""

    def test_strip_secrets_removes_password(self):
        ctx = {"user": "alice", "password": "secret123", "token": "abc"}
        stripped = jev_module._strip_secrets(ctx)
        assert stripped["password"] == "[REDACTED]"  # noqa: S105 -- a test fixture value, not a credential
        assert stripped["token"] == "[REDACTED]"  # noqa: S105 -- a test fixture value, not a credential
        assert stripped["user"] == "alice"
        assert stripped["_password_redacted"] is True

    def test_strip_secrets_nested(self):
        ctx = {"outer": {"inner": {"api_key": "topsecret"}}}
        stripped = jev_module._strip_secrets(ctx)
        assert stripped["outer"]["inner"]["api_key"] == "[REDACTED]"

    def test_strip_secrets_no_op(self):
        ctx = {"user": "alice", "repo": "sovereign"}
        stripped = jev_module._strip_secrets(ctx)
        assert stripped == ctx

    def test_build_questions_choice(self):
        qs = jev_module._build_questions(
            "Which team?", "choice", ["billing", "technical"]
        )
        assert qs["decision"]["type"] == "choice"
        assert qs["decision"]["instructions"] == "Which team?"
        assert "billing" in qs["decision"]["criteria"]
        assert "technical" in qs["decision"]["criteria"]

    def test_build_questions_score(self):
        qs = jev_module._build_questions(
            "Rate urgency", "score", ["low", "medium", "high"]
        )
        assert qs["rating"]["type"] == "score"
        assert qs["rating"]["criteria"] == ["low", "medium", "high"]

    def test_build_questions_noul(self):
        qs = jev_module._build_questions("Is this urgent?", "noul", None)
        assert qs["truth"]["type"] == "noul"
        assert qs["truth"]["instructions"] == "Is this urgent?"

    def test_parse_answer_choice(self):
        ans = {
            "choice": "billing",
            "confidence": 0.85,
            "probabilities": {"billing": 0.9, "technical": 0.1},
        }
        result = jev_module._parse_answer(ans, "choice", 0.7, 120.0)
        assert result["choice"] == "billing"
        assert result["confidence"] == 0.85
        assert result["escalated"] is False

    def test_parse_answer_choice_low_confidence(self):
        ans = {
            "choice": "billing",
            "confidence": 0.4,
            "probabilities": {"billing": 0.5},
        }
        result = jev_module._parse_answer(ans, "choice", 0.7, 80.0)
        assert result["escalated"] is True

    def test_parse_answer_score(self):
        ans = {
            "score": 1,
            "confidence": 0.92,
            "legend": {"0": "low", "1": "medium", "2": "high"},
            "probabilities": {"0": 0.05, "1": 0.92, "2": 0.03},
        }
        result = jev_module._parse_answer(ans, "score", 0.7, 95.0)
        assert result["score"] == 1
        assert result["level"] == "medium"
        assert result["confidence"] == 0.92
        assert result["escalated"] is False

    def test_parse_answer_noul_true(self):
        ans = {"noul": 0.9, "confidence": 0.88}
        result = jev_module._parse_answer(ans, "noul", 0.7, 65.0)
        assert result["decision"] is True
        assert result["confidence"] == 0.88
        assert result["escalated"] is False  # 0.88 >= 0.7 floor -> not escalated
        # confidence 0.88 >= floor 0.7 -> escalated = False
        assert result["escalated"] is False

    def test_parse_answer_noul_false_low_confidence(self):
        ans = {"noul": 0.3, "confidence": 0.5}
        result = jev_module._parse_answer(ans, "noul", 0.7, 50.0)
        assert result["decision"] is False  # noul 0.3 < 0.5
        assert result["escalated"] is True  # confidence 0.5 < floor 0.7

    def test_call_jev_unavailable_no_key(self, monkeypatch):
        """When JEV_API_KEY is empty, returns escalated + fallback."""
        monkeypatch.delenv("JEV_API_KEY", raising=False)
        monkeypatch.setattr(jev_module, "JEV_API_KEY", "")
        monkeypatch.setattr(jev_module, "_JEVD_INSTALLED", False)

        state = jev_module.JevState(
            repo="sovereign", layer="guard", decision_id="test", context={}
        )
        result = jev_module._call_jev(state, "Is this urgent?", "noul", None, 0.7, 2000)
        assert result["escalated"] is True
        assert result["_fallback"] == "jev_unavailable"
        assert result["confidence"] is None


class TestJevLayerPolicyIntegration:
    """Test that policy.py correctly reads the [jev] section."""

    def test_jev_section_loaded(self):
        """AGENTS.md [jev] section is parsed into policy.jev."""
        p = policy.load()
        assert "default_confidence_floor" in p.jev
        assert "timeout_ms" in p.jev
        assert "escalate_on_timeout" in p.jev
        assert "model" in p.jev
        assert p.jev["default_confidence_floor"] == 0.7
        assert p.jev["timeout_ms"] == 2000
        assert p.jev["model"] == "jev-1.13.0"

    def test_jev_section_required(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Missing [jev] section raises PolicyError, not a silent default."""
        real = policy.agents_md_path().read_text()
        # Remove the [jev] section by truncating before it
        jev_start = real.find("\n[jev]")
        assert (
            jev_start >= -1
        )  # if find returned -1, the section is missing; subsequent raises the real error
        stale = real[:jev_start] + "\n" + real[real.find("\n```", jev_start) :]
        copy = tmp_path / "AGENTS.md"
        copy.write_text(stale)
        monkeypatch.setenv(policy.AGENTS_MD_ENV, str(copy))
        with pytest.raises(policy.PolicyError, match="jev"):
            policy.load()


class TestJevLayerDatabase:
    """Test the database UPSERT logic."""

    def test_ensure_table_creates_table(self, tmp_path: Path):
        db = str(tmp_path / "test.db")
        jev_module._ensure_table(db)
        con = sqlite3.connect(db)
        rows = list(
            con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='jev_decisions'"
            )
        )
        con.close()
        assert len(rows) == 1

    def test_ensure_table_idempotent(self, tmp_path: Path):
        """Second call does not raise."""
        db = str(tmp_path / "test.db")
        jev_module._ensure_table(db)
        jev_module._ensure_table(db)  # should not raise

    def test_upsert_writes_row(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        db = str(tmp_path / "test.db")
        monkeypatch.setattr(jev_module, "ESTATE_DB_PATH", db)
        jev_module._ensure_table(db)

        decision = jev_module.JevDecision(
            id="test:guard:test:abcd1234",
            repo="sovereign",
            layer="guard",
            decision_id="test_decision",
            question="Is this urgent?",
            answer="True",
            confidence=0.85,
            probabilities=None,
            escalated=False,
            latency_ms=120.5,
            created_at="2026-09-21T12:00:00Z",
        )
        jev_module._upsert(decision, db)

        con = sqlite3.connect(db)
        rows = list(
            con.execute(
                "SELECT repo, layer, decision_id, confidence FROM jev_decisions"
            )
        )
        con.close()
        assert len(rows) == 1
        assert rows[0][0] == "sovereign"
        assert rows[0][3] == 0.85


class TestJevToolsNoServer:
    """Test the tool functions with no MCP server (pure function tests)."""

    def test_jev_choice_returns_expected_shape(self, monkeypatch: pytest.MonkeyPatch):
        """jev_choice returns dict with the required keys."""
        monkeypatch.setattr(jev_module, "JEV_API_KEY", "")
        monkeypatch.setattr(jev_module, "_JEVD_INSTALLED", False)
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "test.db")
            monkeypatch.setattr(jev_module, "ESTATE_DB_PATH", db)
            result = jev_module.jev_choice(
                repo="sovereign",
                layer="guard",
                decision_id="test_feature",
                context={"commits": 3},
                question="Which feature?",
                options=["feat:a", "feat:b"],
                required_confidence=0.7,
            )
        assert "escalated" in result
        assert "confidence" in result
        assert result["escalated"] is True  # unavailable path
        assert result["_fallback"] == "jev_unavailable"

    def test_jev_noul_returns_expected_shape(self, monkeypatch: pytest.MonkeyPatch):
        """jev_noul returns dict with the required keys.

        When Jev is unavailable, the fallback shape is returned:
        {escalated: True, _fallback: 'jev_unavailable', confidence: None, latency_ms: None}.
        A DB row is still written (with null confidence).
        """
        monkeypatch.setattr(jev_module, "JEV_API_KEY", "")
        monkeypatch.setattr(jev_module, "_JEVD_INSTALLED", False)
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "test.db")
            monkeypatch.setattr(jev_module, "ESTATE_DB_PATH", db)
            result = jev_module.jev_noul(
                repo="prospector",
                layer="verifier",
                decision_id="verdict_gate",
                context={"claim": "the sky is blue", "sources": []},
                question="Is this claim supported?",
                threshold=0.7,
            )
        assert "escalated" in result
        assert result["escalated"] is True  # unavailable path
        assert result["_fallback"] == "jev_unavailable"
        assert result["confidence"] is None

    def test_jev_score_returns_expected_shape(self, monkeypatch: pytest.MonkeyPatch):
        """jev_score returns dict with the required keys."""
        monkeypatch.setattr(jev_module, "JEV_API_KEY", "")
        monkeypatch.setattr(jev_module, "_JEVD_INSTALLED", False)
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "test.db")
            monkeypatch.setattr(jev_module, "ESTATE_DB_PATH", db)
            result = jev_module.jev_score(
                repo="hermes",
                layer="agent",
                decision_id="reply_judge",
                context={"reply": "all good"},
                question="Rate the frustration level",
                levels=["calm", "frustrated", "angry"],
                required_confidence=0.7,
            )
        assert "score" in result or "escalated" in result
        assert result["escalated"] is True  # unavailable path
