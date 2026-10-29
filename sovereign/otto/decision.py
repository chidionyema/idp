"""The founder-decision door: one structured question to the founder, one answer back.

WHAT THIS IS. Any agent -- any harness, any model, laptop or cluster -- can put a bounded,
structured decision in front of the founder on the estate's one Otto Telegram chat, and read
the answer back in the same shape it asked. The founder answers with a comment on the decision
message, in his own words; the door turns that comment into a typed answer.

WHY IT EXISTS LIKE THIS (issue #7340).

* ONE door, not a new layer. The estate already has exactly one Telegram bot and exactly one
  webhook (`platform/otto-gateway/telegram-mirror.yaml`); this module speaks to that bot with
  the same credentials the card uses. There is no second bot, no second webhook, no new
  service, no new database.
* NO model in the delivery or answer path. The cloud router is 503 today; the door must not
  care. Delivery is one Bot API call, matching is a deterministic function, recording is a
  file write. Nothing here calls a model.
* EXACTLY ONE message per decision, ever. Asking twice with the same id never sends a second
  message (the record already exists -> the existing record is returned).
* FAIL CLOSED. No answer by the deadline is `expired`, never "assumed yes". A comment that
  cannot be parsed is recorded verbatim with `option: null` -- never silently coerced into
  an option, never dropped.
* THE FOUNDER'S WORDS ARE THE TRUTH. The answer is stored verbatim. The parsed option is a
  convenience; the comment is the attestation.

THE ANSWER'S DETERMINISTIC MATCHING, in order:

1. The comment must quote the decision id (or be an exact option key / `approve` / `deny`
   when exactly one decision is live -- see `match_comment`).
2. An exact option key (case-insensitive) picks that option.
3. `approve` / `deny` picks the option with that key, if the request has one.
4. Anything else: the whole comment is the answer, `option` stays null, `answer` holds the
   verbatim comment.

THE BUS IS THE DURABLE RECORD, WHEN IT IS THERE. The estate's sovereign bus already has the
ask/wait/answer loop: a session in the `ask` runner parks in `asking` and halts with
default-deny on silence (`sovereign/engine/workflow.py`). The door opens such a session when
the bus is reachable, and the founder's comment is steered into it, so the answer also lands
in the estate's signed receipt chain (`by=founder`, the comment as the attestation). The
local state file is the door's own index -- it is not a second authority, and when the bus
is unreachable the door says so (`bus: "unavailable"`) instead of pretending.

THE WEBHOOK. The estate's reader of the founder's replies is the gateway's webhook. When
that ingress is unreachable (it is today -- #7343), the founder's reply has nowhere to
land, so the door can HOLD the bot's updates itself: `ask --take-webhook` deletes the
webhook, keeps the URL to restore, and the door restores it when the last decision closes.
This is opt-in, bounded by the decision's deadline, and there is never more than one reader:
if the estate's gateway re-registers the webhook, `getUpdates` answers 409 and the door
yields rather than fighting it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

SCHEMA = "founder.decision.v1"
MAX_OPTIONS = 5
MAX_CONTEXT = 5
DEFAULT_DEADLINE_MIN = 60
DEFAULT_BUS_BUDGET = 5000
TELEGRAM_API_BASE = "https://api.telegram.org"

STATE_ASKED = "asked"
STATE_ANSWERED = "answered"
STATE_EXPIRED = "expired"

_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")


class DecisionError(ValueError):
    """A decision request that must not be sent. Raised before anything is delivered."""


# --- the request -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionOption:
    key: str
    label: str

    def to_dict(self) -> dict:
        return {"key": self.key, "label": self.label}


@dataclass(frozen=True)
class DecisionRequest:
    decision_id: str
    question: str
    options: tuple = ()
    context: tuple = ()
    deadline_min: int = DEFAULT_DEADLINE_MIN
    requester: str = ""

    def validate(self) -> None:
        if not self.decision_id or not re.match(
            r"^dec-[0-9a-f]{6,32}$", self.decision_id
        ):
            raise DecisionError(
                f"decision_id must look like dec-<hex>, got {self.decision_id!r}"
            )
        if not self.question.strip():
            raise DecisionError("question must not be empty")
        if len(self.options) > MAX_OPTIONS:
            raise DecisionError(
                f"at most {MAX_OPTIONS} options, got {len(self.options)}"
            )
        if len(self.context) > MAX_CONTEXT:
            raise DecisionError(
                f"at most {MAX_CONTEXT} context links, got {len(self.context)}"
            )
        keys = [o.key for o in self.options]
        if len(set(k.lower() for k in keys)) != len(keys):
            raise DecisionError("option keys must be unique")
        for opt in self.options:
            if not _KEY_RE.match(opt.key):
                raise DecisionError(f"option key {opt.key!r} is not a single safe word")
        if self.deadline_min <= 0:
            raise DecisionError("deadline_min must be positive")

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "question": self.question,
            "options": [o.to_dict() for o in self.options],
            "context": list(self.context),
            "deadline_min": self.deadline_min,
            "requester": self.requester,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DecisionRequest":
        options = tuple(
            DecisionOption(key=str(o["key"]), label=str(o.get("label", "")))
            for o in data.get("options", [])
        )
        return cls(
            decision_id=str(data["decision_id"]),
            question=str(data.get("question", "")),
            options=options,
            context=tuple(str(c) for c in data.get("context", [])),
            deadline_min=int(data.get("deadline_min", DEFAULT_DEADLINE_MIN)),
            requester=str(data.get("requester", "")),
        )


def new_decision_id() -> str:
    return "dec-" + uuid.uuid4().hex[:8]


def parse_options(raw: str) -> tuple:
    """`"ship: land it, hold: wait"` -> (DecisionOption('ship', 'land it'), ...).

    A bare key with no label is allowed (the label defaults to the key). An empty string is
    no options at all -- a question the founder answers in words.
    """
    options = []
    for chunk in (raw or "").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        key, _, label = chunk.partition(":")
        key = key.strip()
        label = label.strip() or key
        if not key:
            raise DecisionError(f"option {chunk!r} has no key")
        options.append(DecisionOption(key=key, label=label))
    return tuple(options)


def parse_context(raw: str) -> tuple:
    links = []
    for chunk in (raw or "").split(","):
        chunk = chunk.strip()
        if chunk:
            links.append(chunk)
    return tuple(links)


def build_request(
    *,
    question: str,
    options: str = "",
    context: str = "",
    deadline_min: int = DEFAULT_DEADLINE_MIN,
    requester: str = "",
    decision_id: str = "",
) -> DecisionRequest:
    request = DecisionRequest(
        decision_id=decision_id or new_decision_id(),
        question=question.strip(),
        options=parse_options(options),
        context=parse_context(context),
        deadline_min=int(deadline_min),
        requester=requester.strip(),
    )
    request.validate()
    return request


# --- the message ----------------------------------------------------------------------------------


def render(request: DecisionRequest) -> str:
    """One message, id first, so the founder can quote it with a comment.

    Plain text on purpose: the estate's card sends HTML, but a decision message must never
    fail to deliver because the question contains a `<` or an `&`.
    """
    lines = [request.decision_id, request.question]
    if request.options:
        lines.append("")
        lines.append("options:")
        for index, opt in enumerate(request.options, start=1):
            lines.append(f"{index}. {opt.key}: {opt.label}")
    if request.context:
        lines.append("")
        lines.append("context:")
        for link in request.context:
            lines.append(f"- {link}")
    lines.append("")
    lines.append(f"answer by commenting: {request.decision_id} <option key>")
    lines.append(
        f"deadline: {request.deadline_min} min   requester: {request.requester or 'unknown'}"
    )
    return "\n".join(lines)


# --- the matcher ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Answer:
    option: Optional[str]
    kind: str
    text: str

    def to_dict(self) -> dict:
        return {"option": self.option, "kind": self.kind, "text": self.text}


def match_comment(comment: str, request: DecisionRequest) -> Answer:
    """Deterministic matching. `kind` says WHICH rule fired.

    * `unrelated`  -- the comment does not answer this decision.
    * `option`     -- an option key (or approve/deny) matched.
    * `free_text`  -- the whole comment is the answer; `option` stays null.
    """
    text = (comment or "").strip()
    if not text:
        return Answer(None, "unrelated", text)
    if request.decision_id in text:
        tail = text.split(request.decision_id, 1)[1].strip()
        return _match_tail(tail, text, request)
    # No id quoted. The only id-less comment that counts is an exact option key (or
    # approve/deny) -- a free-text chat message must never be captured as an answer.
    lowered = text.strip().lower()
    for opt in request.options:
        if lowered == opt.key.lower():
            return Answer(opt.key, "option", text)
    if lowered in ("approve", "deny"):
        for opt in request.options:
            if opt.key.lower() == lowered:
                return Answer(opt.key, "option", text)
        return Answer(None, "free_text", text)
    return Answer(None, "unrelated", text)


def _match_tail(tail: str, text: str, request: DecisionRequest) -> Answer:
    if not tail:
        return Answer(None, "free_text", text)
    first = tail.split()[0].strip().strip(".,:;!?\"'").lower()
    for opt in request.options:
        if opt.key.lower() == first:
            return Answer(opt.key, "option", text)
    if first in ("approve", "deny"):
        for opt in request.options:
            if opt.key.lower() == first:
                return Answer(opt.key, "option", text)
        return Answer(None, "free_text", text)
    return Answer(None, "free_text", text)


# --- the state file -------------------------------------------------------------------------------


def state_path() -> Path:
    override = os.environ.get("ESTATE_DECISION_STATE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".estate" / "sovereign" / "decisions.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(path: Optional[Path] = None) -> dict:
    target = Path(path) if path else state_path()
    if not target.is_file():
        return {"schema": SCHEMA, "decisions": {}}
    try:
        data = json.loads(target.read_text())
    except (json.JSONDecodeError, OSError):
        return {"schema": SCHEMA, "decisions": {}}
    if not isinstance(data, dict):
        return {"schema": SCHEMA, "decisions": {}}
    data.setdefault("schema", SCHEMA)
    data.setdefault("decisions", {})
    return data


def save_state(state: dict, path: Optional[Path] = None) -> Path:
    target = Path(path) if path else state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    os.replace(tmp, target)
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target


def get_decision(decision_id: str, path: Optional[Path] = None) -> Optional[dict]:
    return load_state(path)["decisions"].get(decision_id)


def live_decisions(path: Optional[Path] = None) -> list:
    return [
        rec
        for rec in load_state(path)["decisions"].values()
        if rec.get("state") == STATE_ASKED
    ]


def expire_due(path: Optional[Path] = None, now: Optional[datetime] = None) -> list:
    """Mark every unanswered decision past its deadline as expired. Silence is never a yes."""
    moment = now or _now()
    state = load_state(path)
    expired = []
    for rec in state["decisions"].values():
        if rec.get("state") != STATE_ASKED:
            continue
        deadline = rec.get("deadline_at")
        if not deadline:
            continue
        if moment >= datetime.strptime(deadline, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        ):
            rec["state"] = STATE_EXPIRED
            rec["expired_at"] = _iso(moment)
            rec["option"] = None
            rec["answer"] = None
            expired.append(rec)
    if expired:
        save_state(state, path)
    return expired


# --- the Telegram transport ------------------------------------------------------------------------


def _env_file_values() -> dict:
    """The estate's own credentials file -- the same one `sovereign.otto.card` reads.

    The door does NOT import the card (the card pulls httpx; the door must run on a
    stdlib-only interpreter), but it must read the SAME file, so there is one place where
    the estate's one bot token lives.
    """
    raw = os.environ.get(
        "ESTATE_ENV", str(Path.home() / ".config" / "estate" / "estate.env")
    )
    path = Path(raw).expanduser()
    values: dict = {}
    if not path.is_file():
        return values
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip("'\"")
    except OSError:
        return values
    return values


def telegram_credentials() -> tuple:
    """(token, chat_id) for the estate's one founder bot. Never logged, never printed."""
    values = _env_file_values()
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or values.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_HOME_CHANNEL") or values.get(
        "TELEGRAM_HOME_CHANNEL"
    )
    return (token or None, chat or None)


