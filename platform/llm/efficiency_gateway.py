"""Estate efficiency gateway: one cache-safe token-optimisation chain in a LiteLLM pre-call hook.

MODEL-AGNOSTIC: runs before every vendor call through llm.${ESTATE_ZONE}.
Applies to: minimax, groq, gemini, cerebras, sambanova, openrouter, ollama.
Registered as: efficiency_gateway.proxy_handler_instance in litellm_settings.callbacks.
Mounted at: /etc/litellm/ceilings/efficiency_gateway.py (same ConfigMap as request_ceiling.py).
PYTHONPATH: /etc/litellm/ceilings (set in platform/llm/litellm.yaml env block).

The ceiling (request_ceiling.py) REFUSES oversized requests before they reach this hook.
This hook OPTIMISES requests that pass the ceiling — reducing tokens billed per call.

ONE CHAIN, EVERY LANE (idp#4893, 2026-09-29). Two wire shapes reach this hook -- Anthropic
content blocks (Claude Code) and OpenAI messages (pi, opencode, Cline, every other model) -- and
the estate is model-agnostic, so every step is written once over both. A prompt/KV cache
(Anthropic, OpenAI, vLLM) only hits a byte-identical prefix, so every step is APPEND-STABLE: a
message's transform depends only on itself and the messages before it, never on the
conversation's length, and turn n+1 re-sends the bytes turn n sent. The sliding OpenAI-shaped
chain that ran here before (drop beyond 60 messages, gist beyond 40, non-adjacent line dedup,
cross-call observation handles) rewrote the prefix on every call and is deleted.
  [7] epoch compaction: a step function, never a slide -- shadow state, snap, hash lock (below);
  [8] edge purge: reasoning stripped only inside a lock's fixed range, never the newest turn;
  [2] collapses runs of identical CONSECUTIVE lines inside tool results (never non-adjacent
      dedup, which deletes a repeated `}` or `return` and corrupts code);
  [5] replaces an exact repeat of an earlier large tool result with a pointer to the first
      one, which is still in the request (per request, never a cross-call memory);
  [9] checks tool call/result pairing and the first role, and never drops anything;
  [1] proves the cache survives: hashes system+tools and every transformed message per
      conversation and records how much of the previous call's prefix this call re-sent;
  [3] does NOT act: tool schemas sit in the cached prefix and trimming them degrades tool use.
async_log_success_event then records what the vendor actually billed for the call (uncached,
cache read, cache write 5m/1h, output), so "saved" is measured, not estimated.
"""

import hashlib
import json
import logging
import os
import threading
import time
from typing import Any, Optional, Union

log = logging.getLogger("estate.efficiency-gateway")


# --------------------------------------------------------------------------- ledger
#
# WHY THIS EXISTS (2026-09-18). Every mechanism below already mutated the request and
# incremented an in-memory counter, and that counter died with the process. Measured on the
# founder's own machine: `efficiency-latest.txt` read `hit_rate=0.0% (0 cached / 0 fresh)`
# while ~18M tokens were served at a 99.9% cache-hit rate one process away, so the one
# file that claimed to report the mechanisms reported nothing at all. "Built and wired" is
# not evidence; a scientist wants the per-call delta.
#
# So each mechanism now records bytes in -> bytes out for EVERY call, and the row carries
# the raw before/after sizes so the saving is recomputable by a reader rather than trusted.
# Same ledger shape read_shunt already uses (`est_*` fields, one JSONL line per event), so
# the estate has one audit format and not two.
#
# The ledger may NEVER fail a request (LAW 38): every write is wrapped, and a failure to
# journal is logged and dropped, never raised into the vendor call.
_LEDGER_ENV = "ESTATE_EFFICIENCY_LEDGER"
_LEDGER_DEFAULT = "~/.estate/efficiency-ledger.jsonl"


def _ledger_path() -> str:
    return os.path.expanduser(os.environ.get(_LEDGER_ENV) or _LEDGER_DEFAULT)


def _ledger_write(row: dict[str, Any]) -> None:
    try:
        p = _ledger_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    except Exception as exc:  # noqa: BLE001 - the ledger may never fail the request (LAW 38)
        log.warning("[ledger] not written: %s", exc)


def _json_bytes(obj: Any) -> int:
    """The size of what the vendor would actually be sent, not a character count.

    The mechanisms below mutate nested dicts in place, so measuring the whole messages/
    tools payload before and after is the only honest way to attribute a delta to the
    mechanisms as a group. Per-mechanism numbers are recorded alongside it.
    """
    try:
        return len(json.dumps(obj, separators=(",", ":"), default=str).encode())
    except Exception:  # noqa: BLE001
        return 0


try:
    from litellm.integrations.custom_logger import CustomLogger
except ModuleNotFoundError:
    # Importable on any machine without litellm (CI, laptop).
    class CustomLogger:  # type: ignore[no-redef]
        async def async_pre_call_hook(self, *a, **k):
            raise NotImplementedError


CHARS_PER_TOKEN = 4
TOKENS_PER_MTOK = 1_000_000
MAX_TOOL_DESC_CHARS = int(os.environ.get("ESTATE_MAX_TOOL_DESC_CHARS", "400"))
MAX_HISTORY_MSGS = int(os.environ.get("ESTATE_MAX_HISTORY_MSGS", "60"))
MAX_HISTORY_BYTES = int(os.environ.get("ESTATE_MAX_HISTORY_BYTES", "200000"))
GIST_AFTER_MSGS = int(os.environ.get("ESTATE_GIST_AFTER_MSGS", "40"))
STALE_THRESHOLD = int(os.environ.get("ESTATE_STALE_THRESHOLD", "10"))
MIN_OBS_CHARS = int(os.environ.get("ESTATE_MIN_OBS_CHARS", "500"))


