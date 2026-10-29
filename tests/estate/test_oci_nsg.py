"""The OCI door: what it signs, what it asks for, and what it refuses to print.

The door is the estate's only instrument for the cloud facts (the CLI cannot write NSG rules
and cannot run a command on an instance). A door that cannot fail is not a door, so these
tests exercise the signing convention and the request shapes against nothing but the local
machine: no network, no OCI account, no secret.
"""

import base64
import importlib.util
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "platform/estate/libexec/oci-nsg.py"


def _door():
    spec = importlib.util.spec_from_file_location("oci_nsg_door", SRC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _key(tmp_path):
    path = tmp_path / "signing.pem"
    subprocess.run(  # noqa: S603 - openssl, by absolute path
        ["/usr/bin/openssl", "genrsa", "-out", str(path), "2048"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return path


def test_the_door_signs_what_it_says_it_signs(tmp_path):
    """The signature must verify against the exact string that was signed."""
    mod = _door()
    key = _key(tmp_path)
    message = "date: Mon, 29 Oct 2026 12:00:00 GMT\n(request-target): get /x\nhost: h"
    signature = mod.sign(message, str(key))
    raw = base64.b64decode(signature)
    (tmp_path / "sig.bin").write_bytes(raw)
    (tmp_path / "msg.txt").write_text(message)
    subprocess.run(  # noqa: S603 - openssl, by absolute path
        [
            "/usr/bin/openssl",
            "rsa",
            "-in",
            str(key),
            "-pubout",
            "-out",
            str(tmp_path / "pub.pem"),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    proc = subprocess.run(  # noqa: S603 - openssl, by absolute path
        [
            "/usr/bin/openssl",
            "dgst",
            "-sha256",
            "-verify",
            str(tmp_path / "pub.pem"),
            "-signature",
            str(tmp_path / "sig.bin"),
            str(tmp_path / "msg.txt"),
        ],
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert b"Verified OK" in proc.stdout


def test_the_door_routes_each_service_to_its_own_host():
    """One path, one host: the container engine, the limits service and the identity
    service do not answer on the compute host."""
    mod = _door()
    facts = {"region": "uk-london-1"}
    assert mod.service_host("/20180222/clusters", facts) == (
        "containerengine.uk-london-1.oci.oraclecloud.com"
    )
    assert mod.service_host("/20181025/limitValues", facts) == (
        "limits.uk-london-1.oci.oraclecloud.com"
    )
    assert mod.service_host("/20160918/availabilityDomains", facts) == (
        "identity.uk-london-1.oci.oraclecloud.com"
    )
    assert mod.service_host("/20160918/instances", facts) == (
        "iaas.uk-london-1.oraclecloud.com"
    )


def test_run_command_asks_for_a_text_source_and_prints_the_answer(
    tmp_path, monkeypatch, capsys
):
    """The one door onto an instance that has no public IP: the agent's own plugin."""
    mod = _door()
    script = tmp_path / "probe.sh"
    script.write_text("echo hello\n")
    seen = []

    def fake_call(method, path, body, facts):
        seen.append((method, path, body))
        if method == "POST":
            return 202, {"id": "ocid1.command.oc1..x"}
        return 200, {
            "lifecycleState": "SUCCEEDED",
            "output": base64.b64encode(b"hello").decode(),
        }

    monkeypatch.setattr(mod, "call", fake_call)
    monkeypatch.setattr(mod, "profile", lambda *a, **k: {"region": "uk-london-1"})
    monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
    code = mod.main(
        [
            "oci-nsg.py",
            "run-command",
            "ocid1.instance.oc1.uk-london-1.anwgiljtpixfknico45gu2nuu5dlkqom46gxelgnx2mkcqw2qhexyrigu6rq",
            str(script),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    method, path, body = seen[0]
    assert method == "POST"
    assert path.endswith("/actions/runCommand")
    assert body["source"]["sourceType"] == "TEXT"
    assert body["source"]["text"] == "echo hello\n"
    assert "SUCCEEDED" in out
    assert "hello" in out
