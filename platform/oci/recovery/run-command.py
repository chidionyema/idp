#!/usr/bin/env python3
"""Transport a host script into OCI Run Command, inside the 4096-character limit.

WHY (2026-10-30, #7525). The recovery door -- .github/workflows/recovery-data.yml -- used to
inline the whole host script into one Run Command request. OCI refuses that:

    InvalidParameter: content.source.text size must be between 1 and 4096

platform/oci/recovery/host-repair.sh is 10231 bytes. gzip+base64 of it is 4749 bytes: still over
the limit. So the transport is chunked: the payload is gzip+base64 encoded, split into pieces
below the limit, and each piece is appended to /var/tmp/estate-payload.b64 by its own Run
Command. The commands are created and polled SEQUENTIALLY, because the chunks are order-
dependent: the payload file is truncated by the first chunk and appended by the rest.

The final Run Command decodes the payload, runs the script as root with `sudo -n bash`, writes
the script's whole output to /var/tmp/estate-report.txt, and prints two markers:

    exit=<rc>          the transported script's own exit code
    report_bytes=<n>   how long the report is

The instance agent truncates captured output near 1024 characters, so the report is fetched after
the fact in bounded slices, each slice its own small Run Command.

SECRETS. The helper prints command ids, states and exit codes. It never prints a secret: the
payload is a script, and the script is the thing that decides what to print.

EXIT. The helper exits with the transported script's exit code (0 healthy, 1 repaired but the
connector is still absent, 2 the host was unreadable), or 64 when the payload could not be
decoded on the host.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import io
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# OCI's hard limit on content.source.text. Measured: a 4097-character body is refused with
# "content.source.text size must be between 1 and 4096".
MAX_CONTENT = 4096

# The chunk payload itself. The command that carries it adds ~45 characters of shell around it,
# so 2400 keeps every request comfortably under MAX_CONTENT with room to spare.
DEFAULT_CHUNK_SIZE = 2400

# Where the host accumulates the payload and the report. /var/tmp is the only writable
# directory that survives on the recovery host for a non-login agent, and the payload is
# written mode 0700/0600 by the shell that creates it: it holds a repair script, not a
# secret, but it is still not world-readable.
PAYLOAD_PATH = "/var/tmp/estate-payload.b64"  # noqa: S108
PAYLOAD_BIN = "/var/tmp/estate-payload.bin"  # noqa: S108
SCRIPT_PATH = "/var/tmp/host-script.sh"  # noqa: S108
REPORT_PATH = "/var/tmp/estate-report.txt"  # noqa: S108

# The instance agent truncates captured output near 1024 characters; slices are read under that.
SLICE_BYTES = 900
MAX_SLICES = 24

EXIT_MARKER = re.compile(r"^exit=(\d+)$", re.MULTILINE)
REPORT_BYTES_MARKER = re.compile(r"^report_bytes=(\d+)$", re.MULTILINE)
MODE_RE = re.compile(r"^[a-z][a-z0-9-]*$")


class TransportError(RuntimeError):
    """A transport step failed in a way the caller must see."""


# ---------------------------------------------------------------- pure helpers


def encode_payload(script: bytes) -> str:
    """gzip + base64 the script into a single line of shell-safe ASCII.

    The gzip container is written with mtime=0 so the same script always encodes to the same
    bytes: the transport's own tests compare payloads byte for byte.
    """
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=9, mtime=0) as handle:
        handle.write(script)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def plan_chunks(payload: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[str]:
    """Split the payload into pieces, in order."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    return [payload[i : i + chunk_size] for i in range(0, len(payload), chunk_size)]


def chunk_command(chunk: str, first: bool) -> str:
    """The shell that writes one chunk. The first truncates; the rest append."""
    if not chunk.isascii():
        raise ValueError("chunk must be ascii")
    operator = ">" if first else ">>"
    return f"printf '%s' '{chunk}' {operator} {PAYLOAD_PATH}"