RUN_MIN = int(os.environ.get("ESTATE_RUN_MIN_LINES", "3"))
CONV_MEMORY = 256  # conversations whose prefix hashes are kept for the stability check
CACHE_READ_RATE = (
    0.1  # Anthropic's price of a cache read, relative to an uncached input token
)
CACHE_WRITE_5M_RATE = 1.25
CACHE_WRITE_1H_RATE = 2.0


# Founder 2026-09-28: Opus plans, Sonnet executes, and that "should be impossible to circumvent".
# A harness setting (opusplan) is overridden by any /model switch -- measured that day, 35 pinned
# sessions produced 88% of all turns -- so the router decides. PLAN_MARKER is the text Claude Code
# 2.1.283 injects into the user turn in plan mode (read from its binary). A context too large for
# the executor keeps its model rather than failing the call.
PLAN_MARKER = "Plan mode is active."
EXECUTOR_MODEL = os.environ.get("ESTATE_EXECUTOR_MODEL", "claude-sonnet-5")
EXECUTOR_MAX_BYTES = int(os.environ.get("ESTATE_EXECUTOR_MAX_BYTES", str(600_000)))


def _newest_user_text(data: dict) -> str:
    for m in reversed(data.get("messages") or []):
        if isinstance(m, dict) and m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                return c
            return " ".join(
                b.get("text", "")
                for b in c or []
                if isinstance(b, dict) and b.get("type") == "text"
            )
    return ""


def _fit_executor(data: dict) -> None:
    """Drop what the executor rejects (measured 400s on 2026-09-28, Claude Code 2.1.283):
    `output_config.effort` -- "requires a model that supports per-turn effort" -- and deferred
    tools -- "tool_addition/tool_removal is not supported on this model"."""
    if data.pop("output_config", None) is not None:
        # anthropic_beta_passthrough re-adds any client field a hook removed, unless named here.
        data["litellm_estate_dropped"] = ["output_config"]
    for t in data.get("tools") or []:
        if isinstance(t, dict):
            t.pop("defer_loading", None)


def _route_model(data: dict) -> str:
    model = str(data.get("model") or "")
    if "opus" not in model.lower() or PLAN_MARKER in _newest_user_text(data):
        return model
    size = _json_bytes(data.get("messages") or []) + _json_bytes(
        data.get("system") or []
    )
    if size > EXECUTOR_MAX_BYTES:
        return model
    return EXECUTOR_MODEL


def _is_anthropic(data: dict, call_type: Any) -> bool:
    if "anthropic_messages" in str(call_type):
        return True
    for m in data.get("messages") or []:
        c = m.get("content") if isinstance(m, dict) else None
        if isinstance(c, list) and any(
            isinstance(b, dict) and b.get("type") in ("tool_use", "tool_result")
            for b in c
        ):
            return True
    return False


def _session_id(data: dict) -> str:
    """Claude Code puts {"session_id": ...} as a JSON string in metadata.user_id."""
    meta = data.get("metadata") or {}
    uid = meta.get("user_id") if isinstance(meta, dict) else None
    if isinstance(uid, str):
        try:
            sid = json.loads(uid).get("session_id")
            if sid:
                return str(sid)
        except (ValueError, AttributeError):
            return uid[:64]
    return str(data.get("litellm_session_id") or "-")


# --------------------------------------------------------------------------- holdout
#
# WHY (2026-09-29). The ledger shows what the chain cut and what the vendor billed AFTER the
# cut, never what the same conversation would have been billed without it -- and with a prompt
# cache in play the difference is not the tokens cut: a cut token was mostly a cache read at a
# tenth of the price, and a snap re-writes the prefix at 1.25-2x. The only measurement that
# settles it is a randomised control: a fixed share of conversations runs with every step off,
# and the report compares what the vendor billed per call in each arm. Assignment hashes the
# conversation, never the call, so a conversation stays in one arm for its whole life.
HOLDOUT_PCT = float(os.environ.get("ESTATE_HOLDOUT_PCT", "25"))
HOLDOUT_SALT = os.environ.get("ESTATE_HOLDOUT_SALT", "trial-2026-09-29")


def _conversation_key(data: dict, session: str) -> str:
    """Claude Code sends a session id; pi/opencode do not, so their first message stands in."""
    if session and session != "-":
        return session
    return _h((data.get("messages") or [])[:2])


def _arm(key: str) -> str:
    h = int(hashlib.sha256(f"{HOLDOUT_SALT}:{key}".encode()).hexdigest()[:8], 16)
    return "control" if (h % 10000) < HOLDOUT_PCT * 100 else "treat"


def _strip_cache_control(obj: Any) -> Any:
    # Claude Code moves its cache_control breakpoints every turn; they are not content.
    if isinstance(obj, dict):
        return {
            k: _strip_cache_control(v) for k, v in obj.items() if k != "cache_control"
        }
    if isinstance(obj, list):
        return [_strip_cache_control(v) for v in obj]
    return obj


