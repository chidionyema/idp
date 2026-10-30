"""The runtime sync must converge the laptop's estate onto main -- and say that it did.

Every test here is a falsifier: it names a way the sync could be lying, and fails when it
is. Measured on this laptop (2026-10-30): the sync inherited the founder's global git
config, which rewrites ssh GitHub URLs to https; it never restarted the executor daemon;
it never refreshed the installed pi extensions; and the launchd wrapper turned every
load-gate skip into exit 0, so launchd reported 83 green runs for a job that had not run
at all.
"""

import importlib.machinery
import importlib.util
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SYNC = REPO / "bin/estate-runtime-sync"
WRAPPER = REPO / "bin/load-gate-and-run"


def load_sync():
    """The sync is an extensionless script; a spec alone would have loader=None."""
    loader = importlib.machinery.SourceFileLoader("estate_runtime_sync", str(SYNC))
    spec = importlib.util.spec_from_loader("estate_runtime_sync", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def serve_once(sock_path: Path, reply: bytes) -> threading.Thread:
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock_path))
    srv.listen(1)

    def run():
        try:
            conn, _ = srv.accept()
            conn.recv(65536)
            conn.sendall(reply)
            conn.close()
        finally:
            srv.close()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


# --- the git calls are isolated from the founder's config ------------------------------


def test_the_syncs_git_calls_never_read_the_founders_global_config(monkeypatch):
    mod = load_sync()
    seen = {}

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(argv, **kw):
        seen.update(kw.get("env") or {})
        return Result()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    mod.git("rev-parse", "HEAD")
    assert seen.get("GIT_CONFIG_GLOBAL") == "/dev/null"
    assert seen.get("GIT_CONFIG_SYSTEM") == "/dev/null"
    assert seen.get("GIT_CONFIG_NOSYSTEM") == "1"


def test_the_remote_is_the_ssh_form_whatever_was_configured():
    mod = load_sync()
    assert (
        mod.normalise_remote("git@github.com:chidionyema/idp.git")
        == "ssh://git@github.com:443/chidionyema/idp.git"
    )
    assert (
        mod.normalise_remote("ssh://git@github.com/chidionyema/idp.git")
        == "ssh://git@github.com:443/chidionyema/idp.git"
    )
    assert mod.REMOTE == "ssh://git@github.com:443/chidionyema/idp.git"


def test_the_trees_origin_is_put_on_the_canonical_remote(monkeypatch):
    mod = load_sync()
    calls = []

    def fake_git(*args, check=True, tree=None):
        calls.append(args)
        if args[:2] == ("remote", "get-url"):
            return "https://github.com/chidionyema/idp.git"
        return ""

    monkeypatch.setattr(mod, "git", fake_git)
    note = mod.normalise_origin()
    assert ("remote", "set-url", "origin", mod.REMOTE) in calls
    assert note


def test_an_already_canonical_origin_is_left_alone(monkeypatch):
    mod = load_sync()
    calls = []

    def fake_git(*args, check=True, tree=None):
        calls.append(args)
        if args[:2] == ("remote", "get-url"):
            return mod.REMOTE
        return ""

    monkeypatch.setattr(mod, "git", fake_git)
    assert mod.normalise_origin() == ""
    assert ("remote", "set-url", "origin", mod.REMOTE) not in calls


# --- the executor is a service, and it is asked on its own socket ----------------------


def test_the_executor_is_one_of_the_services_the_sync_restarts():
    mod = load_sync()
    entry = [s for s in mod.SERVICES if s[0] == "ai.estate.executor"]
    assert entry, "the executor daemon is not in the sync's service set"
    assert entry[0][4] == "unix"
    assert entry[0][2].endswith("executor.sock")


