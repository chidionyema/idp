"""The lane registry holds facts, and one observation is a fact (CP1).

WHAT THIS GRADES. `platform/llm/lane_registry.py` claims: error classes are facts, not
counts — ONE 402 transitions a lane to dead:credit; a 429 with a reset schedules
recovery at that reset, not after three more failed user requests; a success (real or
probe) heals it; the registry may never fail a request (LAW 38); probes are cadenced by
state and suppressed by fresh traffic.

THE CLAIM IT IS NOT MAKING: that this lowers the bill or saves latency. Those are
effects, measurable only from the router log after this lands (spec §4). What is
checkable here is the mechanism: the facts are held, transitioned once, persisted
atomically, and reloaded.

CALLED THE WAY LITELLM CALLS IT: async_log_success_event(kwargs, response_obj, start_time,
end_time) and async_log_failure_event(...), signatures from
litellm/integrations/custom_logger.py in the installed 1.98.0.
"""

import asyncio
import datetime as dt
import importlib.util
import json
import pathlib
import sys

import pytest

MODULE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "platform"
    / "llm"
    / "lane_registry.py"
)

# Hermetic model_list: the deployments the tests observe, plus one non-chat lane
# (the reconcile tests square loaded state against THIS, never the laptop's real config).
CONFIG_YAML = """
model_list:
  - model_name: moonshot
    litellm_params:
      model: moonshot/kimi-k3
      api_key: os.environ/NO_SUCH_KEY
  - model_name: groq
    litellm_params:
      model: groq/llama-3.3-70b-versatile
      api_key: os.environ/NO_SUCH_KEY
  - model_name: tts
    litellm_params:
      model: groq/canopylabs/orpheus-v1-english
      api_key: os.environ/NO_SUCH_KEY
    model_info:
      mode: audio_speech
  - model_name: voice-asr
    litellm_params:
      model: groq/whisper-large-v3-turbo
      api_key: os.environ/NO_SUCH_KEY
    model_info:
      mode: audio_transcription
"""


def _load():
    spec = importlib.util.spec_from_file_location("lane_registry", MODULE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lane_registry"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def mod(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_ROUTER_STATE_DIR", str(tmp_path / "router"))
    monkeypatch.setenv("ESTATE_ROUTER_PROBES", "0")
    cfg = tmp_path / "config.yaml"
    cfg.write_text(CONFIG_YAML)
    monkeypatch.setenv("ESTATE_ROUTER_CONFIG", str(cfg))
    return _load()


def _registry(m):
    return m.LaneRegistry()


def _kwargs(deployment: str) -> dict:
    """The kwargs shape LiteLLM passes the log hooks."""
    return {
        "model": deployment,
        "litellm_params": {"metadata": {"deployment": deployment}},
        "model_info": {"id": deployment},
    }


class _Resp:
    def __init__(self, status=None, message=""):
        self.status_code = status
        self.message = message
        self.headers = {}


def _log_success(m, reg, dep, ms=120.0):
    asyncio.run(
        reg.async_log_success_event(
            _kwargs(dep), _Resp(), dt.datetime.now(), dt.datetime.now()
        )
    ) or None


# ------------------------------------------------------------------- error classes


@pytest.mark.parametrize(
    "status,text,state,reason",
    [
        (402, "insufficient balance", "dead", "credit"),
        (None, "Account is suspended", "dead", "credit"),
        (401, "invalid api key", "dead", "auth"),
        (403, "forbidden", "dead", "auth"),
        (429, "rate limit exceeded", "exhausted", "rate"),
        (None, "request timed out", "degraded", "timeout"),
        (500, "internal", "degraded", "server"),
    ],
)
def test_error_class_is_a_fact_after_one_observation(mod, status, text, state, reason):
    reg = _registry(mod)
    reg.observe_failure("moonshot/kimi-k3", status, text)
    lane = reg._lanes["moonshot/kimi-k3"]
    assert lane["state"] == state
    assert lane["reason"] == reason


@pytest.mark.parametrize("status", [400, 404, 413, 415, 422])
def test_caller_errors_never_touch_lane_health(mod, status):
    """A wrong model name (404) is the caller's mistake, not the lane's (measured on the
    :4010 canary: wrong-model 404s were landing as degraded)."""
    reg = _registry(mod)
    reg.observe_success("groq/llama-3.3-70b-versatile", 120.0)
    reg.observe_failure("groq/llama-3.3-70b-versatile", status, "no such model")
    assert reg.state("groq/llama-3.3-70b-versatile") == "ready"


