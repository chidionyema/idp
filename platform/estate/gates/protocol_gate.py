#!/usr/bin/env python3
# ruff: noqa: S110, S112, S310, S602, S603, S607, B007
#
# Per-file exemptions, each because it is the gate's function rather than a smell. This file is a
# hot-path control: it runs on every tool call of every hooked agent, so it must never crash the
# hook it guards, and it must execute the break's own recorded probe with a shell.
#   S110/S112  bare `except: pass` -- a failing probe, an already-dead pid or an unreadable json
#              must never take down the hook. The gate reports state; it does not abort the agent.
#   S602/S603/S607  run_probes() runs the probe string with shell=True. That IS the close
#              mechanism: a break closes only when its own probe passes. The strings come from the
#              estate's protocols.json, never from user input.
#   S310  urlopen against a health endpoint; the scheme is checked before the call.
#   B007  an unused loop index over probe results, kept for parity with the probe list.
# Adopted into the repo 2026-11-10 (AGENTS.md 9 R7): it previously lived only in ~/.estate/gates/,
# outside every repo, so no review, test or CI ever saw it and a 46-byte stub replaced it for nine
# days undetected. Behaviour is unchanged from the installed original; the three defects fixed in
# this change are falsified in tests/estate/test_protocol_gate_orphan.py.
"""protocol_gate.py - stop-the-line for critical protocol breaks.

THE LAW: no agent continues past a critical protocol break until the root cause is PROVEN fixed.
"Note it and proceed" is not a resolution. A break closes only when its probes pass again after having
been seen to fail (the falsifier), plus a written cause. Humans can waive, agents cannot.

  protocol_gate.py report --protocol memory-door --error "URLError ..."   # verify by probe, then open a break
  protocol_gate.py status
  protocol_gate.py prove  --id ID --cause "..." [--evidence FILE]        # runs the probes; closes only if they pass
  protocol_gate.py waive  --id ID --by NAME --reason "..."               # HUMAN ONLY (needs a real terminal)
  protocol_gate.py hook pre|post                                         # harness adapter, JSON on stdin
  protocol_gate.py probe-http URL                                        # exit 0 if ANY HTTP response (transport is up)

State lives in $ESTATE_BREAKS_DIR (default ~/.estate/breaks). Protocol config: protocols.json in that dir.
Wire `hook pre` as a PreToolUse gate (exit 2 = deny) and `hook post` as a PostToolUse detector.
"""

import argparse, bisect, calendar, glob, json, os, re, shlex, shutil, subprocess, sys, time
# urllib is imported where it is used, not here: importing it costs ~1.2 s on this laptop (site + http.client + email
# parsers), and this gate runs on the hot path of EVERY tool call of every hooked agent.

DIR = os.path.expanduser(os.environ.get("ESTATE_BREAKS_DIR", "~/.estate/breaks"))
SELF = os.path.abspath(__file__)
PY = sys.executable or "python3"

DEFAULT_PROTOCOLS = {
    "memory-door": {
        "critical": True,
        "owner": "founder / holder of the OCI account",
        "patterns": [
            r"memory door unreachable",
            r"EOF occurred in violation of protocol",
            r"memdoor",
            r"no MCP_GATEWAY_KEY",
        ],
        "probes": ["%s %s probe-http https://mcp.mumchimp.com/" % (PY, SELF)],
        "roundtrip": [],  # ADD a real authenticated remember+recall round trip here; transport-only proof is weaker
        "repair_scope": [],  # path globs agents may edit while this break is open, e.g. "*/cloudflare/*"
        "required_action": "Restore the memory door (or move it off the dead cluster). Name who must act and give the exact command.",
    },
    "router-cloud": {
        "critical": True,
        "owner": "founder / holder of the OCI account",
        "patterns": [
            r"router\.cloud\.completion",
            r"llm\.mumchimp\.com.*(fail|unreachable|timeout|EOF)",
            r"router.*(SPOF|single point of failure)",
        ],
        "probes": ["%s %s probe-http https://llm.mumchimp.com/" % (PY, SELF)],
        "roundtrip": [],
        "repair_scope": [],
        "required_action": "Restore the LLM router (or point agents at the Cloudflare router). Name who must act and give the exact command.",
    },
}

SAFE_TOOLS = {
    "read",
    "glob",
    "grep",
    "estate_show",
    "estate_list",
    "estate_capabilities",
    "estate_git_state",
    "estate_executor_status",
    "read_files",
    "search_codebase",
}
SHELL_TOOLS = {"bash", "estate_execute", "run_commands"}
EDIT_TOOLS = {"write", "edit", "editor", "apply_patch", "notebookedit"}
# ---------------------------------------------------------------- Cline (measured on Cline 3.0.74)
# Cline's hook payload is NOT Claude Code's shape. What Cline actually writes to a hook script's stdin (captured
# from a live run of the real loader) is:
#   {"clineVersion":"","hookName":"tool_call","timestamp":"...","taskId":"conv-1","workspaceRoots":["/tmp/cline-ws"],
#    "userId":"...","agent_id":"...","parent_agent_id":null,"iteration":1,
#    "tool_call":{"id":"c1","name":"run_commands","input":{"commands":["echo hello"]}},
#    "preToolUse":{"parameters":{"commands":"[\"echo hello\"]"}}}
# and the answer Cline understands is {"cancel":true,"errorMessage":"..."} on stdout -- it blocks the tool call on
# cancel. It does NOT understand Claude Code's exit-2 convention.
# Cline's own tool-name aliases (measured in @cline/core 3.0.74): bash, execute_command and list_files ARE
# run_commands. list_files is therefore a shell tool here, not a read.
CLINE_TOOL_ALIASES = {
    "bash": "run_commands",
    "execute_command": "run_commands",
    "list_files": "run_commands",
    "read_file": "read_files",
    "search_files": "search_codebase",
    "list_code_definition_names": "search_codebase",
    "apply_diff": "editor",
    "replace_in_file": "editor",
    "apply_patch": "apply_patch",
}
ALLOW_INTENTS = {
    "router-status",
    "estate-truth",
    "executor-status",
    "friction-report",
    "router-lane-health",
    "protocol-break-status",
    "protocol-break-prove",
    "governance-state",
    "budget-unlock",
}
ALLOW_CMD = re.compile(
    r"^\s*(ls|cat|head|tail|grep|rg|find|wc|stat|file|dig|nslookup|host|ping|echo|pwd|date|which|env|uname|df|ps|pgrep|"
    r"nc\s+-z|openssl\s+s_client|kubectl\s+(get|describe|logs|config\s+view)|oci\s+.*\b(get|list)\b|"
    r"git\s+(status|log|diff|show|rev-parse|branch|worktree\s+list|remote|ls-remote)|"
    r"curl(\s+-[sSIiLv]+)*\s+\S+|\S*python3?\s+\S*protocol_gate\.py\s+(status|probe-http|report|prove|guard|regress|unlock|governance|budget-check))\b"
)
CURL_WRITE = re.compile(
    r"(^|\s)(-X\s*(POST|PUT|DELETE|PATCH)|-d\b|--data|-T\b|--upload|-F\b|--form)", re.I
)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_protocols():
    p = dict(DEFAULT_PROTOCOLS)
    try:
        p.update(json.load(open(os.path.join(DIR, "protocols.json"))))
    except Exception:
        pass
    return p


def log(ev):
    os.makedirs(DIR, exist_ok=True)
    with open(os.path.join(DIR, "events.jsonl"), "a") as f:
        f.write(json.dumps(dict(ev, ts=now())) + "\n")


def breaks(state=None):
    out = []
    for f in sorted(glob.glob(os.path.join(DIR, "*.json"))):
        if os.path.basename(f) in (
            "protocols.json",
            "agents.json",
            "budget.json",
            "frozen.json",
            "watch_offsets.json",
            "convergence.json",
            "convergence_state.json",
            "agents.targets.json",
        ):
            continue
        try:
            b = json.load(open(f))
        except Exception:
            continue
        if not isinstance(b, dict) or "protocol" not in b or "id" not in b:
            continue
        if state is None or b.get("state") == state:
            out.append(b)
    return out


def save(b):
    os.makedirs(DIR, exist_ok=True)
    tmp = os.path.join(DIR, ".%s.tmp" % b["id"])
    json.dump(b, open(tmp, "w"), indent=1)
    os.replace(tmp, os.path.join(DIR, b["id"] + ".json"))


def run_probes(cmds):
    res = []
    for c in cmds:
        try:
            r = subprocess.run(
                c, shell=True, capture_output=True, text=True, timeout=60
            )
            res.append(dict(cmd=c, rc=r.returncode, out=(r.stdout + r.stderr)[-400:]))
        except Exception as e:
            res.append(dict(cmd=c, rc=99, out=str(e)[:300]))
    return res


