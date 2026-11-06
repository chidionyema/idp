import importlib.util
import io
import socket
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "platform" / "estate" / "memory" / "sandbox_bridge.py"
DOOR = ROOT / "platform" / "estate" / "bin" / "estate-execute"


def load_bridge():
    spec = importlib.util.spec_from_file_location("sandbox_bridge_under_test", BRIDGE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def socket_path():
    path = Path(tempfile.mkdtemp()) / "executor.sock"
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(path))
    return path, sock


def sandbox_env(session="session-1", **extra):
    env = {
        "CODEX_SANDBOX": "seatbelt",
        "CODEX_SESSION_ID": session,
    }
    env.update(extra)
    return env


def test_only_a_sandbox_with_a_socket_crosses_the_door():
    mod = load_bridge()
    path, sock = socket_path()
    try:
        assert mod.should_forward(sandbox_env(), path)
        assert not mod.should_forward({"CODEX_SANDBOX": "none"}, path)
        assert not mod.should_forward(sandbox_env(ESTATE_HOST_EXECUTE="1"), path)
        assert not mod.should_forward(sandbox_env(), path.with_name("missing.sock"))
    finally:
        sock.close()


def test_forward_relays_output_and_exact_exit_without_a_retry_loop():
    mod = load_bridge()
    path, sock = socket_path()
    calls = []
    out, err = io.StringIO(), io.StringIO()

    def call(payload, door, timeout):
        calls.append((payload, door, timeout))
        if payload["verb"] == "execute":
            return {"ok": True, "job_id": "job-7", "ceiling_sec": 9}
        return {
            "ok": True,
            "result": {
                "found": True,
                "state": "finished",
                "exit_code": 7,
                "log": "intent output\n",
            },
        }

    try:
        status = mod.forward(
            DOOR,
            ["health", "scope=all"],
            cwd=ROOT,
            env=sandbox_env(),
            socket_path=path,
            ceiling_sec=9,
            call=call,
            stdout=out,
            stderr=err,
        )
    finally:
        sock.close()

    assert status == 7
    assert out.getvalue() == "intent output\n"
    assert err.getvalue() == ""
    assert [p["verb"] for p, _, _ in calls] == ["execute", "read"]
    command = calls[0][0]["command"]
    assert "ESTATE_HOST_EXECUTE=1" in command
    assert "--session session-1" in command
    assert "health scope=all" in command


def test_a_refusal_is_surfaced_once_and_never_becomes_polling():
    mod = load_bridge()
    path, sock = socket_path()
    calls = []
    err = io.StringIO()

    def call(payload, door, timeout):
        calls.append(payload)
        return {"ok": False, "error": "plan not declared"}

    try:
        status = mod.forward(
            DOOR,
            ["health"],
            cwd=ROOT,
            env=sandbox_env(),
            socket_path=path,
            call=call,
            stderr=err,
        )
    finally:
        sock.close()

    assert status == 3
    assert len(calls) == 1
    assert "plan not declared" in err.getvalue()


def test_missing_session_is_refused_before_the_door_is_asked():
    mod = load_bridge()
    path, sock = socket_path()
    calls = []
    err = io.StringIO()

    def call(payload, door, timeout):
        calls.append(payload)
        raise AssertionError("the door must not be asked without identity")

    try:
        status = mod.forward(
            DOOR,
            ["health"],
            cwd=ROOT,
            env={"CODEX_SANDBOX": "seatbelt"},
            socket_path=path,
            call=call,
            stderr=err,
        )
    finally:
        sock.close()

    assert status == 2
    assert calls == []
    assert "requires ESTATE_SESSION_ID or CODEX_SESSION_ID" in err.getvalue()


def test_the_executor_contains_the_bridge_at_its_process_boundary():
    text = DOOR.read_text()
    assert "_sandbox_bridge()" in text
    assert "ESTATE_HOST_EXECUTE" in text
    assert "readonly database" in text
