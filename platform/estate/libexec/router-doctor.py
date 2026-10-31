#!/usr/bin/env python3
"""router-doctor -- diagnose the laptop router (bin/litellm-local, 127.0.0.1:4000) in seconds,
heal what a machine can heal, and print the one exact fix for what it cannot.

    router-doctor.py [heal|diagnose|watch]   heal is the default; diagnose never changes anything;
                                             watch = heal, silent when OK (launchd, every 120s)

Checks run in dependency order; each failing check gets one heal and a re-check. The first check
still failing after its heal stops the run with `FIX:` and the exact command -- later checks
would only report its consequences. Exit 0 = the router served a real Claude call; 1 = FIX printed.

Why each check exists (2026-09-28, >24h outage): LiteLLM dropped the Max OAuth bearer and every
claude-* call got "401 x-api-key header is required"; the stopgaps left behind were a token pinned
in ~/.claude/settings.json (revoked on the next rotation), a token file on disk and a byte
forwarder on :4001 that bypassed LiteLLM and the efficiency gateway. Each is a check below.

WHY (2026-10-31). This doctor was four wrong answers about the same machine, and each one acted:

  1. It asked the FRONT (:4000) whether the ROUTER was alive. The front answers 503 when the
     box is loaded -- measured: load 115.93 on 4 CPUs, the router at 0.1-0.5% CPU answering
     /health/liveliness in milliseconds, and the front refusing every caller in ~1 ms. The
     doctor read the front's refusal as a dead router and restarted the slot: 121 restarts in
     a day, each cutting every live session. The slot is now asked directly, and a slot that
     is LISTENING is never restarted.
  2. It compared the estate's declared lanes with the STAGED runtime config
     (~/.estate/litellm-local/config.runtime.yaml, 9 lanes from September) while the router
     ran ~/.estate/router-state/config.runtime.yaml (29 lanes from October). It read a
     September shadow as truth, decided 21 lanes were dropped, and reinstalled the router
     every 120 s tick. The truth is the LIVE config, and the render publishes a manifest that
     says exactly what is served and why anything was refused.
  3. It read the Keychain service "Claude Code-credentials" and the settings file
     ~/.claude/settings.json. This machine runs Claude Code with CLAUDE_CONFIG_DIR=
     /Users/roseonyema/.estate/harness/cc, so the live service is
     "Claude Code-credentials-9e3a8f0a" (= sha256(config_dir)[:8]) and the live settings file
     is <config_dir>/settings.json. The doctor read a service and a file that do not exist,
     and reported "no Claude Code login".
  4. It had no actuator budget. A failed check healed, healed again, and healed again, every
     120 s, forever. Now: at most ONE destructive heal per 15 minutes, persisted before the
     action, and after that the doctor escalates (ESCALATED_NO_OP) instead of acting.

Every path, the Keychain service and the active slot now come from ONE immutable reading of
this machine (estate_core.EstateContext), so a machine that moves makes the doctor move with
it instead of silently disagreeing with it.
"""

import importlib.util
import json
import os
import pathlib
import re
import shutil
import socket
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:
    from estate_core import EstateContext
except ImportError:  # pragma: no cover - a staged copy that lost its neighbour
    _spec = importlib.util.spec_from_file_location(
        "estate_core", _HERE / "estate_core.py"
    )
    _module = importlib.util.module_from_spec(_spec)
    sys.modules["estate_core"] = _module
    _spec.loader.exec_module(_module)
    EstateContext = _module.EstateContext

CTX = EstateContext.from_env()