def final_command(mode: str) -> str:
    """The shell that decodes the payload, runs the script as root, and reports the exit code.

    It never fails itself: the transported script's exit code travels in the `exit=` marker, so a
    failing repair is reported, not swallowed.
    """
    if not MODE_RE.match(mode):
        raise ValueError(f"mode must be a simple name, got {mode!r}")
    return "\n".join(
        [
            "SUDO=$(command -v sudo 2>/dev/null || echo /usr/bin/sudo)",
            # base64 and gunzip are read through stdin, not through a file argument: BSD
            # base64 (macOS) refuses a positional file, GNU refuses nothing. Both spellings of
            # the decode flag are tried, so the same body runs on the Linux host and on a
            # laptop. A decode that cannot succeed reports exit=64 instead of dying silently.
            f"if ! base64 -d < {PAYLOAD_PATH} > {PAYLOAD_BIN} 2>/dev/null; then"
            f" if ! base64 -D < {PAYLOAD_PATH} > {PAYLOAD_BIN} 2>/dev/null; then echo 'exit=64'; exit 0; fi; fi",
            f"if ! gzip -dc < {PAYLOAD_BIN} > {SCRIPT_PATH} 2>/dev/null; then echo 'exit=64'; exit 0; fi",
            f"chmod 700 {SCRIPT_PATH}",
            f'"$SUDO" -n bash {SCRIPT_PATH} {mode} > {REPORT_PATH} 2>&1',
            "rc=$?",
            'echo "exit=$rc"',
            f"echo \"report_bytes=$(wc -c < {REPORT_PATH} | tr -d ' ')\"",
            "exit 0",
        ]
    )


SLICE_OPEN = "<<SLICE>>"
SLICE_CLOSE = "<<END>>"
SLICE_RE = re.compile(
    re.escape(SLICE_OPEN) + r"(.*?)" + re.escape(SLICE_CLOSE), re.DOTALL
)


def slice_command(offset: int, size: int = SLICE_BYTES) -> str:
    """The shell that reads one bounded slice of the report.

    The slice is wrapped in explicit markers: the instance agent adds its own trailing newline,
    so the exact bytes of the slice cannot be guessed from the captured text alone.
    """
    if offset == 0:
        body = f"head -c {size} {REPORT_PATH}"
    else:
        body = f"tail -c +{offset + 1} {REPORT_PATH} | head -c {size}"
    # The markers carry no newline of their own: the bytes between them are exactly the
    # bytes of the slice, so the report is reassembled byte for byte.
    return f"printf '{SLICE_OPEN}'; {body}; printf '{SLICE_CLOSE}'"


def parse_slice(text: str) -> str:
    """The exact bytes of one slice, or empty when the markers are missing."""
    match = SLICE_RE.search(text)
    return match.group(1) if match else ""


def reassemble(chunks: list[str]) -> str:
    """The payload the chunks carry, in order."""
    return "".join(chunks)


# ---------------------------------------------------------------- OCI plumbing


def _oci_binary() -> str:
    """The OCI CLI, resolved to an absolute path (the CLI is the only supported transport)."""
    found = shutil.which("oci")
    if not found:
        raise TransportError("the OCI CLI ('oci') is not on PATH")
    return found


