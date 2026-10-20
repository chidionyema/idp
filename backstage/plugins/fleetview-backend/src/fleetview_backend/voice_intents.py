"""Voice to intent: an utterance that names a committed, arg-free estate intent
runs it through estate-execute. Deterministic (no LLM). None = not an intent;
the brain answers.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

READ_ONLY = frozenset(
    {
        "ci-status",
        "ci.errors",
        "cost-today",
        "git-log",
        "lane",
        "router-status",
        "voice-turns",
        "ledger-verify",
    }
)
YES = frozenset({"yes", "confirm", "do it"})
NO = frozenset({"no", "cancel"})
PENDING_TTL_S = 60.0
EXEC_TIMEOUT_S = 120
_CUES = {
    "ok": ("pulse", "info"),
    "error": ("burn", "danger"),
    "pending_confirmation": ("shield_flash", "warn"),
    "cancelled": ("comet_spawn", "info"),
}
_PENDING: dict[str, tuple[str, float]] = {}
_PENDING_TASK: dict[str, str] = {}
_LOCK = threading.Lock()

# "Give an agent a job: <task>" -> agent_jobs.submit, after a spoken read-back and a yes. The task
# is what was said after the phrase, punctuation kept; a job costs a model run and opens a PR, so
# it is never sent on the first utterance.
AGENT_JOB = "agent-job"
_AGENT_JOB_PHRASE = re.compile(
    r"^\s*(?:(?:hey|ok(?:ay)?)[\s,.!]+)?(?:please[\s,]+)?"
    r"(?:give\s+(?:an?\s+)?agent\s+(?:a\s+)?job|agent\s+job|ask\s+an?\s+agent\s+to|have\s+an?\s+agent)"
    r"\b[\s:,.\-]*(?P<task>.*)$",
    re.I | re.S,
)


# "Concierge, <task>" / "ask the concierge to <task>" -> concierge_tasks.start, after a spoken
# read-back and a yes. It opens the founder's Chrome and spends router calls, so never on the first
# utterance. A purchase stops at the pay step and says so; nothing here can pay.
CONCIERGE = "concierge-task"
_CONCIERGE_PHRASE = re.compile(
    r"^\s*(?:(?:hey|ok(?:ay)?)[\s,.!]+)?(?:please[\s,]+)?"
    r"(?:(?:ask|tell|get)\s+(?:the\s+)?concierge\s+to|have\s+(?:the\s+)?concierge|concierge)"
    r"\b[\s:,.\-]*(?P<task>.*)$",
    re.I | re.S,
)


# "How's the Greenlane?" / "what's landing" -> greenlane_live.live()'s one spoken line. Read-only,
# so it answers on the first utterance; unreadable is said as unreadable, never as quiet.
GREENLANE_LIVE = "greenlane-live"
_GREENLANE_PHRASE = re.compile(
    r"\b(?:green\s*lane|what(?:'s|\s+is)\s+landing|merge\s+queue)\b",
    re.I,
)


def _greenlane_live(session_id: str, text: str) -> dict:
    from fleetview_backend import greenlane_live

    view = greenlane_live.live()
    if not view.get("available"):
        _audit(session_id, text, GREENLANE_LIVE, "error", None, 0)
        return result(
            GREENLANE_LIVE,
            "error",
            f"I can't read the Greenlane: {view.get('error', 'unknown')}.",
        )
    _audit(session_id, text, GREENLANE_LIVE, "ok", None, 0)
    return result(GREENLANE_LIVE, "ok", view["sentence"])


def concierge_task(text: str) -> str | None:
    """The task in a concierge utterance ("" when the word came alone), None when it is not one."""
    m = _CONCIERGE_PHRASE.match(text or "")
    if not m:
        return None
    return m.group("task").strip().rstrip(".").strip()


def _concierge(session_id: str, text: str, task: str, now: float) -> dict:
    from fleetview_backend import concierge_tasks

    if not task:
        _audit(session_id, text, CONCIERGE, "error", None, 0)
        return result(
            CONCIERGE, "error", "Say the task too: concierge, then what to do."
        )
    try:
        task = concierge_tasks.validate(task)
    except concierge_tasks.TaskRefused as exc:
        _audit(session_id, text, CONCIERGE, "error", None, 0)
        return result(CONCIERGE, "error", str(exc)[:160])
    with _LOCK:
        _PENDING[session_id] = (CONCIERGE, now)
        _PENDING_TASK[session_id] = task
    _audit(session_id, text, CONCIERGE, "pending_confirmation", None, 0)
    return result(
        CONCIERGE,
        "pending_confirmation",
        f"Ask the concierge to: {task}? Say yes to confirm.",
    )


def _send_concierge(session_id: str, text: str, task: str) -> dict:
    from fleetview_backend import concierge_tasks

    t0 = time.monotonic()
    try:
        started = concierge_tasks.start(task, by=f"voice:{session_id}")
    except concierge_tasks.TaskRefused as exc:
        _audit(
            session_id,
            text,
            CONCIERGE,
            "error",
            exc.status,
            int((time.monotonic() - t0) * 1000),
        )
        return result(CONCIERGE, "error", str(exc)[:160])
    _audit(session_id, text, CONCIERGE, "ok", 0, int((time.monotonic() - t0) * 1000))
    return result(
        CONCIERGE,
        "ok",
        f"The concierge is on it, task {started['task_id']}. Watch it on Fleet; it stops before paying.",
    )


def agent_job_task(text: str) -> str | None:
    """The task in an agent-job utterance ("" when the phrase came alone), None when it is not one."""
    m = _AGENT_JOB_PHRASE.match(text or "")
    if not m:
        return None
    return m.group("task").strip().rstrip(".").strip()


def _agent_job(session_id: str, text: str, task: str, now: float) -> dict:
    from fleetview_backend import agent_jobs

    if not task:
        _audit(session_id, text, AGENT_JOB, "error", None, 0)
        return result(
            AGENT_JOB, "error", "Say the job too: give an agent a job, then what to do."
        )
    try:
        task, _h = agent_jobs.validate(task, "pi")
    except agent_jobs.JobRefused as exc:
        _audit(
            session_id,
            "[agent job refused before read-back]",
            AGENT_JOB,
            "error",
            None,
            0,
        )
        return result(AGENT_JOB, "error", str(exc)[:160])
    with _LOCK:
        _PENDING[session_id] = (AGENT_JOB, now)
        _PENDING_TASK[session_id] = task
    _audit(session_id, text, AGENT_JOB, "pending_confirmation", None, 0)
    return result(
        AGENT_JOB,
        "pending_confirmation",
        f"Send an agent to: {task}? Say yes to confirm.",
    )


def _send_agent_job(session_id: str, text: str, task: str) -> dict:
    from fleetview_backend import agent_jobs

    t0 = time.monotonic()
    try:
        job, _status = agent_jobs.submit(task, "pi", by=f"voice:{session_id}")
    except agent_jobs.JobRefused as exc:
        _audit(
            session_id,
            text,
            AGENT_JOB,
            "error",
            exc.status,
            int((time.monotonic() - t0) * 1000),
        )
        return result(AGENT_JOB, "error", str(exc)[:160])
    dur = int((time.monotonic() - t0) * 1000)
    _audit(session_id, text, AGENT_JOB, "ok", 0, dur)
    if job.get("duplicate"):
        return result(
            AGENT_JOB, "ok", f"That job is already running as run {job['run_id']}."
        )
    if job.get("run_id"):
        return result(AGENT_JOB, "ok", f"Sent. Run {job['run_id']}. Watch it on Fleet.")
    return result(
        AGENT_JOB,
        "ok",
        "Sent. GitHub has not listed the run yet; it will show on Fleet.",
    )


def default_dir() -> Path:
    env = os.environ.get("FLEETVIEW_INTENTS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[5] / "platform" / "estate" / "intents"


def normalise(text: str) -> str:
    if text is None:
        text = ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def name_tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[-._]", name.lower()) if t]


def load_catalog(directory: str | Path | None = None) -> list[str]:
    if directory is None:
        directory = default_dir()
    directory = Path(directory)
    if not directory.is_dir():
        return []
    names = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text())
        except (OSError, yaml.YAMLError):
            continue  # an unreadable or malformed intent is simply not in the voice catalog
        if not isinstance(doc, dict):
            continue
        name = doc.get("name") or path.stem
        if not isinstance(name, str) or not name:
            continue
        args = doc.get("args") or {}
        if not isinstance(args, dict):
            continue
        if not all(isinstance(v, dict) and "default" in v for v in args.values()):
            continue
        names.append(name)
    return sorted(names)


def description(name: str, directory: str | Path | None = None) -> str:
    """The intent's own `description`, one line, for the voice operator to speak."""
    directory = Path(directory) if directory is not None else default_dir()
    for stem in (name, name.replace(".", "-")):
        path = directory / f"{stem}.yaml"
        if path.is_file():
            try:
                doc = yaml.safe_load(path.read_text())
            except (OSError, yaml.YAMLError):
                return ""
            desc = doc.get("description") if isinstance(doc, dict) else None
            return " ".join(str(desc).split())[:200] if desc else ""
    return ""