def test_router_model_not_found_never_touches_lane_health(mod):
    """The router's own 'model group does not exist' carries no HTTP status; before the
    text rule it landed as degraded (measured on the :4010 canary 2026-10-02)."""
    reg = _registry(mod)
    reg.observe_success("groq/llama-3.3-70b-versatile", 120.0)
    reg.observe_failure(
        "groq/llama-3.3-70b-versatile", None, "model group does not exist"
    )
    assert reg.state("groq/llama-3.3-70b-versatile") == "ready"


def test_one_observation_is_enough_no_three_strikes(mod):
    """The measured defect: three real user requests burned on a fact already known."""
    reg = _registry(mod)
    reg.observe_failure("moonshot/kimi-k3", 402, "insufficient balance")
    assert reg.servable("moonshot/kimi-k3") is False


def test_429_with_retry_after_schedules_recovery(mod):
    reg = _registry(mod)
    reg.observe_failure("groq/llama", 429, "rate limit", headers={"retry-after": "30"})
    lane = reg._lanes["groq/llama"]
    assert lane["state"] == "exhausted"
    assert lane["reset_at"] is not None and lane["reset_at"] > 0


# ------------------------------------------------------------------------ healing


def test_success_heals_a_dead_lane(mod, tmp_path):
    reg = _registry(mod)
    reg.observe_failure("moonshot/kimi-k3", 402, "insufficient balance")
    assert not reg.servable("moonshot/kimi-k3")
    reg.observe_success("moonshot/kimi-k3", 250.0)
    assert reg.servable("moonshot/kimi-k3")
    # the transition is journalled: /fleet reads it
    rows = (tmp_path / "router" / "lanes.jsonl").read_text().strip().splitlines()
    events = [json.loads(r) for r in rows]
    assert any(e["event"] == "transition" and e["to"] == "ready" for e in events)


def test_hook_payload_shape_from_litellm(mod):
    """The failure hook reads the deployment from metadata/model_info, the status from
    the exception, exactly as LiteLLM 1.98.0 passes them."""
    reg = _registry(mod)

    class _Exc:
        status_code = 402
        message = "insufficient balance"

        def __str__(self):
            return "insufficient balance"

    asyncio.run(
        reg.async_log_failure_event(
            _kwargs("moonshot/kimi-k3"), _Exc(), dt.datetime.now(), dt.datetime.now()
        )
    )
    assert reg.state("moonshot/kimi-k3") == "dead"


# --------------------------------------------------------------------- LAW 38


def test_the_registry_never_fails_a_request(mod, monkeypatch, tmp_path):
    """Unwritable state dir, garbage kwargs: every hook returns, none raises."""
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file")
    monkeypatch.setenv("ESTATE_ROUTER_STATE_DIR", str(blocker / "router"))
    reg = _registry(mod)
    reg.observe_failure("groq/llama", 429, "rate limit")  # persist fails, no raise
    reg.observe_success("groq/llama", 100.0)
    asyncio.run(reg.async_log_failure_event({"model": None}, None, None, None))
    asyncio.run(reg.async_log_success_event({"litellm_params": {}}, None, None, None))


# ------------------------------------------------------------------- probe cadence


def test_probe_cadence_by_state(mod):
    reg = _registry(mod)
    now = 1000.0

    def lane(dep, state, last_obs, last_probe, reset_at=None):
        reg._lanes[dep] = mod._blank(dep)
        reg._lanes[dep].update(
            state=state,
            last_observation=last_obs,
            last_probe=last_probe,
            reset_at=reset_at,
        )

    lane("a/fresh", "ready", now - 10, 0)  # fresh traffic: never probed
    lane("b/idle", "ready", now - 61, 0)  # idle: 60s cadence
    lane("c/dead", "dead", now - 120, 0)  # dead: 10min cadence
    lane("d/wait", "exhausted", now - 120, 0, reset_at=now + 60)  # before reset: no
    lane("e/after", "exhausted", now - 120, 0, reset_at=now - 1)  # reset passed: yes

    assert reg.probe_due("a/fresh", now) is False
    assert reg.probe_due("b/idle", now) is True
    assert reg.probe_due("c/dead", now) is False
    assert reg.probe_due("c/dead", now + 601) is True
    assert reg.probe_due("d/wait", now) is False
    assert reg.probe_due("e/after", now) is True