def all_ok(res):
    return all(r["rc"] == 0 for r in res)


SHELL_BUILTINS = {
    "cd",
    "test",
    "[",
    "true",
    "false",
    "echo",
    "export",
    "source",
    ".",
    "exit",
    "command",
    "type",
}


def probe_defects(cmds):
    """A probe must be a runnable command. A sentence is not a probe: its 'failing baseline' is a shell syntax error, it can
    never pass, and the break it guards can only be waived by hand. Reject it when the break would open, not ten days later."""
    bad = []
    for c in cmds:
        try:
            argv = shlex.split(c)
        except ValueError:
            bad.append((c, "unparseable"))
            continue
        while argv and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[0]):
            argv = argv[1:]  # leading VAR=value
        if not argv:
            bad.append((c, "empty"))
            continue
        head = argv[0]
        if (
            head in SHELL_BUILTINS
            or shutil.which(head)
            or os.path.isfile(os.path.expanduser(head))
        ):
            continue
        bad.append((c, "not a command: %s" % head))
    return bad


def expire_directives():
    """A human-directive protocol (expires_hours in protocols.json) cannot be proven by a probe, so it must not be able to stop the
    fleet forever. Past its expiry the break is closed as EXPIRED and frozen processes resume. Called from the alarm loop AND the hook
    pre-path, so it still fires when the alarm daemon is dead. Cheap: returns at once when nothing is open."""
    op = breaks("OPEN")
    if not op:
        return []
    P = load_protocols()
    out = []
    for b in op:
        h = P.get(b["protocol"], {}).get("expires_hours")
        if not h:
            continue
        try:
            age_h = (
                time.time()
                - calendar.timegm(time.strptime(b["opened_at"], "%Y-%m-%dT%H:%M:%SZ"))
            ) / 3600.0
        except Exception:
            continue
        if age_h >= float(h):
            b.update(state="EXPIRED", closed_at=now(), expired_after_hours=h)
            save(b)
            log(dict(event="expired", id=b["id"], hours=h))
            out.append(b["id"])
    if out and not breaks("OPEN"):
        try:
            do_thaw()
        except Exception as e:
            log(dict(event="thaw_error", err=str(e)[:200]))
    return out


def cmd_probe_http(a):
    import urllib.request, urllib.error

    try:
        urllib.request.urlopen(urllib.request.Request(a.url), timeout=10)
        sys.exit(0)
    except urllib.error.HTTPError:
        sys.exit(0)  # server answered: transport is up
    except Exception as e:
        print("transport down: %s" % e, file=sys.stderr)
        sys.exit(1)


def open_break(protocol, error, by="unknown", force=None):
    P = load_protocols()
    cfg = P.get(protocol)
    if not cfg:
        print("unknown protocol %s" % protocol, file=sys.stderr)
        return None
    # An unarmed protocol can never stop the line. Arming is an explicit act: a detector whose matcher fires on prose, or whose
    # probe flaps on a known outage, must not be able to paralyse the fleet with no path to green.
    if not cfg.get("armed", True):
        log(
            dict(
                event="not_armed",
                protocol=protocol,
                note="protocol is not armed; no break opened",
            )
        )
        return None
    for b in breaks("OPEN"):
        if b["protocol"] == protocol:
            return b  # already open: one break per protocol
    probes = cfg.get("probes", []) + cfg.get("roundtrip", [])
    if not force:
        bad = probe_defects(probes)
        if bad:
            msg = (
                "REFUSED to open %s: probe is not a runnable command (a sentence is not a probe): %s"
                % (protocol, "; ".join("%r (%s)" % (c[:70], why) for c, why in bad))
            )
            print(msg, file=sys.stderr)
            log(dict(event="probe_defect", protocol=protocol, detail=msg[:300]))
            return None
    baseline = force if force else (run_probes(probes) if probes else [])
    if not force and baseline and all_ok(baseline):
        log(
            dict(
                event="no-break",
                protocol=protocol,
                note="probes pass; error was transient or stale",
            )
        )
        return None  # never lock on a ghost
    b = dict(
        id="%s-%s" % (protocol, time.strftime("%Y%m%dT%H%M%S", time.gmtime())),
        protocol=protocol,
        severity="critical" if cfg.get("critical") else "major",
        state="OPEN",
        opened_at=now(),
        opened_by=by,
        error=error[:500],
        baseline=baseline,
        owner=cfg.get("owner"),
        required_action=cfg.get("required_action"),
        repair_scope=cfg.get("repair_scope", []),
        probes=probes,
        recurrence=len(
            [
                x
                for x in breaks()
                if x["protocol"] == protocol
                and x["state"] in ("CLOSED", "WAIVED", "EXPIRED")
            ]
        ),
    )
    save(b)
    log(dict(event="open", id=b["id"], protocol=protocol, by=by))
    return b


def deny_message(bs):
    L = [
        "PROTOCOL BREAK OPEN - THE LINE IS STOPPED. No other work until the root cause is proven fixed. 'Note it and proceed' is not allowed."
    ]
    for b in bs:
        L.append(
            "- %s [%s] since %s. Error: %s"
            % (b["id"], b["protocol"], b["opened_at"], b["error"][:160])
        )
        if b.get("recurrence"):
            L.append(
                "  RECURRENCE #%d: this has failed before. Nothing may fail twice. This is a GOVERNANCE FAILURE: the earlier guard did not hold."
                % b["recurrence"]
            )
        L.append(
            "  Owner: %s | Needed: %s" % (b.get("owner"), b.get("required_action"))
        )
    L.append(
        "Allowed now: read-only diagnosis, and edits inside the break's repair scope. To close: find the root cause, fix it, then run: "
        "%s %s prove --id <ID> --cause '<measured cause, not a guess>'. It closes only if the failing probes now pass."
        % (PY, SELF)
    )
    L.append(
        "If the fix needs a human (cloud account, money, decision): say who and the exact command, then STOP."
    )
    return "\n".join(L)


def shell_ok(cmd):
    c = re.sub(r"2>&1|2>/dev/null|>/dev/null", "", cmd)
    if re.search(r"[<>`]|\$\(", c):
        return False
    for seg in re.split(r"&&|\|\||[;|\n]", c):
        seg = seg.strip()
        if not seg:
            continue
        if not ALLOW_CMD.match(seg):
            return False
        if seg.startswith("curl") and CURL_WRITE.search(seg):
            return False
    return True


def gate(tool, inp, bs):
    t = (tool or "").lower().split("__")[-1]
    if t in SAFE_TOOLS:
        return True, ""
    if t in SHELL_TOOLS:
        cmds = (
            inp.get("commands")
            if isinstance(inp.get("commands"), list)
            else [inp.get("command") or inp.get("cmd") or ""]
        )
        cmds = [c if isinstance(c, str) else json.dumps(c) for c in cmds]
        # A shell tool whose command shape this gate cannot read is DENIED, not allowed: shell_ok("") is True, so an
        # unreadable shell call would otherwise walk straight through a stop-the-line break.
        if not any(c.strip() for c in cmds):
            return (
                False,
                "shell tool called with no command this gate can read while a break is open",
            )
        bad = [c for c in cmds if not shell_ok(c)]
        return (not bad), ("blocked command: %s" % str(bad[0])[:140] if bad else "")
    if t == "estate_invoke":
        i = inp.get("intent")
        return (i in ALLOW_INTENTS), (
            "intent %s is not allowed while a break is open" % i
            if i not in ALLOW_INTENTS
            else ""
        )
    if t in EDIT_TOOLS:
        path = inp.get("path") or ""
        if t == "apply_patch":
            path = re.findall(
                r"\*\*\* (?:Add|Update|Delete) File: (.+)", inp.get("input", "")
            )
        paths = path if isinstance(path, list) else [path]
        scopes = [s for b in bs for s in b.get("repair_scope", [])]
        import fnmatch

        scopes = [os.path.expanduser(s) for s in scopes]
        paths = [os.path.expanduser(p) for p in paths]
        ok = bool(scopes) and all(
            any(fnmatch.fnmatch(p, s) for s in scopes) for p in paths
        )
        return ok, (
            "edit outside the repair scope: %s" % ", ".join(paths)[:140]
            if not ok
            else ""
        )
    if t in ("remember", "recall", "brief"):
        return (
            True,
            "",
        )  # these are the very calls that must keep failing loudly, not be gated
    return False, "tool %s is not allowed while a break is open" % tool


def _maybe_json(v):
    """Cline's preToolUse.parameters carries every value as a STRING, so a list of commands arrives as its JSON text."""
    if isinstance(v, str):
        t = v.strip()
        if t[:1] in "[{":
            try:
                return json.loads(t)
            except Exception:
                return v
    return v