def test_a_changed_executor_path_demands_a_restart():
    mod = load_sync()
    for path in (
        "mcp/plugins/estate_executor.py",
        "platform/executor/daemon.py",
        "platform/estate/memory/plan.py",
        "platform/estate/bin/estate-execute",
        "extensions/estate-capabilities/index.ts",
    ):
        assert "ai.estate.executor" in mod.services_for([path]), path
    assert "ai.estate.executor" not in mod.services_for(["docs/readme.md"])


def test_the_executor_probe_needs_a_parsed_ok_true():
    mod = load_sync()
    d = Path(tempfile.mkdtemp(dir="/tmp", prefix="exsock"))
    sock = d / "executor.sock"
    t = serve_once(sock, b'{"ok": true}\n')
    assert mod.socket_answers(sock, 10) is True
    t.join(10)


def test_the_sync_probes_the_socket_the_daemon_actually_serves(monkeypatch, tmp_path):
    """The daemon's own name for the override wins.

    The sync read ESTATE_EXECUTOR_SOCKET and the daemon read IDP_EXECUTOR_SOCKET. With the
    daemon's name set, the sync probed a socket nobody served, called a healthy executor
    dead, and could roll a good tree back on that lie.
    """
    one = str(tmp_path / "one.sock")
    two = str(tmp_path / "two.sock")
    monkeypatch.setenv("IDP_EXECUTOR_SOCKET", one)
    monkeypatch.setenv("ESTATE_EXECUTOR_SOCKET", two)
    mod = load_sync()
    assert str(mod.EXECUTOR_SOCKET) == one

    monkeypatch.delenv("IDP_EXECUTOR_SOCKET")
    mod = load_sync()
    assert str(mod.EXECUTOR_SOCKET) == two

    monkeypatch.delenv("ESTATE_EXECUTOR_SOCKET")
    mod = load_sync()
    assert str(mod.EXECUTOR_SOCKET) == str(mod.STATE / "executor.sock")


def _load_daemon():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "estate_executor_daemon", REPO / "platform/executor/daemon.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_daemon_accepts_the_estate_socket_name_too(monkeypatch, tmp_path):
    one = str(tmp_path / "one.sock")
    two = str(tmp_path / "two.sock")
    monkeypatch.setenv("IDP_EXECUTOR_SOCKET", one)
    monkeypatch.setenv("ESTATE_EXECUTOR_SOCKET", two)
    assert _load_daemon().SOCKET_PATH == one

    monkeypatch.delenv("IDP_EXECUTOR_SOCKET")
    assert _load_daemon().SOCKET_PATH == two

    monkeypatch.delenv("ESTATE_EXECUTOR_SOCKET")
    assert _load_daemon().SOCKET_PATH.endswith("/.estate/executor.sock")


# --- a service is restarted against the revision it last served, not against this run's diff


def test_a_tree_that_moved_in_an_earlier_run_still_demands_its_restart(monkeypatch):
    mod = load_sync()
    heads = {"ai.estate.executor": "aaaa1111"}

    def fake_git(*args, check=True, tree=None):
        if args[:2] == ("diff", "--name-only"):
            return "mcp/plugins/estate_executor.py\n"
        return ""

    monkeypatch.setattr(mod, "git", fake_git)
    # this run's diff is empty: the tree moved in an EARLIER run, and the daemon there is
    # still serving the bytes from before the move.
    due = mod.services_for([], False, heads, "bbbb2222")
    assert "ai.estate.executor" in due


def test_a_service_whose_files_did_not_change_is_not_restarted(monkeypatch):
    mod = load_sync()
    heads = {"ai.estate.executor": "aaaa1111"}

    def fake_git(*args, check=True, tree=None):
        if args[:2] == ("diff", "--name-only"):
            return "docs/readme.md\n"
        return ""

    monkeypatch.setattr(mod, "git", fake_git)
    assert mod.services_for([], False, heads, "bbbb2222") == []


