"""Lane registry — the router already knows before the request arrives (CP1).

Spec: docs/specs/2026-10-01-anticipatory-router.md section 2.1. The estate router today
learns a lane is dead by failing THREE real user requests on it (`allowed_fails: 3`,
`cooldown_time: 60`, platform/llm/config.local.yaml) and probes nothing ahead of time
(`background_health_checks: false`). Measured 2026-10-01: pi -> moonshot/kimi-k3 burned
two retries on an account that had been out of balance for hours ("No fallback model group
found"), because no component held that fact.

This module holds one record per DEPLOYMENT (not per alias), in the router process:

  * passive measurement, free: every real call already is a probe. The success and
    failure logging hooks record latency, status, error class and the vendor's own
    rate-limit headers (x-ratelimit-remaining-*, retry-after).
  * error classes are facts, not counts. ONE observation transitions the lane:
    402 / "insufficient" / "suspended" / "balance" -> dead:credit   (until a probe answers)
    401 / 403                                  -> dead:auth
    429 with a reset                           -> exhausted (until the reset)
    timeout                                    -> degraded
    The router never re-learns a fact by failing three more user requests.
  * forecast: remaining quota / recent consumption rate = time to exhaustion. A lane
    forecast to exhaust inside the probe interval is drained (state `draining`) BEFORE
    it returns a 429 to a user.
  * active probes, only where passive data is stale: one-token calls through the
    deployment's own params, in parallel, cadence by state — a `ready` lane with fresh
    traffic is not probed; an idle one every 60 s; `exhausted` at its reset time;
    `dead` every 10 min (it rejoins the moment credit returns — no person flips it back).

State lives at ~/.estate/router/lanes.json (atomic tmp+rename) and every transition is
appended to ~/.estate/router/lanes.jsonl — the /fleet surface reads those files until the
bus contract grows a `router` enum (crew#1013, idp#4887 own the stream side).

LAW 38 (the registry may never fail a request): every observe, every write, every probe
is wrapped; a failure to journal is logged and dropped, never raised into the vendor call.

Registered as lane_registry.proxy_handler_instance in litellm_settings.callbacks; staged
by bin/litellm-local like every other MODULE.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Optional

log = logging.getLogger("estate.lane-registry")

# LiteLLM is present in the router image and absent everywhere else (CI, laptop tests) -- the
# estate's own rule from request_ceiling.py. The registry's LOGIC must be testable from both,
# and the proxy REFUSES TO START with a callback that is not a CustomLogger (measured
# 2026-10-02 on the :4010 canary: "resolved to LaneRegistry ... which is neither a CustomLogger
# instance nor a callable" -> "Application startup failed. Exiting.").
try:
    from litellm.integrations.custom_logger import CustomLogger
except ModuleNotFoundError:  # pragma: no cover - exercised wherever litellm is absent

    class CustomLogger:  # type: ignore[no-redef]
        """Stand-in so the registry stays importable and testable outside the router image."""


READY = "ready"
DEGRADED = "degraded"  # timeouts / slow, still served
EXHAUSTED = "exhausted"  # 429 with a reset time; rejoins at reset or probe
DRAINING = "draining"  # forecast to exhaust soon; route table deprioritises
DEAD = "dead"  # credit or auth; only a probe brings it back

REASON_CREDIT = "credit"
REASON_AUTH = "auth"
REASON_RATE = "rate"
REASON_TIMEOUT = "timeout"

SERVABLE = (READY, DEGRADED, DRAINING)  # states the route table may use

_DIR_ENV = "ESTATE_ROUTER_STATE_DIR"
_DIR_DEFAULT = "~/.estate/router"
_PROBES_ENV = "ESTATE_ROUTER_PROBES"  # "0" disables; default on
_CONFIG_ENV = "ESTATE_ROUTER_CONFIG"  # LiteLLM config with the model_list
_CONFIG_DEFAULT = "~/.estate/litellm-local/config.yaml"

# cadence (s) for the active probe, by state
CADENCE = {
    READY: 60,  # only when idle — fresh traffic suppresses it
    DEGRADED: 60,
    EXHAUSTED: 30,  # at/after its reset time
    DRAINING: 30,
    DEAD: 600,  # 10 min: it rejoins the moment credit returns
}
_SWEEP_S = 10
_PROBE_TIMEOUT_S = 10
_PROBE_CONCURRENCY = 4
_FRESH_S = 60  # a lane with a real call this recent needs no probe

# Modes a completion-shaped probe can actually grade. Other modes (audio_speech,
# audio_transcription, embeddings, image...) are real-traffic-only: a chat probe on them
# is a 400 about the CALLER, never about the lane. Measured on the live router 2026-10-02:
# orpheus TTS probed with chat -> voice-tts dead with no healing path, every TTS call
# rescued to a chat lane (garbled audio, not a rescue).
_CHAT_MODES = ("", "chat", "completion")

_RESET_HDRS = (
    "x-ratelimit-requests-reset",
    "x-ratelimit-reset-requests",
    "x-ratelimit-reset-tokens",
    "x-ratelimit-reset",
)
_REMAIN_HDRS = (
    "x-ratelimit-remaining-requests",
    "x-ratelimit-remaining-tokens",
    "x-ratelimit-remaining",
)

_CREDIT_RE = re.compile(r"insufficient|balance|suspended|payment|402", re.I)
_CALLER_ERROR_RE = re.compile(
    r"not found|does not exist|no deployments|model group|invalid model", re.I
)


def _state_dir() -> str:
    return os.path.expanduser(os.environ.get(_DIR_ENV) or _DIR_DEFAULT)


def _config_path() -> str:
    return os.path.expanduser(os.environ.get(_CONFIG_ENV) or _CONFIG_DEFAULT)


def _modes() -> dict[str, str]:
    """deployment -> model_info.mode from the staged config ("" when unstated = chat)."""
    out: dict[str, str] = {}
    try:
        import yaml

        doc = yaml.safe_load(open(_config_path(), encoding="utf-8")) or {}
        for m in doc.get("model_list") or []:
            if not isinstance(m, dict):
                continue
            key = str((m.get("litellm_params") or {}).get("model") or "")
            if not key:
                key = str(m.get("model_name") or "")
            if key:
                out[key] = str(((m.get("model_info") or {}).get("mode")) or "").lower()
    except Exception as exc:  # noqa: BLE001 - LAW 38
        log.warning("[lane-registry] modes not readable: %s", exc)
    return out


# --------------------------------------------------------------------- classification


def classify_failure(status: Optional[int], text: str) -> tuple[str, str]:
    """One observation is enough. Returns (state, reason); ("", "") = caller error — the
    lane's health is untouched (a 404 says the model name was wrong, nothing about the lane;
    measured on the :4010 canary 2026-10-02: wrong-model 404s were landing as degraded)."""
    text = text or ""
    if status in (400, 404, 413, 415, 422):
        return "", ""
    if status is None and _CALLER_ERROR_RE.search(text):
        # the router's own "model group does not exist" carries no HTTP status; measured on
        # the :4010 canary 2026-10-02 (transition to degraded for a model that never existed)
        return "", ""
    if (
        status == 429
        or "rate limit" in text.lower()
        or "resource_exhausted" in text.lower()
    ):
        return EXHAUSTED, REASON_RATE
    if (
        status in (401, 403)
        or "unauthor" in text.lower()
        or "invalid api key" in text.lower()
    ):
        return DEAD, REASON_AUTH
    if _CREDIT_RE.search(text) or status == 402:
        return DEAD, REASON_CREDIT
    if status is None and ("timeout" in text.lower() or "timed out" in text.lower()):
        return DEGRADED, REASON_TIMEOUT
    if status is not None and 500 <= status < 600:
        return DEGRADED, "server"
    return DEGRADED, "error"


def _hdrs_of(obj: Any) -> dict[str, str]:
    """Headers from a LiteLLM response/exception, whatever shape it arrives in."""
    out: dict[str, str] = {}
    for carrier in (
        obj,
        getattr(obj, "response", None),
        getattr(obj, "_response", None),
    ):
        if not carrier:
            continue
        raw = None
        if isinstance(carrier, dict):
            raw = carrier.get("headers") or carrier.get("response_headers")
        else:
            raw = getattr(carrier, "headers", None)
        if raw:
            try:
                for k in raw.keys():
                    out[str(k).lower()] = str(raw.get(k, ""))
            except Exception as exc:  # noqa: BLE001 - headers are best-effort telemetry
                log.debug("[lane-registry] header extraction skipped: %s", exc)
        if out:
            break
    return out


def _reset_epoch(hdrs: dict[str, str], now: float) -> Optional[float]:
    """reset headers: epoch seconds, ISO 8601, or relative seconds (retry-after)."""
    ra = hdrs.get("retry-after")
    if ra:
        try:
            return now + float(ra)
        except ValueError:
            pass
    for h in _RESET_HDRS:
        v = hdrs.get(h)
        if not v:
            continue
        try:
            fv = float(v)
        except ValueError:
            continue
        # heuristics are not guesswork here: epoch values are ~1.7e9, ms ~1.7e12, s/duration small
        if fv > 1e12:
            return fv / 1000.0
        if fv > 1e9:
            return fv
        return now + fv
    return None


# -------------------------------------------------------------------------- the record


def _blank(deployment: str) -> dict[str, Any]:
    return {
        "deployment": deployment,
        "state": READY,
        "reason": "",
        "since": time.time(),
        "last_observation": 0.0,  # last REAL call (success or failure)
        "last_probe": 0.0,
        "latency_ms_p50": None,
        "latency_ms_p95": None,
        "status": None,
        "reset_at": None,  # epoch, for exhausted
        "remaining_requests": None,  # from vendor headers, when the vendor says
        "remaining_tokens": None,
        "consumed_recent": 0.0,  # tokens/min over the recent window (passive)
        "forecast_exhausts_at": None,
        "billing": "metered",
    }


class LaneRegistry(CustomLogger):
    """One instance lives in the router process; hooks feed it, probes heal it."""

    def __init__(self) -> None:
        self._lanes: dict[str, dict[str, Any]] = {}
        self._lat: dict[str, list[float]] = {}
        self._lock = asyncio.Lock() if _has_loop() else None
        self._probe_task: Optional[asyncio.Task] = None
        self._on_transition: list[Any] = []  # route_table subscribes here
        self._load()

    # ------------------------------------------------------------------ persistence

    def _json_path(self) -> str:
        return os.path.join(_state_dir(), "lanes.json")

    def _jsonl_path(self) -> str:
        return os.path.join(_state_dir(), "lanes.jsonl")

    def _load(self) -> None:
        try:
            with open(self._json_path(), encoding="utf-8") as fh:
                doc = json.load(fh)
            for row in doc.get("lanes", []):
                if isinstance(row, dict) and row.get("deployment"):
                    self._lanes[str(row["deployment"])] = row
        except FileNotFoundError:
            pass
        except Exception as exc:  # noqa: BLE001 - LAW 38: never fail the request path
            log.warning("[lane-registry] lanes.json not loaded: %s", exc)
        self._reconcile_loaded()

    def _reconcile_loaded(self) -> None:
        """Loaded state must square with the config actually staged.

        Two measured defects of the boot-window state (2026-10-02, live router):
          * ghost records — a failure attributed before it resolved to a deployment
            ("gemini", "cheap": dead:auth with no params, unhealable noise);
          * non-chat lanes dead from a completion-shaped probe era — real traffic is
            their only observer now, so a dead non-chat lane could never heal.
        """
        try:
            known = _modes()
            if not known:
                return  # config unreadable: fail open, judge nothing
            ghosts = [k for k in self._lanes if k not in known]
            for k in ghosts:
                del self._lanes[k]
            if ghosts:
                self._persist("load-purge", "ghosts", {"dropped": ghosts})
            for key, mode in known.items():
                if mode in _CHAT_MODES:
                    continue
                lane = self._lanes.get(key)
                if lane and lane.get("state") in (DEAD, EXHAUSTED):
                    # measured 2026-10-02 on the live router: a TTS lane took ONE 429
                    # with no reset header -> exhausted with reset_at=None -> not
                    # servable -> no real traffic -> chat-shaped probes 400 as caller
                    # errors -> permanent. Real traffic is the only observer for
                    # non-chat lanes: hand back, the next real call re-condemns in ONE
                    # observation if the lane is truly out (rate windows are minutes).
                    old = lane["state"]
                    lane["state"] = READY
                    lane["reason"] = ""
                    lane["since"] = time.time()
                    lane["reset_at"] = None
                    self._persist(
                        "load-heal", key, {"from": old, "to": READY, "why": "non-chat"}
                    )
        except Exception as exc:  # noqa: BLE001 - LAW 38
            log.warning("[lane-registry] loaded state not reconciled: %s", exc)

    def _persist(
        self, event: str, deployment: str, extra: Optional[dict] = None
    ) -> None:
        """Atomic snapshot + one append-only transition row. Never raises (LAW 38)."""
        try:
            import pathlib

            d = pathlib.Path(_state_dir())
            d.mkdir(parents=True, exist_ok=True)
            snap = d / "lanes.json"
            tmp = d / "lanes.json.tmp"
            tmp.write_text(
                json.dumps(
                    {"lanes": list(self._lanes.values())}, indent=2, sort_keys=True
                ),
                encoding="utf-8",
            )
            os.replace(tmp, snap)
            with open(self._jsonl_path(), "a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "t": round(time.time(), 3),
                            "event": event,
                            "lane": deployment,
                            **(extra or {}),
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("[lane-registry] journal not written: %s", exc)

    # ------------------------------------------------------------------- observation

    def _transition(
        self,
        lane: dict[str, Any],
        state: str,
        reason: str,
        reset_at: Optional[float] = None,
    ) -> None:
        if lane["state"] == state and lane.get("reason") == reason:
            return
        old = lane["state"]
        lane["state"] = state
        lane["reason"] = reason
        lane["since"] = time.time()
        lane["reset_at"] = reset_at if state == EXHAUSTED else None
        self._persist(
            "transition", lane["deployment"], {"from": old, "to": state, "why": reason}
        )
        for cb in list(self._on_transition):
            try:
                cb(lane["deployment"], state)
            except Exception as exc:  # noqa: BLE001
                log.warning("[lane-registry] transition listener failed: %s", exc)

    def _record(self, deployment: str) -> dict[str, Any]:
        return self._lanes.setdefault(deployment, _blank(deployment))

    def observe_success(
        self, deployment: str, latency_ms: float, headers: Optional[dict] = None
    ) -> None:
        try:
            lane = self._record(deployment)
            now = time.time()
            lane["last_observation"] = now
            lane["status"] = 200
            hist = self._lat.setdefault(deployment, [])
            hist.append(latency_ms)
            del hist[:-50]
            s = sorted(hist)
            lane["latency_ms_p50"] = s[len(s) // 2]
            lane["latency_ms_p95"] = (
                s[int(len(s) * 0.95) - 1] if len(s) >= 20 else s[-1]
            )
            hdrs = {k.lower(): v for k, v in (headers or {}).items()}
            for h in _REMAIN_HDRS:
                if h in hdrs:
                    try:
                        lane["remaining_requests"] = float(hdrs[h])
                        break
                    except ValueError:
                        pass
            reset = _reset_epoch(hdrs, now)
            if lane["state"] in (EXHAUSTED, DEAD, DRAINING):
                # credit came back / reset passed — a real call is the strongest probe
                self._transition(lane, READY, "")
            elif (
                reset
                and lane["state"] == READY
                and lane.get("remaining_requests") is not None
                and lane["remaining_requests"] < 5
            ):
                self._transition(lane, DRAINING, "quota")
            lane["forecast_exhausts_at"] = self._forecast(lane)
            self._persist(
                "observe",
                deployment,
                {"latency_ms": latency_ms, "remaining": lane["remaining_requests"]},
            )
        except Exception as exc:  # noqa: BLE001 - LAW 38
            log.warning("[lane-registry] success not recorded: %s", exc)

    def observe_failure(
        self,
        deployment: str,
        status: Optional[int],
        text: str,
        headers: Optional[dict] = None,
    ) -> None:
        try:
            lane = self._record(deployment)
            now = time.time()
            lane["last_observation"] = now
            lane["status"] = status
            state, reason = classify_failure(status, text)
            if not state:
                # caller error: observed, journaled, but never a lane-health transition
                self._persist(
                    "observe", deployment, {"status": status, "caller_error": True}
                )
                return
            hdrs = {k.lower(): v for k, v in (headers or {}).items()}
            reset = _reset_epoch(hdrs, now)
            self._transition(lane, state, reason, reset_at=reset)
            self._persist("observe", deployment, {"status": status, "state": state})
        except Exception as exc:  # noqa: BLE001 - LAW 38
            log.warning("[lane-registry] failure not recorded: %s", exc)

    def _forecast(self, lane: dict[str, Any]) -> Optional[float]:
        """remaining / consumption-rate = time to exhaustion; None when unknowable."""
        rem = lane.get("remaining_tokens")
        rate = lane.get("consumed_recent")
        if rem is None or not rate or rate <= 0:
            return None
        return time.time() + (rem / rate) * 60.0

    # -------------------------------------------------------------------- reading

    def state(self, deployment: str) -> str:
        lane = self._lanes.get(deployment)
        if not lane:
            return READY  # unknown lanes are never condemned without evidence
        if (
            lane["state"] == EXHAUSTED
            and lane.get("reset_at")
            and time.time() >= lane["reset_at"]
        ):
            # reset passed with no traffic: hand back to probing, not to users
            return EXHAUSTED
        return lane["state"]

    def servable(self, deployment: str) -> bool:
        return self.state(deployment) in SERVABLE

    def snapshot(self) -> dict[str, Any]:
        return {"lanes": [dict(v) for v in self._lanes.values()]}

    def on_transition(self, cb: Any) -> None:
        self._on_transition.append(cb)

    # -------------------------------------------------------------------- probes

    def probe_due(self, deployment: str, now: Optional[float] = None) -> bool:
        lane = self._lanes.get(deployment)
        if not lane:
            return False
        now = now or time.time()
        if lane["state"] == READY and now - lane["last_observation"] < _FRESH_S:
            return False  # fresh traffic: no probe
        if (
            lane["state"] == EXHAUSTED
            and lane.get("reset_at")
            and now < lane["reset_at"]
        ):
            return False  # the vendor told us when; don't ask before then
        cad = CADENCE.get(lane["state"], 60)
        return now - max(lane["last_probe"], lane["last_observation"]) >= cad

    async def _probe_one(self, deployment: str, params: dict[str, Any]) -> None:
        import litellm

        lane = self._record(deployment)
        lane["last_probe"] = time.time()
        if not (params.get("api_key") or params.get("api_base")):
            # No resolved params for this deployment (no config, or no key in this process):
            # a keyless probe would fail auth and condemn a healthy lane. Skip, never guess.
            self._persist(
                "probe", deployment, {"verdict": "skipped", "why": "no params"}
            )
            return
        try:
            await asyncio.wait_for(
                litellm.acompletion(
                    model=params.get("model", deployment),
                    api_key=params.get("api_key"),
                    api_base=params.get("api_base"),
                    messages=[{"role": "user", "content": "1"}],
                    max_tokens=1,
                    timeout=_PROBE_TIMEOUT_S,
                ),
                _PROBE_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            self._persist("probe", deployment, {"verdict": "timeout"})
            return
        except Exception as exc:  # noqa: BLE001 - a failed probe is a fact, not an error
            st = getattr(exc, "status_code", None)
            self._persist(
                "probe",
                deployment,
                {"verdict": "fail", "status": st, "text": str(exc)[:200]},
            )
            state, reason = classify_failure(
                st if isinstance(st, int) else None, str(exc)
            )
            if state in (DEAD, EXHAUSTED):
                self._transition(lane, state, reason)
            return
        self._persist("probe", deployment, {"verdict": "ok"})
        self._transition(
            lane, READY, ""
        )  # a dead lane rejoins the moment credit returns

    async def _probe_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(_SWEEP_S)
                params = self._deployment_params()
                due = [d for d in params if d in self._lanes and self.probe_due(d)]
                if not due:
                    continue
                sem = asyncio.Semaphore(_PROBE_CONCURRENCY)

                async def guarded(
                    d: str, _sem: "asyncio.Semaphore" = sem, _params: dict = params
                ) -> None:
                    async with _sem:
                        await self._probe_one(d, _params.get(d, {}))

                await asyncio.gather(*(guarded(d) for d in due))
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - the loop outlives any one sweep
                log.warning("[lane-registry] probe sweep failed: %s", exc)

    def _deployment_params(self) -> dict[str, dict[str, Any]]:
        """model_list of the staged config -> {deployment: params}. os.environ/X resolved."""
        out: dict[str, dict[str, Any]] = {}
        try:
            import yaml

            doc = yaml.safe_load(open(_config_path(), encoding="utf-8")) or {}
            for m in doc.get("model_list") or []:
                if not isinstance(m, dict):
                    continue
                lp = dict(m.get("litellm_params") or {})
                key = lp.get("model", m.get("model_name", ""))
                mode = str(((m.get("model_info") or {}).get("mode")) or "").lower()
                if mode not in _CHAT_MODES:
                    continue  # a completion probe cannot grade this mode (see _CHAT_MODES)
                for f in ("api_key", "api_base"):
                    v = lp.get(f)
                    if isinstance(v, str) and v.startswith("os.environ/"):
                        lp[f] = os.environ.get(v.split("/", 1)[1])
                out[key] = lp
        except Exception as exc:  # noqa: BLE001 - probes degrade to nothing, never crash
            log.warning("[lane-registry] config not readable for probes: %s", exc)
        return out

    def ensure_probes(self) -> None:
        """Start the probe loop once, on the router's event loop. Never raises."""
        try:
            if os.environ.get(_PROBES_ENV) == "0":
                return
            if self._probe_task and not self._probe_task.done():
                return
            loop = asyncio.get_running_loop()
            self._probe_task = loop.create_task(self._probe_loop())
        except RuntimeError:
            pass  # no loop (import time / tests): the first hook call starts it
        except Exception as exc:  # noqa: BLE001
            log.warning("[lane-registry] probes not started: %s", exc)

    # -------------------------------------------------------- LiteLLM hooks (proxy)

    @staticmethod
    def _deployment_of(kwargs: dict[str, Any]) -> Optional[str]:
        md = (kwargs.get("litellm_params") or {}).get("metadata") or {}
        for k in ("deployment", "deployment_name", "model_id"):
            if md.get(k):
                return str(md[k])
        mi = kwargs.get("model_info") or {}
        if mi.get("id"):
            return str(mi["id"])
        m = kwargs.get("model")
        if m:
            # a resolved failure can carry the bare model name: count it only if it names
            # a REAL deployment in the staged config. Otherwise it is a requested alias
            # (or garbage) and is never a lane-health fact — the ghost-record defect
            # (measured 2026-10-02 on the live router: "gemini", "cheap" dead:auth forever)
            try:
                if str(m) in _modes():
                    return str(m)
            except Exception as exc:  # noqa: BLE001 - attribution must never raise
                log.debug("[lane-registry] model-name attribution skipped: %s", exc)
        return None

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            self.ensure_probes()
            ms = 0.0
            try:
                ms = (end_time - start_time).total_seconds() * 1000.0
            except Exception as exc:  # noqa: BLE001 - telemetry must never break a call
                log.debug("[lane-registry] timing unavailable: %s", exc)
            dep = self._deployment_of(kwargs)
            if dep:
                self.observe_success(dep, ms, _hdrs_of(response_obj))
        except Exception as exc:  # noqa: BLE001 - LAW 38
            log.warning("[lane-registry] success hook: %s", exc)

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        try:
            self.ensure_probes()
            status = getattr(response_obj, "status_code", None)
            if status is None and isinstance(response_obj, dict):
                status = response_obj.get("status_code")
            text = str(getattr(response_obj, "message", "") or response_obj or "")
            if not text and status is None:
                # routing failures carry no response object; the error is in kwargs (measured
                # on the :4010 canary 2026-10-02: response_obj was empty for a 404 model-group miss)
                exc = kwargs.get("exception")
                if exc is not None:
                    status = getattr(exc, "status_code", None)
                    text = str(getattr(exc, "message", "") or exc)
            dep = self._deployment_of(kwargs)
            if dep:
                self.observe_failure(
                    dep,
                    status if isinstance(status, int) else None,
                    text,
                    _hdrs_of(response_obj),
                )
        except Exception as exc:  # noqa: BLE001 - LAW 38
            log.warning("[lane-registry] failure hook: %s", exc)


def _has_loop() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


proxy_handler_instance = LaneRegistry()
