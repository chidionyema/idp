"""Special forces, bound to the estate's ONE plan contract.

The founder's drop (special-forces-v0) is a bounded state machine: the agent never moves itself
between stages; the machine decides what may be written, whether an artefact is accepted, and
when a unit is parked. It shipped with two protocols of its own, which was a SECOND idea of what
an agent must prove before its work counts -- and the estate already has one contract for that
(platform/estate/memory/plan.py: declare_plan -> add_bdd -> address_edgecases +
address_2nd_order_effects -> complete_goal).

So here the machine is BOUND to that contract rather than standing beside it:

  * a unit may only start for a session that has DECLARED a plan (the ledger is the evidence),
  * every protocol stage names the estate contract stage it carries (``contract_stage``), and a
    stage whose contract stage the ledger has not recorded is REFUSED (retryable, with the exact
    command that would record it),
  * the ``complete_goal`` stage is refused until the ledger says every sub-goal of the declared
    plan is done -- the estate's own rule, applied once and not re-invented.

One contract, one machine. The alerter that shipped with the drop is deliberately NOT installed:
the estate already alerts, and the founder's Telegram token's polling is off limits.

This module is the BINDING layer. The machine itself (sf_machine.py) is the founder's, unchanged.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PROTOCOL_DIR = os.path.join(HERE, "protocols")
MACHINE = os.path.join(HERE, "sf_machine.py")
# The plan contract lives beside this module in a repo checkout (platform/estate/memory/plan.py)
# and one level up in the staged runtime tree (~/.estate/memory/plan.py). Both are searched, so
# the same binding works wherever the founder's runtime actually lives.
_CANDIDATE_ROOTS = [
    HERE,
    os.path.dirname(os.path.dirname(HERE)),
    os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
    os.path.join(os.path.expanduser("~"), ".estate"),
    # The memory installer stages the contract under ~/.estate/memory, keeping the repository's
    # directory shape: ~/.estate/memory/platform/estate/memory/plan.py. Without this root the
    # staged unit cannot see the contract it is bound to.
    os.path.join(os.path.expanduser("~"), ".estate", "memory"),
    os.path.join(os.path.expanduser("~"), ".estate", "runtime", "idp"),
]


def _plan_module_path() -> str:
    for root in _CANDIDATE_ROOTS:
        for rel in (
            os.path.join("platform", "estate", "memory", "plan.py"),
            os.path.join("memory", "plan.py"),
        ):
            path = os.path.join(root, rel)
            if os.path.exists(path):
                return path
    return os.path.join(ROOT, "platform", "estate", "memory", "plan.py")


PLAN_MODULE_PATH = _plan_module_path()

# The estate's contract stages, in the order the contract puts them in.
CONTRACT_STAGES = (
    "declare_plan",
    "add_bdd",
    "address_edgecases",
    "address_2nd_order_effects",
    "complete_goal",
)
# A stage that carries work but records nothing in the contract. Legal, but it is not evidence.
EXTRA_STAGES = ("implement",)
LEGAL_STAGES = frozenset(CONTRACT_STAGES) | frozenset(EXTRA_STAGES)

# The machine's exit codes, kept exactly: 0 ok | 1 retryable | 2 refused | 3 write denied.
EXIT_OK = 0
EXIT_RETRY = 1
EXIT_REFUSED = 2
EXIT_WRITE_DENIED = 3

TERMINAL = ("done", "parked", "failed")

UNIT_ROOT = os.environ.get("ESTATE_UNIT_DIR") or os.path.join(
    os.path.expanduser("~"), ".estate", "units"
)


# --------------------------------------------------------------------------- the plan contract


def _plan_module():
    """The estate's plan contract, loaded from the repo this module lives in.

    None when it cannot load: the binding then refuses, because a unit that cannot see the
    contract cannot honour it, and a unit that starts without one would be the second contract
    this work exists to remove.
    """
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "estate_plan_contract_for_units", PLAN_MODULE_PATH
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 - a broken contract must not take the estate down
        return None


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name or "")).strip("_") or "anonymous"


# --------------------------------------------------------------------------- where a unit lives


def session_dir(session_id: str) -> str:
    return os.path.join(UNIT_ROOT, _safe_name(session_id))


def state_path(session_id: str, unit: str) -> str:
    return os.path.join(session_dir(session_id), f"{_safe_name(unit)}.state.json")


def log_path(session_id: str, unit: str) -> str:
    return os.path.join(session_dir(session_id), f"{_safe_name(unit)}.events.jsonl")


def _active_pointer(session_id: str) -> str:
    return os.path.join(session_dir(session_id), "active.json")


def load_state(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001 - an unreadable state is no state
        return None


def save_state(path: str, state: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, path)


def active_state(session_id: str, unit: str = ""):
    """The unit this session is running: the named one, or the one the pointer names."""
    if unit:
        return load_state(state_path(session_id, unit))
    try:
        with open(_active_pointer(session_id), encoding="utf-8") as fh:
            name = json.load(fh).get("unit", "")
    except Exception:  # noqa: BLE001 - no pointer means no named unit
        return None
    return load_state(state_path(session_id, name)) if name else None


def _set_active(session_id: str, unit: str) -> None:
    d = session_dir(session_id)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "active.json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"unit": unit, "at": time.time()}, fh)
    os.replace(tmp, os.path.join(d, "active.json"))


# --------------------------------------------------------------------------- the protocols


def protocol_path(name: str) -> str:
    if os.sep in name or name.startswith("."):
        return name
    return os.path.join(PROTOCOL_DIR, f"{name}.json")


def load_protocol(name: str) -> dict:
    with open(protocol_path(name), encoding="utf-8") as fh:
        return json.load(fh)


def protocol_stages(proto: dict) -> list:
    return list(proto.get("stages") or [])


def contract_map(proto: dict) -> dict:
    """stage name -> the estate contract stage it carries."""
    return {
        s.get("name", ""): s.get("contract_stage", "") for s in protocol_stages(proto)
    }


def protocol_errors(proto: dict) -> list:
    """Every way this protocol is not bound to the estate contract."""
    errs = []
    stages = protocol_stages(proto)
    if not stages:
        errs.append("protocol has no stages")
    for s in stages:
        cs = s.get("contract_stage")
        if cs not in LEGAL_STAGES:
            errs.append(
                f'stage "{s.get("name")}" names contract_stage {cs!r}, which is not an estate '
                f"contract stage ({', '.join(sorted(LEGAL_STAGES))})"
            )
    return errs


def contract_coverage(proto: dict) -> set:
    return {
        s.get("contract_stage")
        for s in protocol_stages(proto)
        if s.get("contract_stage") in CONTRACT_STAGES
    }


# --------------------------------------------------------------------------- the ledger


def ledger_plan(session_id: str):
    module = _plan_module()
    if module is None:
        return None
    try:
        return module.ledger_plan(session_id)
    except Exception:  # noqa: BLE001 - an unreadable ledger is no plan
        return None


def first_open_goal(plan_state: dict) -> str:
    done = set((plan_state or {}).get("done") or [])
    for s in (plan_state or {}).get("subgoals") or []:
        if s.get("id") not in done:
            return s.get("id", "")
    subgoals = (plan_state or {}).get("subgoals") or []
    return subgoals[0].get("id", "") if subgoals else ""


def ledger_stage_recorded(session_id: str, contract_stage: str, goal_id: str = ""):
    """Has the estate's ledger recorded this contract stage for this session?

    Returns (recorded, detail). The detail is the refusal text when it has not: the exact
    command that would record it, so the refusal is a door, not a wall.
    """
    plan_state = ledger_plan(session_id)
    if not plan_state:
        return False, (
            "no plan is declared for this session; declare one first: "
            'estate-plan declare_plan \'{"goal": "...", "subgoals": [{"id": "g1", '
            '"text": "..."}]}\''
        )
    gid = goal_id or first_open_goal(plan_state)
    if contract_stage == "declare_plan":
        return True, "plan declared"
    if contract_stage == "add_bdd":
        ok = gid in (plan_state.get("bdd") or {})
        tool = "add_bdd"
    elif contract_stage == "address_edgecases":
        ok = gid in (plan_state.get("edgecases") or {})
        tool = "address_edgecases"
    elif contract_stage == "address_2nd_order_effects":
        ok = gid in (plan_state.get("effects") or {})
        tool = "address_2nd_order_effects"
    elif contract_stage == "complete_goal":
        ids = [s.get("id") for s in plan_state.get("subgoals") or []]
        ok = bool(ids) and set(ids) <= set(plan_state.get("done") or [])
        tool = "complete_goal"
    else:
        return True, f"{contract_stage} records nothing in the contract"
    if ok:
        return True, f"{tool} recorded for {gid}"
    return False, (
        f"the plan ledger has not recorded {tool} for {gid}; the estate's contract comes first: "
        f"estate-plan {tool} '<json>'"
    )


# --------------------------------------------------------------------------- the machine


def _machine(args: list, state: str, log: str):
    cmd = [sys.executable, MACHINE] + list(args)
    if "--state" not in args:
        cmd += ["--state", state]
    if "--log" not in args:
        cmd += ["--log", log]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return EXIT_REFUSED, "the machine did not answer within 120s"
    except Exception as exc:  # noqa: BLE001 - a broken machine is a refusal, not a crash
        return EXIT_REFUSED, f"the machine could not run: {type(exc).__name__}"
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def _payload(raw: str) -> dict:
    for line in reversed((raw or "").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return {}


def cur_stage(state: dict) -> dict:
    stages = (state.get("protocol") or {}).get("stages") or []
    idx = int(state.get("idx") or 0)
    return stages[idx] if idx < len(stages) else {}


def allowed_writes(state: dict) -> list:
    stage = cur_stage(state)
    claim = state.get("claim", "")
    return [g.replace("{claim}", claim) for g in stage.get("writes", [])]


# --------------------------------------------------------------------------- the operations


def start(
    session_id: str,
    claim: str,
    unit: str,
    protocol: str,
    prove_cmd: str = "",
    goal_id: str = "",
):
    """Start a bounded unit for a session that has declared a plan."""
    plan_state = ledger_plan(session_id)
    if not plan_state:
        return {
            "ok": False,
            "exit": EXIT_REFUSED,
            "error": (
                "no plan is declared for this session, so there is nothing for this unit to bound. "
                "Declare one first: estate-plan declare_plan '<json>'"
            ),
        }
    try:
        proto = load_protocol(protocol)
    except Exception as exc:  # noqa: BLE001 - a missing protocol is a refusal, not a crash
        return {
            "ok": False,
            "exit": EXIT_REFUSED,
            "error": f"cannot read protocol {protocol}: {type(exc).__name__}",
        }
    errs = protocol_errors(proto)
    if errs:
        return {
            "ok": False,
            "exit": EXIT_REFUSED,
            "error": "protocol is not bound to the estate contract: " + "; ".join(errs),
        }
    d = session_dir(session_id)
    os.makedirs(d, exist_ok=True)
    st_path = state_path(session_id, unit)
    lg = log_path(session_id, unit)
    args = [
        "start",
        "--protocol",
        protocol_path(protocol),
        "--claim",
        claim,
        "--unit",
        unit,
        "--state",
        st_path,
        "--log",
        lg,
    ]
    if prove_cmd:
        args += ["--prove-cmd", prove_cmd]
    code, raw = _machine(args, st_path, lg)
    if code != EXIT_OK:
        return {
            "ok": False,
            "exit": code,
            "error": raw or "the machine refused the start",
        }
    state = load_state(st_path) or {}
    state["session"] = session_id
    state["goal_id"] = goal_id or first_open_goal(plan_state)
    save_state(st_path, state)
    _set_active(session_id, unit)
    return {
        "ok": True,
        "exit": EXIT_OK,
        "unit": unit,
        "claim": claim,
        "goal_id": state["goal_id"],
        "stage": cur_stage(state).get("name"),
        "writes": allowed_writes(state),
        "output": _payload(raw),
    }


def submit(session_id: str, artifact: str, unit: str = ""):
    """Hand the stage's artefact to the machine, after the contract says the stage is earned."""
    state = active_state(session_id, unit)
    if state is None:
        return {
            "ok": False,
            "exit": EXIT_REFUSED,
            "error": "no unit is running for this session",
        }
    if state.get("status") in TERMINAL:
        return {
            "ok": False,
            "exit": EXIT_REFUSED,
            "error": f"unit is {state['status']}; no further actions",
        }
    stage = cur_stage(state)
    contract_stage = stage.get("contract_stage", "")
    detail = ""
    if contract_stage in CONTRACT_STAGES:
        recorded, detail = ledger_stage_recorded(
            session_id, contract_stage, state.get("goal_id", "")
        )
        if not recorded:
            return {
                "ok": False,
                "exit": EXIT_RETRY,
                "error": detail,
                "stage": stage.get("name"),
                "contract_stage": contract_stage,
            }
    if stage.get("estate_ledger"):
        # The evidence of this stage IS the contract, so the artefact handed to the machine is a
        # receipt of what the ledger says -- not a second copy of the contract.
        artifact = _write_evidence(state, contract_stage, detail)
    st_path = state_path(session_id, state.get("unit", ""))
    lg = log_path(session_id, state.get("unit", ""))
    code, raw = _machine(
        ["submit", "--state", st_path, "--artifact", artifact], st_path, lg
    )
    payload = _payload(raw)
    if code == EXIT_OK:
        state = load_state(st_path) or state
        return {
            "ok": True,
            "exit": EXIT_OK,
            "stage": payload.get("stage"),
            "status": payload.get("status", state.get("status")),
            "output": payload,
        }
    return {
        "ok": False,
        "exit": code,
        "error": payload.get("reason") or raw or "the machine refused the artefact",
        "output": payload,
    }