def match(text: str, catalog: list[str]) -> str | None:
    words = set(normalise(text).split())
    best = None
    best_key = None
    for name in catalog:
        tokens = name_tokens(name)
        if not tokens:
            continue
        if set(tokens) <= words:
            key = (len(tokens), len(name))
            if best_key is None or key > best_key:
                best_key = key
                best = name
    return best


def result(intent: str, status: str, text: str) -> dict:
    cue, severity = _CUES[status]
    return {
        "kind": "intent_result",
        "intent": intent,
        "status": status,
        "text": text,
        "visual": {"cue": cue, "target": "fleet", "severity": severity},
        "ticket": None,
    }


def _spoken(name: str) -> str:
    out = name
    for ch in "-._":
        out = out.replace(ch, " ")
    return out


def _last_line(s: str) -> str:
    for line in reversed(s.splitlines()):
        line = line.strip()
        if line:
            return line[:160]
    return ""


def _spoken_result(s: str) -> str:
    # An intent that answers in JSON (ci-status) ends on "}", which is not an answer: say its
    # "summary" sentence instead (2026-10-13).
    try:
        body = json.loads(s)
    except ValueError:
        return _last_line(s)
    if isinstance(body, dict) and isinstance(body.get("summary"), str):
        return body["summary"][:160]
    return _last_line(s)