def cline_commands(inp):
    """Every shape Cline can carry a shell command in. A shape this function cannot read yields NO command, so the
    gate denies it: an unreadable shell call is never a pass."""
    out = []

    def push(x):
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, list):
            for y in x:
                push(y)
        elif isinstance(x, dict):
            c = x.get("command") or x.get("cmd") or ""
            if isinstance(c, str):
                args = x.get("args")
                if isinstance(args, list):
                    c = " ".join([c] + [str(a) for a in args])
                out.append(c)

    for key in ("commands", "command", "cmd"):
        if key in inp:
            push(_maybe_json(inp.get(key)))
    return [c for c in out if isinstance(c, str) and c.strip()]


def cline_normalize(d):
    """Cline's tool_call payload -> (tool, input) the gate already understands."""
    tc = d.get("tool_call") if isinstance(d.get("tool_call"), dict) else {}
    ptu = d.get("preToolUse") if isinstance(d.get("preToolUse"), dict) else {}
    name = (tc.get("name") or ptu.get("toolName") or "").strip()
    inp = tc.get("input")
    if not isinstance(inp, dict):
        inp = {}
    params = ptu.get("parameters") if isinstance(ptu.get("parameters"), dict) else {}
    if not inp and params:
        inp = dict((k, _maybe_json(v)) for k, v in params.items())
    name = name.lower().split("__")[-1]
    name = CLINE_TOOL_ALIASES.get(name, name)
    if name == "run_commands":
        return name, {"commands": cline_commands(inp)}
    return name, inp


def action_log(phase, d, tool, payload):
    """One line per tool call: hashes only (no content, no secrets). The seal's agent_actions stream (quad Layer 2 shape: intent, args_hash, result_hash)."""
    try:
        import hashlib

        txt = (
            payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)
        )
        os.makedirs(DIR, exist_ok=True)
        with open(os.path.join(DIR, "actions.jsonl"), "a") as f:
            f.write(
                json.dumps(
                    dict(
                        ts=now(),
                        phase=phase,
                        agent=os.environ.get("ESTATE_AGENT_URN", ""),
                        goal=gkey(d),
                        session=d.get("session_id", ""),
                        tool=tool,
                        **(
                            {"args_hash": hashlib.sha256(txt.encode()).hexdigest()[:32]}
                            if phase == "pre"
                            else {
                                "result_hash": hashlib.sha256(txt.encode()).hexdigest()[
                                    :32
                                ]
                            }
                        ),
                    )
                )
                + "\n"
            )
    except Exception:
        pass


def _deny_out(a, msg):
    """One denial, in the language of the harness that called us. Cline blocks on cancel:true; Claude Code on exit 2."""
    if a.format == "cline":
        print(json.dumps({"cancel": True, "errorMessage": msg}))
        sys.exit(0)
    if a.format == "json":
        print(json.dumps(dict(allow=False, reason=msg)))
        sys.exit(0)
    print(msg, file=sys.stderr)
    sys.exit(2)


def _allow_out(a, adv=""):
    if a.format == "cline":
        print("{}")
        sys.exit(0)  # valid JSON, no control fields: Cline runs the tool
    if adv and a.format == "claude":
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "additionalContext": adv,
                    }
                }
            )
        )
    sys.exit(0)


def cmd_hook(a):
    try:
        d = json.load(sys.stdin)
    except Exception:
        d = {}
    tool = d.get("tool_name") or d.get("tool") or ""
    inp = d.get("tool_input") or d.get("input") or d.get("arguments") or {}
    if a.format == "cline":
        if a.phase == "pre":
            tool, inp = cline_normalize(d)
            d = dict(d)
            d["tool_name"] = tool
            d["tool_input"] = inp
            d.setdefault("session_id", d.get("taskId", ""))
        else:
            tr = d.get("tool_result") if isinstance(d.get("tool_result"), dict) else {}
            tool = tr.get("name") or ""
            inp = tr.get("input") if isinstance(tr.get("input"), dict) else {}
            d = dict(d)
            d["tool_name"] = tool
            d["tool_input"] = inp
            d["tool_response"] = (
                tr.get("output") if tr.get("output") is not None else json.dumps(tr)
            )
    if a.phase == "pre":
        if re.search(
            r"\.estate/seal/(key|hmac)|ESTATE_SEAL_KEY", json.dumps(inp)
        ):  # the agent never touches the signing key (v0: same-uid, so this is a fence, not isolation)
            msg = "DENIED: the seal signing key is outside agent reach."
            log(dict(event="seal_key_denied", tool=tool))
            _deny_out(a, msg)
        action_log("pre", d, tool, inp)
        try:
            expire_directives()
        except Exception as e:
            log(dict(event="expire_error", err=str(e)[:200]))
        bs = breaks("OPEN")
        if not bs:
            try:
                deny, adv = budget_pre(d)
            except Exception as e:
                # R1, repaired 2026-11-11: this branch used to `_allow_out(a)` -- a budget layer
                # that could not run (a timeout, a spawn failure, an unreadable store) silently
                # became a budget that said YES. The failure mode of the guard was to allow, which
                # is not a guard. The spend could not be measured, so the turn is denied and the
                # unmeasured budget is named.
                log(dict(event="budget_error_failclosed", err=str(e)[:200]))
                _deny_out(
                    a,
                    "budget layer error, so the spend could not be measured: %s" % e,
                )
                return
            if deny:
                _deny_out(a, deny)
            ci = conv_inject(d)
            if ci:
                adv = (adv + "\n" if adv else "") + ci
            if adv:
                print(adv, file=sys.stderr)
            _allow_out(a, adv)
        ok, why = gate(tool, inp, bs)
        if ok:
            _allow_out(a)
        msg = deny_message(bs) + "\nDenied: " + why
        # A refusal that is not recorded is a refusal nobody can prove happened. The events stream is the evidence.
        log(
            dict(
                event="deny",
                tool=tool,
                reason=why[:200],
                breaks=[b["id"] for b in bs],
                session=d.get("session_id", ""),
            )
        )
        _deny_out(a, msg)
    action_log(
        "post",
        d,
        tool,
        d.get("tool_response") or d.get("result") or d.get("output") or "",
    )
    try:
        budget_post(d)
    except Exception as e:
        # Post-phase bookkeeping: the work has ALREADY run, so refusing the turn here would be a
        # lie about what happened. The name says so instead of reading as a fail-open -- a live
        # event called `budget_error_failopen` answers a grep for fail-opens with a benign branch
        # and teaches the next agent the wrong lesson.
        log(dict(event="budget_post_error_after_the_work_ran", err=str(e)[:200]))
    res = d.get("tool_response") or d.get("result") or d.get("output") or ""
    txt = res if isinstance(res, str) else json.dumps(res)
    if (tool or "").lower().split("__")[-1] in SAFE_TOOLS:
        sys.exit(0)
    P = load_protocols()
    for name, cfg in P.items():
        if (
            cfg.get("critical")
            and cfg.get("armed", True)
            and any(re.search(p, txt, re.I) for p in cfg.get("patterns", []))
        ):
            b = open_break(name, txt[:300], by=d.get("session_id") or "hook")
            if b:
                park(
                    gkey(d),
                    os.environ.get("ESTATE_GOAL_TEXT", "(unknown)"),
                    name,
                    txt[:300],
                    d.get("session_id", ""),
                )
                print(deny_message([b]), file=sys.stderr)
                sys.exit(2)
    sys.exit(0)


def cmd_report(a):
    b = open_break(a.protocol, a.error, by=a.by)
    if not b:
        print(
            "no break opened (probes pass, protocol unknown/unarmed, or a probe was rejected as not runnable: see stderr/events.jsonl)"
        )
        return
    print(deny_message([b]))
    sys.exit(2)


def cmd_status(a):
    bs = breaks()
    if not bs:
        print("no protocol breaks recorded")
        return
    for b in bs:
        print(
            "%-8s %s [%s] opened %s%s"
            % (
                b["state"],
                b["id"],
                b["protocol"],
                b["opened_at"],
                " closed " + b.get("closed_at", "") if b["state"] != "OPEN" else "",
            )
        )