def test_the_trees_reflog_says_which_revision_the_services_were_serving(monkeypatch):
    mod = load_sync()

    def fake_git(*args, check=True, tree=None):
        if args[:1] == ("reflog",):
            return (
                "bbbb2222 HEAD@{0}: checkout: moving from aaaa1111 to bbbb2222\n"
                "aaaa1111 HEAD@{1}: checkout: moving from 0000000 to aaaa1111\n"
            )
        return ""

    monkeypatch.setattr(mod, "git", fake_git)
    assert mod.tree_last_move() == "aaaa1111"


def test_a_socket_that_does_not_say_ok_is_not_health():
    mod = load_sync()
    d = Path(tempfile.mkdtemp(dir="/tmp", prefix="exsock"))
    sock = d / "executor.sock"
    t = serve_once(sock, b'{"ok": false}\n')
    assert mod.socket_answers(sock, 3) is False
    t.join(10)


# --- the status says whether the estate converged --------------------------------------


def _status_env(monkeypatch, tmp_path):
    mod = load_sync()
    monkeypatch.setattr(mod, "STATUS", tmp_path / "status.json")
    monkeypatch.setattr(mod, "SKIP_LOG", tmp_path / "skips.log")
    return mod


def test_the_status_reports_a_tree_that_is_behind_main(monkeypatch, tmp_path):
    mod = _status_env(monkeypatch, tmp_path)
    mod.write_status(
        {
            "last_run": time.time(),
            "last_success": time.time(),
            "tree_head": "aaaaaaa",
            "origin_main": "bbbbbbb",
            "ok": True,
        }
    )
    state = mod.read_status()
    assert state["stale"] is True
    assert state["converged"] is False


def test_a_starved_job_is_visible(monkeypatch, tmp_path):
    mod = _status_env(monkeypatch, tmp_path)
    mod.write_status(
        {
            "last_run": time.time(),
            "last_success": time.time() - 3600,
            "tree_head": "aaaaaaa",
            "origin_main": "aaaaaaa",
            "ok": True,
        }
    )
    state = mod.read_status()
    assert state["starved"] is True
    assert state["converged"] is False


def test_a_skipped_run_is_counted_and_named(monkeypatch, tmp_path):
    mod = _status_env(monkeypatch, tmp_path)
    mod.write_status(
        {
            "last_run": time.time(),
            "last_success": time.time() - 60,
            "tree_head": "aaaaaaa",
            "origin_main": "aaaaaaa",
            "ok": True,
        }
    )
    ts = mod.iso(time.time() + 5)
    mod.SKIP_LOG.write_text(
        f"{ts} skip /Users/roseonyema/.estate/bin/estate-runtime-sync\n"
    )
    state = mod.read_status()
    assert state["skipped_since_last_success"] == 1
    assert "estate-runtime-sync" in state["last_skip"]
    assert state["converged"] is False


def test_a_healthy_run_reads_as_converged(monkeypatch, tmp_path):
    mod = _status_env(monkeypatch, tmp_path)
    mod.write_status(
        {
            "last_run": time.time(),
            "last_success": time.time(),
            "tree_head": "aaaaaaa",
            "origin_main": "aaaaaaa",
            "ok": True,
        }
    )
    state = mod.read_status()
    assert state["stale"] is False
    assert state["starved"] is False
    assert state["skipped_since_last_success"] == 0
    assert state["converged"] is True


# --- the installed pi extensions are converged too --------------------------------------