HOME = CTX.home
PORT = CTX.front_port
BASE = CTX.front_base()
LABEL = "com.estate.litellm-local"
FRONT_LABEL = "com.estate.litellm-front"
# Since 2026-10-02 :4000 is the front (platform/llm/front.py) and the router runs in slot 4001
# or 4002, named here; deploys switch slots with no gap. No file: the single router on :4000.
ACTIVE = CTX.active_file
STAGE = CTX.stage
LOG = CTX.log_path
SETTINGS = CTX.claude_settings
ALERTS = CTX.alerts_path
# The config the RUNNING router reads, and the typed truth the render published about it.
RUNTIME_CONFIG = CTX.runtime_config
MANIFEST = CTX.manifest_path
# The actuator budget: one destructive heal per window, then escalation.
HEAL_STATE = CTX.heal_state_path
# The marker of the OAuth-forwarding patch in anthropic_beta_passthrough.py (PR #4789).
OAUTH_PATCH = "_pre.clean_headers = clean_headers"
# Install sources, most trusted first: the main runtime clone, then the shared checkout.
SOURCES = [HOME / ".estate/runtime/idp", HOME / "Documents/code/idp"]
PROBE_MODEL = "claude-haiku-4-5"
# Founder, 2026-09-28: the Claude Code model is opusplan (Opus plans, Sonnet executes) and "must
# never be changed again". A /model switch or a hand edit is reverted within one watch tick.
REQUIRED_MODEL = "opusplan"
# One destructive heal per this many seconds. After that the doctor ESCALATES: it reports the
# exact fix and changes nothing. (2026-10-31: 121 restarts of a healthy router in one day.)
HEAL_BUDGET_SEC = 900
# The heals that change the machine. A heal that only refreshes a credential is not one of
# them: it costs a model call, not a session.
DESTRUCTIVE_HEALS = frozenset(
    (
        "launchd",
        "liveliness",
        "front",
        "oauth-patch",
        "lanes",
        "settings",
        "bypass",
    )
)

MODE = (sys.argv[1] if len(sys.argv) > 1 else "heal").lower()
HEAL = MODE not in ("diagnose", "false", "0", "no")
WATCH = MODE == "watch"
LAST = CTX.last_state_path  # the latest run, overwritten: bounded by design
T0 = time.time()
OUT = []


class Fix(Exception):
    """A failure no heal can clear; the message is the exact fix."""


def say(tag, name, detail=""):
    line = "%-15s %-18s %s" % (tag, name, detail)
    OUT.append(line)
    if not WATCH:
        print(line, flush=True)


def alert(level, msg):
    try:
        ALERTS.parent.mkdir(parents=True, exist_ok=True)
        with ALERTS.open("a") as f:
            f.write(
                json.dumps(
                    {
                        "ts": time.time(),
                        "source": "router-doctor",
                        "level": level,
                        "msg": msg,
                    }
                )
                + "\n"
            )
    except OSError:
        pass


def sh(argv, timeout=60, **kw):
    """Run a fixed argv, bounded. Never a shell."""
    return CTX.run(argv, timeout=timeout, **kw)


def http(path, body=None, headers=None, timeout=5, base=None):
    """One bounded HTTP call. (code, body). 0 means the call itself failed.

    `base` is one of this machine's own bases (the front or a router slot), never a
    caller-supplied URL.
    """
    return CTX.http(path, base=base, body=body, headers=headers, timeout=timeout)


def uid():
    return os.getuid()


# ---- the slots -------------------------------------------------------------------------------


def active_slot():
    """The slot the front is sending connections to, or the default slot.

    Read through the context so there is ONE reading of the active file: the front, the
    doctor and the tests must not disagree about which slot is serving.
    """
    return CTX.port_of(ACTIVE) or CTX.default_slot()


def slot_base(port=None):
    """The base URL of the router slot that is serving."""
    return CTX.slot_base(port if port is not None else active_slot())


def slot_label(port=None):
    """The launchd label of the router slot."""
    return "%s-%d" % (LABEL, int(port if port is not None else active_slot()))


# ---- the actuator budget ----------------------------------------------------------------------


def heal_budget_state():
    return CTX.read_json(HEAL_STATE, {}) or {}


def heal_budget_left():
    """How long until another destructive heal is allowed."""
    last = heal_budget_state().get("last") or {}
    at = float(last.get("at") or 0)
    return HEAL_BUDGET_SEC - (time.time() - at)


def spend_heal_budget(name):
    """Record the intent to act, BEFORE acting.

    Persisted first, so a doctor that dies mid-heal cannot be mistaken for one that has not
    healed yet: the next tick sees the budget spent and escalates instead of acting again.
    """
    state = heal_budget_state()
    state["last"] = {"at": time.time(), "name": name}
    CTX.write_json(HEAL_STATE, state)