def cmd_prove(a):
    b = next((x for x in breaks("OPEN") if x["id"] == a.id), None)
    if not b:
        print("no OPEN break %s" % a.id, file=sys.stderr)
        sys.exit(1)
    if len((a.cause or "").strip()) < 40:
        print(
            "REFUSED: --cause must state a measured root cause (40+ chars). A note is not a cause.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not b.get("baseline"):
        print(
            "REFUSED: this break has no recorded failing baseline, so it cannot be proven; a human must waive it.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not (a.guard_cmd or "").strip():
        print(
            "REFUSED: --guard-cmd is required: the regression test that fails if this ever breaks again. Nothing may fail twice.",
            file=sys.stderr,
        )
        sys.exit(1)
    if re.search(
        r"protocol_gate\.py\s+(status|guard-status)\b", a.guard_cmd
    ) or a.guard_cmd.strip() in ("true", ":"):
        print(
            "REFUSED: --guard-cmd must be a real regression test. 'status' exits 0 while a break is open, and 'true' tests nothing.",
            file=sys.stderr,
        )
        sys.exit(1)
    # A break opened before probe_defects() existed still carries a non-command (prose) probe. Running it yields a shell
    # syntax error that no fix can ever make pass, so prove is structurally impossible and the break is un-closeable by
    # any automated route. Say that, name the one route that works (a human waive), and refuse honestly instead of
    # reporting a permanent rc=2 as if it were an unfixed root cause.
    bad = probe_defects(b.get("probes") or [])
    if bad:
        print(
            "REFUSED: this break's probes are not runnable commands, so it can never be proven closed.\n"
            + "\n".join("  %s | %s" % (reason, cmd[:120]) for cmd, reason in bad)
            + "\nThis is a defect in how the break was opened, not an unfixed root cause.\n"
            + "Close it with a human waiver: PROTOCOL_GATE_HUMAN=1 protocol_gate.py waive --id %s --by <human> --reason <why>"
            % b["id"],
            file=sys.stderr,
        )
        sys.exit(2)
    res = run_probes(b["probes"])
    if not all_ok(res):
        print(
            "REFUSED: probes still fail. Root cause is NOT fixed.\n"
            + "\n".join(
                "  rc=%s %s | %s" % (r["rc"], r["cmd"][-70:], r["out"].strip()[:120])
                for r in res
            ),
            file=sys.stderr,
        )
        sys.exit(1)
    g = run_probes([a.guard_cmd])
    if not all_ok(g):
        print(
            "REFUSED: the guard command does not pass now: %s"
            % g[0]["out"].strip()[:200],
            file=sys.stderr,
        )
        sys.exit(1)
    b.update(
        state="CLOSED",
        closed_at=now(),
        proof=dict(
            cause=a.cause,
            evidence=a.evidence,
            probes_after=res,
            guard_cmd=a.guard_cmd,
            falsifier="failed at open, passes now",
        ),
    )
    save(b)
    log(dict(event="closed", id=b["id"]))
    print("CLOSED %s (failed at open, passes now)" % b["id"])
    if not breaks("OPEN"):
        print("resumed %d frozen process(es)" % do_thaw())
    if not [x for x in b["probes"] if "probe-http" not in x]:
        print(
            "note: transport-level proof only. Add a real remember/recall round trip under 'roundtrip' in protocols.json."
        )


def cmd_waive(a):
    if not sys.stdin.isatty() or os.environ.get("PROTOCOL_GATE_HUMAN") != "1":
        print(
            "REFUSED: waiving is human-only (needs a real terminal and PROTOCOL_GATE_HUMAN=1).",
            file=sys.stderr,
        )
        sys.exit(1)
    b = next((x for x in breaks("OPEN") if x["id"] == a.id), None)
    if not b:
        print("no OPEN break", file=sys.stderr)
        sys.exit(1)
    b.update(state="WAIVED", closed_at=now(), waived_by=a.by, waive_reason=a.reason)
    save(b)
    log(dict(event="waived", id=b["id"], by=a.by))
    print("WAIVED %s by %s" % (b["id"], a.by))


def cmd_guard(a):
    bs = breaks("OPEN")
    if not bs:
        sys.exit(0)
    print(deny_message(bs), file=sys.stderr)
    sys.exit(1)


def regress():
    reopened = []
    for b in breaks("CLOSED"):
        # A self-test protocol's guard is the drill's own scratch state, not a production invariant.
        # Regressing it would stop the whole fleet on a synthetic drill, so self-tests never regress.
        if b["protocol"].startswith("selftest-"):
            continue
        g = (b.get("proof") or {}).get("guard_cmd")
        if not g:
            continue
        r = run_probes([g])
        if not all_ok(r):
            nb = open_break(
                b["protocol"],
                "REGRESSION: guard of %s failed: %s"
                % (b["id"], r[0]["out"].strip()[:160]),
                by="regress",
                force=r,
            )
            if nb:
                reopened.append(nb["id"])
    return reopened


def cmd_regress(a):
    r = regress()
    print("reopened: %s" % (", ".join(r) if r else "none"))
    sys.exit(1 if r else 0)


def notify(text, level):
    if os.environ.get("ESTATE_ALARM_DRYRUN"):
        print("ALARM L%d: %s" % (level, text))
        return
    try:
        if sys.platform == "darwin":
            t = text.replace('"', "'")[:200]
            # bounded: an osascript that waits on a TCC prompt must never hold the alarm hostage
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "%s" with title "PROTOCOL BREAK - LINE STOPPED" sound name "Sosumi"'
                    % t,
                ],
                capture_output=True,
                timeout=15,
            )
            if level >= 3:
                subprocess.run(
                    ["say", "Protocol break. The line is stopped. " + t[:120]],
                    capture_output=True,
                    timeout=15,
                )
    except Exception as e:
        print("notify failed: %s" % str(e)[:120], file=sys.stderr)
    hook = os.environ.get("ESTATE_ALARM_WEBHOOK")
    if hook:
        import urllib.request

        try:
            urllib.request.urlopen(
                urllib.request.Request(
                    hook,
                    data=json.dumps({"text": text}).encode(),
                    headers={"Content-Type": "application/json"},
                ),
                timeout=10,
            )
        except Exception as e:
            print("webhook failed: %s" % e, file=sys.stderr)