def test_the_installed_pi_extensions_are_refreshed_from_main(monkeypatch, tmp_path):
    mod = load_sync()
    tree = tmp_path / "tree"
    dest = tmp_path / "pi"
    (tree / "extensions/estate-capabilities").mkdir(parents=True)
    (tree / "extensions/estate-capabilities/index.ts").write_text("new bytes\n")
    (tree / "extensions/breaker").mkdir(parents=True)
    (dest / "estate-capabilities").mkdir(parents=True)
    (dest / "estate-capabilities/index.ts").write_text("old bytes\n")
    (dest / "pi-governance").mkdir(parents=True)
    (dest / "pi-governance/index.ts").write_text("the host's own\n")
    monkeypatch.setattr(mod, "TREE", tree)
    monkeypatch.setattr(mod, "PI_EXTENSIONS", dest)

    _notes, state = mod.sync_pi_extensions()

    assert (dest / "estate-capabilities/index.ts").read_text() == "new bytes\n"
    # an extension the host has and main does not is reported, never touched
    assert (dest / "pi-governance/index.ts").read_text() == "the host's own\n"
    # an extension main has and the host does not is reported, never installed
    assert not (dest / "breaker").exists()
    assert "breaker" in state["on_main_not_installed"]
    assert "pi-governance" in state["installed_not_on_main"]


def test_an_unchanged_pi_extension_is_not_rewritten(monkeypatch, tmp_path):
    mod = load_sync()
    tree = tmp_path / "tree"
    dest = tmp_path / "pi"
    (tree / "extensions/estate-capabilities").mkdir(parents=True)
    (tree / "extensions/estate-capabilities/index.ts").write_text("same\n")
    (dest / "estate-capabilities").mkdir(parents=True)
    target = dest / "estate-capabilities/index.ts"
    target.write_text("same\n")
    before = target.stat().st_mtime_ns
    monkeypatch.setattr(mod, "TREE", tree)
    monkeypatch.setattr(mod, "PI_EXTENSIONS", dest)

    _notes, state = mod.sync_pi_extensions()

    assert state["refreshed"] == []
    assert target.stat().st_mtime_ns == before


# --- the launchd wrapper: a skip is named, and a missing gate never disables the fleet --


def test_the_wrapper_records_the_command_it_refused(tmp_path):
    home = tmp_path / "home"
    (home / ".estate/bin").mkdir(parents=True)
    gate = home / ".estate/bin/load-gate"
    gate.write_text("#!/bin/sh\nexit 75\n")
    gate.chmod(0o755)
    marker = tmp_path / "ran"
    fake = tmp_path / "estate-runtime-sync"
    fake.write_text(f"#!/bin/sh\necho ran > {marker}\n")
    fake.chmod(0o755)

    r = subprocess.run(
        ["/bin/sh", str(WRAPPER), str(fake)],
        capture_output=True,
        text=True,
        env=dict(os.environ, HOME=str(home)),
    )

    assert r.returncode == 0
    assert not marker.exists(), "a skipped job ran the command anyway"
    skips = (home / ".estate/logs/load-gate-skips.log").read_text()
    assert "estate-runtime-sync" in skips
    assert "skip" in skips


def test_a_missing_gate_runs_the_command(tmp_path):
    home = tmp_path / "home"
    (home / ".estate/bin").mkdir(parents=True)
    marker = tmp_path / "ran"
    fake = tmp_path / "estate-runtime-sync"
    fake.write_text(f"#!/bin/sh\necho ran > {marker}\n")
    fake.chmod(0o755)

    r = subprocess.run(
        ["/bin/sh", str(WRAPPER), str(fake)],
        capture_output=True,
        text=True,
        env=dict(os.environ, HOME=str(home)),
    )

    assert r.returncode == 0
    assert marker.exists(), "a missing gate disabled the job"


def test_the_sync_stages_the_wrapper():
    mod = load_sync()
    assert "load-gate-and-run" in mod.LAUNCHERS
    assert "load-gate-and-run" in mod.launchers()


def test_the_wrapper_is_copied_into_the_estate_bin(monkeypatch, tmp_path):
    mod = load_sync()
    tree = tmp_path / "tree"
    state = tmp_path / "estate"
    (tree / "bin").mkdir(parents=True)
    (tree / "bin/load-gate-and-run").write_text("#!/bin/sh\n")
    for sub in ("intents", "libexec", "skills"):
        (tree / "platform/estate" / sub).mkdir(parents=True)
    monkeypatch.setattr(mod, "TREE", tree)
    monkeypatch.setattr(mod, "STATE", state)
    monkeypatch.setattr(mod, "LAUNCHERS", ["load-gate-and-run"])

    mod.stage()

    assert (state / "bin/load-gate-and-run").exists()