# ------------------------------------------------------------------ persistence


def test_snapshot_persists_and_reloads(mod):
    reg = _registry(mod)
    reg.observe_failure("moonshot/kimi-k3", 402, "insufficient balance")
    fresh = _registry(mod)  # same state dir: the fact survives
    assert fresh.state("moonshot/kimi-k3") == "dead"
    snap = fresh.snapshot()
    assert any(l["deployment"] == "moonshot/kimi-k3" for l in snap["lanes"])


# ------------------------------------- measured live defects, 2026-10-02 (fix lane)


def test_unresolved_failure_is_never_attributed(mod):
    """A model-group miss carries no deployment metadata: the requested name is not a
    lane, and must not grow a ghost record (measured on the live router: 'gemini' and
    'cheap' sat dead:auth with no params and no healing path, pure noise)."""
    reg = _registry(mod)
    kwargs = {"model": "brand-new-alias", "litellm_params": {}}
    asyncio.run(
        reg.async_log_failure_event(kwargs, None, dt.datetime.now(), dt.datetime.now())
    )
    assert "brand-new-alias" not in reg._lanes


def test_alias_named_failure_is_not_a_lane_fact(mod):
    """The same failure whose bare model IS an alias ('groq'): aliases are not
    deployments; only a name present in the staged model_list counts."""
    reg = _registry(mod)
    kwargs = {"model": "groq", "litellm_params": {}}
    asyncio.run(
        reg.async_log_failure_event(
            kwargs,
            _Resp(status=401, message="bad key"),
            dt.datetime.now(),
            dt.datetime.now(),
        )
    )
    assert "groq" not in reg._lanes


def test_probe_params_skip_non_chat_modes(mod):
    """A completion-shaped probe cannot grade audio_speech: the TTS lane is
    real-traffic-only (the chat-probe era is what killed voice-tts for good)."""
    params = _registry(mod)._deployment_params()
    assert "groq/canopylabs/orpheus-v1-english" not in params
    assert params["moonshot/kimi-k3"]["model"] == "moonshot/kimi-k3"


def test_load_reconciles_ghost_and_probe_era_deaths(mod, tmp_path):
    """Boot-window state squares with the config actually staged: ghosts drop, a
    non-chat lane stuck dead OR exhausted-no-reset heals (real traffic re-condemns in
    one observation if it is truly out — the measured orpheus shape), a chat lane's
    death is real evidence."""
    d = tmp_path / "router"
    d.mkdir(parents=True)
    (d / "lanes.json").write_text(
        json.dumps(
            {
                "lanes": [
                    {
                        "deployment": "gemini",
                        "state": "dead",
                        "reason": "auth",
                        "since": 1,
                        "last_observation": 1,
                        "last_probe": 0,
                    },
                    {
                        "deployment": "groq/canopylabs/orpheus-v1-english",
                        "state": "exhausted",
                        "reason": "rate",
                        "reset_at": None,
                        "since": 1,
                        "last_observation": 1,
                        "last_probe": 0,
                    },
                    {
                        "deployment": "groq/whisper-large-v3-turbo",
                        "state": "dead",
                        "reason": "credit",
                        "since": 1,
                        "last_observation": 1,
                        "last_probe": 0,
                    },
                    {
                        "deployment": "moonshot/kimi-k3",
                        "state": "dead",
                        "reason": "credit",
                        "since": 1,
                        "last_observation": 1,
                        "last_probe": 0,
                    },
                ]
            }
        )
    )
    reg = _registry(mod)
    assert "gemini" not in reg._lanes  # ghost: dropped
    # the measured orpheus shape (exhausted, rate, no reset) and a dead non-chat lane
    # both heal: real traffic is their only observer now
    assert reg.state("groq/canopylabs/orpheus-v1-english") == "ready"
    assert reg.state("groq/whisper-large-v3-turbo") == "ready"
    assert reg.state("moonshot/kimi-k3") == "dead"  # chat death is evidence, kept