def executor() -> str | None:
    exe = os.path.expanduser(
        os.environ.get("ESTATE_EXECUTE") or "~/.estate/bin/estate-execute"
    )
    return exe if os.path.isfile(exe) and os.access(exe, os.X_OK) else None


# THE POD HANDS AN INTENT TO THE LAPTOP (2026-10-13). The pod has no estate-execute and, until this
# image shipped the catalog, no intents to match either, so "check ci status" on the live site was
# answered by the model as a question. FLEETVIEW_INTENTS_URL is the laptop's own /voice/intent over
# fleetview-mac-egress.yaml: the pod matches locally (no turn waits on the Mac to learn it named
# nothing) and forwards only a match, or the yes/no to a confirmation the laptop is holding.
_REMOTE_PENDING: dict[str, float] = {}


def laptop_url() -> str:
    return os.environ.get("FLEETVIEW_INTENTS_URL", "").strip()


def _forward(url: str, text: str, session_id: str) -> dict | None:
    req = urllib.request.Request(  # noqa: S310 -- fixed, operator-supplied URL only
        url,
        data=json.dumps({"text": text, "session_id": session_id}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=EXEC_TIMEOUT_S + 15) as resp:  # noqa: S310
        if resp.status == 204:
            return None
        body = json.loads(resp.read())
    if not (
        isinstance(body, dict)
        and body.get("status") in _CUES
        and isinstance(body.get("text"), str)
    ):
        raise ValueError(
            "the laptop answered with something that is not an intent result"
        )
    return body


def _on_laptop(
    url: str, text: str, session_id: str, name: str, now: float
) -> dict | None:
    t0 = time.monotonic()
    try:
        ran = _forward(url, text, session_id)
    except (OSError, ValueError):
        _audit(
            session_id, text, name, "error", None, int((time.monotonic() - t0) * 1000)
        )
        return result(
            name, "error", "The laptop is not answering, so that cannot run now."
        )
    if ran is not None and ran["status"] == "pending_confirmation":
        with _LOCK:
            _REMOTE_PENDING[session_id] = now
    return ran


def execute(intent: str) -> tuple[str, str, int | None, int]:
    exe = executor()
    if exe is None:
        return ("error", "Intents run on the laptop only.", None, 0)
    t0 = time.monotonic()
    try:
        # argv list, no shell; intent is a name from the committed catalog, never words from speech.
        proc = subprocess.run(  # noqa: S603
            [exe, intent],
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT_S,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        dur = int((time.monotonic() - t0) * 1000)
        return ("error", f"{_spoken(intent)} timed out.", None, dur)
    except OSError:
        dur = int((time.monotonic() - t0) * 1000)
        return ("error", f"{_spoken(intent)} could not start.", None, dur)
    dur = int((time.monotonic() - t0) * 1000)
    if proc.returncode == 0:
        return ("ok", _spoken_result(proc.stdout) or f"{_spoken(intent)} done.", 0, dur)
    last = _last_line(proc.stderr) or _last_line(proc.stdout)
    text = (
        f"{_spoken(intent)} failed. {last}" if last else f"{_spoken(intent)} failed."
    )[:160]
    return ("error", text, proc.returncode, dur)


def _audit(session_id, utterance, intent, status, rc, duration_ms) -> None:
    path = Path(
        os.path.expanduser(
            os.environ.get("FLEETVIEW_INTENT_LOG") or "~/.estate/voice-intents.jsonl"
        )
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "utterance": utterance,
                "intent": intent,
                "status": status,
                "rc": rc,
                "duration_ms": duration_ms,
            }
        )
        with path.open("a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def handle(text: str, session_id: str) -> dict | None:
    norm = normalise(text)
    now = time.monotonic()
    with _LOCK:
        pend = _PENDING.pop(session_id, None)
        pend_task = _PENDING_TASK.pop(session_id, "")
    if pend and now - pend[1] <= PENDING_TTL_S:
        name = pend[0]
        if name == AGENT_JOB and norm in YES:
            return _send_agent_job(session_id, text, pend_task)
        if name == CONCIERGE and norm in YES:
            return _send_concierge(session_id, text, pend_task)
        if norm in YES:
            status, msg, rc, dur = execute(name)
            _audit(session_id, text, name, status, rc, dur)
            return result(name, status, msg)
        if norm in NO:
            _audit(session_id, text, name, "cancelled", None, 0)
            return result(name, "cancelled", f"Cancelled {_spoken(name)}.")

    url = laptop_url() if executor() is None else ""
    with _LOCK:
        remote_since = _REMOTE_PENDING.pop(session_id, None)
    if url and remote_since is not None and now - remote_since <= PENDING_TTL_S:
        if norm in YES or norm in NO:
            return _on_laptop(url, text, session_id, "intent", now)

    task = agent_job_task(text)
    if task is not None:
        return _agent_job(session_id, text, task, now)
    task = concierge_task(text)
    if task is not None:
        return _concierge(session_id, text, task, now)
    if _GREENLANE_PHRASE.search(text or ""):
        return _greenlane_live(session_id, text)

    name = match(text, load_catalog())
    if name is None:
        return None
    if url:
        return _on_laptop(url, text, session_id, name, now)

    if name not in READ_ONLY:
        with _LOCK:
            _PENDING[session_id] = (name, now)
        _audit(session_id, text, name, "pending_confirmation", None, 0)
        return result(name, "pending_confirmation", f"Run {name}? Say yes to confirm.")

    status, msg, rc, dur = execute(name)
    _audit(session_id, text, name, status, rc, dur)
    return result(name, status, msg)
