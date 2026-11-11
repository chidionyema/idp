"""Founder prompts are captured from harness-owned transcripts, never agent submissions."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "bin/founder-prompt-collector"


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def _env(tmp_path: Path) -> dict[str, str]:
    return {
        **os.environ,
        "HOME": str(tmp_path),
        "ESTATE_FOUNDER_PROMPT_LEDGER": str(tmp_path / "prompts.jsonl"),
        "ESTATE_CODEX_SESSION_GLOB": str(tmp_path / "codex/**/*.jsonl"),
        "ESTATE_PI_SESSION_GLOB": str(tmp_path / "pi/**/*.jsonl"),
        "ESTATE_CLAUDE_SESSION_GLOB": str(tmp_path / "claude/**/*.jsonl"),
        "ESTATE_OPENCODE_SESSION_GLOB": str(tmp_path / "opencode/**/*.jsonl"),
    }


def _fixtures(tmp_path: Path) -> None:
    _write(
        tmp_path / "codex/codex-session.jsonl",
        [
            {
                "timestamp": "2026-11-10T10:00:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "first founder prompt"}],
                },
            },
            {
                "timestamp": "2026-11-10T10:01:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "not a founder prompt"}
                    ],
                },
            },
            {
                "timestamp": "2026-11-10T10:01:30Z",
                "type": "event_msg",
                "payload": {
                    "type": "item_completed",
                    "item": {
                        "type": "UserMessage",
                        "content": [{"type": "text", "text": "event-only prompt"}],
                    },
                },
            },
            {
                "timestamp": "2026-11-10T10:00:00.006Z",
                "type": "event_msg",
                "payload": {
                    "type": "item_completed",
                    "item": {
                        "type": "UserMessage",
                        "content": [{"type": "text", "text": "first founder prompt"}],
                    },
                },
            },
        ],
    )
    _write(
        tmp_path / "pi/pi-session.jsonl",
        [
            {
                "type": "session",
                "id": "pi-session",
                "timestamp": "2026-11-10T10:02:00Z",
            },
            {
                "type": "message",
                "timestamp": "2026-11-10T10:02:01Z",
                "message": {
                    "role": "user",
                    "content": "pi prompt with sk-abcdefghijklmnopqrstuvwxyz",
                },
            },
        ],
    )
    _write(
        tmp_path / "claude/claude-session.jsonl",
        [
            {
                "type": "user",
                "isSidechain": False,
                "timestamp": "2026-11-10T10:03:00Z",
                "message": {"role": "user", "content": "claude founder prompt"},
            },
            {
                "type": "user",
                "isSidechain": False,
                "timestamp": "2026-11-10T10:03:01Z",
                "message": {
                    "role": "user",
                    "content": [{"type": "tool_result", "content": "not a prompt"}],
                },
            },
        ],
    )


def _run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(COLLECTOR), *args],
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_all_harness_transcripts_are_collected_and_deduplicated(tmp_path):
    _fixtures(tmp_path)
    first = _run(tmp_path, "collect")
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["added"] == 4
    second = _run(tmp_path, "collect")
    assert json.loads(second.stdout)["added"] == 0

    rows = [
        json.loads(line)
        for line in (tmp_path / "prompts.jsonl").read_text().splitlines()
    ]
    assert [row["source"] for row in rows] == ["codex", "codex", "pi", "claude"]
    assert all(row["occurred_at"].endswith("Z") for row in rows)
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in rows[2]["text"]
    assert rows[2]["redactions"] == ["api-key:1"]


def test_session_check_returns_count_timestamps_and_ledger_hash(tmp_path):
    _fixtures(tmp_path)
    result = _run(tmp_path, "check", "--session", "codex-session")
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["count"] == 2
    assert summary["first_at"] == "2026-11-10T10:00:00Z"
    assert summary["last_at"] == "2026-11-10T10:01:30Z"
    assert len(summary["ledger_sha256"]) == 64


def test_one_partial_transcript_line_does_not_drop_the_whole_session(tmp_path):
    _fixtures(tmp_path)
    codex = tmp_path / "codex/codex-session.jsonl"
    codex.write_text(codex.read_text() + '{"half_written":\n')
    result = _run(tmp_path, "collect")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["added"] == 4


def test_missing_prompts_refuse_the_session(tmp_path):
    result = _run(tmp_path, "check", "--session", "no-such-session")
    assert result.returncode == 1


def test_installed_collector_resolves_modules_from_the_runtime_tree(tmp_path):
    estate = tmp_path / "estate"
    installed = estate / "bin/founder-prompt-collector"
    installed.parent.mkdir(parents=True)
    shutil.copy2(COLLECTOR, installed)

    runtime = tmp_path / "runtime/idp"
    memory = runtime / "platform/estate/memory"
    governance = runtime / "platform/estate/governance"
    memory.mkdir(parents=True)
    governance.mkdir(parents=True)
    (memory / "plan.py").symlink_to(ROOT / "platform/estate/memory/plan.py")
    (governance / "optimus.py").symlink_to(
        ROOT / "platform/estate/governance/optimus.py"
    )
    env = {
        **_env(tmp_path),
        "HOME": str(estate),
        "IDP_ROOT": str(runtime),
    }
    result = subprocess.run(
        [sys.executable, str(installed), "--help"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "ModuleNotFoundError" not in result.stderr


def test_machine_context_is_not_mistaken_for_the_founders_words(tmp_path):
    _write(
        tmp_path / "codex/codex-session.jsonl",
        [
            {
                "timestamp": "2026-11-11T00:40:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "<environment_context>machine state</environment_context>\n"
                                "<in-app-browser-context>browser state"
                                "</in-app-browser-context>\n\n"
                                "## My request:\n"
                                "track every instruction\n"
                            ),
                        }
                    ],
                },
            }
        ],
    )

    result = _run(tmp_path, "collect")

    assert result.returncode == 0, result.stderr
    rows = [
        json.loads(line)
        for line in (tmp_path / "prompts.jsonl").read_text().splitlines()
    ]
    assert rows[-1]["text"] == "track every instruction"


def test_a_cleaner_upgrade_reprocesses_transcripts_from_the_old_cache(tmp_path):
    _fixtures(tmp_path)
    first = _run(tmp_path, "collect")
    assert first.returncode == 0 and json.loads(first.stdout)["added"] == 4

    cache = tmp_path / ".estate/state/founder-prompts.sources.json"
    old = json.loads(cache.read_text())
    assert all(value.startswith("cache-v2:") for value in old.values())
    cache.write_text(
        json.dumps({path: value.split(":", 1)[-1] for path, value in old.items()})
    )
    (tmp_path / "prompts.jsonl").unlink()

    upgraded = _run(tmp_path, "collect")

    assert upgraded.returncode == 0, upgraded.stderr
    assert json.loads(upgraded.stdout)["added"] == 4


def test_a_cleaner_upgrade_repairs_an_existing_polluted_prompt(tmp_path):
    _fixtures(tmp_path)
    first = _run(tmp_path, "collect")
    assert first.returncode == 0
    ledger = tmp_path / "prompts.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    original_id = rows[0]["id"]
    rows[0]["text"] = (
        "<in-app-browser-context>old polluted context</in-app-browser-context>\n"
        "## My request:\nfirst founder prompt"
    )
    ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    cache = tmp_path / ".estate/state/founder-prompts.sources.json"
    old = json.loads(cache.read_text())
    cache.write_text(
        json.dumps({path: value.split(":", 1)[-1] for path, value in old.items()})
    )

    repaired = _run(tmp_path, "collect")

    assert repaired.returncode == 0, repaired.stderr
    repaired_rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    match = [row for row in repaired_rows if row["id"] == original_id]
    assert len(match) == 1
    assert match[0]["text"] in {"first founder prompt", "event-only prompt"}


def test_existing_polluted_prompt_is_repaired_without_rescanning_the_transcript(
    tmp_path,
):
    _fixtures(tmp_path)
    first = _run(tmp_path, "collect")
    assert first.returncode == 0
    ledger = tmp_path / "prompts.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    rows[0]["text"] = (
        "<in-app-browser-context>old polluted context</in-app-browser-context>\n"
        "## My request:\nfirst founder prompt"
    )
    ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    repaired = _run(tmp_path, "collect")

    assert repaired.returncode == 0, repaired.stderr
    assert json.loads(repaired.stdout)["added"] == 0
    repaired_rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert repaired_rows[0]["text"] == "first founder prompt"
