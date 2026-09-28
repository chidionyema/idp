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
"""

import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HOME = pathlib.Path.home()
PORT = 4000
BASE = "http://127.0.0.1:%d" % PORT
LABEL = "com.estate.litellm-local"
STAGE = HOME / ".estate/litellm-local"
PLIST = HOME / ("Library/LaunchAgents/%s.plist" % LABEL)
LOG = HOME / "Library/Logs/litellm-local.log"
SETTINGS = HOME / ".claude/settings.json"
ALERTS = HOME / ".estate/alerts/inbox.jsonl"
# The marker of the OAuth-forwarding patch in anthropic_beta_passthrough.py (PR #4789).
OAUTH_PATCH = "_pre.clean_headers = clean_headers"
# Install sources, most trusted first: the main runtime clone, then the shared checkout.
SOURCES = [HOME / ".estate/runtime/idp", HOME / "Documents/code/idp"]
PROBE_MODEL = "claude-haiku-4-5"
# Founder, 2026-09-28: the Claude Code model is opusplan (Opus plans, Sonnet executes) and "must
# never be changed again". A /model switch or a hand edit is reverted within one watch tick.
REQUIRED_MODEL = "opusplan"

MODE = (sys.argv[1] if len(sys.argv) > 1 else "heal").lower()
HEAL = MODE not in ("diagnose", "false", "0", "no")
WATCH = MODE == "watch"
LAST = (
    HOME / ".estate/router-doctor.last"
)  # the latest run, overwritten: bounded by design
T0 = time.time()
OUT = []


class Fix(Exception):
    """A failure no heal can clear; the message is the exact fix."""


def say(tag, name, detail=""):
    line = "%-7s %-18s %s" % (tag, name, detail)
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
    try:
        r = subprocess.run(  # noqa: S603 -- fixed argv built in this file, no shell
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            **kw,
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timeout after %ss" % timeout


def http(path, body=None, headers=None, timeout=5):
    # BASE is the fixed http://127.0.0.1 router, never a caller-supplied URL.
    req = urllib.request.Request(  # noqa: S310
        BASE + path,
        data=json.dumps(body).encode() if body else None,
        headers=headers or {},
        method="POST" if body else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:  # refused, timeout, reset
        return 0, str(e)


def uid():
    return os.getuid()


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
    end = time.time() + secs
    while time.time() < end:
        if http("/health/liveliness", timeout=2)[0] == 200:
            return True
        time.sleep(1)
    return False


def keychain_token():
    rc, out = sh(
        ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
        timeout=10,
    )
    if rc != 0 or not out:
        raise Fix("no Claude Code login in the keychain -- run: claude  then  /login")
    return json.loads(out).get("claudeAiOauth", {})


# ---- checks: each returns (ok, detail); heal_<name> returns what it did ------------------------


def check_launchd():
    if not PLIST.exists():
        return False, "no plist at %s" % PLIST
    rc, out = sh(["launchctl", "print", "gui/%d/%s" % (uid(), LABEL)], timeout=10)
    if rc != 0:
        return False, "agent not loaded"
    state = re.search(r"\bstate = (\S+)", out)
    return (state and state.group(1) == "running"), "state=%s" % (
        state.group(1) if state else "?"
    )


def heal_launchd():
    return reinstall()


def listening():
    """True when something accepts TCP on the router port -- alive, however slow it answers."""
    try:
        socket.create_connection(("127.0.0.1", PORT), timeout=5).close()
        return True
    except OSError:
        return False


def check_live():
    code, body = http("/health/liveliness", timeout=3)
    if code == 200:
        return True, "HTTP 200 "
    # A slow answer under laptop load is not a dead router: restarting it cuts every live
    # session (29 of 35 restarts on 2026-09-28 were this). Only a refused port is healed.
    if code == 0 and listening():
        return True, "slow (%s) but listening -- not restarted" % body[:40]
    return False, "HTTP %s %s" % (code, body[:80])


def heal_live():
    sh(["launchctl", "kickstart", "-k", "gui/%d/%s" % (uid(), LABEL)], timeout=15)
    if wait_live():
        return "kickstarted"
    return reinstall()


def check_patch():
    mod = STAGE / "modules/anthropic_beta_passthrough.py"
    if not mod.exists():
        return False, "staged passthrough module missing"
    return OAUTH_PATCH in mod.read_text(), "Max OAuth forwarding patch staged"


def heal_patch():
    return reinstall()


def check_lanes():
    cfg = STAGE / "config.runtime.yaml"
    if not cfg.exists():
        return False, "no config.runtime.yaml"
    text = cfg.read_text()
    missing = [
        n
        for n in ("claude-*", "efficiency_gateway", "anthropic_beta_passthrough")
        if n not in text
    ]
    return (
        not missing,
        "missing: %s" % missing if missing else "claude-* lane + efficiency gateway",
    )


def heal_lanes():
    return reinstall()


def check_settings():
    try:
        d = json.loads(SETTINGS.read_text())
    except (OSError, ValueError) as e:
        return False, "unreadable: %s" % e
    env = d.get("env", {})
    bad = []
    if d.get("model") != REQUIRED_MODEL:
        bad.append("model=%r, must be %s" % (d.get("model"), REQUIRED_MODEL))
    if "ANTHROPIC_MODEL" in env:
        bad.append("ANTHROPIC_MODEL=%r overrides the model" % env["ANTHROPIC_MODEL"])
    if env.get("ANTHROPIC_BASE_URL") != BASE:
        bad.append("ANTHROPIC_BASE_URL=%r" % env.get("ANTHROPIC_BASE_URL"))
    for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        if k in env:
            bad.append("%s pinned (dies on token rotation)" % k)
    return not bad, "; ".join(
        bad
    ) or "base_url=router, model=%s, no pinned token" % REQUIRED_MODEL


def heal_settings():
    # One backup, overwritten: a revert every tick must not pile up files.
    shutil.copy2(SETTINGS, str(SETTINGS) + ".bak-router-doctor")
    d = json.loads(SETTINGS.read_text())
    d["model"] = REQUIRED_MODEL
    env = d.setdefault("env", {})
    env.pop("ANTHROPIC_MODEL", None)
    env["ANTHROPIC_BASE_URL"] = BASE
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    SETTINGS.write_text(json.dumps(d, indent=2) + "\n")
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
    token = keychain_token().get("accessToken", "")
    code, body = http(
        "/v1/messages",
        timeout=30,
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
        "settings",
        check_settings,
        heal_settings,
        "fix ~/.claude/settings.json env: ANTHROPIC_BASE_URL=%s, no ANTHROPIC_API_KEY"
        % BASE,
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
