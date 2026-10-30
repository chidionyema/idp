"""Voice to intent: an utterance that names a committed estate intent runs it through
estate-execute. Deterministic (no LLM). None = not an intent; the brain answers.

ARGUMENTS (2026-10-22, EPIC-IDP-090 S1). Until this file knew about arguments, `execute()` called
`[exe, intent]` and never anything else -- so an intent that declares `args` had those declarations
read by nobody and passed by nothing, and the spoken path could only ever reach the 64 intents whose
every argument has a default. Now the arguments are a schema: `intent_args()` reads them out of the
intent YAML, `input_schema()` renders them as an MCP-shaped JSON Schema for the Face and for any
speech brain that wants to fill them, and `execute()` turns supplied values into `--k=v` argv. The
allow-list did not move: only an argument the intent itself declares can be passed, values must be
scalars, the name must be a committed intent, and the READ_ONLY/confirmation rule is unchanged.
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
        "friction-report",
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
    # An utterance whose confirmation window closed: said out loud, never silence (2026-10-23).
    "expired": ("comet_spawn", "warn"),
}
_PENDING: dict[str, tuple[str, float, dict[str, str] | None]] = {}
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


def load_all(directory: str | Path | None = None) -> list[str]:
    """Every committed intent, including the ones the spoken path cannot reach by name alone.

    `load_catalog()` is what an utterance may name: arg-free, so speech never has to fill a value.
    This is what a caller that *brings* the values may name. It is still only ever a name that
    exists in the committed directory -- nothing here reads words out of an utterance.
    """
    directory = Path(directory) if directory is not None else default_dir()
    if not directory.is_dir():
        return []
    names = []
    for path in sorted(directory.glob("*.yaml")):
        doc = intent_doc(path.stem, directory)
        name = doc.get("name") or path.stem
        if isinstance(name, str) and name:
            names.append(name)
    return sorted(set(names))


def intent_path(name: str, directory: str | Path | None = None) -> Path | None:
    """The committed YAML for one intent name, or None. One resolver, so `description`,
    `intent_args` and `known` can never disagree about what this catalogue contains."""
    directory = Path(directory) if directory is not None else default_dir()
    for stem in (name, name.replace(".", "-")):
        path = directory / f"{stem}.yaml"
        if path.is_file():
            return path
    return None


def intent_doc(name: str, directory: str | Path | None = None) -> dict:
    path = intent_path(name, directory)
    if path is None:
        return {}
    try:
        doc = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError):
        return {}
    return doc if isinstance(doc, dict) else {}


def known(name: str, directory: str | Path | None = None) -> bool:
    """Is this a committed intent? A name from speech or from a deck is only ever run when it is."""
    return intent_path(name, directory) is not None


def intent_args(name: str, directory: str | Path | None = None) -> dict[str, dict]:
    """The arguments this intent declares, exactly as its YAML declares them.

    `{arg: {type, description, default, ...}}`. This is the only source of truth for what may be
    passed: `execute()` refuses anything not in here, so an argument cannot be smuggled in by an
    utterance, a deck click or a caller of the API.
    """
    args = intent_doc(name, directory).get("args") or {}
    if not isinstance(args, dict):
        return {}
    return {k: v for k, v in args.items() if isinstance(k, str) and isinstance(v, dict)}


def input_schema(name: str, directory: str | Path | None = None) -> dict:
    """The intent's arguments as an MCP-shaped JSON Schema (type object, properties, required).

    Same shape a model already knows how to fill, so "run ci-status for repo idp" can be turned
    into `{repo: idp}` by whatever is listening, and the Face's deck can render a field per
    property without a second description of the same intent living in TypeScript.
    """
    props: dict[str, dict] = {}
    required: list[str] = []
    for arg, spec in intent_args(name, directory).items():
        typ = spec.get("type") or "string"
        prop: dict = {"type": typ if isinstance(typ, str) else "string"}
        desc = spec.get("description")
        if desc:
            prop["description"] = " ".join(str(desc).split())[:200]
        if "default" in spec:
            prop["default"] = spec["default"]
        else:
            required.append(arg)
        props[arg] = prop
    return {"type": "object", "properties": props, "required": required}


def description(name: str, directory: str | Path | None = None) -> str:
    """The intent's own `description`, one line, for the voice operator to speak."""
    desc = intent_doc(name, directory).get("description")
    return " ".join(str(desc).split())[:200] if desc else ""


