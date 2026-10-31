#!/usr/bin/env python3
"""estate_core -- ONE reading of this machine, for every estate script that has to know it.

Measured 2026-10-31, in the laptop router's doctor: four hardcoded literals, four wrong
answers about the same machine.

  1. The Keychain service was the literal "Claude Code-credentials". The live service is
     "Claude Code-credentials-9e3a8f0a": Claude Code appends sha256(CLAUDE_CONFIG_DIR)[:8].
     The doctor read a service that does not exist and reported "no Claude Code login".
  2. The Claude settings path was the literal ~/.claude/settings.json. The live harness reads
     CLAUDE_CONFIG_DIR=/Users/roseonyema/.estate/harness/cc, so the doctor read a file that
     does not exist -- and its heal crashed on the missing file.
  3. The lane check compared the estate's declared lanes with the STAGED runtime config
     (~/.estate/litellm-local/config.runtime.yaml, Sep 29, 9 lanes) while the router runs
     ~/.estate/router-state/config.runtime.yaml (Oct 31, 29 lanes). The doctor compared the
     estate against a September shadow, decided 21 lanes were dropped, and reinstalled the
     router -- every 120 s tick, for the whole day.
  4. The live check asked the FRONT (:4000) whether the ROUTER was alive. The front answers
     503 when the box is loaded, and it was refusing every caller in ~1 ms at load 115.93
     while the router sat at 0.3% CPU answering /health/liveliness in milliseconds. The doctor
     read the front's refusal as a dead router and restarted the slot: 121 restarts.

The class is not "the doctor is wrong". The class is: a script that decides where things live
decides it again, in a literal, and a machine that changes its mind (a new CLAUDE_CONFIG_DIR,
a new state directory, a slot that moved) makes that script wrong while it still reports
"healthy" or "broken" with total confidence.

This module is the fix: one immutable context that resolves every path, the keychain service
and the active slot ONCE, from the environment and the estate's own state, and every caller
asks it instead of guessing.

Rules of this module:
  * Nothing here mutates the machine. A context is a READING of the machine, not a change to
    it; the doctor's heals stay in the doctor.
  * Nothing here reaches the network unless a caller explicitly asks for an HTTP call, and
    then only to a base URL the caller passes in.
  * Nothing here prints a secret. The keychain SERVICE NAME is derived, not its contents.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import pathlib
import subprocess
import types
import urllib.error
import urllib.request

__all__ = ["EstateContext", "derive_keychain_service"]

# The base name Claude Code uses for its OAuth credential in the login keychain.
KEYCHAIN_BASE = "Claude Code-credentials"


def derive_keychain_service(config_dir) -> str:
    """The Keychain service name Claude Code uses for this config directory.

    Measured 2026-10-31: with CLAUDE_CONFIG_DIR=/Users/roseonyema/.estate/harness/cc the live
    service is "Claude Code-credentials-9e3a8f0a", and
    sha256("/Users/roseonyema/.estate/harness/cc")[:8] == "9e3a8f0a". The default directory
    keeps the plain name as a fallback, so both are tried.
    """
    digest = hashlib.sha256(str(config_dir).encode("utf-8")).hexdigest()[:8]
    return "%s-%s" % (KEYCHAIN_BASE, digest)


@dataclasses.dataclass(frozen=True)
class EstateContext:
    """Where everything is, resolved once. Immutable: a second reading is a new context."""

    home: pathlib.Path
    estate_home: pathlib.Path
    router_state: pathlib.Path
    stage: pathlib.Path
    claude_config_dir: pathlib.Path
    front_port: int
    slot_ports: tuple
    env: types.MappingProxyType

    # -- construction -------------------------------------------------------------------------

    @classmethod
    def from_env(cls, env=None, home=None) -> "EstateContext":
        """Build the context from the environment (and, for tests, from overrides)."""
        source = dict(os.environ if env is None else env)
        resolved_home = pathlib.Path(
            home or source.get("HOME") or os.path.expanduser("~")
        )
        estate_home = pathlib.Path(
            source.get("ESTATE_HOME") or (resolved_home / ".estate")
        )
        router_state = pathlib.Path(
            source.get("ESTATE_ROUTER_STATE") or (estate_home / "router-state")
        )
        stage = pathlib.Path(
            source.get("ESTATE_ROUTER_STAGE") or (estate_home / "litellm-local")
        )
        claude_config_dir = pathlib.Path(
            source.get("CLAUDE_CONFIG_DIR")
            or cls._default_claude_dir(resolved_home, estate_home)
        )
        front_port = int(source.get("ESTATE_ROUTER_FRONT_PORT") or 4000)
        raw_slots = source.get("ESTATE_ROUTER_SLOTS") or "4001,4002"
        slot_ports = tuple(
            int(part) for part in str(raw_slots).split(",") if str(part).strip()
        )
        return cls(
            home=resolved_home,
            estate_home=estate_home,
            router_state=router_state,
            stage=stage,
            claude_config_dir=claude_config_dir,
            front_port=front_port,
            slot_ports=slot_ports,
            env=types.MappingProxyType(source),
        )

    @staticmethod
    def _default_claude_dir(home, estate_home):
        """Where Claude Code keeps its settings when the environment does not say.

        Measured 2026-10-31: the harness this estate runs reads
        CLAUDE_CONFIG_DIR=$HOME/.estate/harness/cc, and its settings.json points at the router.
        The doctor's launchd job inherits no CLAUDE_CONFIG_DIR, so without this rule it read
        $HOME/.claude/settings.json -- a file that is not the harness's -- and reported the
        harness as unconfigured while the estate was serving every caller.

        The rule: the estate's harness directory when it exists (that is the harness the estate
        runs), otherwise the historical ~/.claude.
        """
        harness = pathlib.Path(estate_home) / "harness" / "cc"
        if harness.is_dir():
            return harness
        return pathlib.Path(home) / ".claude"

    # -- the state directory ------------------------------------------------------------------

    @property
    def active_file(self) -> pathlib.Path:
        """The file the front reads for each new connection: the slot that is serving.

        ESTATE_ROUTER_ACTIVE wins over the state directory, because the front reads that
        variable itself (measured: the front and the doctor must resolve the SAME file, or the
        doctor judges a slot the front is not using).
        """
        override = self.env.get("ESTATE_ROUTER_ACTIVE")
        if override:
            return pathlib.Path(override)
        return self.router_state / "active"

    @property
    def runtime_config(self) -> pathlib.Path:
        """The config the RUNNING router reads. The staged copy is a shadow, never the truth."""
        return self.router_state / "config.runtime.yaml"

    @property
    def catalog_path(self) -> pathlib.Path:
        return self.router_state / "catalog.json"

    @property
    def lanes_path(self) -> pathlib.Path:
        return self.router_state / "lanes.json"

    @property
    def manifest_path(self) -> pathlib.Path:
        """The typed truth about the lanes: what was declared, served, refused, and chained."""
        return self.router_state / "manifest.json"

    @property
    def heal_state_path(self) -> pathlib.Path:
        """The destructive-heal budget: one restart per window, then escalation."""
        return self.router_state / "doctor-heals.json"

    @property
    def stage_config(self) -> pathlib.Path:
        return self.stage / "config.runtime.yaml"

    # -- the harness --------------------------------------------------------------------------

    @property
    def claude_settings(self) -> pathlib.Path:
        """The settings file of the harness that is actually configured to run."""
        return self.claude_config_dir / "settings.json"

    @property
    def keychain_service(self) -> str:
        return derive_keychain_service(self.claude_config_dir)

    @property
    def keychain_services(self) -> tuple:
        """The services to try, most likely first.

        A custom CLAUDE_CONFIG_DIR uses the suffixed name; the plain name is the historical
        one for the default ~/.claude directory and stays as a fallback for both.
        """
        plain = KEYCHAIN_BASE
        derived = self.keychain_service
        default_dir = self.home / ".claude"
        if self.claude_config_dir == default_dir:
            return (plain, derived)
        return (derived, plain)

    # -- the machine --------------------------------------------------------------------------

    @property
    def log_path(self) -> pathlib.Path:
        return self.home / "Library/Logs/litellm-local.log"

    @property
    def alerts_path(self) -> pathlib.Path:
        return self.estate_home / "alerts/inbox.jsonl"

    @property
    def last_state_path(self) -> pathlib.Path:
        return self.estate_home / "router-doctor.last"

    # -- the slots ----------------------------------------------------------------------------

    def port_of(self, active_file=None):
        """The slot recorded in an active file, or None when none is recorded.

        The file is a parameter so a caller that overrides the active file (a test, or a
        machine whose front reads a different one) still reads it through this one rule.
        """
        try:
            return int(
                pathlib.Path(active_file or self.active_file).read_text().strip()
            )
        except (OSError, ValueError):
            return None

    def recorded_port(self):
        """The slot the front is sending connections to, or None when none is recorded."""
        return self.port_of()

    def active_port(self):
        """The slot to judge: the recorded active one, or the default.

        The fallback matters: a machine whose active file was lost must still be judged
        against a real slot instead of against nothing.
        """
        return self.recorded_port() or self.default_slot()

    def default_slot(self):
        """The slot to judge when the active one is not recorded."""
        return self.slot_ports[-1] if self.slot_ports else None

    def slot_base(self, port) -> str:
        return "http://127.0.0.1:%d" % int(port)

    def front_base(self) -> str:
        return "http://127.0.0.1:%d" % int(self.front_port)

    # -- running things ------------------------------------------------------------------------

    def run(self, argv, timeout=60, cwd=None, env=None):
        """Run a fixed argv, bounded, and report (rc, output). Never uses a shell."""
        try:
            result = subprocess.run(  # noqa: S603 -- fixed argv built by the caller
                list(argv),
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                cwd=str(cwd) if cwd else None,
                env=dict(env) if env is not None else None,
            )
            return result.returncode, (result.stdout + result.stderr).strip()
        except subprocess.TimeoutExpired:
            return 124, "timeout after %ss" % timeout
        except OSError as exc:
            return 127, str(exc)

    def http(self, path, base=None, body=None, headers=None, timeout=5):
        """One bounded HTTP call. (code, body). 0 means the call itself failed."""
        url = (base or self.front_base()) + path
        request = urllib.request.Request(  # noqa: S310 -- a loopback base, never a caller's URL
            url,
            data=json.dumps(body).encode() if body else None,
            headers=headers or {},
            method="POST" if body else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return response.status, response.read().decode(errors="replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode(errors="replace")
        except Exception as exc:  # refused, timeout, reset
            return 0, str(exc)

    def read_json(self, path, default=None):
        """Read a JSON file, or return the default. Never raises on a malformed file."""
        try:
            return json.loads(pathlib.Path(path).read_text())
        except (OSError, ValueError):
            return default

    def write_json(self, path, payload) -> bool:
        """Write a JSON file atomically. Returns False when the write did not happen.

        Atomic because a reader must never see half a file: the doctor reads this state while
        the watcher writes it, and a torn read would look like a corrupt budget.
        """
        return self.write_text(
            path, json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )

    def write_text(self, path, text) -> bool:
        """Write a text file atomically: a temporary file, then os.replace."""
        target = pathlib.Path(path)
        tmp = target.with_name(target.name + ".tmp")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(text)
            os.replace(str(tmp), str(target))
            return True
        except OSError:
            try:
                tmp.unlink()
            except OSError:
                pass
            return False