def telegram_call(
    token: str, method: str, payload: dict, timeout_s: float = 10.0
) -> dict:
    """One Bot API call. The token is never logged, never in an exception message."""
    url = f"{TELEGRAM_API_BASE}/bot{token}/{method}"
    body = json.dumps(payload).encode()
    request = urllib.request.Request(  # noqa: S310 - the Bot API is a fixed https endpoint
        url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:  # noqa: S310
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        try:
            return json.loads(detail)
        except json.JSONDecodeError:
            return {"ok": False, "description": f"http {exc.code}"}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"ok": False, "description": f"{type(exc).__name__}"}


def send_message(token: str, chat_id: str, text: str) -> Optional[int]:
    result = telegram_call(
        token,
        "sendMessage",
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
    )
    if not result.get("ok"):
        return None
    try:
        return int(result["result"]["message_id"])
    except (KeyError, TypeError, ValueError):
        return None


def get_updates(token: str, limit: int = 100) -> list:
    """Pending updates. Empty when the estate's webhook owns the bot (409) -- that is a
    yield, not a failure: the door never fights the estate's own reader."""
    result = telegram_call(token, "getUpdates", {"limit": limit, "timeout": 0})
    if not result.get("ok"):
        return []
    updates = result.get("result")
    return updates if isinstance(updates, list) else []