# ---- the checks --------------------------------------------------------------------------------


def install_source():
    """The first checkout whose passthrough module carries the OAuth patch."""
    for src in SOURCES:
        mod = src / "platform/llm/anthropic_beta_passthrough.py"
        if (
            (src / "bin/litellm-local").exists()
            and mod.exists()
            and OAUTH_PATCH in mod.read_text()
        ):
            return src
    raise Fix(
        "no checkout carries the Max OAuth forwarding patch -- merge "
        "https://github.com/chidionyema/idp/pull/4789, then rerun this intent"
    )


def reinstall():
    src = install_source()
    rc, out = sh([str(src / "bin/litellm-local"), "install"], timeout=180)
    return "install from %s rc=%d: %s" % (src, rc, out.splitlines()[-1] if out else "")


def wait_live(secs=45):
    """Wait for the SLOT that is serving to answer. The front is not the router."""
    end = time.time() + secs
    while time.time() < end:
        if http("/health/liveliness", timeout=2, base=slot_base())[0] == 200:
            return True
        time.sleep(1)
    return False


def keychain_token():
    """The Max OAuth credential, from whichever service this machine actually uses.

    The service name is derived from CLAUDE_CONFIG_DIR (sha256(config_dir)[:8], measured), and
    the plain name stays as a fallback for the default ~/.claude directory. The credential is
    never printed.
    """
    for service in CTX.keychain_services:
        rc, out = sh(
            ["security", "find-generic-password", "-s", service, "-w"],
            timeout=10,
        )
        if rc != 0 or not out:
            continue
        try:
            payload = json.loads(out)
        except ValueError:
            continue
        oauth = payload.get("claudeAiOauth")
        if oauth:
            return oauth
    raise Fix(
        "no Claude Code login in the keychain (tried %s) -- run: claude  then  /login"
        % ", ".join(CTX.keychain_services)
    )


# ---- checks: each returns (ok, detail); heal_<name> returns what it did ------------------------


def router_labels():
    """The launchd agents that serve :4000: front + active slot, or the single router."""
    try:
        return [FRONT_LABEL, slot_label(int(ACTIVE.read_text().strip()))]
    except (OSError, ValueError):
        return [LABEL]


def check_launchd():
    states = []
    for label in router_labels():
        plist = HOME / ("Library/LaunchAgents/%s.plist" % label)
        if not plist.exists():
            return False, "no plist at %s" % plist
        rc, out = sh(["launchctl", "print", "gui/%d/%s" % (uid(), label)], timeout=10)
        if rc != 0:
            return False, "%s not loaded" % label
        state = re.search(r"\bstate = (\S+)", out)
        if not (state and state.group(1) == "running"):
            return False, "%s state=%s" % (label, state.group(1) if state else "?")
        states.append(label)
    return True, "running: %s" % ", ".join(states)


def heal_launchd():
    return reinstall()


def listening(port=None):
    """True when something accepts TCP on the port -- alive, however slow it answers."""
    try:
        socket.create_connection(
            ("127.0.0.1", int(port if port is not None else active_slot())), timeout=5
        ).close()
        return True
    except OSError:
        return False


def check_live():
    """Is the SLOT that is serving answering?

    The front is not the router. Measured 2026-10-31: the front was refusing every caller
    with a 503 in ~1 ms while the router answered /health/liveliness in milliseconds, and the
    doctor read that refusal as a dead router and restarted the slot 121 times in a day.
    """
    code, body = http("/health/liveliness", timeout=3, base=slot_base())
    if code == 200:
        return True, "HTTP 200 on slot %d" % active_slot()
    # A slow answer under laptop load is not a dead router: restarting it cuts every live
    # session (29 of 35 restarts on 2026-09-28 were this). Only a refused port is healed.
    if code == 0 and listening():
        return True, "slow (%s) but listening -- not restarted" % body[:40]
    return False, "HTTP %s %s" % (code, body[:80])