def _h(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(_strip_cache_control(obj), sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def _collapse_runs(text: str) -> tuple[str, int]:
    """Collapse runs of >= RUN_MIN identical consecutive non-blank lines. Returns (text, bytes saved).

    Only adjacent repeats: the first line stays verbatim and the rest become one count marker,
    so no information is lost and nothing non-adjacent (a `}` or `return` in code) is touched.
    """
    lines = text.split("\n")
    out: list = []
    i = 0
    changed = False
    while i < len(lines):
        j = i
        while j + 1 < len(lines) and lines[j + 1] == lines[i]:
            j += 1
        n = j - i + 1
        marker = f"[router: previous line repeated {n - 1} more times]"
        if (
            lines[i].strip()
            and n >= RUN_MIN
            and len(marker) < len("\n".join(lines[i + 1 : j + 1]))
        ):
            out += [lines[i], marker]
            changed = True
        else:
            out += lines[i : j + 1]
        i = j + 1
    if not changed:
        return text, 0
    new = "\n".join(out)
    return new, len(text.encode()) - len(new.encode())


def _tool_result_text(block: dict) -> Optional[str]:
    """The text of a tool_result whose content is text only; None if it carries anything else."""
    c = block.get("content")
    if isinstance(c, str):
        return c
    if (
        isinstance(c, list)
        and c
        and all(isinstance(b, dict) and b.get("type") == "text" for b in c)
    ):
        return "\n".join(str(b.get("text") or "") for b in c)
    return None


# --------------------------------------------------------------------------- epochs
#
# [7] EPOCH COMPACTION + [8] EDGE PURGE, one implementation for every lane (idp#4893). Measured
# 2026-09-29: 870.6 MB sent in a day, 0.3 % cut, because the Anthropic chain never compacted and
# the OpenAI chain compacted by sliding window, which rewrites the prefix on every call so no
# prompt/KV cache (Anthropic, OpenAI, vLLM) can ever hit. The physics are the same everywhere:
# a prefix must be immutable. So compaction is a step function, never a slide:
#
#   shadow state -- once a conversation is big enough, a background thread folds the history it
#       has not yet seen into a small YAML state document through the router's own cheap lanes
#       (LiteLLM owns the fallback chain). Chunked, so no fold exceeds a free model's context;
#       the caller never waits for it.
#   snap -- when the payload passes ESTATE_EPOCH_TOKENS, cut at a clean boundary the state
#       already covers (an assistant turn that no tool call/result pair crosses) and replace
#       everything before it with the frozen state. One deliberate cache miss.
#   hash lock -- the lock (hash of the replaced messages + the frozen state text) is persisted.
#       The harness never learns of the cut and re-sends the full history every call; every
#       call whose history starts with exactly those messages gets exactly the same bytes, so
#       the prefix stays byte-identical until the next epoch.
#   edge purge -- thinking/reasoning is stripped only from the assistant turns between the cut
#       and the last assistant turn at snap time: a range fixed in the lock, so deterministic.
#
# Two wire shapes reach this hook, so every helper reads both: Anthropic content blocks
# (tool_use / tool_result / thinking) and OpenAI messages (leading system, tool_calls,
# role="tool", reasoning_content).

EPOCH_TOKENS = int(os.environ.get("ESTATE_EPOCH_TOKENS", "80000"))
EPOCH_KEEP_TOKENS = int(os.environ.get("ESTATE_EPOCH_KEEP_TOKENS", "16000"))
EPOCH_STRIP = os.environ.get("ESTATE_EPOCH_STRIP", "1") != "0"
SHADOW_FROM_TOKENS = int(os.environ.get("ESTATE_SHADOW_FROM_TOKENS", "40000"))
SHADOW_EVERY_TOKENS = int(os.environ.get("ESTATE_SHADOW_EVERY_TOKENS", "8000"))
SHADOW_CHUNK_CHARS = int(os.environ.get("ESTATE_SHADOW_CHUNK_CHARS", "24000"))
SHADOW_MSG_CHARS = 1500
# Fold chunks run ~9-14k tokens: groq's free tier caps at 8k TPM, cerebras wants payment and
# sambanova's key is rejected, so the fold goes to lanes proven to take a full chunk.
SHADOW_MODEL = os.environ.get("ESTATE_SHADOW_MODEL", "deepseek")
SHADOW_FALLBACKS = [
    x for x in os.environ.get("ESTATE_SHADOW_FALLBACKS", "minimax,fast").split(",") if x
]
SHADOW_URL = os.environ.get(
    "ESTATE_SHADOW_URL", "http://127.0.0.1:4000/v1/chat/completions"
)
STATE_MAX_CHARS = 6000
INTERNAL = "estate-shadow-state"  # metadata tag on the router's own fold calls
_EPOCH_DIR_ENV = "ESTATE_EPOCH_DIR"
_EPOCH_DIR_DEFAULT = "~/.estate/efficiency-epochs"
SHADOW_PROMPT = (
    "You maintain the working memory of a software agent's session as one YAML document. "
    "Given the CURRENT STATE and NEW EVENTS from the session, return the updated YAML only, "
    "no prose, no code fences. Keys: objective, decisions, facts (proven, with exact paths, "
    "commands, ids, numbers), failures (what was tried and why it failed), open, next. "
    "Keep every concrete identifier; drop chatter; never invent anything not in the events. "
    "Stay under 1500 words."
)


def _split_head(msgs: list) -> "tuple[list, list]":
    """(leading system messages, the conversation after them)."""
    i = 0
    while (
        i < len(msgs) and isinstance(msgs[i], dict) and msgs[i].get("role") == "system"
    ):
        i += 1
    return msgs[:i], msgs[i:]


def _calls_made(m: Any) -> set:
    """Tool-call ids an assistant message opens, either wire shape."""
    if not isinstance(m, dict) or m.get("role") != "assistant":
        return set()
    ids = {tc.get("id") for tc in m.get("tool_calls") or [] if isinstance(tc, dict)}
    c = m.get("content")
    if isinstance(c, list):
        ids |= {
            b.get("id")
            for b in c
            if isinstance(b, dict) and b.get("type") == "tool_use"
        }
    return ids


def _result_blocks(m: Any) -> list:
    """Every tool result a message carries, either wire shape (the block, or the tool message)."""
    if not isinstance(m, dict):
        return []
    if m.get("role") == "tool":
        return [m]
    c = m.get("content")
    if m.get("role") == "user" and isinstance(c, list):
        return [b for b in c if isinstance(b, dict) and b.get("type") == "tool_result"]
    return []


def _clean_cut(hist: list, cut: int) -> bool:
    """True when hist[cut] is an assistant turn and no tool call/result pair crosses the cut."""
    if not (0 < cut < len(hist)) or not isinstance(hist[cut], dict):
        return False
    if hist[cut].get("role") != "assistant":
        return False
    opened: set = set()
    for m in hist[:cut]:
        opened |= _calls_made(m)
    for m in hist[cut:]:
        for b in _result_blocks(m):
            if (b.get("tool_use_id") or b.get("tool_call_id")) in opened:
                return False
    return True


def _strip_reasoning(m: Any) -> int:
    """Drop thinking/reasoning from one assistant message, either wire shape. Bytes removed."""
    if not isinstance(m, dict) or m.get("role") != "assistant":
        return 0
    before = _json_bytes(m)
    for k in ("reasoning_content", "thinking_blocks", "reasoning"):
        m.pop(k, None)
    c = m.get("content")
    if isinstance(c, list):
        kept = [
            b
            for b in c
            if not (
                isinstance(b, dict)
                and b.get("type") in ("thinking", "redacted_thinking")
            )
        ]
        if kept:  # never leave an empty turn
            m["content"] = kept
    return before - _json_bytes(m)


def _render(m: Any) -> str:
    """One message as plain text for the fold; thinking is never sent, long bodies are capped."""
    if not isinstance(m, dict):
        return ""
    parts = []
    c = m.get("content")
    if isinstance(c, str):
        parts.append(c[:SHADOW_MSG_CHARS])
    elif isinstance(c, list):
        for b in c:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if t == "text":
                parts.append(str(b.get("text") or "")[:SHADOW_MSG_CHARS])
            elif t == "tool_use":
                parts.append(
                    f"call {b.get('name')} {json.dumps(b.get('input'), default=str)[:400]}"
                )
            elif t == "tool_result":
                text = _tool_result_text(b) or "[non-text result]"
                tag = "ERROR" if b.get("is_error") else "result"
                parts.append(f"{tag}: {text[:SHADOW_MSG_CHARS]}")
    for tc in m.get("tool_calls") or []:
        fn = (tc.get("function") or {}) if isinstance(tc, dict) else {}
        parts.append(f"call {fn.get('name')} {str(fn.get('arguments'))[:400]}")
    body = "\n".join(p for p in parts if p)
    return f"[{m.get('role')}] {body}" if body else ""


def _chunks(hist: list) -> list:
    out, cur = [], ""
    for m in hist:
        r = _render(m)
        if not r:
            continue
        if cur and len(cur) + len(r) > SHADOW_CHUNK_CHARS:
            out.append(cur)
            cur = ""
        cur += r[:SHADOW_CHUNK_CHARS] + "\n"
    if cur:
        out.append(cur)
    return out


def _fold_remote(state: str, events: str) -> str:
    """One fold through the router's own cheap lanes; LiteLLM walks the fallbacks."""
    import urllib.request

    key = os.environ.get("ESTATE_LOCAL_CALLER_KEY") or os.environ.get(
        "LITELLM_MASTER_KEY", ""
    )
    body = {
        "model": SHADOW_MODEL,
        "fallbacks": SHADOW_FALLBACKS,
        "temperature": 0,
        "max_tokens": 2000,
        "metadata": {"estate_internal": INTERNAL},
        "messages": [
            {"role": "system", "content": SHADOW_PROMPT},
            {
                "role": "user",
                "content": f"CURRENT STATE:\n{state or '(empty)'}\n\nNEW EVENTS:\n{events}",
            },
        ],
    }
    headers = {"Content-Type": "application/json", "X-Estate-Internal": INTERNAL}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if not SHADOW_URL.startswith(("http://", "https://")):
        raise ValueError(f"ESTATE_SHADOW_URL must be http(s): {SHADOW_URL!r}")
    req = urllib.request.Request(  # noqa: S310 - scheme checked above
        SHADOW_URL, data=json.dumps(body).encode(), headers=headers
    )
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 - fixed local router URL
        out = json.load(r)["choices"][0]["message"]["content"] or ""
    out = out.strip()
    if out.startswith("```"):
        out = out.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    if not out:
        raise ValueError("fold returned an empty state")
    return out[:STATE_MAX_CHARS]


def _is_internal(data: dict) -> bool:
    meta = data.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("estate_internal") == INTERNAL:
        return True
    req = data.get("proxy_server_request") or {}
    hdrs = req.get("headers") or {} if isinstance(req, dict) else {}
    return isinstance(hdrs, dict) and hdrs.get("x-estate-internal") == INTERNAL


def _fresh(root: str) -> dict:
    return {"covered": 0, "covered_hash": root, "state": "", "locks": []}


class _Epochs:
    """[7] epoch snap + hash lock, [8] edge purge, and the shadow state behind them."""

    def __init__(self) -> None:
        self._mu = threading.Lock()
        self._convs: dict = {}
        self._busy: set = set()
        self.fold = _fold_remote  # (state, events) -> state; tests inject a stub
        self.spawn = lambda fn, *a: threading.Thread(
            target=fn, args=a, daemon=True
        ).start()

    def _path(self, key: str) -> str:
        d = os.path.expanduser(os.environ.get(_EPOCH_DIR_ENV) or _EPOCH_DIR_DEFAULT)
        return os.path.join(d, hashlib.sha256(key.encode()).hexdigest()[:24] + ".json")

    def _load(self, key: str, root: str) -> dict:
        rec = self._convs.get(key)
        if rec is None:
            try:
                with open(self._path(key), encoding="utf-8") as fh:
                    rec = json.load(fh)
            except (OSError, ValueError):
                rec = _fresh(root)
            self._convs[key] = rec
            while len(self._convs) > CONV_MEMORY:
                self._convs.pop(next(iter(self._convs)))
        return rec

    def _save(self, key: str, rec: dict) -> None:
        try:
            p = self._path(key)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            tmp = f"{p}.{os.getpid()}.tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(rec, fh)
            os.replace(tmp, p)
        except Exception as exc:  # noqa: BLE001 - never fail the request (LAW 38)
            log.warning("[7-Epoch] lock not persisted: %s", exc)

    def apply(self, data: dict, session: str) -> dict:
        """Rewrite data["messages"] under the newest matching lock; maybe snap; maybe fold."""
        msgs = data.get("messages") or []
        head, hist = _split_head(msgs)
        m7: dict = {
            "action": "none",
            "bytes": 0,
            "why": f"step compaction at {EPOCH_TOKENS} tokens under a hash lock; never a slide",
        }
        m8: dict = {
            "action": "none",
            "blocks": 0,
            "bytes": 0,
            "why": "reasoning stripped only inside a lock's fixed edge range",
        }
        if not hist:
            return {"m7": m7, "m8": m8}
        hh = [_h(m) for m in hist]
        sizes = [_json_bytes(m) for m in hist]
        cum = [hashlib.sha256(b"epoch").hexdigest()[:16]]
        for x in hh:
            cum.append(hashlib.sha256((cum[-1] + x).encode()).hexdigest()[:16])
        key = f"{session}:{hh[0]}"
        with self._mu:
            rec = self._load(key, cum[0])
            if rec["covered"] > len(hist) or cum[rec["covered"]] != rec["covered_hash"]:
                # the history was rewritten under us (the harness compacted, or a new branch)
                rec = _fresh(cum[0])
                self._convs[key] = rec
            lock = next(
                (
                    lk
                    for lk in reversed(rec["locks"])
                    if lk["cut"] <= len(hist) and cum[lk["cut"]] == lk["hash"]
                ),
                None,
            )
            base = lock["cut"] if lock else 0
            tokens = (
                sum(sizes[base:]) + len(lock["state"] if lock else "")
            ) // CHARS_PER_TOKEN
            if tokens > EPOCH_TOKENS and rec["state"] and rec["covered"] > base:
                keep, limit = 0, len(hist)
                while limit > 0 and keep < EPOCH_KEEP_TOKENS * CHARS_PER_TOKEN:
                    limit -= 1
                    keep += sizes[limit]
                cut = min(rec["covered"], limit)
                while cut > base + 1 and not _clean_cut(hist, cut):
                    cut -= 1
                if cut > base + 1 and _clean_cut(hist, cut):
                    last_asst = max(
                        i
                        for i, m in enumerate(hist)
                        if isinstance(m, dict) and m.get("role") == "assistant"
                    )
                    lock = {
                        "n": len(rec["locks"]) + 1,
                        "cut": cut,
                        "hash": cum[cut],
                        "state": rec["state"],
                        "edge_end": last_asst,
                        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                    rec["locks"] = (rec["locks"] + [lock])[-8:]
                    self._save(key, rec)
                    m7["action"] = "snapped"
            covered, state = rec["covered"], rec["state"]
            fold = (
                sum(sizes) // CHARS_PER_TOKEN >= SHADOW_FROM_TOKENS
                and sum(sizes[covered:]) // CHARS_PER_TOKEN >= SHADOW_EVERY_TOKENS
                and key not in self._busy
            )
            if fold:
                self._busy.add(key)
        if fold:
            # rendered now, before later steps touch the messages; folded off the request path
            self.spawn(
                self._shadow,
                key,
                state,
                _chunks(hist[covered:]),
                covered,
                len(hist),
                cum,
            )
        m7["shadow"] = {
            "covered_msgs": covered,
            "state_chars": len(state),
            "folding": bool(fold) or key in self._busy,
        }
        if lock is None:
            m7["est_tokens"] = sum(sizes) // CHARS_PER_TOKEN
            return {"m7": m7, "m8": m8}
        cut = lock["cut"]
        stripped = saved8 = 0
        if EPOCH_STRIP:
            for m in hist[cut : lock["edge_end"]]:
                sv = _strip_reasoning(m)
                if sv > 0:
                    stripped, saved8 = stripped + 1, saved8 + sv
        note = {
            "role": "user",
            "content": (
                f"[estate router, epoch {lock['n']}: the first {cut} messages of this "
                "conversation were replaced by this state document, which the router kept "
                "from them. Treat it as your memory of that work; every message after it is "
                f"verbatim.]\n\n{lock['state']}"
            ),
        }
        data["messages"] = head + [note] + hist[cut:]
        if m7["action"] != "snapped":
            m7["action"] = "locked"
        m7.update(
            epoch=lock["n"],
            replaced_msgs=cut,
            bytes=max(0, sum(sizes[:cut]) - _json_bytes(note)),
            est_tokens=_json_bytes(data["messages"]) // CHARS_PER_TOKEN,
        )
        if stripped:
            m8.update(action="stripped", blocks=stripped, bytes=saved8)
        return {"m7": m7, "m8": m8}

    def _shadow(self, key, state, chunks, base, target, cum) -> None:
        started, err = time.time(), None
        try:
            for ch in chunks:
                state = self.fold(state, ch)
            with self._mu:
                rec = self._convs.get(key)
                if rec is not None and rec["covered"] == base:
                    rec.update(covered=target, covered_hash=cum[target], state=state)
                    self._save(key, rec)
        except Exception as exc:  # noqa: BLE001 - a failed fold only delays the next epoch
            err = str(exc)[:300]
        finally:
            with self._mu:
                self._busy.discard(key)
            row = {
                "v": 2,
                "kind": "shadow",
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
                "model": SHADOW_MODEL,
                "ok": err is None,
                "ms": round((time.time() - started) * 1000),
                "chunks": len(chunks),
                "covered_msgs": target if err is None else base,
                "state_chars": len(state or ""),
            }
            if err:
                row["error"] = err
            _ledger_write(row)


class _AnthropicSteps:
    """The append-stable chain, for every lane and both wire shapes. See the module docstring."""

    def __init__(self) -> None:
        # conversation key -> (system+tools hash, [per-message hash, ...]) from its last call
        self._convs: "dict[str, tuple[str, list]]" = {}

    def run(self, data: dict, session: str) -> dict:
        msgs = data.get("messages") or []
        steps: dict = {}

        # [2] TokenKiller -- adjacent runs only, inside tool_result text
        runs = saved2 = 0
        for m in msgs:
            for b in _result_blocks(m):
                c = b.get("content")
                if isinstance(c, str):
                    new, sv = _collapse_runs(c)
                    if sv > 0:
                        b["content"], runs, saved2 = new, runs + 1, saved2 + sv
                elif isinstance(c, list):
                    for tb in c:
                        if (
                            isinstance(tb, dict)
                            and tb.get("type") == "text"
                            and isinstance(tb.get("text"), str)
                        ):
                            new, sv = _collapse_runs(tb["text"])
                            if sv > 0:
                                tb["text"], runs, saved2 = new, runs + 1, saved2 + sv
        steps["m2"] = {
            "action": "collapsed" if runs else "none",
            "blocks": runs,
            "bytes": saved2,
            "why": "adjacent identical lines in tool results -> one line + count",
        }

        # [5] SoLPi -- exact repeats of an earlier large tool_result, within THIS request
        first: dict = {}
        hits = saved5 = 0
        for m in msgs:
            for b in _result_blocks(m):
                # Errors are never deduplicated: a repeated denial is new information to the
                # model, and the pointer hid which call was refused.
                if b.get("is_error"):
                    continue
                text = _tool_result_text(b)
                if text is None or len(text) < MIN_OBS_CHARS:
                    continue
                h = hashlib.sha256(text.encode()).hexdigest()[:16]
                if h not in first:
                    first[h] = b.get("tool_use_id") or b.get("tool_call_id")
                    continue
                ref = (
                    f"[router: identical to the tool result of {first[h]} earlier in this "
                    f"conversation ({len(text)} chars, sha256 {h[:8]}); not repeated]"
                )
                before = _json_bytes(b.get("content"))
                b["content"] = ref
                hits += 1
                saved5 += before - _json_bytes(ref)
        steps["m5"] = {
            "action": "deduplicated" if hits else "none",
            "results": hits,
            "bytes": saved5,
            "why": f"exact repeat (>= {MIN_OBS_CHARS} chars) of an earlier tool result in the same request",
        }
        steps["m6"] = {
            "action": "merged-into-m5",
            "bytes": 0,
            "why": "one dedup pass; a second would only re-hash the same blocks",
        }

        # [3] [7] [8] -- deliberately inert on this lane, and saying so every call
        tools = data.get("tools") or []
        steps["m3"] = {
            "action": "skipped",
            "bytes": 0,
            "tools": len(tools),
            "tools_bytes": _json_bytes(tools),
            "why": "tool schemas sit in the cached prefix (0.1x); trimming them costs tool-use quality",
        }
        est_tokens = (
            _json_bytes(msgs) + _json_bytes(data.get("system")) + _json_bytes(tools)
        ) // CHARS_PER_TOKEN
        steps["m7"] = {
            "action": "skipped",
            "bytes": 0,
            "est_tokens": est_tokens,
            "why": "Claude Code compacts its own history; dropping turns breaks the cache and loses context",
        }
        steps["m8"] = {
            "action": "skipped",
            "bytes": 0,
            "why": "assistant turns carry thinking signatures; Anthropic rejects edited ones",
        }

        # [9] pairing -- every tool_result answers a tool_use in the assistant turn before it
        orphans = 0
        open_ids: set = set()
        for m in msgs:
            if isinstance(m, dict) and m.get("role") == "assistant":
                open_ids = _calls_made(m)
                continue
            for b in _result_blocks(m):
                if (b.get("tool_use_id") or b.get("tool_call_id")) not in open_ids:
                    orphans += 1
        head_msgs, hist = _split_head(msgs)
        first_role = hist[0].get("role") if hist and isinstance(hist[0], dict) else None
        steps["m9"] = {
            "action": "checked",
            "orphans": orphans,
            "first_role": first_role,
            "why": "reports, never drops: pairs are kept whole by construction",
        }

        # [1] CacheGuardian -- measured last, on exactly the bytes that will be sent
        head = _h([data.get("system"), tools, head_msgs])
        hashes = [_h(m) for m in hist]
        conv = f"{session}:{data.get('model')}:{hashes[0] if hashes else '-'}"
        prev = self._convs.pop(conv, None)
        common = 0
        if prev:
            for a, b in zip(prev[1], hashes):  # noqa: B905 -- runtime falls back to py3.9, no strict= kwarg
                if a != b:
                    break
                common += 1
        self._convs[conv] = (head, hashes)
        while len(self._convs) > CONV_MEMORY:
            self._convs.pop(next(iter(self._convs)))
        steps["m1"] = {
            "action": "first-call" if prev is None else "checked",
            "system_tools_changed": bool(prev and prev[0] != head),
            "prefix_prev_msgs": len(prev[1]) if prev else 0,
            "prefix_kept_msgs": common,
            "prefix_broken": bool(prev and (common < len(prev[1]) or prev[0] != head)),
            "why": "this call must re-send the previous call's messages byte-identical or the cache misses",
        }
        return steps


def _cost_usd(kwargs: dict) -> Optional[float]:
    """The dollars LiteLLM billed this call at from its maintained price map, cache rates included.

    Never a price sheet of our own: a reader can check the figure against LiteLLM's
    model_prices_and_context_window.json for the same model and usage.
    """
    for c in (
        kwargs.get("response_cost"),
        (kwargs.get("standard_logging_object") or {}).get("response_cost"),
    ):
        try:
            if c is not None:
                return round(float(c), 8)
        except (TypeError, ValueError):
            continue
    return None


def _usage_numbers(response_obj: Any, kwargs: dict) -> Optional[dict]:
    """What Anthropic billed for the call, from the response usage LiteLLM hands the callback."""
    u = None
    try:
        u = (
            response_obj.get("usage")
            if isinstance(response_obj, dict)
            else getattr(response_obj, "usage", None)
        )
    except Exception:  # noqa: BLE001
        u = None
    if u is None:
        slo = kwargs.get("standard_logging_object") or {}
        u = (slo.get("metadata") or {}).get("usage_object")
    if u is None:
        return None

    def g(o: Any, k: str) -> Any:
        return o.get(k) if isinstance(o, dict) else getattr(o, k, None)

    prompt = int(g(u, "prompt_tokens") or 0)
    # Anthropic reports cache_read_input_tokens; OpenAI-style vendors prompt_tokens_details.cached_tokens
    read = int(
        g(u, "cache_read_input_tokens")
        or g(g(u, "prompt_tokens_details") or {}, "cached_tokens")
        or 0
    )
    write = int(g(u, "cache_creation_input_tokens") or 0)
    details = (
        g(g(u, "prompt_tokens_details") or {}, "cache_creation_token_details") or {}
    )
    w1h = int(g(details, "ephemeral_1h_input_tokens") or 0)
    w5m = max(0, write - w1h)
    uncached = max(0, prompt - read - write)
    out = int(g(u, "completion_tokens") or 0)
    # Input-token-equivalents at Anthropic's relative prices: what the call cost, and what the
    # same prompt would have cost with no cache at all. Exact given the usage, no estimation.
    billed = (
        uncached
        + w5m * CACHE_WRITE_5M_RATE
        + w1h * CACHE_WRITE_1H_RATE
        + read * CACHE_READ_RATE
    )
    return {
        "prompt_tokens": prompt,
        "uncached_input": uncached,
        "cache_read": read,
        "cache_write_5m": w5m,
        "cache_write_1h": w1h,
        "output_tokens": out,
        "input_equiv_billed": round(billed, 1),
        "input_equiv_no_cache": prompt,
        "cache_saved_input_equiv": round(prompt - billed, 1),
        "cache_hit_pct": round(read / prompt * 100, 2) if prompt else 0.0,
    }


class EstateEfficiencyGateway(CustomLogger):
    """One append-stable chain on every call, every lane: m7 epoch, m8 edge purge, m2, m5, m9, m1."""

    def __init__(self) -> None:
        self._calls = 0
        self._cumulative_tokens = 0
        # Anthropic lane: prefix memory per conversation, and the pre-call summary per call id
        # so the outcome row carries what the router did next to what Anthropic billed.
        self._anthropic = _AnthropicSteps()
        self._pending: dict = {}
        # [7][8] on every lane: epoch snap + hash lock + edge purge (idp#4893)
        self._epochs = _Epochs()

    # ---------------------------------------------------------------------- hook

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: Union[Any, str],
    ) -> Optional[dict]:
        """Run all 8 mechanisms in sequence, then record what they actually saved.

        The before/after byte counts are taken around the WHOLE chain and written to the
        ledger alongside each mechanism's own per-mechanism byte delta. A reader can then
        check two independent things: that the mechanisms changed the payload at all, and
        which one changed it. `bytes_saved` is the chain total; the per-mechanism numbers
        are measured inside each step, so they are independent rather than a decomposition
        of a number that was computed after the fact.
        """
        started = time.time()
        if _is_internal(data):
            return (
                data  # the router's own shadow-state fold: never compacted or recorded
            )
        try:
            return self._anthropic_call(data, call_type, started)
        except Exception as exc:  # noqa: BLE001 - never fail the request (LAW 38)
            log.warning("[EfficiencyGateway] chain skipped: %s", exc)
            return data

    # ------------------------------------------------------------ anthropic lane

    def _anthropic_call(self, data: dict, call_type: Any, started: float) -> dict:
        session = _session_id(data)
        requested = data.get("model") or ""
        data["model"] = _route_model(data)
        if data["model"] != requested:
            _fit_executor(data)
        msgs = data.get("messages") or []
        before = _json_bytes(msgs)
        conv = _conversation_key(data, session)
        arm = _arm(conv)
        if arm == "control":
            steps: dict = {}  # the holdout: the vendor gets exactly what the caller sent
        else:
            epoch = self._run_epochs(data, session)
            steps = self._anthropic.run(data, session)
            steps.update(epoch)
        after = _json_bytes(data.get("messages") or [])
        self._calls += 1
        self._cumulative_tokens += (steps.get("m7") or {}).get("est_tokens", 0)
        row = {
            "v": 2,
            "kind": "pre",
            "arm": arm,
            "conv": conv[:16],
            "mode": "anthropic" if _is_anthropic(data, call_type) else "openai",
            "call_id": data.get("litellm_call_id"),
            "session": session,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
            "call_type": str(call_type),
            "model": data.get("model") or "",
            "model_requested": requested,
            "ms": round((time.time() - started) * 1000, 2),
            "messages": len(msgs),
            "bytes_before": before,
            "bytes_after": after,
            "bytes_saved": max(0, before - after),
            "est_tokens_cut": max(0, before - after) // CHARS_PER_TOKEN,
            "steps": steps,
        }
        _ledger_write(row)
        if row["call_id"]:
            self._pending[row["call_id"]] = row
            while len(self._pending) > 512:
                self._pending.pop(next(iter(self._pending)))
        if arm == "control":
            return data
        m1 = steps["m1"]
        log.info(
            "[EfficiencyGateway] anthropic %s msgs=%d saved=%dB (m2 %dB, m5 %dB) prefix %d/%d%s",
            row["model"],
            len(msgs),
            row["bytes_saved"],
            steps["m2"]["bytes"],
            steps["m5"]["bytes"],
            m1["prefix_kept_msgs"],
            m1["prefix_prev_msgs"],
            " BROKEN" if m1["prefix_broken"] else "",
        )
        return data

    def _run_epochs(self, data: dict, session: Optional[str] = None) -> dict:
        try:
            return self._epochs.apply(data, session or _session_id(data))
        except Exception as exc:  # noqa: BLE001 - never fail the request (LAW 38)
            log.warning("[7-Epoch] skipped: %s", exc)
            return {
                "m7": {
                    "action": "error",
                    "bytes": 0,
                    "est_tokens": 0,
                    "error": str(exc)[:200],
                },
                "m8": {"action": "none", "blocks": 0, "bytes": 0},
            }

    def _outcome(
        self,
        kwargs: dict,
        response_obj: Any,
        start_time: Any,
        end_time: Any,
        error: Any = None,
    ) -> None:
        try:
            call_id = kwargs.get("litellm_call_id")
            pre = self._pending.pop(call_id, None) if call_id else None
            if pre is None:
                return  # not a call this gateway shaped (e.g. OpenAI lane): nothing to pair
            try:
                ms = round((end_time - start_time).total_seconds() * 1000)
            except Exception:  # noqa: BLE001
                ms = None
            row = {
                "v": 2,
                "kind": "outcome",
                "mode": pre["mode"],
                "call_id": call_id,
                "session": pre.get("session"),
                "model": pre.get("model"),
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "latency_ms": ms,
                "ok": error is None,
                "arm": pre.get("arm", "treat"),
                "conv": pre.get("conv"),
                "messages": pre.get("messages"),
                "bytes_before": pre.get("bytes_before"),
                "bytes_after": pre.get("bytes_after"),
                "est_tokens_cut": pre.get("est_tokens_cut", 0),
                "prefix_broken": (pre["steps"].get("m1") or {}).get("prefix_broken"),
            }
            if error is not None:
                row["error"] = str(error)[:300]
            else:
                row["usage"] = _usage_numbers(response_obj, kwargs)
                row["cost_usd"] = _cost_usd(kwargs)
            _ledger_write(row)
        except Exception as exc:  # noqa: BLE001 - the ledger may never fail the request
            log.warning("[ledger] outcome not written: %s", exc)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._outcome(kwargs, response_obj, start_time, end_time)

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        self._outcome(
            kwargs,
            response_obj,
            start_time,
            end_time,
            error=kwargs.get("exception") or "failed",
        )


proxy_handler_instance = EstateEfficiencyGateway()
