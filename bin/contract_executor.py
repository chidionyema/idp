#!/usr/bin/env python3
"""Design-by-Contract executor: a tool call is refused unless its own contract holds.

Why this exists (founder essay 2026-09-14, "PhD cold military surgeon"): "A layer in front of
Handler.handle requiring every tool call to declare a pre-condition ... and a post-condition ...
A deterministic script (NOT the agent) checks the post-condition against the live system. If it
fails, the PRM penalises the trajectory and the agent is forced to adapt before continuing."

Ticket: docs/tickets/2026-09-14-reasoning-gateway.md, deliverable D3.

  bin/idp-contract --pre "pod uptime > 0s" --post "readiness probe passes within 30s" \\
      --tool restart_pod --observe <observations.json>
  bin/idp-contract --run <contract.json>          exit 0 held, 1 refused, 2 BLIND
  bin/idp-contract --explain <contract.json>       names which condition, and when, it failed

A condition is `<subject> <op> <value>` (`>`, `>=`, `<`, `<=`, `==`, `!=`) or `<subject> passes`
/ `<subject> fails`, with an optional trailing `within <N>s` deadline. The pre-condition is
checked once, before the tool is credited as having run; the post-condition is polled against a
series of timestamped observations up to its deadline, and the first sample that satisfies it
is what "passes" means -- a post-condition that only turns true after its own deadline is a
refusal, the exact "probe still fails" case the ticket names.

Observations are BYTES the caller declares (a subject's value at a timestamp), never a value
this script invents. A subject with no observation at all is BLIND, not a passing contract --
the same fail-closed convention bin/idp-epistemic and bin/idp-budget already use.

The honest limit: this script does not itself reach a live cluster -- there is no live prober
wired here, deliberately (the ticket's own stack table says "buy or use open source for the
underlying graph logic and math engines", and wiring a second, bespoke k8s client here would be
exactly that reinvention, R43). It grades declared observations, real or replayed from a live
probe upstream; a bare invocation reports the estate's own recorded contract runs, same as
bin/idp-prm and bin/idp-budget do for sessions (R38 -- historical runs are reported, not failed).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_OPS = {">", ">=", "<", "<=", "==", "!="}
_BOOL_OPS = {"passes", "fails"}

_CONDITION_RE = re.compile(
    r"^(?P<subject>.+?)\s+(?P<op>>=|<=|==|!=|>|<|passes|fails)"
    r"(?:\s+(?P<value>[^\s]+))?"
    r"(?:\s+within\s+(?P<deadline>\d+(?:\.\d+)?)\s*s)?$",
    re.IGNORECASE,
)


class ConditionError(ValueError):
    pass


def _coerce(raw: str) -> float | str | bool:
    if raw is None:
        return None
    low = raw.strip().lower()
    if low in ("true", "ready", "pass", "passing"):
        return True
    if low in ("false", "notready", "fail", "failing"):
        return False
    stripped = re.sub(r"[a-zA-Z%]+$", "", raw.strip())
    try:
        return float(stripped)
    except ValueError:
        return raw.strip()


def parse_condition(text: str) -> dict:
    """A condition is bytes in, bytes out -- no clause this parser cannot match is accepted."""
    m = _CONDITION_RE.match(text.strip())
    if not m:
        raise ConditionError(f"cannot parse condition: {text!r}")
    op = m.group("op").lower()
    value = m.group("value")
    if op in _BOOL_OPS and value:
        raise ConditionError(f"{op!r} takes no value, got {value!r} in {text!r}")
    if op in _OPS and value is None:
        raise ConditionError(f"{op!r} needs a value in {text!r}")
    deadline = m.group("deadline")
    return {
        "raw": text.strip(),
        "subject": m.group("subject").strip().lower(),
        "op": op,
        "value": _coerce(value) if value else None,
        "deadline_s": float(deadline) if deadline else None,
    }


def _holds(op: str, observed, expected) -> bool:
    if op == "passes":
        return bool(observed)
    if op == "fails":
        return not bool(observed)
    try:
        a, b = float(observed), float(expected)
    except (TypeError, ValueError):
        a, b = observed, expected
    if op == ">":
        return a > b
    if op == ">=":
        return a >= b
    if op == "<":
        return a < b
    if op == "<=":
        return a <= b
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    raise ConditionError(f"unknown operator {op!r}")


def _samples_for(observations: dict, subject: str) -> list[tuple[float, object]] | None:
    if subject not in observations:
        return None
    raw = observations[subject]
    if isinstance(raw, list):
        return [(float(t), v) for t, v in raw]
    return [(0.0, raw)]


def check_condition(cond: dict, observations: dict) -> dict:
    """Returns {held, checked_at, observed, blind}. Polls up to deadline_s for a passing sample."""
    samples = _samples_for(observations, cond["subject"])
    if samples is None:
        return {"held": False, "checked_at": None, "observed": None, "blind": True}
    deadline = cond["deadline_s"]
    window = [s for s in samples if deadline is None or s[0] <= deadline]
    window.sort(key=lambda s: s[0])
    for t, value in window:
        if _holds(cond["op"], value, cond["value"]):
            return {"held": True, "checked_at": t, "observed": value, "blind": False}
    last = window[-1] if window else (None, None)
    return {"held": False, "checked_at": last[0], "observed": last[1], "blind": False}


def run_contract(record: dict) -> dict:
    """Grade one contract record: {tool, pre, post, observations}. BYTES only, no live reach."""
    tool = record.get("tool", "?")
    pre = parse_condition(record["pre"])
    post = parse_condition(record["post"])
    observations = record.get("observations") or {}

    pre_result = check_condition(pre, observations)
    if pre_result["blind"]:
        return {
            "tool": tool,
            "refused": True,
            "blind": True,
            "cause": "pre_condition_unobserved",
            "detail": f"no observation for {pre['subject']!r}; a missing reading is BLIND, not held",
        }
    if not pre_result["held"]:
        return {
            "tool": tool,
            "refused": True,
            "blind": False,
            "cause": "pre_condition_failed",
            "detail": f"pre-condition {pre['raw']!r} did not hold (observed {pre_result['observed']!r}); {tool} was never credited as run",
        }

    post_result = check_condition(post, observations)
    if post_result["blind"]:
        return {
            "tool": tool,
            "refused": True,
            "blind": True,
            "cause": "post_condition_unobserved",
            "detail": f"no observation for {post['subject']!r}; a missing reading is BLIND, not held",
        }
    if not post_result["held"]:
        deadline_note = (
            f" within {post['deadline_s']:.0f}s" if post["deadline_s"] else ""
        )
        return {
            "tool": tool,
            "refused": True,
            "blind": False,
            "cause": "post_condition_failed",
            "detail": (
                f"post-condition {post['raw']!r} never held{deadline_note} "
                f"(last observed {post_result['observed']!r} at t={post_result['checked_at']})"
            ),
        }

    return {
        "tool": tool,
        "refused": False,
        "blind": False,
        "cause": None,
        "detail": f"pre and post both held; post confirmed at t={post_result['checked_at']}",
    }


def _blind(why: str) -> dict:
    return {
        "tool": "?",
        "refused": True,
        "blind": True,
        "cause": "unreadable",
        "detail": why,
    }


def load_contract(path: Path | str) -> dict:
    p = Path(path)
    if not p.exists():
        return _blind(f"{p} does not exist")
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return _blind(f"{p} could not be read: {exc}")


def grade_file(path: Path | str) -> dict:
    record = load_contract(path)
    if record.get("blind") and "tool" not in (record.get("_raw") or {}):
        # load_contract's own failure shape doubles as a BLIND verdict already.
        if (
            set(record.keys()) == {"tool", "refused", "blind", "cause", "detail"}
            and record["cause"] == "unreadable"
        ):
            return record
    try:
        return run_contract(record)
    except (ConditionError, KeyError) as exc:
        return _blind(f"{path}: {exc}")


def _estate_contract_runs(limit: int = 25) -> list[Path]:
    root = Path.home() / ".pi" / "agent" / "contracts"
    if not root.exists():
        return []
    return sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[
        :limit
    ]


def _sweep_estate() -> int:
    """The live case bin/idp-rules requires: replay the estate's own recorded contract runs.

    Mirrors bin/idp-prm and bin/idp-budget's bare-invocation convention (R43, R38): a contract
    run recorded before this gate existed was never checked live, so it is reported, never
    failed, on a bare sweep. Naming one contract by name (--run <path>) still refuses for real.
    """
    runs = _estate_contract_runs()
    if not runs:
        print(
            "ok    contract no recorded contract runs on this machine "
            "(~/.pi/agent/contracts/*.json); nothing to sweep"
        )
        return 0
    would_refuse = 0
    for path in runs:
        verdict = grade_file(path)
        if verdict.get("blind"):
            continue
        if verdict["refused"]:
            would_refuse += 1
    print(
        f"ok    contract {len(runs)} recorded run(s) swept; {would_refuse} would have been "
        "refused. Historical, reported not failed -- --run one by name to act on it."
    )
    return 0


def _usage() -> str:
    return (
        "usage: idp-contract --run <contract.json>\n"
        "       idp-contract --explain <contract.json>\n"
        "       idp-contract --pre <cond> --post <cond> --tool <name> --observe <observations.json>\n"
        "       idp-contract --self-test\n"
        "       idp-contract --help"
    )


def _print_verdict(verdict: dict, prefix: str) -> None:
    print(
        f"{prefix} tool={verdict['tool']} cause={verdict['cause'] or 'none'}: {verdict['detail']}"
    )


def _self_test() -> int:
    """LAW 45: this script has not run until --self-test proves it, against its own fixtures."""
    root = Path(__file__).resolve().parent.parent
    bad = root / "tests/fixtures/contract/bad/contract.json"
    good = root / "tests/fixtures/contract/good/contract.json"
    if not bad.exists() or not good.exists():
        print(
            f"SKIP contract --self-test: fixtures not found under {root}/tests/fixtures/contract"
        )
        return 0
    v_bad = grade_file(bad)
    v_good = grade_file(good)
    if not v_bad["refused"]:
        print(f"FAIL contract --self-test: {bad} should have been refused and was not")
        return 1
    if v_good["refused"]:
        print(
            f"FAIL contract --self-test: {good} should have held and was refused: {v_good['detail']}"
        )
        return 1
    print("ok   contract --self-test: bad fixture refused, good fixture held")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] in ("--help", "-h"):
        print(_usage())
        return 0
    if len(argv) > 1 and argv[1] == "--self-test":
        return _self_test()

    args = argv[1:]
    mode: str | None = None
    path: str | None = None
    pre: str | None = None
    post: str | None = None
    tool: str | None = None
    observe: str | None = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--run":
            i += 1
            mode = "run"
            path = args[i]
        elif a == "--explain":
            i += 1
            mode = "explain"
            path = args[i]
        elif a == "--pre":
            i += 1
            pre = args[i]
        elif a == "--post":
            i += 1
            post = args[i]
        elif a == "--tool":
            i += 1
            tool = args[i]
        elif a == "--observe":
            i += 1
            observe = args[i]
        i += 1

    if not args:
        return _sweep_estate()

    if pre and post and tool:
        if not observe:
            print(
                "BLIND contract no --observe given and no live prober is wired here "
                "(honest limit -- see module docstring); pass --observe <observations.json>",
                file=sys.stderr,
            )
            return 2
        obs_record = load_contract(observe)
        if obs_record.get("blind"):
            print(f"BLIND contract {obs_record['detail']}", file=sys.stderr)
            return 2
        record = {"tool": tool, "pre": pre, "post": post, "observations": obs_record}
        verdict = run_contract(record)
    elif mode and path:
        verdict = grade_file(path)
    else:
        print(_usage(), file=sys.stderr)
        return 2

    if verdict.get("blind"):
        print(f"BLIND contract {verdict['detail']}", file=sys.stderr)
        return 2

    if mode == "explain":
        if verdict["refused"]:
            print(f"refused ({verdict['cause']}): {verdict['detail']}")
        else:
            print(f"held: {verdict['detail']}")
        return 0

    if verdict["refused"]:
        print(
            f"FAIL  contract refused ({verdict['cause']}): {verdict['detail']}",
            file=sys.stderr,
        )
        return 1

    print(f"ok    contract {verdict['tool']} held: {verdict['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