def heal_live():
    """Never restart a slot that is answering. That is the invariant that stops the loop."""
    port = active_slot()
    if listening():
        return "not restarted: slot %d is listening" % port
    sh(
        ["launchctl", "kickstart", "-k", "gui/%d/%s" % (uid(), slot_label(port))],
        timeout=15,
    )
    if wait_live():
        return "kickstarted"
    return reinstall()


def check_front():
    """The front's caller-facing path: the port every agent on this machine calls.

    The front and the slot are different machines' worth of behaviour: a front that answers
    503 while the slot is healthy is a front fault, and the fix is a front restart -- not a
    router swap, which would cut every live session.
    """
    code, body = http("/health/liveliness", timeout=3, base=BASE)
    if code == 200:
        return True, "HTTP 200 on the front"
    slot_ok, slot_detail = check_live()
    if slot_ok and code == 503:
        return (
            False,
            "the front refuses (HTTP 503) while the slot is healthy (%s)" % slot_detail,
        )
    return False, "HTTP %s %s" % (code, body[:80])


def heal_front():
    """Restart the front only. The router keeps serving the sessions it is serving."""
    sh(
        ["launchctl", "kickstart", "-k", "gui/%d/%s" % (uid(), FRONT_LABEL)],
        timeout=15,
    )
    return "front restarted (%s)" % FRONT_LABEL


def check_patch():
    mod = STAGE / "modules/anthropic_beta_passthrough.py"
    if not mod.exists():
        return False, "staged passthrough module missing"
    return OAUTH_PATCH in mod.read_text(), "Max OAuth forwarding patch staged"


def heal_patch():
    return reinstall()


def served_lanes(text):
    """The lanes a rendered config serves."""
    return set(re.findall(r"model_name:\s*(\S+)", text))


def dropped_lanes(source: str, runtime: str) -> list:
    """Lanes the source config declares that the rendered runtime config does not serve (#7352)."""
    want = re.findall(r"model_name:\s*(\S+)", source)
    have = set(re.findall(r"model_name:\s*(\S+)", runtime))
    return sorted({n for n in want if n not in have})


def check_lanes():
    """Are the lanes the estate declared actually served by the LIVE router config?

    The truth is ~/.estate/router-state/config.runtime.yaml -- the config the running router
    reads. The staged copy is a shadow (measured 2026-10-31: nine lanes from September against
    the router's twenty-nine), and reading the shadow as truth is what made the doctor
    reinstall the router every 120 s for a whole day.
    """
    if not RUNTIME_CONFIG.exists():
        return False, "no runtime config at %s" % RUNTIME_CONFIG
    text = RUNTIME_CONFIG.read_text()
    missing = [
        n
        for n in ("claude-*", "efficiency_gateway", "anthropic_beta_passthrough")
        if n not in text
    ]
    if missing:
        return False, "missing: %s" % (missing,)
    if not MANIFEST.exists():
        # No manifest yet (a router rendered before this change): fall back to the declared
        # source, and say so, rather than pretending the truth is known.
        src = STAGE / "config.yaml"
        dropped = dropped_lanes(src.read_text(), text) if src.exists() else []
        if dropped:
            return False, "dropped (key absent at render): %s" % (dropped,)
        return (
            True,
            "claude-* lane + efficiency gateway (no manifest: source comparison only)",
        )
    manifest = CTX.read_json(MANIFEST) or {}
    expected = set(manifest.get("expected_served") or [])
    live = served_lanes(text)
    absent = sorted(expected - live)
    if absent:
        return False, "declared served but absent from the live config: %s" % (absent,)
    return True, "%d lanes served, as the manifest declares" % len(live)


def heal_lanes():
    return reinstall()


