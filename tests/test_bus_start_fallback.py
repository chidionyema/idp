"""A missing preferred broker path must not leave the bus BLIND when a broker exists."""

import importlib.util
import os
import tempfile
from pathlib import Path

BUS_START = (
    Path(__file__).resolve().parent.parent
    / "platform"
    / "estate"
    / "libexec"
    / "bus-start.py"
)


def _load(home: Path):
    spec = importlib.util.spec_from_file_location("bus_start_under_test", BUS_START)
    module = importlib.util.module_from_spec(spec)
    old_home = os.environ.get("HOME")
    old_override = os.environ.pop("ESTATE_NATS_BIN", None)
    os.environ["HOME"] = str(home)
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home
        if old_override is not None:
            os.environ["ESTATE_NATS_BIN"] = old_override


def test_existing_cache_binary_wins():
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        cache = home / ".cache" / "estate-tools" / "nats-server"
        cache.parent.mkdir(parents=True)
        cache.write_text("#!/bin/sh\n")
        module = _load(home)
        assert module.resolve_bin() == cache


def test_missing_cache_binary_falls_back_to_a_real_path():
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        module = _load(home)
        resolved = module.resolve_bin()
        cache = home / ".cache" / "estate-tools" / "nats-server"
        assert resolved != cache
        # Either a system broker is installed, or PATH resolution found none. It must not
        # return a path that does not exist while a broker is present elsewhere.
        assert resolved.exists() or resolved == cache
