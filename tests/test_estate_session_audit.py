"""The session audit counts the stalls, and counts only the stalls.

WHAT THIS GRADES. `bin/estate-session-audit` reads the Claude Code transcripts and reports how
many sessions gave up with "Request timed out", how long the client waited before it gave up,
and how long a healthy answer took. The numbers it reports are cited by the front's budget
(platform/llm/front.py) and by the audit in docs/audits/2026-10-30-claude-code-session-stalls/,
so a wrong count there is a wrong budget.

THE FALSIFIER IS HERE. The known-bad fixture is a transcript where the phrase appears inside a
longer message: somebody QUOTING the error. Counted as a stall, the estate's own notes would
become evidence of their own bug. The known-good fixture is a transcript where the assistant
entry IS exactly the error: it must be counted, with the client's patience measured from the
request that went out.
"""

import importlib.machinery
import importlib.util
import json
import pathlib

MODULE = pathlib.Path(__file__).resolve().parents[1] / "bin" / "estate-session-audit"


def load():
    loader = importlib.machinery.SourceFileLoader("estate_session_audit", str(MODULE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


AUDIT = load()


def entry(kind: str, at: str, text: str = "", sidechain: bool = False) -> dict:
    """One transcript entry, in the shape the Claude Code harness writes."""
    e = {"type": kind, "timestamp": at, "isSidechain": sidechain}
    if kind == "assistant":
        e["message"] = {
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
        }
    elif kind == "user":
        e["message"] = {"role": "user", "content": text}
    return e


def write(path: pathlib.Path, entries: list) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return path


def test_a_quote_of_the_error_is_not_a_stall(tmp_path):
    """The known-bad fixture: the phrase inside a longer message is a quotation."""
    path = write(
        tmp_path / "proj" / "s1.jsonl",
        [
            entry("user", "2026-10-28T23:00:00Z", "hello"),
            entry("api-request", "2026-10-28T23:00:01Z"),
            entry(
                "assistant",
                "2026-10-28T23:00:02Z",
                'The earlier run said "Request timed out" in the log, which is worth looking at.',
            ),
        ],
    )
    session = AUDIT.audit_transcript(path, tmp_path)
    assert session["timeout_events"] == []
    assert session["closed"] == "clean"
    assert session["answers"] == 1


def test_the_error_itself_is_a_stall_with_the_patience_measured(tmp_path):
    """The known-good fixture: the assistant entry IS the error."""
    path = write(
        tmp_path / "proj" / "s2.jsonl",
        [
            entry("user", "2026-10-28T23:00:00Z", "hello"),
            entry("api-request", "2026-10-28T23:00:01Z"),
            entry("assistant", "2026-10-28T23:06:01Z", "Request timed out"),
        ],
    )
    session = AUDIT.audit_transcript(path, tmp_path)
    assert len(session["timeout_events"]) == 1
    assert session["timeout_events"][0]["patience_s"] == 360.0
    assert session["closed"] == "stalled"


def test_trailing_whitespace_is_still_the_error(tmp_path):
    path = write(
        tmp_path / "proj" / "s3.jsonl",
        [
            entry("api-request", "2026-10-28T23:00:01Z"),
            entry("assistant", "2026-10-28T23:06:01Z", "Request timed out  \n"),
        ],
    )
    session = AUDIT.audit_transcript(path, tmp_path)
    assert len(session["timeout_events"]) == 1


def test_a_retried_answer_is_measured_from_the_first_request(tmp_path):
    """The caller waited for both attempts; the attempt is the one that worked."""
    path = write(
        tmp_path / "proj" / "s4.jsonl",
        [
            entry("api-request", "2026-10-28T23:00:01Z"),
            entry("api-request", "2026-10-28T23:00:31Z"),
            entry("assistant", "2026-10-28T23:00:40Z", "here is your answer"),
        ],
    )
    session = AUDIT.audit_transcript(path, tmp_path)
    answer = session["answer_latencies"][0]
    assert answer["attempt_s"] == 9.0  # the attempt that worked
    assert answer["caller_wait_s"] == 39.0  # what the caller waited
    assert answer["attempts"] == 2


def test_a_subagent_stall_is_not_the_founders_stall(tmp_path):
    """A sidechain is the CLI's own work, and the audit counts it apart."""
    path = write(
        tmp_path / "proj" / "s5.jsonl",
        [
            entry("api-request", "2026-10-28T23:00:01Z", sidechain=True),
            entry(
                "assistant", "2026-10-28T23:06:01Z", "Request timed out", sidechain=True
            ),
        ],
    )
    session = AUDIT.audit_transcript(path, tmp_path)
    assert session["kind"] == "subagent"
    assert len(session["timeout_events"]) == 1


def test_the_desktop_surface_is_counted_apart_from_the_cli(tmp_path):
    cli = write(
        tmp_path / "-Users-x-Documents-code-idp" / "c.jsonl",
        [entry("api-request", "2026-10-28T23:00:01Z")],
    )
    desktop = write(
        tmp_path
        / "-Users-x-Library-Application-Support-Claude-scratch-workspa"
        / "d.jsonl",
        [entry("api-request", "2026-10-28T23:00:01Z")],
    )
    assert AUDIT.audit_transcript(cli, tmp_path)["surface"] == "cli"
    assert AUDIT.audit_transcript(desktop, tmp_path)["surface"] == "desktop"


def test_the_summary_splits_the_founders_sessions_from_the_subagents(tmp_path):
    main = write(
        tmp_path / "proj" / "m.jsonl",
        [
            entry("api-request", "2026-10-28T23:00:01Z"),
            entry("assistant", "2026-10-28T23:06:01Z", "Request timed out"),
        ],
    )
    sub = write(
        tmp_path / "proj" / "u.jsonl",
        [
            entry("api-request", "2026-10-28T23:00:01Z", sidechain=True),
            entry(
                "assistant", "2026-10-28T23:06:01Z", "Request timed out", sidechain=True
            ),
        ],
    )
    sessions = [
        AUDIT.audit_transcript(main, tmp_path),
        AUDIT.audit_transcript(sub, tmp_path),
    ]
    summary = AUDIT.summarise(sessions)
    assert summary["timeout_events"] == 2
    assert summary["main_sessions_only"]["timeout_events"] == 1
    assert summary["main_sessions_only"]["sessions_with_timeouts"] == 1
    assert summary["client_patience_s"]["p50"] == 360.0


def test_the_audit_writes_a_machine_readable_artifact_and_its_digest(tmp_path):
    """The artifact is what the documentation cites, so it must exist and be stable."""
    write(
        tmp_path / "proj" / "s6.jsonl",
        [
            entry("api-request", "2026-10-28T23:00:01Z"),
            entry("assistant", "2026-10-28T23:00:09Z", "here is your answer"),
        ],
    )
    out = tmp_path / "audit"
    assert AUDIT.main(["--root", str(tmp_path), "--out", str(out)]) == 0
    artifact = out / "sessions.json"
    assert artifact.exists()
    audit = json.loads(artifact.read_text())
    assert audit["schema"] == AUDIT.SCHEMA
    assert audit["measurement"]["answers"] == 1
    assert (out / "README.md").exists()
    # The digest is of the bytes on disk, so a re-run over the same transcripts is identical.
    assert AUDIT.main(["--root", str(tmp_path), "--out", str(out)]) == 0
    assert json.loads(artifact.read_text())["measurement"] == audit["measurement"]
