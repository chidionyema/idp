"""idp#3525 CP5, ORCH-03: sovereign/engine/tracing.trace_session()'s new
config_id parameter.

"Every routed call SHALL carry a config_id tag" -- this is the write
side; sovereign/engine/config_experiment.py is the read side.
"""

from __future__ import annotations

from typing import Any

import pytest

from sovereign.engine import tracing


class _FakeLangfuseClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def trace(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)

    def flush(self) -> None:
        pass


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> _FakeLangfuseClient:
    client = _FakeLangfuseClient()
    monkeypatch.setattr(tracing, "_get_client", lambda: client)
    monkeypatch.setattr(tracing, "_record_flush_ok", lambda: None)
    return client


def test_config_id_is_appended_to_tags_when_given(
    fake_client: _FakeLangfuseClient,
) -> None:
    tracing.trace_session(
        "sess-1", "do the thing", "codex", "done", config_id="cheap-v2"
    )
    assert len(fake_client.calls) == 1
    assert "config_id:cheap-v2" in fake_client.calls[0]["tags"]


def test_no_config_id_tag_when_config_id_is_not_given(
    fake_client: _FakeLangfuseClient,
) -> None:
    tracing.trace_session("sess-1", "do the thing", "codex", "done")
    assert len(fake_client.calls) == 1
    assert not any(
        str(t).startswith("config_id:") for t in fake_client.calls[0]["tags"]
    )


def test_existing_tags_are_unchanged_by_the_new_parameter(
    fake_client: _FakeLangfuseClient,
) -> None:
    tracing.trace_session(
        "sess-1", "do the thing", "codex", "done", config_id="cheap-v2"
    )
    tags = fake_client.calls[0]["tags"]
    assert tags[:3] == ["sess-1", "runner:codex", "status:done"]
