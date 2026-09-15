"""idp#3525 CP6, FL-03 -- config_id trace tagging is pure information gain on
already-paid infrastructure; zero new cost.

Code review record, proved as running code: trace_session() makes exactly one
Langfuse client call (client.trace(...) then client.flush()) whether or not
config_id is passed. config_id only ever changes the length of the `tags`
list handed to that one call -- it never adds a second call, a second client,
or a second network round trip.
"""

from __future__ import annotations

from typing import Any

import pytest

from sovereign.engine import tracing


class _FakeLangfuseClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.flush_count = 0

    def trace(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)

    def flush(self) -> None:
        self.flush_count += 1


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> _FakeLangfuseClient:
    client = _FakeLangfuseClient()
    monkeypatch.setattr(tracing, "_get_client", lambda: client)
    monkeypatch.setattr(tracing, "_record_flush_ok", lambda: None)
    return client


def test_config_id_adds_no_extra_client_call(fake_client: _FakeLangfuseClient) -> None:
    tracing.trace_session("s1", "task", "runner", "ok")
    tracing.trace_session("s2", "task", "runner", "ok", config_id="cell-a")
    counts = (len(fake_client.calls), fake_client.flush_count)
    assert counts == (2, 2)


def test_config_id_only_changes_the_tags_list(fake_client: _FakeLangfuseClient) -> None:
    tracing.trace_session("s3", "task", "runner", "ok")
    tracing.trace_session("s3", "task", "runner", "ok", config_id="cell-b")
    tags_without = fake_client.calls[0]["tags"]
    tags_with = fake_client.calls[1]["tags"]
    added = [tag for tag in tags_with if tag not in tags_without]
    assert added == ["config_id:cell-b"]