def catalogue(directory: str | Path | None = None) -> list[dict]:
    """What the estate can do by voice, for the Face's command deck: every arg-free intent with its
    own one-line description, whether it runs on the first utterance (read-only) or waits for a
    spoken yes, and the arguments it takes. The same load_catalog() the matcher uses, so the deck
    can never offer a command the voice would not run by name alone.

    `args` and `inputSchema` are what make the deck more than a list of buttons: an intent that
    takes `repo` or `pr` says so here, in the intent's own words, instead of every caller carrying
    a hardcoded idea of the shape. Intents whose arguments have no defaults are deliberately still
    absent from this list -- they are reachable when a caller supplies the arguments, not by an
    utterance that names them and nothing else.
    """
    return [
        {
            "name": name,
            "description": description(name, directory),
            "read_only": name in READ_ONLY,
            "args": intent_args(name, directory),
            "inputSchema": input_schema(name, directory),
        }
        for name in load_catalog(directory)
    ]


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


def _forward(
    url: str, text: str, session_id: str, args: dict | None = None
) -> dict | None:
    payload: dict[str, object] = {"text": text, "session_id": session_id}
    # The arguments ride along (2026-10-23). Before this, the pod forwarded the intent's NAME and
    # dropped everything the caller said about it: a deck click on `pr-list` with
    # {"limit": 2, "state": "merged"} reached the laptop as the word "pr-list", was confirmed as
    # "Run pr-list? Say yes to confirm." -- no repo, no limit -- and ran with the intent's defaults.
    # Measured in production: the read-back never named an argument and state=merged still listed
    # open PRs. An argument the founder cannot hear is one they cannot be said to have approved.
    if args:
        payload["args"] = args
    req = urllib.request.Request(  # noqa: S310 -- fixed, operator-supplied URL only
        url,
        data=json.dumps(payload).encode(),
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
    url: str,
    text: str,
    session_id: str,
    name: str,
    now: float,
    args: dict | None = None,
) -> dict | None:
    t0 = time.monotonic()
    try:
        ran = _forward(url, text, session_id, args)
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


