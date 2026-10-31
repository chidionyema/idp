"""The router doctor answers about the SLOT that is serving, and acts at most once (idp#7660).

WHAT THIS GRADES. `platform/estate/libexec/router-doctor.py` was four wrong answers about one
machine, and each wrong answer acted:

  1. it asked the FRONT (:4000) whether the ROUTER was alive, read the front's load-based 503
     as a dead router, and restarted the slot -- 121 restarts in a day, each cutting every
     live session;
  2. it compared the estate's declared lanes with the STAGED runtime config (nine lanes from
     September) while the router ran the live one (twenty-nine lanes from October), and
     reinstalled the router every 120 s tick;
  3. it read a Keychain service and a settings file that do not exist on this machine;
  4. it had no actuator budget: a failed check healed, healed, healed, forever.

These are the falsifiers for that class: the doctor must ask the slot, never restart a slot
that is answering, restart the front when the front is the broken one, escalate instead of
acting twice, and say the truth about base-URL drift without undoing the founder's routing.
"""

import importlib.machinery
import importlib.util
import json
import time
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "platform/estate/libexec/router-doctor.py"


def load():
    loader = importlib.machinery.SourceFileLoader("router_doctor_truth", str(SRC))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def test_the_liveness_probe_asks_the_slot_not_the_front(monkeypatch):
    m = load()
    seen = []

    def fake_http(path, *a, **k):
        seen.append((path, k.get("base")))
        return 200, "ok"

    monkeypatch.setattr(m, "http", fake_http)
    monkeypatch.setattr(m, "ACTIVE", Path("/nonexistent/active"))
    ok, why = m.check_live()
    assert ok is True
    assert seen, "the doctor asked nothing"
    path, base = seen[0]
    assert path == "/health/liveliness", path
    assert base == m.slot_base(), "the doctor asked %s, not the serving slot %s" % (
        base,
        m.slot_base(),
    )
    assert base != m.BASE, "the front is not the router"


def test_the_doctor_never_asks_the_litellm_health_endpoint(monkeypatch):
    """LiteLLM's /health hangs when the router is busy (measured 2026-10-31). Only
    /health/liveliness is admissible: a health check that hangs is a health check that
    turns a slow router into a dead one."""
    m = load()
    asked = []

    def fake_http(path, *a, **k):
        asked.append(path)
        return 200, "ok"

    monkeypatch.setattr(m, "http", fake_http)
    m.check_live()
    m.check_front()
    assert asked, "nothing was asked"
    for path in asked:
        assert path == "/health/liveliness", path


def test_a_listening_slot_is_never_restarted(monkeypatch):
    m = load()
    ran = []
    monkeypatch.setattr(m, "sh", lambda argv, **k: ran.append(argv) or (0, ""))
    monkeypatch.setattr(m, "listening", lambda *a, **k: True)
    did = m.heal_live()
    assert "not restarted" in did, did
    assert not ran, ran


def test_a_slow_slot_that_still_listens_is_healthy(monkeypatch):
    """A refused connection is dead; a timeout is slow. Only the first is a restart."""
    m = load()
    monkeypatch.setattr(m, "http", lambda *a, **k: (0, "timed out"))
    monkeypatch.setattr(m, "listening", lambda *a, **k: True)
    ok, why = m.check_live()
    assert ok is True, why
    assert "listening" in why, why

    monkeypatch.setattr(m, "listening", lambda *a, **k: False)
    ok, why = m.check_live()
    assert ok is False, why


def test_a_front_that_refuses_a_healthy_slot_is_a_front_fault(monkeypatch):
    m = load()
    calls = []

    def fake_http(path, *a, **k):
        calls.append(k.get("base"))
        if k.get("base") == m.BASE:
            return 503, "saturated"
        return 200, "ok"

    monkeypatch.setattr(m, "http", fake_http)
    ok, why = m.check_front()
    assert ok is False
    assert "front" in why.lower(), why


def test_the_front_heal_restarts_the_front_and_not_the_router(monkeypatch):
    m = load()
    ran = []
    monkeypatch.setattr(m, "sh", lambda argv, **k: ran.append(argv) or (0, ""))
    m.heal_front()
    assert ran, "nothing was restarted"
    joined = " ".join(ran[0])
    assert m.FRONT_LABEL in joined, joined
    assert m.slot_label() not in joined, joined