def webhook_info(token: str) -> dict:
    result = telegram_call(token, "getWebhookInfo", {})
    if not result.get("ok"):
        return {}
    info = result.get("result")
    return info if isinstance(info, dict) else {}


def delete_webhook(token: str) -> bool:
    return bool(telegram_call(token, "deleteWebhook", {}).get("ok"))


def set_webhook(token: str, url: str) -> bool:
    return bool(telegram_call(token, "setWebhook", {"url": url}).get("ok"))


def update_text(update: dict) -> Optional[str]:
    message = update.get("message") if isinstance(update, dict) else None
    if not isinstance(message, dict):
        return None
    text = message.get("text")
    return str(text) if isinstance(text, str) else None


def update_chat_id(update: dict) -> Optional[str]:
    message = update.get("message") if isinstance(update, dict) else None
    if not isinstance(message, dict):
        return None
    chat = message.get("chat")
    if not isinstance(chat, dict):
        return None
    chat_id = chat.get("id")
    return str(chat_id) if chat_id is not None else None


# --- the bus (the durable record, when it is there) ------------------------------------------------


def _sb(repo: str, *args: str, timeout_s: float = 30.0) -> tuple:
    sb = Path(repo).expanduser() / "bin" / "sb"
    if not sb.is_file():
        return False, f"no bus at {sb}"
    try:
        proc = subprocess.run(  # noqa: S603 - the estate's own CLI, fixed path
            [str(sb), *args, "--json"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"{type(exc).__name__}"
    out = proc.stdout.strip()
    if proc.returncode != 0:
        return False, (proc.stderr.strip() or out or f"exit {proc.returncode}")[-200:]
    try:
        return True, json.loads(out)
    except (json.JSONDecodeError, ValueError):
        return True, out


def bus_start_ask(
    task: str, by: str, repo: str, budget: int = DEFAULT_BUS_BUDGET
) -> Optional[str]:
    """Open a session in the `ask` runner: it parks in `asking` and halts with default-deny
    on silence. The session id is the durable record of the decision."""
    ok, data = _sb(
        repo,
        "start",
        "--task",
        task,
        "--runner",
        "ask",
        "--by",
        by,
        "--budget",
        str(budget),
    )
    if not ok or not isinstance(data, dict):
        return None
    session_id = data.get("session_id") or data.get("id")
    return str(session_id) if session_id else None


def bus_steer(session_id: str, text: str, repo: str, by: str = "founder") -> bool:
    """The founder's comment, steered into the waiting session: the estate's signed receipt
    chain records by=founder and the comment as the attestation."""
    ok, _data = _sb(repo, "steer", session_id, "--by", by, "--text", text)
    return bool(ok)


def bus_show(session_id: str, repo: str) -> Optional[dict]:
    ok, data = _sb(repo, "show", session_id)
    return data if ok and isinstance(data, dict) else None


# --- the door -------------------------------------------------------------------------------------


@dataclass
class Door:
    """The door itself: a request in, one message out, one answer back."""

    state_file: Optional[Path] = None
    repo: str = str(Path.home() / "Documents" / "code" / "idp")
    bus: bool = False
    bus_budget: int = DEFAULT_BUS_BUDGET
    transport: Optional[Callable[[str], Optional[int]]] = None
    token: Optional[str] = None
    chat_id: Optional[str] = None

    def _credentials(self) -> tuple:
        if self.token and self.chat_id:
            return self.token, self.chat_id
        token, chat = telegram_credentials()
        self.token = self.token or token
        self.chat_id = self.chat_id or chat
        return self.token, self.chat_id

    def ask(self, request: DecisionRequest, *, take_webhook: bool = False) -> dict:
        request.validate()
        state = load_state(self.state_file)
        existing = state["decisions"].get(request.decision_id)
        if existing:
            # Idempotent: one message per decision, ever.
            return {**existing, "ok": True, "sent": False, "idempotent": True}

        token, chat = self._credentials()
        sender = self.transport
        if sender is None:
            if not (token and chat):
                return {
                    "ok": False,
                    "error": "no telegram credentials on this host",
                    "decision_id": request.decision_id,
                }
            sender = lambda text: send_message(token, chat, text)  # noqa: E731
        message_id = sender(render(request))
        if message_id is None:
            return {
                "ok": False,
                "error": "the decision message was not delivered",
                "decision_id": request.decision_id,
            }

        created = _now()
        record = {
            **request.to_dict(),
            "schema": SCHEMA,
            "state": STATE_ASKED,
            "created_at": _iso(created),
            "deadline_at": _iso(created + timedelta(minutes=request.deadline_min)),
            "message_id": message_id,
            "chat_id": chat or "",
            "option": None,
            "answer": None,
            "answer_kind": None,
            "answered_at": None,
            "session_id": None,
            "bus": "skipped",
            "webhook_held": False,
            "webhook_url": "",
        }
        if self.bus:
            session_id = bus_start_ask(
                render(request),
                request.requester or "estate",
                self.repo,
                self.bus_budget,
            )
            if session_id:
                record["session_id"] = session_id
                record["bus"] = "open"
        state["decisions"][request.decision_id] = record
        save_state(state, self.state_file)

        if take_webhook and token:
            record["webhook_url"] = self.hold_webhook(token)
            record["webhook_held"] = bool(record["webhook_url"])
            save_state(state, self.state_file)
        return {**record, "ok": True, "sent": True}

    def hold_webhook(self, token: str) -> str:
        """Take the bot's updates so the founder's reply can come back to THIS host.

        Only when the estate's own reader cannot answer: the door checks that the registered
        webhook URL is unreachable before it takes over, and it keeps the URL so it can put it
        back. If the estate's gateway re-registers the webhook, `getUpdates` answers 409 and
        the door yields -- there is never more than one reader.
        """
        info: dict = {}
        for attempt in range(3):
            info = webhook_info(token)
            if info:
                break
            time.sleep(1.0 + attempt)
        url = str(info.get("url") or "")
        if not url:
            # No webhook, or the Bot API would not say: either way the door does NOT take
            # over on a guess. Failing closed here costs a reply, never a stolen bot.
            return ""
        if _url_reachable(url):
            # The estate's reader is alive: it owns the founder's replies. Do not fight it.
            return ""
        if delete_webhook(token):
            return url
        return ""

    def restore_webhook(self, token: str, url: str) -> bool:
        if not url:
            return False
        return set_webhook(token, url)

    def reply(self, text: str) -> Optional[int]:
        """One message to the founder's chat, outside the decision flow.

        The door's job is decisions; this is the narrow exception an operator needs when the
        estate's own reader is down and the founder is talking into a channel nobody is
        listening to. It is NOT reachable from the intent, so no agent can turn the door into
        a chatty surface.
        """
        token, chat = self._credentials()
        if not (token and chat):
            return None
        return send_message(token, chat, text)

    def answer(self, decision_id: str, comment: str) -> Optional[dict]:
        """Record the founder's comment as the answer. Idempotent: the first answer wins.

        A LATE answer is still an answer: the founder's explicit words are never dropped
        because the clock ran out. The record says `late: true`, so the reader can see that
        the deadline was blown. Silence is what expires; an explicit answer never does.
        """
        state = load_state(self.state_file)
        record = state["decisions"].get(decision_id)
        if record is None:
            return None
        if record.get("state") not in (STATE_ASKED, STATE_EXPIRED):
            return record
        request = DecisionRequest.from_dict(record)
        answer = match_comment(comment, request)
        if answer.kind == "unrelated":
            return record
        moment = _now()
        if record.get("state") == STATE_EXPIRED:
            record["late"] = True
        record["state"] = STATE_ANSWERED
        record["option"] = answer.option
        record["answer"] = answer.text
        record["answer_kind"] = answer.kind
        record["answered_at"] = _iso(moment)
        state["decisions"][decision_id] = record
        save_state(state, self.state_file)
        if record.get("session_id") and self.bus:
            if bus_steer(record["session_id"], answer.text, self.repo):
                record["bus"] = "answered"
                save_state(state, self.state_file)
        return record

    def absorb(self, comment: str) -> Optional[dict]:
        """Attribute a founder comment to a decision and record it.

        A comment that quotes a decision id belongs to that decision. A comment that quotes
        no id is only attributed when it is EXACTLY an option key (or approve/deny) and
        exactly one decision is live -- an ordinary chat message is never captured.
        """
        text = (comment or "").strip()
        if not text:
            return None
        state = load_state(self.state_file)
        for decision_id, record in state["decisions"].items():
            if record.get("state") != STATE_ASKED:
                continue
            if decision_id in text:
                return self.answer(decision_id, text)
        # A late answer: the founder answered after the deadline. His words are an answer,
        # not silence, and the record says so.
        for decision_id, record in state["decisions"].items():
            if record.get("state") != STATE_EXPIRED:
                continue
            if decision_id in text:
                return self.answer(decision_id, text)
        live = [r for r in state["decisions"].values() if r.get("state") == STATE_ASKED]
        if len(live) == 1:
            record = live[0]
            request = DecisionRequest.from_dict(record)
            answer = match_comment(text, request)
            if answer.kind == "option":
                return self.answer(request.decision_id, text)
        return None

    def poll(self, *, take_webhook: bool = False) -> dict:
        """Read the bot's pending updates and record any answer they carry."""
        token, chat = self._credentials()
        if not token:
            return {"ok": False, "error": "no telegram credentials on this host"}
        updates = get_updates(token)
        answered = []
        for update in updates:
            text = update_text(update)
            if not text:
                continue
            if chat and update_chat_id(update) not in (None, chat):
                continue
            record = self.absorb(text)
            if record and record.get("state") == STATE_ANSWERED:
                answered.append(record.get("decision_id"))
        # Expire first, then hand the estate its webhook back: a decision that closed by
        # EXPIRY is closed, and the estate's own reader must get the founder's replies back.
        expire_due(self.state_file)
        state = load_state(self.state_file)
        held = [
            rec
            for rec in state["decisions"].values()
            if rec.get("webhook_held") and rec.get("state") != STATE_ASKED
        ]
        restored = []
        for rec in held:
            if self.restore_webhook(token, str(rec.get("webhook_url") or "")):
                restored.append(rec.get("decision_id"))
                rec["webhook_held"] = False
        if held:
            save_state(state, self.state_file)
        return {
            "ok": True,
            "updates": len(updates),
            "answered": answered,
            "restored": restored,
        }

    def show(self, decision_id: str) -> Optional[dict]:
        expire_due(self.state_file)
        return get_decision(decision_id, self.state_file)


def _url_reachable(url: str, timeout_s: float = 3.0) -> bool:
    """Is the estate's own reader of the founder's replies alive? A HEAD/GET is enough."""
    request = urllib.request.Request(url, method="GET")  # noqa: S310 - fixed estate ingress
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:  # noqa: S310
            return 200 <= int(response.status) < 500
    except urllib.error.HTTPError:
        # The gateway answers 4xx/5xx for a bot path it does not like; it is still ALIVE.
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def wait_for_answer(
    door: Door, decision_id: str, seconds: float, poll_every: float = 4.0
) -> dict:
    """Bounded wait for the founder.

    The wait ENDING is not the decision EXPIRING: a decision stays `asked` until its own
    deadline passes. Silence inside the window is not a yes, and it is not an expiry either
    -- it is a decision that is still open, and the next `show` says so.
    """
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        door.poll()
        record = door.show(decision_id)
        if record and record.get("state") == STATE_ANSWERED:
            return record
        time.sleep(min(poll_every, max(0.5, deadline - time.monotonic())))
    expire_due(door.state_file)
    return door.show(decision_id) or {}