# --- the whole run: what it restarts, and what the status says --------------------------


def _stub_run(monkeypatch, tmp_path):
    """A runtime-sync run with everything but the decisions taken out."""
    mod = load_sync()
    monkeypatch.setattr(mod, "STATUS", tmp_path / "status.json")
    monkeypatch.setattr(mod, "SERVICES_STATE", tmp_path / "services.json")
    monkeypatch.setattr(mod, "SKIP_LOG", tmp_path / "skips.log")
    monkeypatch.setattr(mod, "LOG", tmp_path / "sync.log")
    monkeypatch.setattr(mod, "ensure_tree", lambda: None)
    monkeypatch.setattr(mod, "scrub_tree", lambda: "")
    monkeypatch.setattr(mod, "normalise_origin", lambda: "")
    monkeypatch.setattr(mod, "link_data", lambda: None)
    monkeypatch.setattr(mod, "stage", lambda: [])
    monkeypatch.setattr(mod, "sync_memory", lambda: [])
    monkeypatch.setattr(mod, "sync_artifact_policy", lambda: [])
    monkeypatch.setattr(mod, "sync_router", lambda: [])
    monkeypatch.setattr(mod, "sync_frontend", lambda _sha: [])
    monkeypatch.setattr(mod, "sync_pi_extensions", lambda: ([], {}))
    monkeypatch.setattr(mod, "alert", lambda _t: None)
    monkeypatch.setattr(mod, "socket_answers", lambda *a, **k: True)
    monkeypatch.setattr(mod, "service_answers", lambda *a, **k: True)
    return mod


def test_the_status_says_whether_the_executor_is_healthy_when_nothing_changed(
    monkeypatch, tmp_path
):
    mod = _stub_run(monkeypatch, tmp_path)
    kicks = []
    monkeypatch.setattr(mod, "kickstart", lambda label: kicks.append(label))

    def fake_git(*args, check=True, tree=None):
        if args[:2] == ("rev-parse", "HEAD"):
            return "bbbb2222"
        if args[:2] == ("rev-parse", "origin/main"):
            return "bbbb2222"
        if args[:1] == ("diff",):
            return ""
        if args[:1] == ("reflog",):
            return ""
        return ""

    monkeypatch.setattr(mod, "git", fake_git)

    assert mod.main() == 0
    status = json.loads((tmp_path / "status.json").read_text())
    # nothing changed, so nothing was restarted -- but the status still says whether the
    # door is up right now. A status that only knows about restarts cannot see a dead door.
    assert status["restarted"] == []
    assert status["services"]["ai.estate.executor"] is True


def test_a_daemon_left_stale_by_an_earlier_run_is_restarted_even_when_nothing_changed(
    monkeypatch, tmp_path
):
    mod = _stub_run(monkeypatch, tmp_path)
    kicks = []
    monkeypatch.setattr(mod, "kickstart", lambda label: kicks.append(label))

    def fake_git(*args, check=True, tree=None):
        if args[:2] == ("rev-parse", "HEAD"):
            return "bbbb2222"
        if args[:2] == ("rev-parse", "origin/main"):
            return "bbbb2222"
        if args[:2] == ("diff", "--name-only"):
            # the executor's own bytes changed between the revision it served and the tree
            return "mcp/plugins/estate_executor.py\n"
        if args[:1] == ("reflog",):
            return "bbbb2222 HEAD@{0}: checkout: moving from aaaa1111 to bbbb2222\n"
        return ""

    monkeypatch.setattr(mod, "git", fake_git)

    assert mod.main() == 0
    assert "ai.estate.executor" in kicks
    heads = json.loads((tmp_path / "services.json").read_text())
    assert heads["ai.estate.executor"] == "bbbb2222"