def test_a_second_destructive_heal_escalates_instead_of_acting(tmp_path, monkeypatch):
    m = load()
    monkeypatch.setattr(m, "alert", lambda *a, **k: None)
    heals = tmp_path / "doctor-heals.json"
    monkeypatch.setattr(m, "HEAL_STATE", heals)
    monkeypatch.setattr(m, "LAST", tmp_path / "last")
    monkeypatch.setattr(m, "MODE", "heal")
    monkeypatch.setattr(m, "HEAL", True)
    monkeypatch.setattr(m, "WATCH", False)

    def failing_check():
        return False, "still broken"

    def destructive_heal():
        heals.append("acted")
        return "acted"

    monkeypatch.setattr(
        m, "CHECKS", [("lanes", failing_check, destructive_heal, "fix it")]
    )

    # The first run may act: nothing has healed yet.
    assert m.main() == 1  # the fake check still fails after the heal
    assert heals.read_text() != ""

    # The second run, inside the budget window, must NOT act: it escalates.
    heals.write_text(json.dumps({"last": {"at": time.time(), "name": "lanes"}}))
    m.OUT.clear()
    m.main()
    said = "\n".join(m.OUT)
    assert "ESCALATED_NO_OP" in said, said


def test_base_url_drift_is_advisory_and_model_drift_is_not(tmp_path, monkeypatch):
    m = load()
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(m, "SETTINGS", settings)

    settings.write_text(
        json.dumps(
            {
                "model": "opusplan",
                "env": {"ANTHROPIC_BASE_URL": "https://api.anthropic.com"},
            }
        )
    )
    ok, why = m.check_settings()
    assert ok is True, why
    assert "advisory" in why, why

    settings.write_text(json.dumps({"model": "sonnet", "env": {}}))
    ok, why = m.check_settings()
    assert ok is False, why
    assert "opusplan" in why, why


def test_the_keychain_service_is_derived_from_the_harness_directory(
    tmp_path, monkeypatch
):
    # The machine this doctor runs on configures Claude Code with its own directory, so the
    # credential lives under a suffixed service name (sha256(dir)[:8], measured 2026-10-31).
    harness = tmp_path / "harness-cc"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(harness))
    m = load()
    asked = []

    def fake_sh(argv, **k):
        asked.append(argv[3] if len(argv) > 3 else "")
        if asked[-1] == m.CTX.keychain_service:
            return 0, json.dumps({"claudeAiOauth": {"accessToken": "x"}})
        return 1, ""

    monkeypatch.setattr(m, "sh", fake_sh)
    token = m.keychain_token()
    assert token == {"accessToken": "x"}
    assert asked[0] == m.CTX.keychain_service, asked
    assert asked[0] != "Claude Code-credentials", "the plain service was asked first"
    assert m.CTX.keychain_service.startswith("Claude Code-credentials-")


def test_a_refusal_without_a_reason_fails_the_manifest_check(tmp_path, monkeypatch):
    m = load()
    manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(m, "MANIFEST", manifest)
    monkeypatch.setattr(m, "RUNTIME_CONFIG", tmp_path / "config.runtime.yaml")
    manifest.write_text(
        json.dumps(
            {
                "declared": ["a", "b"],
                "expected_served": ["a"],
                "refused_with_reason": [{"lane": "b"}],
                "fallbacks": {},
            }
        )
    )
    ok, why = m.check_manifest()
    assert ok is False
    assert "reason" in why, why


def test_a_fallback_to_a_lane_nobody_serves_fails_the_manifest_check(
    tmp_path, monkeypatch
):
    m = load()
    manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(m, "MANIFEST", manifest)
    monkeypatch.setattr(m, "RUNTIME_CONFIG", tmp_path / "config.runtime.yaml")
    manifest.write_text(
        json.dumps(
            {
                "declared": ["a", "b"],
                "expected_served": ["a"],
                "refused_with_reason": [{"lane": "b", "reason": "no key"}],
                "fallbacks": {"a": ["b"]},
            }
        )
    )
    ok, why = m.check_manifest()
    assert ok is False
    assert "not served" in why, why


def test_a_live_lane_nobody_declared_fails_the_manifest_check(tmp_path, monkeypatch):
    m = load()
    manifest = tmp_path / "manifest.json"
    runtime = tmp_path / "config.runtime.yaml"
    monkeypatch.setattr(m, "MANIFEST", manifest)
    monkeypatch.setattr(m, "RUNTIME_CONFIG", runtime)
    runtime.write_text("- model_name: a\n- model_name: surprise\n")
    manifest.write_text(
        json.dumps(
            {
                "declared": ["a"],
                "expected_served": ["a"],
                "refused_with_reason": [],
                "fallbacks": {},
            }
        )
    )
    ok, why = m.check_manifest()
    assert ok is False
    assert "surprise" in why, why


def test_a_manifest_mismatch_never_reinstalls(monkeypatch):
    """A mismatch is reported, not acted on: the reinstall is how the doctor spent a day
    restarting a healthy router."""
    m = load()
    ran = []
    monkeypatch.setattr(m, "sh", lambda argv, **k: ran.append(argv) or (0, ""))
    try:
        m.heal_manifest()
    except m.Fix as fix:
        assert "nothing was changed" in str(fix)
    else:
        raise AssertionError("a manifest mismatch must not be healed silently")
    assert not ran, ran