def _oci(args: list[str], *, what: str) -> str:
    # The arguments are built here, never taken from a caller: this is a transport, not a
    # shell, and nothing in `args` is interpolated into a command line.
    proc = subprocess.run(  # noqa: S603
        [_oci_binary(), *args], capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise TransportError(
            f"{what} failed (exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()}"
        )
    return proc.stdout.strip()


def resolve_instance(compartment: str, display_name: str) -> str:
    out = _oci(
        [
            "compute",
            "instance",
            "list",
            "-c",
            compartment,
            "--display-name",
            display_name,
            "--lifecycle-state",
            "RUNNING",
            "--query",
            "data[0].id",
            "--raw-output",
        ],
        what="resolving the recovery instance",
    )
    if not out or out == "null":
        raise TransportError(
            f"no RUNNING instance named {display_name} in {compartment}"
        )
    return out


def create_command(
    compartment: str,
    instance_id: str,
    display_name: str,
    text: str,
    timeout_s: int,
) -> str:
    if len(text) > MAX_CONTENT:
        raise TransportError(
            f"refusing to send {len(text)} characters: OCI allows {MAX_CONTENT} per request"
        )
    content = json.dumps(
        {
            "source": {"sourceType": "TEXT", "text": text},
            "output": {"outputType": "TEXT"},
        }
    )
    return _oci(
        [
            "instance-agent",
            "command",
            "create",
            "-c",
            compartment,
            "--display-name",
            display_name,
            "--timeout-in-seconds",
            str(timeout_s),
            "--target",
            json.dumps({"instanceId": instance_id}),
            "--content",
            content,
            "--query",
            "data.id",
            "--raw-output",
        ],
        what="creating the Run Command",
    )


def wait_for_command(
    command_id: str, instance_id: str, poll_seconds: int, wait_timeout: int
) -> str:
    """Poll one command to a terminal state. Sequential by design: order is the protocol."""
    deadline = time.monotonic() + wait_timeout
    state = "PENDING"
    while True:
        out = _oci(
            [
                "instance-agent",
                "command-execution",
                "get",
                "--command-id",
                command_id,
                "--instance-id",
                instance_id,
                "--query",
                'data."lifecycle-state"',
                "--raw-output",
            ],
            what="polling the Run Command",
        )
        state = out or "PENDING"
        if state in {"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELED"}:
            return state
        if time.monotonic() > deadline:
            return "TIMED_OUT"
        time.sleep(poll_seconds)


def command_output(command_id: str, instance_id: str) -> str:
    return _oci(
        [
            "instance-agent",
            "command-execution",
            "get",
            "--command-id",
            command_id,
            "--instance-id",
            instance_id,
            "--query",
            "data.content.text",
            "--raw-output",
        ],
        what="reading the Run Command output",
    )


def say(line: str) -> None:
    print(line, flush=True)


# ---------------------------------------------------------------- the run


def transport(args: argparse.Namespace) -> int:
    script = Path(args.script).read_bytes()
    payload = encode_payload(script)
    chunks = plan_chunks(payload, args.chunk_size)
    say(
        f"ok      run-command  payload={len(payload)} chunk(s)={len(chunks)} script={len(script)}B"
    )

    instance_id = args.instance_id or resolve_instance(
        args.compartment, args.display_name
    )
    say(f"ok      run-command  instance={instance_id}")

    for index, chunk in enumerate(chunks):
        text = chunk_command(chunk, first=index == 0)
        command_id = create_command(
            args.compartment,
            instance_id,
            f"{args.display_name}-{args.run_id}-chunk{index}",
            text,
            args.timeout,
        )
        state = wait_for_command(
            command_id, instance_id, args.poll_seconds, args.wait_timeout
        )
        if state != "SUCCEEDED":
            raise TransportError(f"chunk {index} ended in state {state}")
        say(f"ok      run-command  chunk {index}/{len(chunks)} state={state}")

    command_id = create_command(
        args.compartment,
        instance_id,
        f"{args.display_name}-{args.run_id}-final",
        final_command(args.mode),
        args.timeout,
    )
    state = wait_for_command(
        command_id, instance_id, args.poll_seconds, args.wait_timeout
    )
    if state != "SUCCEEDED":
        raise TransportError(f"the final command ended in state {state}")
    final_output = command_output(command_id, instance_id)

    match = EXIT_MARKER.search(final_output)
    if not match:
        raise TransportError(f"the host printed no exit marker: {final_output[:200]!r}")
    exit_code = int(match.group(1))
    bytes_match = REPORT_BYTES_MARKER.search(final_output)
    report_bytes = int(bytes_match.group(1)) if bytes_match else 0
    say(f"ok      run-command  host exit={exit_code} report_bytes={report_bytes}")

    report = ""
    if report_bytes > 0:
        slices = min(MAX_SLICES, (report_bytes + SLICE_BYTES - 1) // SLICE_BYTES)
        for index in range(slices):
            slice_id = create_command(
                args.compartment,
                instance_id,
                f"{args.display_name}-{args.run_id}-slice{index}",
                slice_command(index * SLICE_BYTES),
                args.timeout,
            )
            slice_state = wait_for_command(
                slice_id, instance_id, args.poll_seconds, args.wait_timeout
            )
            if slice_state != "SUCCEEDED":
                raise TransportError(
                    f"report slice {index} ended in state {slice_state}"
                )
            captured = command_output(slice_id, instance_id)
            piece = parse_slice(captured)
            if not piece and captured.strip():
                raise TransportError(
                    f"report slice {index} came back without its markers: {captured[:120]!r}"
                )
            report += piece

    say("---- host report ----")
    say(report.rstrip("\n"))
    say("---- end host report ----")
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--script", required=True, help="the host script to transport")
    parser.add_argument(
        "--mode", required=True, help="the argument the host script takes"
    )
    parser.add_argument("--compartment", required=True, help="the OCI compartment")
    parser.add_argument(
        "--instance-id", default="", help="the instance, resolved when absent"
    )
    parser.add_argument("--display-name", default="estate-recovery")
    parser.add_argument("--run-id", default="local")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--poll-seconds", type=int, default=15)
    parser.add_argument("--timeout", type=int, default=6000, help="per-command timeout")
    parser.add_argument("--wait-timeout", type=int, default=3600)
    args = parser.parse_args(argv)

    try:
        return transport(args)
    except TransportError as exc:
        say(f"FAIL    run-command  {exc}")
        return 70


if __name__ == "__main__":
    sys.exit(main())
