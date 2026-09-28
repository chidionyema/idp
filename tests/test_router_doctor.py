"""router-doctor must map each known upstream failure to its heal and its exact fix.

Each body below is the one the laptop router actually returned when that cause was live
(2026-09-28); an unknown body must never trigger a heal, because the watch runs every 120s
and a restart on every tick would cut every live session.
"""

from __future__ import annotations

import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "platform", "estate", "libexec", "router-doctor.py")


def _doctor():
    spec = importlib.util.spec_from_file_location("router_doctor", PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cause(mod, body):
    mod.check_e2e.last = body
    return mod.e2e_cause()


def test_dropped_bearer_heals_by_restaging_the_patch():
    d = _doctor()
    heal, fix = _cause(d, '{"error":{"message":"x-api-key header is required"}}')
    assert heal is d.heal_patch
    assert "clean_headers" in fix


def test_revoked_login_tries_a_refresh_then_names_login():
    d = _doctor()
    heal, fix = _cause(d, '{"message":"OAuth access token has been revoked."}')
    assert heal is d.heal_token
    assert "/login" in fix


def test_rate_limit_is_never_healed_locally():
    d = _doctor()
    heal, _ = _cause(d, '{"type":"rate_limit_error"}')
    assert heal is None


def test_unknown_failure_is_never_healed():
    d = _doctor()
    heal, fix = _cause(d, '{"error":"something new"}')
    assert heal is None
    assert "E2E_CAUSES" in fix


def test_pinned_token_in_settings_fails_the_check(tmp_path):
    d = _doctor()
    d.SETTINGS = tmp_path / "settings.json"
    d.SETTINGS.write_text(
        '{"env":{"ANTHROPIC_BASE_URL":"%s","ANTHROPIC_API_KEY":"x"}}' % d.BASE
    )
    ok, detail = d.check_settings()
    assert not ok and "ANTHROPIC_API_KEY" in detail
    d.heal_settings()
    assert d.check_settings()[0]


def test_a_changed_model_is_reverted_to_opusplan(tmp_path):
    d = _doctor()
    d.SETTINGS = tmp_path / "settings.json"
    d.SETTINGS.write_text(
        '{"model":"opus[1m]","env":{"ANTHROPIC_BASE_URL":"%s","ANTHROPIC_MODEL":"opus"}}'
        % d.BASE
    )
    ok, detail = d.check_settings()
    assert not ok and "must be opusplan" in detail and "ANTHROPIC_MODEL" in detail
    d.heal_settings()
    assert d.check_settings()[0]
    assert '"model": "opusplan"' in d.SETTINGS.read_text()