def check_manifest():
    """The typed truth the render published: declared, served, refused, chained.

    Fail-closed on a refusal without a reason and on a fallback that points at a lane nobody
    serves: either one is a claim the runtime does not keep.
    """
    if not MANIFEST.exists():
        return False, "no manifest at %s (the render has not published one)" % MANIFEST
    manifest = CTX.read_json(MANIFEST)
    if not isinstance(manifest, dict):
        return False, "manifest unreadable at %s" % MANIFEST
    declared = set(manifest.get("declared") or [])
    expected = set(manifest.get("expected_served") or [])
    refused = manifest.get("refused_with_reason") or []
    fallbacks = manifest.get("fallbacks") or {}
    bad = []
    if not declared:
        bad.append("declared is empty")
    if not expected:
        bad.append("expected_served is empty")
    for entry in refused:
        if not isinstance(entry, dict):
            bad.append("refusal is not a record: %r" % (entry,))
            continue
        if not str(entry.get("reason") or "").strip():
            bad.append("refused lane %r has no reason" % entry.get("lane"))
    for source, chain in fallbacks.items():
        for target in chain or []:
            if target not in expected:
                bad.append("fallback %s -> %s is not served" % (source, target))
    # The other direction: a lane the live config serves that nobody declared. That is a
    # lane nobody knows the cost of, and it is how a shadow config becomes truth.
    if RUNTIME_CONFIG.exists():
        live = served_lanes(RUNTIME_CONFIG.read_text())
        extra = sorted(live - declared)
        if extra:
            bad.append("live but undeclared: %s" % (extra,))
    if bad:
        return False, "; ".join(bad)
    return True, "%d declared, %d served, %d refused with a reason" % (
        len(declared),
        len(expected),
        len(refused),
    )


def heal_manifest():
    """A manifest mismatch is REPORTED, never acted on.

    A reinstall is how the doctor spent a day restarting a healthy router (121 times): the
    truth it compared against was wrong, and the machine paid for the comparison. A mismatch
    between the published manifest and the live config is a visible failure with an exact
    fix; it is not an actuator command.
    """
    raise Fix(
        "the published manifest does not match the live runtime -- re-render with "
        "bin/litellm-local install (nothing was changed)"
    )


def check_settings():
    """The harness settings, read from the file this machine actually uses.

    The base URL is ADVISORY: the founder's decision (2026-10-29) is that Claude Code runs
    direct on his own Max login, so the doctor reports the routing and never rewrites it.
    A pinned token and a changed model are still failures.
    """
    try:
        d = json.loads(SETTINGS.read_text())
    except FileNotFoundError:
        return False, "no settings file at %s" % SETTINGS
    except (OSError, ValueError) as e:
        return False, "unreadable: %s" % e
    env = d.get("env", {})
    bad = []
    if d.get("model") != REQUIRED_MODEL:
        bad.append("model=%r, must be %s" % (d.get("model"), REQUIRED_MODEL))
    if "ANTHROPIC_MODEL" in env:
        bad.append("ANTHROPIC_MODEL=%r overrides the model" % env["ANTHROPIC_MODEL"])
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        if k in env:
            bad.append("%s pinned (dies on token rotation)" % k)
    advice = []
    base = env.get("ANTHROPIC_BASE_URL")
    if base != BASE:
        advice.append(
            "ANTHROPIC_BASE_URL=%r (advisory: Claude Code may route direct)" % base
        )
    detail = (
        "; ".join(bad)
        or "; ".join(advice)
        or "model=%s, no pinned token" % REQUIRED_MODEL
    )
    return not bad, detail


def heal_settings():
    """Rewrite the harness settings: destructive, backed up, and reported.

    The base URL is NOT restored: the doctor must not undo the founder's routing decision.
    """
    if not SETTINGS.exists():
        raise Fix("no settings file at %s -- restore it, then rerun" % SETTINGS)
    shutil.copy2(SETTINGS, str(SETTINGS) + ".bak-router-doctor")
    d = json.loads(SETTINGS.read_text())
    d["model"] = REQUIRED_MODEL
    env = d.setdefault("env", {})
    env.pop("ANTHROPIC_MODEL", None)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    CTX.write_text(SETTINGS, json.dumps(d, indent=2) + "\n")
    return "settings.json rewritten (backup kept); running sessions keep old env until restarted"


def check_bypass():
    """Nothing may sit beside the router: a token file or a side forwarder is a bypass."""
    found = []
    for f in ("oauth.token", "byte_forwarder.py"):
        if (STAGE / f).exists():
            found.append(str(STAGE / f))
    rc, out = sh(["pgrep", "-fl", "byte_forwarder"], timeout=5)
    if rc == 0 and out:
        found.append(
            "forwarder pid(s) " + " ".join(l.split()[0] for l in out.splitlines())
        )
    return not found, "; ".join(found) or "no token file, no side forwarder"