def _write_evidence(state: dict, contract_stage: str, detail: str) -> str:
    """The machine wants a file; the contract's evidence is the ledger.

    So the binding writes a small JSON receipt (what the ledger says, and where it says it) into
    the unit's own directory and hands THAT to the machine. The artefact is then the contract
    itself, not a second copy of it.
    """
    d = session_dir(state.get("session", ""))
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{_safe_name(state.get('unit', 'unit'))}.evidence.json")
    payload = {
        "contract_stage": contract_stage,
        "detail": detail,
        "ledger": os.path.join(
            UNIT_ROOT, "..", "plans", f"{_safe_name(state.get('session', ''))}.jsonl"
        ),
        "at": time.time(),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    return path


def check_write(session_id: str, path: str, unit: str = ""):
    """May this session write this path, in the stage it is in?"""
    state = active_state(session_id, unit)
    if state is None:
        return {
            "ok": False,
            "exit": EXIT_REFUSED,
            "error": "no unit is running for this session",
        }
    st_path = state_path(session_id, state.get("unit", ""))
    lg = log_path(session_id, state.get("unit", ""))
    code, raw = _machine(
        ["check-write", "--state", st_path, "--path", path], st_path, lg
    )
    payload = _payload(raw)
    return {
        "ok": code == EXIT_OK,
        "exit": code,
        "error": payload.get("error"),
        "allowed": payload.get("allowed", allowed_writes(state)),
        "stage": cur_stage(state).get("name"),
    }


def spend(session_id: str, tokens: int, unit: str = ""):
    state = active_state(session_id, unit)
    if state is None:
        return {
            "ok": False,
            "exit": EXIT_REFUSED,
            "error": "no unit is running for this session",
        }
    st_path = state_path(session_id, state.get("unit", ""))
    lg = log_path(session_id, state.get("unit", ""))
    code, raw = _machine(
        ["spend", "--state", st_path, "--tokens", str(int(tokens))], st_path, lg
    )
    payload = _payload(raw)
    return {
        "ok": code == EXIT_OK,
        "exit": code,
        "error": payload.get("error"),
        "output": payload,
    }


def status(session_id: str, unit: str = ""):
    state = active_state(session_id, unit)
    if state is None:
        return {
            "ok": True,
            "exit": EXIT_OK,
            "status": "none",
            "units": _list_units(session_id),
        }
    st_path = state_path(session_id, state.get("unit", ""))
    code, raw = _machine(
        ["status", "--state", st_path],
        st_path,
        log_path(session_id, state.get("unit", "")),
    )
    payload = _payload(raw)
    return {
        "ok": code == EXIT_OK,
        "exit": code,
        "status": payload.get("status"),
        "stage": payload.get("stage"),
        "tokens": payload.get("tokens"),
        "retries": payload.get("retries"),
        "writes": allowed_writes(state),
        "contract_stage": cur_stage(state).get("contract_stage"),
    }


def _list_units(session_id: str) -> list:
    d = session_dir(session_id)
    try:
        names = os.listdir(d)
    except Exception:  # noqa: BLE001 - no directory means no units
        return []
    out = []
    for n in names:
        if n.endswith(".state.json"):
            out.append(n[: -len(".state.json")])
    return sorted(out)


# --------------------------------------------------------------------------- the door's gate


_REDIRECT = re.compile(r"(?:\d?>>?|&>>?)\s*([^\s;|&()<>]+)")
_TEE = re.compile(r"\btee\b(?:\s+-[^\s]+)*\s+([^\s;|&()]+)")
_CP = re.compile(r"\bcp\b(?:\s+-[^\s]+)*\s+(?:\S+)\s+([^\s;|&()]+)")
_MV = re.compile(r"\bmv\b(?:\s+-[^\s]+)*\s+(?:\S+)\s+([^\s;|&()]+)")
_TOUCH = re.compile(r"\btouch\b(?:\s+-[^\s]+)*\s+([^\s;|&()]+)")
_MKDIR = re.compile(r"\bmkdir\b(?:\s+-[^\s]+)*\s+([^\s;|&()]+)")
_RM = re.compile(r"\brm\b(?:\s+-[^\s]+)*\s+([^\s;|&()]+)")


def write_targets(command: str) -> list:
    """The paths a command EXPLICITLY writes.

    Only explicit targets count: a redirect, a tee, a copy's destination, a touch, a mkdir, a
    removal. Inferring "this program might write somewhere" from an arbitrary command line is a
    heuristic that refuses correct work (R38), so the door's boundary is enforced where the
    target is named, and the harness's own check-write covers the rest.
    """
    if not isinstance(command, str) or not command.strip():
        return []
    out = []
    for pattern in (_REDIRECT, _TEE, _CP, _MV, _TOUCH, _MKDIR, _RM):
        for match in pattern.finditer(command):
            target = match.group(1).strip().strip("'\"")
            if target and target != "-":
                out.append(_relative(target))
    seen, uniq = set(), []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def _relative(path: str) -> str:
    p = os.path.expanduser(path)
    if os.path.isabs(p):
        try:
            p = os.path.relpath(p, os.getcwd())
        except Exception:  # noqa: BLE001 - a path on another volume stays absolute
            pass
    return os.path.normpath(p).lstrip("./") or p


def gate(session_id: str, command: str) -> dict:
    """The door's verdict on one command for a session running a unit.

    {"ok": True} when there is nothing to refuse. {"ok": False, "reason": "write_denied"} when
    the command writes outside the unit's boundary for the stage it is in.
    """
    if not session_id:
        return {"ok": True, "reason": "no_session_presented"}
    state = active_state(session_id)
    if state is None:
        return {"ok": True, "reason": "no_unit"}
    if state.get("status") in TERMINAL:
        return {"ok": True, "reason": "unit_terminal"}
    targets = write_targets(command)
    if not targets:
        return {"ok": True, "reason": "no_explicit_write"}
    allowed = allowed_writes(state)
    stage = cur_stage(state)
    outside = [t for t in targets if not any(fnmatch.fnmatch(t, g) for g in allowed)]
    if outside:
        return {
            "ok": False,
            "reason": "write_denied",
            "exit_code": EXIT_WRITE_DENIED,
            "stage": stage.get("name"),
            "contract_stage": stage.get("contract_stage"),
            "allowed": allowed,
            "detail": (
                f"write denied in stage '{stage.get('name')}': "
                f"{', '.join(outside)} is outside the unit's allowed paths "
                f"({', '.join(allowed) if allowed else 'none'})"
            ),
        }
    return {"ok": True, "reason": "inside_unit_boundary"}