def arg_value(value: object) -> str | None:
    """One argument, as the single argv word it will be, or None when it is not a scalar.

    `--k=v` is one argv element handed to subprocess without a shell, so a value cannot become a
    second command; the scalar rule is the second half of that: a dict or a list has no meaning to
    an intent and is refused rather than stringified into something surprising.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    return None


VOICE_SESSION_PREFIX = "voice:"


def estate_session_id(session_id: str) -> str:
    """The estate session a spoken turn belongs to, namespaced.

    A voice session is not a plan session. It has no ledger, and it must never look like one:
    the door refuses a session that has a ledger and has declared no plan, so a voice id that
    collided with an agent's plan-session name would refuse a founder's spoken command. The
    namespace keeps the two apart (idp#7579 R1). Empty in, empty out: a caller with no session
    stays identity-less automation, which the door allows and records.
    """
    sid = (session_id or "").strip()
    if not sid:
        return ""
    if sid.startswith(VOICE_SESSION_PREFIX):
        return sid
    return VOICE_SESSION_PREFIX + sid


def build_argv(
    exe: str,
    intent: str,
    args: dict | None,
    directory: str | Path | None = None,
    session: str = "",
) -> list[str]:
    """argv for one intent: `[exe, intent, --k=v ...]`, only for arguments the intent declares.

    The session, when the caller stated one, rides as `--session <id>`: the door treats an
    explicit session as authoritative, so the run is attributable even if the child's environment
    is scrubbed.

    Raises ValueError for an undeclared argument or a non-scalar value. The caller reports that as
    an intent error, so a bad argument is a spoken refusal, never a partially-run command.
    """
    declared = intent_args(intent, directory)
    argv = [exe, intent]
    if session:
        argv.extend(["--session", session])
    for key in sorted(args or {}):
        if key not in declared:
            raise ValueError(f"{_spoken(intent)} takes no {key}")
        value = arg_value(args[key])
        if value is None:
            raise ValueError(f"{key} has to be a single value")
        argv.append(f"--{key}={value}")
    return argv


def execute(
    intent: str,
    args: dict | None = None,
    directory: str | Path | None = None,
    session_id: str = "",
) -> tuple[str, str, int | None, int]:
    exe = executor()
    if exe is None:
        return ("error", "Intents run on the laptop only.", None, 0)
    session = estate_session_id(session_id)
    try:
        # argv list, no shell; intent is a name from the committed catalog, never words from
        # speech, and each argument is one argv word only if the intent declares it.
        argv = build_argv(exe, intent, args, directory, session)
    except ValueError as exc:
        return ("error", str(exc)[:160], 2, 0)
    env = None
    if session:
        # The session travels twice: as the explicit `--session` flag (authoritative at the door)
        # and in the environment (so a child that re-execs keeps the identity). The door prefers
        # the explicit flag, so the two cannot disagree.
        env = dict(os.environ)
        env["ESTATE_SESSION_ID"] = session
    t0 = time.monotonic()
    try:
        proc = subprocess.run(  # noqa: S603
            argv,
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT_S,
            check=False,
            stdin=subprocess.DEVNULL,
            env=env,
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


def _audit(session_id, utterance, intent, status, rc, duration_ms, args=None) -> None:
    """One line per turn. Argument NAMES are recorded, never their values: what was asked for is
    evidence, and a value can be a token."""
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
                "arg_names": sorted(args or {}),
            }
        )
        with path.open("a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def handle(text: str, session_id: str, args: dict | None = None) -> dict | None:
    """One utterance (or one deck command) to an intent result.

    `args` is how a caller that is not speaking fills an intent's declared arguments -- the Face's
    deck, or a controller. It never widens what may run: the name must still be a committed intent,
    the intent must still declare each argument, and a non-read-only intent still waits for a
    spoken yes, which is now read back with its arguments so the founder hears what they are
    confirming.
    """
    norm = normalise(text)
    now = time.monotonic()
    with _LOCK:
        pend = _PENDING.pop(session_id, None)
        pend_task = _PENDING_TASK.pop(session_id, "")
    if pend and now - pend[1] > PENDING_TTL_S:
        # A yes that arrives after the window is the founder answering something the estate has
        # already forgotten. Falling through answered it with silence: measured 2026-10-23T07:47Z
        # on the public path, an intent+args confirmation went unanswered for two minutes, then
        # "yes" returned HTTP 204 and an empty body -- which reads as a broken microphone, not as
        # an expiry. PENDING_TTL_S is 60 s, so this is easy to hit while speaking.
        if norm in YES or norm in NO:
            name = pend[0]
            pend_args = pend[2] if len(pend) > 2 else None
            _audit(session_id, text, name, "expired", None, 0, pend_args)
            return result(
                name,
                "expired",
                f"That confirmation expired before I heard you. Say {_spoken(name)} again and "
                "I will ask once more.",
            )
        pend = None
    if pend and now - pend[1] <= PENDING_TTL_S:
        name = pend[0]
        pend_args = pend[2] if len(pend) > 2 else None
        if name == AGENT_JOB and norm in YES:
            return _send_agent_job(session_id, text, pend_task)
        if name == CONCIERGE and norm in YES:
            return _send_concierge(session_id, text, pend_task)
        if norm in YES:
            status, msg, rc, dur = execute(name, pend_args, session_id=session_id)
            _audit(session_id, text, name, status, rc, dur, pend_args)
            return result(name, status, msg)
        if norm in NO:
            _audit(session_id, text, name, "cancelled", None, 0, pend_args)
            return result(name, "cancelled", f"Cancelled {_spoken(name)}.")

    url = laptop_url() if executor() is None else ""
    with _LOCK:
        remote_since = _REMOTE_PENDING.pop(session_id, None)
    if url and remote_since is not None and now - remote_since <= PENDING_TTL_S:
        if norm in YES or norm in NO:
            return _on_laptop(url, text, session_id, "intent", now)
    if url and remote_since is not None and (norm in YES or norm in NO):
        # The laptop held the confirmation and has since dropped it; the pod still remembers asking.
        return result(
            "intent",
            "expired",
            "That confirmation expired before I heard you. Say the command again and I will ask "
            "once more.",
        )

    task = agent_job_task(text)
    if task is not None:
        return _agent_job(session_id, text, task, now)
    task = concierge_task(text)
    if task is not None:
        return _concierge(session_id, text, task, now)

    catalog = load_catalog()
    name = match(text, catalog)
    if name is None and args:
        # a caller that brings the values may name an intent the spoken path cannot reach, because
        # speech alone cannot supply a required argument. Still a committed name, never free words.
        name = match(text, load_all())
    if name is None:
        return None
    if args:
        declared = intent_args(name)
        bad = sorted(k for k in args if k not in declared)
        if bad:
            _audit(session_id, text, name, "error", 2, 0, args)
            return result(name, "error", f"{_spoken(name)} takes no {bad[0]}.")
    if url:
        return _on_laptop(url, text, session_id, name, now, args)

    if name not in READ_ONLY:
        with _LOCK:
            _PENDING[session_id] = (name, now, args or None)
        _audit(session_id, text, name, "pending_confirmation", None, 0, args)
        with_what = ""
        if args:
            with_what = " with " + ", ".join(f"{k} {args[k]}" for k in sorted(args))
        return result(
            name, "pending_confirmation", f"Run {name}{with_what}? Say yes to confirm."
        )

    status, msg, rc, dur = execute(name, args, session_id=session_id)
    _audit(session_id, text, name, status, rc, dur, args)
    return result(name, status, msg)