def alarm_once():
    try:
        watch_once()
    except Exception as e:
        log(dict(event="watch_error", err=str(e)[:200]))
    try:
        expire_directives()
    except Exception as e:
        log(dict(event="expire_error", err=str(e)[:200]))
    P = load_protocols()
    op = breaks("OPEN")
    af = os.path.join(DIR, "ALARM.txt")
    try:
        enforce_physical()
    except Exception as e:
        log(dict(event="enforce_error", err=str(e)[:200]))
    try:
        conv_enforce(conv_tick())
    except Exception as e:
        log(dict(event="converge_error", err=str(e)[:200]))
    if not op:
        if os.path.exists(af):
            os.remove(af)
        return False
    lines = []
    for b in op:
        age = int(
            (
                time.time()
                - time.mktime(time.strptime(b["opened_at"], "%Y-%m-%dT%H:%M:%SZ"))
                + time.timezone
            )
            / 60
        )
        level = min(5, 1 + age // 10 + (1 if b.get("recurrence") else 0))
        msg = "%s [%s] open %dm%s. Owner: %s. Needed: %s" % (
            b["id"],
            b["protocol"],
            age,
            " RECURRENCE#%d" % b["recurrence"] if b.get("recurrence") else "",
            b.get("owner"),
            b.get("required_action"),
        )
        lines.append(msg)
        notify(msg, level)
        cfg = P.get(b["protocol"], {})
        dc = cfg.get("dispatch_cmd")
        due = (time.time() - b.get("dispatched_ts", 0)) > 60 * cfg.get(
            "redispatch_min", 30
        ) and b.get("dispatch_count", 0) < acfg()["max_dispatch"]
        if dc and b.get("dispatch_count", 0) >= acfg()["max_dispatch"]:
            (
                lines.append(
                    "  DISPATCHER GAVE UP after %d tries: the founder must act on %s"
                    % (b.get("dispatch_count", 0), b["id"])
                ),
                notify(
                    "DISPATCHER GAVE UP on %s after %d tries: founder must act"
                    % (b["id"], b.get("dispatch_count", 0)),
                    5,
                ),
            )
        if dc and due:
            env = dict(
                os.environ,
                BREAK_ID=b["id"],
                BREAK_PROTOCOL=b["protocol"],
                BREAK_ERROR=b["error"],
            )
            subprocess.Popen(
                dc,
                shell=True,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            b["dispatched_ts"] = time.time()
            b["dispatch_count"] = b.get("dispatch_count", 0) + 1
            save(b)
            log(dict(event="dispatch", id=b["id"], n=b["dispatch_count"]))
        elif not dc:
            lines.append(
                "  NO DISPATCHER CONFIGURED for %s: set dispatch_cmd in protocols.json so a headless agent starts the repair."
                % b["protocol"]
            )
    os.makedirs(DIR, exist_ok=True)
    open(af, "w").write(chr(10).join(lines) + chr(10))
    return True


def cmd_alarm(a):
    n = 0
    while True:
        n += 1
        alarm_once()
        if n % a.regress_every == 0:
            regress()
        if a.once:
            sys.exit(1 if breaks("OPEN") else 0)
        time.sleep(a.interval)


# ---------------------------------------------------------------- pass budget, parking, unlock (oracle-rationing-protocol)
# A "pass" = one round of tool calls whose results the agent waits for. Parallel calls (several pre-hooks before any post-hook) are ONE pass.
# Only DISCOVERY passes (read-only) are rationed; any mutating action is progress and resets the count. Sequential discovery with no action is the thrash.
# Limits (budget.json in DIR): warn_at=2, stop_at=3, max_tool_calls=400 per goal. Token/dollar caps cannot be seen from a hook: enforce them at the router (virtual key budget).
# Fails OPEN on its own bugs (loudly, in events.jsonl): a fence a correct machine cannot satisfy is an outage. The break registry above does not fail open.
EXIT_BUDGET = 77
BUDGET_DEFAULT = dict(warn_at=2, stop_at=3, max_tool_calls=400, stale_inflight_s=120)


def bcfg():
    c = dict(BUDGET_DEFAULT)
    try:
        c.update(json.load(open(os.path.join(DIR, "budget.json"))))
    except Exception:
        pass
    return c


def gkey(d=None, explicit=None):
    k = (
        explicit
        or os.environ.get("ESTATE_GOAL_ID")
        or (d or {}).get("session_id")
        or "default"
    )
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(k))[:80]


def bpath(k):
    return os.path.join(DIR, "budget", k + ".json")


def bload(k):
    try:
        return json.load(open(bpath(k)))
    except Exception:
        return dict(goal=k, disc=0, inflight=0, last_ts=0, calls=0, stopped=None)


def bsave(k, st):
    os.makedirs(os.path.dirname(bpath(k)), exist_ok=True)
    tmp = bpath(k) + ".tmp"
    json.dump(st, open(tmp, "w"), indent=1)
    os.replace(tmp, bpath(k))


def readonly(tool, inp):
    t = (tool or "").lower().split("__")[-1]
    if t in SAFE_TOOLS or t in ("remember", "recall", "brief"):
        return True
    if t in SHELL_TOOLS:
        cmds = (
            inp.get("commands")
            if isinstance(inp.get("commands"), list)
            else [inp.get("command") or inp.get("cmd") or ""]
        )
        return all(shell_ok(c if isinstance(c, str) else json.dumps(c)) for c in cmds)
    if t == "estate_invoke":
        return inp.get("intent") in ALLOW_INTENTS
    return False


def park(k, objective, blocking, error, session=""):
    os.makedirs(DIR, exist_ok=True)
    row = dict(
        ts=now(),
        goal=k,
        session=session,
        parked_objective=objective,
        blocking=blocking,
        error_payload=str(error)[:500],
        status="PARKED",
    )
    with open(os.path.join(DIR, "unfinished_tasks.jsonl"), "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def stop_msg(st):
    return (
        "E_BUDGET_EXHAUSTED (exit %d): HARD_STOP on goal %s. %s\nNormal work is halted. You may only: write the remediation artifact (edit/write tools), then run:\n"
        "  %s %s unlock --goal %s --kind plan|oracle --artifact <file you just wrote> --cmd '<command that proves it: exits 0>' --why '<40+ chars: what was reachable in one call, or what the tool could not expose>'\n"
        "plan = POOR_PLANNING: the state WAS reachable in one call; the artifact is a composite probe that returns it in one call. oracle = POOR_ORACLE: no single call could expose it; "
        "the artifact is the tool/probe change and --cmd is a test showing it now does. A written excuse unlocks nothing. Parked task is recorded in unfinished_tasks.jsonl."
        % (EXIT_BUDGET, st["goal"], st["stopped"].get("why", ""), PY, SELF, st["goal"])
    )


def gov_block(st):
    cfg = bcfg()
    s = st.get("stopped")
    status = (
        "HARD_STOP"
        if s
        else ("WARNING" if st.get("disc", 0) >= cfg["warn_at"] else "OK")
    )
    return (
        'governance_state:\n  status: %s\n  pass_count: %d\n  parked_task_id: %s\n  parked_objective: "%s"\n  attribution: %s\n  proof_or_error: "%s"\n  remediation_ticket: "%s"\n'
        % (
            status,
            st.get("disc", 0),
            st["goal"] if s else "none",
            (s or {}).get("objective", ""),
            "NONE" if not s else "AWAITING_PROOF",
            (s or {}).get("why", ""),
            "unlock required" if s else "none",
        )
    )


def budget_pre(d):
    """returns (deny_message_or_None, advisory_or_None). Mutates state."""
    cfg = bcfg()
    if os.environ.get("ESTATE_BUDGET", "on" if cfg.get("enabled") else "off") != "on":
        return (
            None,
            None,
        )  # opt-in per harness: a human's interactive session is not rationed
    k = gkey(d)
    st = bload(k)
    tool = d.get("tool_name") or d.get("tool") or ""
    inp = d.get("tool_input") or d.get("input") or d.get("arguments") or {}
    t = tool.lower().split("__")[-1]
    tm = time.time()
    if st.get("stopped"):
        cmd = inp.get("command") or inp.get("cmd") or ""
        if (
            t in EDIT_TOOLS
            or t in ("remember", "recall", "brief")
            or (
                t in SHELL_TOOLS
                and re.search(
                    r"protocol_gate\.py\s+(unlock|status|governance)", str(cmd)
                )
            )
        ):
            return None, None
        return stop_msg(st), None
    st["calls"] = st.get("calls", 0) + 1
    if st["calls"] > cfg["max_tool_calls"]:
        st["stopped"] = dict(
            at=tm,
            why="tool-call cap %d reached for this goal (runaway guard)"
            % cfg["max_tool_calls"],
            objective=os.environ.get("ESTATE_GOAL_TEXT", "(unknown)"),
        )
        bsave(k, st)
        park(
            k,
            st["stopped"]["objective"],
            "budget",
            st["stopped"]["why"],
            d.get("session_id", ""),
        )
        log(dict(event="hard_stop", goal=k, why="call cap"))
        return stop_msg(st), None
    adv = None
    if readonly(tool, inp):
        if (
            st.get("inflight", 0) <= 0
            or tm - st.get("last_ts", 0) > cfg["stale_inflight_s"]
        ):
            st["disc"] = st.get("disc", 0) + 1
            st["inflight"] = 0  # a new discovery pass
            if st["disc"] >= cfg["stop_at"]:
                st["stopped"] = dict(
                    at=tm,
                    why="%d sequential discovery passes with no action. Batch your state-gathering into one composite call."
                    % st["disc"],
                    objective=os.environ.get("ESTATE_GOAL_TEXT", "(unknown)"),
                )
                bsave(k, st)
                park(
                    k,
                    st["stopped"]["objective"],
                    "budget",
                    st["stopped"]["why"],
                    d.get("session_id", ""),
                )
                log(dict(event="hard_stop", goal=k, passes=st["disc"]))
                return stop_msg(st), None
            if st["disc"] == cfg["warn_at"]:
                adv = (
                    "ORACLE_BUDGET_WARNING: discovery pass %d of %d with no action. One more sequential read-only pass is a HARD_STOP. State in one line why pass 1 was not enough, then batch everything you still need into ONE call.\n%s"
                    % (st["disc"], cfg["stop_at"], gov_block(st))
                )
    else:
        st["disc"] = 0  # acting is progress
    st["inflight"] = st.get("inflight", 0) + 1
    st["last_ts"] = tm
    bsave(k, st)
    return None, adv


def budget_post(d):
    k = gkey(d)
    st = bload(k)
    st["inflight"] = max(0, st.get("inflight", 0) - 1)
    st["last_ts"] = time.time()
    bsave(k, st)


def cmd_unlock(a):
    k = gkey(None, a.goal)
    st = bload(k)
    s = st.get("stopped")
    if not s:
        print("goal %s is not stopped" % k)
        return
    if len((a.why or "").strip()) < 40:
        print(
            "REFUSED: --why must say what was reachable in one call (plan) or what the tool could not expose (oracle). 40+ chars.",
            file=sys.stderr,
        )
        sys.exit(1)
    ap_ = os.path.expanduser(a.artifact or "")
    if not os.path.isfile(ap_) or os.path.getmtime(ap_) < s["at"]:
        print(
            "REFUSED: --artifact must be a file written AFTER the hard stop (the composite probe or the tool change).",
            file=sys.stderr,
        )
        sys.exit(1)
    if not (a.cmd or "").strip():
        print(
            "REFUSED: --cmd required: a command that exits 0 and shows the fix works.",
            file=sys.stderr,
        )
        sys.exit(1)
    r = run_probes([a.cmd])
    if not all_ok(r) or not r[0]["out"].strip():
        print(
            "REFUSED: --cmd did not exit 0 with output: rc=%s %s"
            % (r[0]["rc"], r[0]["out"][:200]),
            file=sys.stderr,
        )
        sys.exit(1)
    attr = "POOR_PLANNING" if a.kind == "plan" else "POOR_ORACLE"
    with open(os.path.join(DIR, "unlocks.jsonl"), "a") as f:
        f.write(
            json.dumps(
                dict(
                    ts=now(),
                    goal=k,
                    attribution=attr,
                    artifact=ap_,
                    cmd=a.cmd,
                    why=a.why,
                    proof_out=r[0]["out"][-300:],
                )
            )
            + "\n"
        )
    st.update(stopped=None, disc=0, inflight=0)
    bsave(k, st)
    log(dict(event="unlocked", goal=k, attribution=attr))
    print("UNLOCKED %s as %s. The parked task may resume." % (k, attr))


def cmd_budget_check(a):
    st = bload(gkey(None, a.goal))
    if st.get("stopped"):
        print(stop_msg(st), file=sys.stderr)
        sys.exit(EXIT_BUDGET)
    sys.exit(0)


def cmd_governance(a):
    print(gov_block(bload(gkey(None, a.goal))))


# ---------------------------------------------------------------- harness-agnostic enforcement: freeze, watch, run
# Hooks only work where a harness has them. These work for ANY model on ANY harness because they act from outside:
#   freeze  - while a break is open or a goal is hard-stopped, SIGSTOP every registered agent process (state kept; thaw resumes it).
#   watch   - read every harness's transcript files for the protocol's failure patterns and open a (probe-verified) break.
#   run     - the one launch wrapper: refuses to start an agent while a break is open, registers its pid, exempts the repair agent.
# agents.json in DIR: {"patterns": [regex over `ps` command lines to treat as agents], "exempt": [...], "freeze": true, "transcripts": [globs]}
import signal

DEFAULT_TRANSCRIPTS = [
    "~/.cline/data/sessions/*/*.messages.json",
    "~/.pi/agent/sessions/*/*.jsonl",
    "~/.codex/sessions/*/*/*/*.jsonl",
    "~/.codex/sessions/*/*.jsonl",
    "~/.claude/projects/*/*.jsonl",
]


def acfg():
    c = dict(
        patterns=[],
        exempt=[],
        freeze=True,
        transcripts=DEFAULT_TRANSCRIPTS,
        max_dispatch=3,
    )
    try:
        c.update(json.load(open(os.path.join(DIR, "agents.json"))))
    except Exception:
        pass
    return c


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def reg_read(name):
    out = {}
    try:
        for l in open(os.path.join(DIR, name)).read().splitlines():
            p, _, cmd = l.partition("\t")
            if p.isdigit() and alive(int(p)):
                out[int(p)] = cmd
    except Exception:
        pass
    return out


def reg_add(name, pid, cmd):
    os.makedirs(DIR, exist_ok=True)
    with open(os.path.join(DIR, name), "a") as f:
        f.write("%d\t%s\n" % (pid, cmd[:200]))


def ps_table():
    try:
        out = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,command="],
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout
    except Exception:
        return {}
    t = {}
    for l in out.splitlines():
        m = re.match(r"\s*(\d+)\s+(\d+)\s+(.*)", l)
        if m:
            t[int(m.group(1))] = (int(m.group(2)), m.group(3))
    return t


def descendants(root, table):
    kids = {root}
    changed = True
    while changed:
        changed = False
        for p, (pp, _) in table.items():
            if pp in kids and p not in kids:
                kids.add(p)
                changed = True
    return kids


def agent_pids():
    c = acfg()
    table = ps_table()
    me = os.getpid()
    skip = {me, os.getppid()}
    tools = re.compile(r"protocol_gate\.py|seal\.py|lane_dna\.py")
    repair = set()
    for rp in reg_read("repair.pids"):
        repair |= descendants(rp, table)
    found = {}
    for pid, cmd in reg_read("agents.pids").items():
        for d in descendants(pid, table):
            found[d] = table.get(d, (0, cmd))[1]
    for pid, (pp, cmd) in table.items():
        if any(re.search(p, cmd) for p in c["patterns"]) and not any(
            re.search(e, cmd) for e in c["exempt"]
        ):
            found[pid] = cmd
    return {
        p: cmd
        for p, cmd in found.items()
        if p not in skip and p not in repair and not tools.search(cmd)
    }


def frozen_state():
    try:
        return json.load(open(os.path.join(DIR, "frozen.json")))
    except Exception:
        return {}


def do_freeze(dry=False):
    fs = frozen_state()
    n = 0
    for pid, cmd in agent_pids().items():
        if str(pid) in fs:
            continue
        if dry:
            print("would freeze %d  %s" % (pid, cmd[:100]))
            continue
        try:
            os.kill(pid, signal.SIGSTOP)
            fs[str(pid)] = dict(cmd=cmd[:160], ts=now())
            n += 1
        except Exception:
            pass
    if not dry:
        os.makedirs(DIR, exist_ok=True)
        json.dump(fs, open(os.path.join(DIR, "frozen.json"), "w"), indent=1)
        log(dict(event="freeze", n=n))
    return n


def do_thaw():
    fs = frozen_state()
    n = 0
    for pid in list(fs):
        try:
            os.kill(int(pid), signal.SIGCONT)
            n += 1
        except Exception:
            pass
    json.dump({}, open(os.path.join(DIR, "frozen.json"), "w"))
    if n:
        log(dict(event="thaw", n=n))
    # A thaw that resumes processes but leaves the break OPEN is a lie: enforce_physical() re-freezes on the next alarm
    # cycle because breaks("OPEN") is still true, so the founder resumes, is frozen again, and the estate deadlocks
    # (AGENTS.md section 9 R6: the recovery path must not depend on what it recovers). Resuming IS the release, so the
    # break must record it. Only unpiloted-directive breaks are closed here, never a probe-backed break whose root
    # cause is still unfixed: those keep their OPEN state and require prove/waive.
    released = []
    for b in breaks("OPEN"):
        if probe_defects(b.get("probes") or []):
            b.update(
                state="THAWED",
                closed_at=now(),
                waived_by="founder",
                waive_reason="thawed: break carried a non-runnable probe, so prove was structurally impossible",
            )
            save(b)
            log(dict(event="thawed-break", id=b["id"]))
            released.append(b["id"])
    for bid in released:
        print("thawed %s (non-runnable probe; no longer blocks)" % bid)
    return n


def do_thaw_pids_only():
    fs = frozen_state()
    n = 0
    for pid in list(fs):
        try:
            os.kill(int(pid), signal.SIGCONT)
            n += 1
        except Exception:
            pass
    json.dump({}, open(os.path.join(DIR, "frozen.json"), "w"))
    return n


def stopped_goals():
    return (
        [
            os.path.basename(f)[:-5]
            for f in glob.glob(os.path.join(DIR, "budget", "*.json"))
            if (lambda d: d.get("stopped"))(
                json.load(open(f)) if os.path.getsize(f) else {}
            )
        ]
        if os.path.isdir(os.path.join(DIR, "budget"))
        else []
    )


def enforce_physical():
    """Called every alarm cycle. Break open -> everything stops. Nothing open -> everything resumes."""
    if acfg()["freeze"] and breaks("OPEN"):
        return do_freeze()
    if frozen_state():
        return do_thaw()
    return 0


def cmd_freeze(a):
    if a.dry_run:
        do_freeze(True)
        return
    print("froze %d agent process(es)" % do_freeze())


def cmd_agents(a):
    """List running processes that look like agent workers so the founder can approve patterns once (nothing is frozen by guesswork)."""
    words = re.compile(
        r"(cline|pi-coding-agent|/\.pi/|codex|gemini|opencode|aider|claude(?!-forensics)|goose|cursor-agent)",
        re.I,
    )
    tools = re.compile(
        r"protocol_gate\.py|seal\.py|lane_dna\.py|Claude\.app|Helper|crashpad|grep|ps -ax"
    )
    hits = {}
    for pid, (pp, cmd) in ps_table().items():
        if words.search(cmd) and not tools.search(cmd) and pid != os.getpid():
            hits[pid] = cmd
    for pid, cmd in sorted(hits.items()):
        print("%6d  %s" % (pid, cmd[:140]))
    pats = sorted(
        {re.escape(re.sub(r"\s.*", "", c).rsplit("/", 1)[-1]) for c in hits.values()}
    )
    print("\nsuggested ~/.estate/breaks/agents.json (review, then save):")
    print(json.dumps({"patterns": pats, "exempt": [], "freeze": True}, indent=1))


def cmd_thaw(a):
    print("resumed %d process(es)" % do_thaw())


def cmd_run(a):
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        print("usage: protocol_gate.py run [--repair] -- <command...>", file=sys.stderr)
        sys.exit(2)
    if not a.repair and breaks("OPEN"):
        print(
            deny_message(breaks("OPEN"))
            + "\nREFUSED to start: a protocol break is open.",
            file=sys.stderr,
        )
        sys.exit(1)
    env = dict(os.environ, ESTATE_BUDGET=os.environ.get("ESTATE_BUDGET", "on"))
    p = subprocess.Popen(cmd, env=env)
    reg_add("repair.pids" if a.repair else "agents.pids", p.pid, " ".join(cmd))
    if a.target:
        try:
            tg = json.load(open(os.path.join(DIR, "agents.targets.json")))
        except Exception:
            tg = {}
        tg[str(p.pid)] = a.target
        json.dump(tg, open(os.path.join(DIR, "agents.targets.json"), "w"))
    log(dict(event="run", repair=a.repair, pid=p.pid, cmd=" ".join(cmd)[:120]))
    sys.exit(p.wait())


WATCH_OFF = "watch_offsets.json"
# The watch runs on a real laptop, where the transcript corpus is hundreds of files and tens of MB, most of them
# ONE long JSON line. Two unbounded things made it hang there: `.*` in a pattern is quadratic on a single long line
# (and `.` never crosses a newline), and every tick read the tail of every file. So: a linear matcher for the pattern
# shapes the protocols use, and a byte/file budget per tick with a cursor carried in watch_offsets.json, so the corpus
# is covered over several ticks and no transcript is skipped forever.
WATCH_MAX_BYTES = int(
    os.environ.get("ESTATE_WATCH_MAX_BYTES", 8 * 1024 * 1024)
)  # transcript bytes read per tick
WATCH_MAX_FILES = int(
    os.environ.get("ESTATE_WATCH_MAX_FILES", 80)
)  # files opened per tick
WATCH_FILE_CAP = int(
    os.environ.get("ESTATE_WATCH_FILE_CAP", 1024 * 1024)
)  # bytes read from one file per tick
GENERIC_GAP = 1000  # characters a `.*` may span in the fallback matcher (keeps the regex path linear-ish)
GENERIC_STEP = 512 * 1024  # chunk size for the fallback matcher


def _split_gaps(pat):
    """Split a pattern source on unescaped `.*` outside character classes: the literal segments between the gaps."""
    segs = []
    cur = ""
    i = 0
    n = len(pat)
    inclass = False
    while i < n:
        c = pat[i]
        if c == "\\" and i + 1 < n:
            cur += pat[i : i + 2]
            i += 2
            continue
        if inclass:
            cur += c
            if c == "]":
                inclass = False
            i += 1
            continue
        if c == "[":
            inclass = True
            cur += c
            i += 1
            continue
        if pat.startswith(".*", i):
            segs.append(cur)
            cur = ""
            i += 2
            continue
        cur += c
        i += 1
    segs.append(cur)
    return segs


def _literal_alts(seg):
    """The literal alternatives of one segment, or None when the segment is not purely literal (regex path then)."""
    s = seg.strip()
    while s.startswith("(") and s.endswith(")"):
        depth = 0
        whole = True
        for k, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and k != len(s) - 1:
                    whole = False
                    break
        if not whole:
            return None
        s = s[1:-1].strip()
    parts = [p.strip() for p in s.split("|")] if "|" in s else [s]
    out = []
    for p in parts:
        if not p:
            return None
        lit = ""
        i = 0
        while i < len(p):
            ch = p[i]
            if ch == "\\":
                if i + 1 >= len(p):
                    return None
                nx = p[i + 1]
                if nx.isalnum() or nx == "_":
                    return None  # \d, \w, \n: not a plain literal
                lit += nx
                i += 2
                continue
            if ch in ".^$*+?()[]{}|":
                return None
            lit += ch
            i += 1
        out.append(lit)
    return out


class Matcher:
    """Exact, linear matcher for the pattern shapes the protocols use: literal segments separated by `.*`.
    `.*` never crosses a newline in the original regex and this matcher keeps that rule exactly.
    Any other shape falls back to the regex engine with the gap bounded, so no pattern can backtrack quadratically."""

    def __init__(self, pattern):
        self.pattern = pattern
        self.segs = None
        try:
            self.rx = re.compile(
                re.sub(r"(?<!\\)\.\*", ".{0,%d}" % GENERIC_GAP, pattern), re.I
            )
        except Exception:
            self.rx = re.compile(re.escape(pattern), re.I)
        try:
            alts = [_literal_alts(s) for s in _split_gaps(pattern)]
            if all(a and len(a) for a in alts):
                self.segs = alts
        except Exception:
            self.segs = None

    def _two(self, chunk):
        """segment1 (.*) segment2, with the gap unable to cross a newline."""
        cands = []
        for alt in self.segs[0]:
            for m in re.finditer(re.escape(alt), chunk, re.I):
                cands.append((m.end(), m.start()))
        if not cands:
            return None
        cands.sort()
        ends = [c[0] for c in cands]
        for alt in self.segs[1]:
            for m in re.finditer(re.escape(alt), chunk, re.I):
                j = m.start()
                i = bisect.bisect_right(ends, j) - 1
                if i < 0:
                    continue
                e0, s0 = cands[i]
                if e0 > j or "\n" in chunk[e0:j]:
                    continue
                return (s0, m.end())
        return None

    def search(self, chunk):
        """Return (start, end) of a match in chunk, or None."""
        if self.segs is None:
            m = self.rx.search(chunk)
            return (m.start(), m.end()) if m else None
        if len(self.segs) == 1:
            for alt in self.segs[0]:
                m = re.search(re.escape(alt), chunk, re.I)
                if m:
                    return (m.start(), m.end())
            return None
        if len(self.segs) == 2:
            return self._two(chunk)
        m = self.rx.search(chunk)
        return (m.start(), m.end()) if m else None


def watch_once(initial_tail=200000):
    """Scan new transcript bytes for critical-protocol failure patterns. Opening a break is probe-verified, so prose that merely mentions a failure never locks the line.
    Bounded on purpose: per tick at most WATCH_MAX_BYTES are read across at most WATCH_MAX_FILES files, and the cursor
    in watch_offsets.json carries the rest over to the next tick."""
    path = os.path.join(DIR, WATCH_OFF)
    try:
        st = json.load(open(path))
    except Exception:
        st = {}
    if not isinstance(st, dict):
        st = {}
    offsets = st.get("files") if isinstance(st.get("files"), dict) else {}
    cursor = st.get("cursor")
    P = {
        n: c
        for n, c in load_protocols().items()
        if c.get("critical") and c.get("armed", True)
    }
    matchers = []
    for name, cfg in P.items():
        for p in cfg.get("patterns", []):
            try:
                matchers.append((name, Matcher(p)))
            except Exception as e:
                log(dict(event="watch_pattern_error", pattern=p, err=str(e)[:200]))
    files = []
    for g in acfg()["transcripts"]:
        try:
            files += glob.glob(os.path.expanduser(g))
        except Exception:
            pass
    files = sorted(set(files))
    if cursor in files:
        i = files.index(cursor)
        files = files[i + 1 :] + files[: i + 1]
    used = 0
    nfiles = 0
    opened = []
    last = cursor
    for f in files:
        if used >= WATCH_MAX_BYTES or nfiles >= WATCH_MAX_FILES:
            break
        try:
            size = os.path.getsize(f)
        except Exception:
            continue
        try:
            start = int(offsets.get(f, max(0, size - initial_tail)))
        except Exception:
            start = max(0, size - initial_tail)
        if size <= start:
            offsets[f] = size
            last = f
            nfiles += 1
            continue
        want = min(size - start, WATCH_MAX_BYTES - used, WATCH_FILE_CAP)
        try:
            with open(f, "rb") as fh:
                fh.seek(start)
                raw = fh.read(want)
        except Exception:
            continue
        chunk = raw.decode("utf-8", "replace")
        offsets[f] = start + len(raw)
        used += len(raw)
        nfiles += 1
        last = f
        for name, mt in matchers:
            m = mt.search(chunk)
            if not m:
                continue
            b = open_break(
                name,
                "seen in %s: ...%s..."
                % (
                    os.path.basename(f),
                    chunk[max(0, m[0] - 80) : m[1] + 80].replace("\n", " "),
                ),
                by="watch",
            )
            if b:
                opened.append(b["id"])
    os.makedirs(DIR, exist_ok=True)
    json.dump(dict(files=offsets, cursor=last), open(path, "w"))
    return opened


def cmd_watch(a):
    while True:
        o = watch_once()
        if o:
            print("break(s) opened: %s" % ", ".join(o))
        if a.once:
            sys.exit(1 if o else 0)
        time.sleep(a.interval)


# ---------------------------------------------------------------- convergence: desired outcomes, deadlines, steering
# convergence.json in DIR: {"steer": true, "targets": [{"id","description","check":"cmd exits 0 when achieved","deadline_min":120}]}
# Open protocol breaks are targets too (deadline_min per protocol, default 30). Each tick: measure every target; unmet ones start a clock.
# Everyone is told (CONVERGENCE.md, notification, and an injected brief on hooked harnesses' tool calls). Past the deadline the alarm is
# maximal and, with steer on, every agent NOT registered to an overdue target is frozen: the fleet is forced onto the outcome.
CONV_STATE = "convergence_state.json"


def conv_cfg():
    c = dict(steer=True, targets=[], break_deadline_min=30)
    try:
        c.update(json.load(open(os.path.join(DIR, "convergence.json"))))
    except Exception:
        pass
    return c


def conv_tick():
    c = conv_cfg()
    P = load_protocols()
    try:
        st = json.load(open(os.path.join(DIR, CONV_STATE)))
    except Exception:
        st = {}
    t0 = time.time()
    gaps = []
    for t in c["targets"]:
        r = run_probes([t["check"]])
        rec = st.setdefault(t["id"], {})
        if all_ok(r):
            rec.pop("first_seen", None)
            rec["achieved"] = now()
            continue
        fs = rec.setdefault("first_seen", t0)
        due = fs + 60 * t.get("deadline_min", 120)
        gaps.append(
            dict(
                id=t["id"],
                description=t["description"],
                due=due,
                left_s=int(due - t0),
                overdue=t0 > due,
                kind="target",
                evidence=r[0]["out"].strip()[-120:],
            )
        )
    for b in breaks("OPEN"):
        opened = (
            time.mktime(time.strptime(b["opened_at"], "%Y-%m-%dT%H:%M:%SZ"))
            - time.timezone
        )
        due = opened + 60 * P.get(b["protocol"], {}).get(
            "deadline_min", c["break_deadline_min"]
        )
        gaps.append(
            dict(
                id=b["id"],
                description="Restore %s: %s"
                % (b["protocol"], (b.get("required_action") or "")[:100]),
                due=due,
                left_s=int(due - t0),
                overdue=t0 > due,
                kind="break",
                protocol=b["protocol"],
                evidence=b["error"][:120],
            )
        )
    json.dump(st, open(os.path.join(DIR, CONV_STATE), "w"), indent=1)
    return gaps


def conv_text(gaps):
    if not gaps:
        return "CONVERGENCE: every target met. Nothing is overdue.\n"
    L = [
        "CONVERGENCE ALARM - the fleet is NOT aligned with the desired outcome. Every agent: work on these, in this order, or stop.",
        "",
    ]
    for g in sorted(gaps, key=lambda x: x["left_s"]):
        L.append(
            "- [%s] %s | %s | evidence: %s"
            % (
                "OVERDUE %dm" % (-g["left_s"] // 60)
                if g["overdue"]
                else "due in %dm" % (g["left_s"] // 60),
                g["id"],
                g["description"],
                g["evidence"],
            )
        )
    L.append(
        "\nWhen a deadline passes, every agent not registered to an overdue target is FROZEN. Do not note it and proceed. Fix the cause and prove it."
    )
    return "\n".join(L) + "\n"


def conv_enforce(gaps):
    """Broadcast + steer. Returns number of processes frozen."""
    os.makedirs(DIR, exist_ok=True)
    open(os.path.join(DIR, "CONVERGENCE.md"), "w").write(conv_text(gaps))
    if not gaps:
        return 0
    over = [g for g in gaps if g["overdue"]]
    worst = min(gaps, key=lambda g: g["left_s"])
    notify(
        "%s: %s (%s)"
        % (
            "OVERDUE" if over else "converging",
            worst["description"][:90],
            "overdue" if worst["overdue"] else "%dm left" % (worst["left_s"] // 60),
        ),
        5 if over else 2,
    )
    if not (over and conv_cfg()["steer"]):
        return 0
    try:
        tg = json.load(open(os.path.join(DIR, "agents.targets.json")))
    except Exception:
        tg = {}
    overdue_ids = {g["id"] for g in over} | {
        g.get("protocol") for g in over if g.get("protocol")
    }
    fs = frozen_state()
    n = 0
    for pid, cmd in agent_pids().items():
        if tg.get(str(pid)) in overdue_ids or str(pid) in fs:
            continue
        try:
            os.kill(pid, signal.SIGSTOP)
            fs[str(pid)] = dict(
                cmd=cmd[:160], ts=now(), why="unaligned with overdue target"
            )
            n += 1
        except Exception:
            pass
    json.dump(fs, open(os.path.join(DIR, "frozen.json"), "w"), indent=1)
    if n:
        log(dict(event="steer_freeze", n=n))
    return n


def conv_inject(d):
    """Text to put in front of an agent on a hooked harness, at most every 10 minutes per goal (always while overdue)."""
    p = os.path.join(DIR, "CONVERGENCE.md")
    try:
        if time.time() - os.path.getmtime(p) > 600:
            return None  # stale alarm file is not evidence
        txt = open(p).read()
    except Exception:
        return None
    if txt.startswith("CONVERGENCE: every"):
        return None
    os.makedirs(os.path.join(DIR, "inject"), exist_ok=True)
    ip = os.path.join(DIR, "inject", gkey(d) + ".ts")
    gap = time.time() - (os.path.getmtime(ip) if os.path.exists(ip) else 0)
    if gap < 600 and "OVERDUE" not in txt:
        return None
    if gap < 120:
        return None
    open(ip, "w").write("x")
    return txt


def cmd_converge(a):
    if a.what == "status":
        print(conv_text(conv_tick()))
    elif a.what == "brief":
        print(
            open(os.path.join(DIR, "CONVERGENCE.md")).read()
            if os.path.exists(os.path.join(DIR, "CONVERGENCE.md"))
            else "no brief yet: run converge tick"
        )
    else:
        g = conv_tick()
        print("frozen %d" % conv_enforce(g))
        sys.exit(1 if g else 0)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="c", required=True)
    s = sp.add_parser("probe-http")
    s.add_argument("url")
    s.set_defaults(f=cmd_probe_http)
    s = sp.add_parser("report")
    s.add_argument("--protocol", required=True)
    s.add_argument("--error", default="")
    s.add_argument("--by", default="cli")
    s.set_defaults(f=cmd_report)
    s = sp.add_parser("status")
    s.set_defaults(f=cmd_status)
    s = sp.add_parser("guard")
    s.set_defaults(f=cmd_guard)
    s = sp.add_parser("regress")
    s.set_defaults(f=cmd_regress)
    s = sp.add_parser("alarm")
    s.add_argument("--once", action="store_true")
    s.add_argument("--interval", type=int, default=60)
    s.add_argument("--regress-every", type=int, default=5)
    s.set_defaults(f=cmd_alarm)
    s = sp.add_parser("prove")
    s.add_argument("--id", required=True)
    s.add_argument("--cause", default="")
    s.add_argument("--evidence", default="")
    s.add_argument("--guard-cmd", default="")
    s.set_defaults(f=cmd_prove)
    s = sp.add_parser("waive")
    s.add_argument("--id", required=True)
    s.add_argument("--by", required=True)
    s.add_argument("--reason", required=True)
    s.set_defaults(f=cmd_waive)
    s = sp.add_parser("unlock")
    s.add_argument("--goal")
    s.add_argument("--kind", required=True, choices=["plan", "oracle"])
    s.add_argument("--artifact", default="")
    s.add_argument("--cmd", default="")
    s.add_argument("--why", default="")
    s.set_defaults(f=cmd_unlock)
    s = sp.add_parser("budget-check")
    s.add_argument("--goal")
    s.set_defaults(f=cmd_budget_check)
    s = sp.add_parser("governance")
    s.add_argument("--goal")
    s.set_defaults(f=cmd_governance)
    s = sp.add_parser("freeze")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(f=cmd_freeze)
    sp.add_parser("thaw").set_defaults(f=cmd_thaw)
    sp.add_parser("agents").set_defaults(f=cmd_agents)
    s = sp.add_parser("converge")
    s.add_argument("what", choices=["status", "brief", "tick"])
    s.set_defaults(f=cmd_converge)
    s = sp.add_parser("watch")
    s.add_argument("--once", action="store_true")
    s.add_argument("--interval", type=int, default=30)
    s.set_defaults(f=cmd_watch)
    s = sp.add_parser("run")
    s.add_argument("--repair", action="store_true")
    s.add_argument("--target")
    s.add_argument("cmd", nargs=argparse.REMAINDER)
    s.set_defaults(f=cmd_run)
    s = sp.add_parser("hook")
    s.add_argument("phase", choices=["pre", "post"])
    s.add_argument("--format", default="claude", choices=["claude", "json", "cline"])
    s.set_defaults(f=cmd_hook)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
