"""The zone resolver (lib/estate_zone.py) reads the estate's zone the one way every reader does.

Three properties, proved here rather than narrated:
  the environment wins when it is set (the cluster's ConfigMap sets ESTATE_ZONE);
  the file that declares the zone is read when the environment is silent (the laptop exports
  nothing -- measured 2026-11-17: printenv ESTATE_ZONE is empty in this machine's session);
  an unknown zone is an empty string -- never an exception, never a guess, because a reader that
  cannot know the zone must stop rather than dial a host it invented.

The expected zone is read from the declaration, never written here: a test that pins the zone is
a test a migration voids.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
ZONE_KEY = re.compile(r"^\s*ESTATE_ZONE:\s*(\S+)", re.M)


def _load():
    path = REPO / "lib" / "estate_zone.py"
    spec = importlib.util.spec_from_file_location("estate_zone_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def zone_module():
    return _load()


def _declared_zone() -> str:
    for cfg in sorted((REPO / "clusters").glob("*/estate-config.yaml")):
        match = ZONE_KEY.search(cfg.read_text())
        if match:
            return match.group(1)
    raise AssertionError("no clusters/*/estate-config.yaml declares ESTATE_ZONE")


def test_the_environment_wins(zone_module, monkeypatch):
    monkeypatch.setenv("ESTATE_ZONE", "zone.example")
    assert zone_module.estate_zone() == "zone.example"


def test_the_declaration_is_read_when_the_environment_is_silent(zone_module, monkeypatch):
    monkeypatch.delenv("ESTATE_ZONE", raising=False)
    assert zone_module.estate_zone() == _declared_zone()


def test_an_unknown_zone_is_empty_and_never_raises(zone_module, monkeypatch, tmp_path):
    monkeypatch.delenv("ESTATE_ZONE", raising=False)
    monkeypatch.setattr(zone_module, "_roots", lambda: [tmp_path])
    assert zone_module.estate_zone() == ""
    assert zone_module.estate_host("llm") == ""
    assert zone_module.estate_router("/v1/models") == ""


def test_the_hosts_are_built_from_the_zone(zone_module, monkeypatch):
    monkeypatch.setenv("ESTATE_ZONE", "zone.example")
    assert zone_module.estate_host("catalogue", "/fleet") == "https://catalogue.zone.example/fleet"
    assert zone_module.estate_router("/v1/models") == "https://llm.zone.example/v1/models"


def test_the_resolver_spells_no_zone(zone_module):
    """The resolver reads the zone; it never carries one. The estate-zone gate grades the tree,
    and this is the same law applied to the one file that every reader trusts."""
    source = (REPO / "lib" / "estate_zone.py").read_text()
    for cfg in sorted((REPO / "clusters").glob("*/estate-config.yaml")):
        for zone in ZONE_KEY.findall(cfg.read_text()):
            assert zone not in source, f"the resolver spells the zone {zone}"


def test_the_resolver_is_importable_as_a_module(zone_module):
    """lib/estate_zone.py is imported by a sys.path insert (the estate_spatial.py precedent), so
    the module must import cleanly on its own, with no estate import machinery."""
    assert zone_module.__name__.endswith("estate_zone_under_test")
    assert callable(zone_module.estate_zone)
    assert os.path.basename(zone_module.__file__) == "estate_zone.py"
