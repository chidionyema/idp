"""ESTATE_AGENT's max_age must reach the server as an int64 of nanoseconds.

nats-py takes max_age in SECONDS and converts it; a value already in nanos became 9e20 on the
wire, past int64, and the server refused add_stream with "invalid JSON" (err_code 10025).
"""

from __future__ import annotations

import pytest

from fleetview_backend import nats_adapter

api = pytest.importorskip("nats.js.api")


def test_stream_max_age_serialises_as_fifteen_minutes_of_nanos():
    cfg = api.StreamConfig(
        name=nats_adapter.STREAM_NAME,
        subjects=nats_adapter.STREAM_SUBJECTS,
        max_age=nats_adapter.STREAM_MAX_AGE_S,
    )
    wire = cfg.as_dict()["max_age"]
    assert wire == 15 * 60 * 1_000_000_000
    assert wire < 2**63