def heal_bypass():
    did = []
    for f in ("oauth.token", "byte_forwarder.py", "forwarder.log"):
        p = STAGE / f
        if p.exists():
            p.unlink()
            did.append("rm " + f)
    rc, out = sh(["pgrep", "-f", "byte_forwarder"], timeout=5)
    for pid in out.split() if rc == 0 else []:
        # A session still connected through it would lose its next call; leave it to exit on restart.
        _, conns = sh(
            ["lsof", "-nP", "-a", "-p", pid, "-iTCP", "-sTCP:ESTABLISHED"], timeout=5
        )
        if "ESTABLISHED" in conns:
            did.append("pid %s still serving a session (restart that session)" % pid)
        else:
            os.kill(int(pid), 15)
            did.append("killed idle forwarder %s" % pid)
    return ", ".join(did)


def check_token():
    oauth = keychain_token()
    left = (oauth.get("expiresAt", 0) / 1000.0) - time.time()
    return left > 60, "Max token %s" % (
        "valid %dm" % (left // 60) if left > 60 else "EXPIRED"
    )


def heal_token():
    # Claude Code refreshes its own token on use; one tiny call through the router makes it.
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
    }
    env["ANTHROPIC_BASE_URL"] = BASE
    rc, out = sh(
        ["claude", "-p", "reply ok", "--model", PROBE_MODEL],
        timeout=90,
        cwd=str(HOME),
        env=env,
    )
    return "claude -p rc=%d" % rc


# Known upstream answers -> (heal, exact fix). Order matters: first match wins.
E2E_CAUSES = [
    (
        "x-api-key header is required",
        heal_patch,
        "LiteLLM dropped the Max bearer again -- the OAuth patch is not active. "
        "Check `rg -n clean_headers %s/modules/anthropic_beta_passthrough.py` and the LiteLLM "
        "version (pinned 1.98.0); if LiteLLM moved, re-point the patch at its clean_headers"
        % STAGE,
    ),
    ("revoked", heal_token, "Max login revoked -- run: claude  then  /login"),
    (
        "expired",
        heal_token,
        "Max login expired and did not refresh -- run: claude  then  /login",
    ),
    (
        "spends a key the router holds",
        heal_lanes,
        "the claude-* lane gained an api_key in llm/config.base.yaml -- remove it (lane must stay "
        "keyless: callers bring their own Max token), bin/idp-vendor-render, rerun this intent",
    ),
    (
        "anthropic-beta",
        heal_patch,
        "a new Claude Code beta is being filtered -- the beta passthrough in "
        "anthropic_beta_passthrough.py is not active; reinstall from main",
    ),
    (
        "rate_limit",
        None,
        "Max plan rate limit at Anthropic -- nothing local to fix; wait for the window",
    ),
    (
        "overloaded",
        None,
        "Anthropic is overloaded -- see https://status.anthropic.com ; nothing local",
    ),
]


def check_e2e():
    """A real Claude call, through the slot that is serving."""
    token = keychain_token().get("accessToken", "")
    code, body = http(
        "/v1/messages",
        timeout=30,
        base=slot_base(),
        body={
            "model": PROBE_MODEL,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        },
        headers={
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
            "authorization": "Bearer " + token,
        },
    )
    check_e2e.last = body
    if code == 200 and '"type":"message"' in body.replace(" ", ""):
        return True, "real Claude call through the router: 200"
    return False, "HTTP %s %s" % (code, re.sub(r"\s+", " ", body)[:220])


def e2e_cause():
    body = getattr(check_e2e, "last", "")
    for needle, heal, fix in E2E_CAUSES:
        if needle in body:
            return heal, fix
    # No heal for an unknown failure: a restart every watch tick would cut every live session.
    return None, (
        "unrecognised failure -- read the last 40 lines of %s; the probe body is "
        "above. Add the new cause to E2E_CAUSES in router-doctor.py once fixed" % LOG
    )


def heal_e2e():
    heal, fix = e2e_cause()
    if heal is None:
        raise Fix(fix)
    return heal()


CHECKS = [
    (
        "launchd",
        check_launchd,
        heal_launchd,
        "launchd agent will not load -- run: ~/.estate/runtime/idp/bin/litellm-local install",
    ),
    (
        "liveliness",
        check_live,
        heal_live,
        "router will not come up -- run: tail -60 %s  (the crash is at the bottom)"
        % LOG,
    ),
    (
        "front",
        check_front,
        heal_front,
        "the front refuses while the router is healthy -- run: launchctl kickstart -k "
        "gui/%d/%s" % (uid(), FRONT_LABEL),
    ),
    (
        "oauth-patch",
        check_patch,
        heal_patch,
        "OAuth forwarding patch not staged -- merge PR #4789, then rerun this intent",
    ),
    (
        "lanes",
        check_lanes,
        heal_lanes,
        "claude-* lane or efficiency gateway missing from the rendered config -- "
        "bin/idp-vendor-render in a clean worktree of main, then rerun",
    ),
    (
        "manifest",
        check_manifest,
        heal_manifest,
        "the published manifest does not match the runtime -- re-render with "
        "bin/litellm-local install, then rerun (reported, never acted on)",
    ),
    (
        "settings",
        check_settings,
        heal_settings,
        "fix %s: model=%s, no ANTHROPIC_API_KEY" % (SETTINGS, REQUIRED_MODEL),
    ),
    (
        "bypass",
        check_bypass,
        heal_bypass,
        "restart the Claude Code sessions still on the side forwarder, then rerun",
    ),
    ("max-token", check_token, heal_token, "run: claude  then  /login"),
    ("e2e", check_e2e, heal_e2e, None),
]


def main():
    say("doctor", "mode=%s" % MODE, BASE)
    healed = []
    for name, check, heal, fix in CHECKS:
        t = time.time()
        try:
            ok, detail = check()
            if ok:
                say("ok", name, "%s (%.1fs)" % (detail, time.time() - t))
                continue
            say("FAIL", name, detail)
            if name == "e2e":
                fix = e2e_cause()[1]
            if not HEAL:
                if name == "bypass":  # a leftover beside the router, not a router fault
                    say("warn", name, fix)
                    continue
                raise Fix("heal mode clears this on its own; if it cannot: " + fix)
            if name in DESTRUCTIVE_HEALS:
                left = heal_budget_left()
                if left > 0:
                    say(
                        "ESCALATED_NO_OP",
                        name,
                        "a destructive heal ran %.0fs ago; the budget allows one per %ds. "
                        "The exact fix is below and nothing was changed."
                        % (
                            HEAL_BUDGET_SEC - left,
                            HEAL_BUDGET_SEC,
                        ),
                    )
                    raise Fix(
                        "escalated (no action taken): a destructive heal ran %.0fs ago and the "
                        "budget allows one per %ds. Fix it by hand: %s"
                        % (HEAL_BUDGET_SEC - left, HEAL_BUDGET_SEC, fix)
                    )
                spend_heal_budget(name)
            did = heal()
            ok, detail = check()
            if ok:
                say("HEALED", name, "%s -> %s" % (did, detail))
                healed.append(name)
                continue
            # a session still on the side forwarder is not a router fault
            if name == "bypass":
                say("warn", name, "%s -> %s" % (did, detail))
                continue
            raise Fix(fix)
        except Fix as f:
            say("FIX:", name, str(f))
            alert("error", "%s: %s" % (name, f))
            return finish("BROKEN", 1)
    for name in healed:
        alert("info", "self-healed: %s" % name)
    return finish("HEALED+OK" if healed else "OK", 0)


def finish(verdict, rc):
    say("doctor", verdict, "%.1fs" % (time.time() - T0))
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        LAST.write_text("%s\n%s\n" % (stamp, "\n".join(OUT)))
    except OSError:
        pass
    if WATCH and verdict != "OK":
        print(stamp + "\n" + "\n".join(OUT), flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
