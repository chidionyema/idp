"""The founder tracker must answer three questions from evidence alone:

What did the founder ask for, who owns it now, and which claim/ticket/PR/test proves it?

These tests exercise the real CLI against a temporary append-only ledger. They deliberately
assert the refusal path first: a claimed completion without evidence is not a verified
instruction.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "instruction"


def _load_tracker():
    loader = importlib.machinery.SourceFileLoader(
        "estate_instruction_tracker", str(SCRIPT)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def _run(tmp_path, monkeypatch, capsys, *args: str) -> tuple[int, str]:
    monkeypatch.setenv("ESTATE_INSTRUCTIONS", str(tmp_path / "instructions.jsonl"))
    module = _load_tracker()
    code = module.main(list(args))
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def _new(tmp_path, monkeypatch, capsys, text: str = "ship the founder tracker") -> str:
    code, out = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "new",
        "--text",
        text,
        "--session",
        "session-1",
        "--owner",
        "codex",
    )
    assert code == 0
    return out.strip().splitlines()[-1]


def _write_plan(
    tmp_path: Path,
    instruction_id: str,
    *,
    session: str = "session-1",
    complete: bool = True,
) -> Path:
    plans = tmp_path / "plans"
    plans.mkdir(exist_ok=True)
    events = [
        {
            "tool": "declare_plan",
            "session": session,
            "args": {
                "goal": "Track every founder instruction end to end",
                "subgoals": [{"id": "g1", "text": "join the instruction and claim"}],
                "instruction_id": instruction_id,
                "prompt": "founder-a",
            },
        }
    ]
    if complete:
        events.extend(
            [
                {
                    "tool": "add_bdd",
                    "session": session,
                    "args": {
                        "goal_id": "g1",
                        "given": "a founder instruction",
                        "when": "work is claimed",
                        "then": "the claim carries the instruction and plan digest",
                    },
                },
                {
                    "tool": "address_edgecases",
                    "session": session,
                    "args": {
                        "goal_id": "g1",
                        "edgecases": ["missing instruction id is refused"],
                    },
                },
                {
                    "tool": "address_2nd_order_effects",
                    "session": session,
                    "args": {
                        "goal_id": "g1",
                        "effects": ["claim and tracker converge on one key"],
                    },
                },
            ]
        )
    path = plans / f"{session}.jsonl"
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n")
    return plans


def test_verified_requires_evidence(tmp_path, monkeypatch, capsys):
    instruction_id = _new(tmp_path, monkeypatch, capsys)

    code, out = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "move",
        instruction_id,
        "--state",
        "verified",
        "--note",
        "claimed complete",
    )

    assert code == 2
    assert "UNPROVEN" in out
    rows = [
        json.loads(line)
        for line in (tmp_path / "instructions.jsonl").read_text().splitlines()
    ]
    assert not any(row.get("type") == "state" for row in rows)


def test_verified_requires_plan_claim_and_evidence(tmp_path, monkeypatch, capsys):
    instruction_id = _new(tmp_path, monkeypatch, capsys)
    plans = _write_plan(tmp_path, instruction_id)
    monkeypatch.setenv("ESTATE_PLAN_LEDGER_DIR", str(plans))

    code, out = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "move",
        instruction_id,
        "--state",
        "verified",
        "--note",
        "claimed complete",
    )
    assert code == 2 and "PLAN" in out

    code, _ = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "evidence",
        instruction_id,
        "--kind",
        "test",
        "--ref",
        "tests/test_instruction_tracker.py",
    )
    assert code == 0
    code, _ = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "sync-plan",
        instruction_id,
        "--session",
        "session-1",
    )
    assert code == 0

    code, out = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "move",
        instruction_id,
        "--state",
        "verified",
        "--note",
        "claimed complete",
    )
    assert code == 2 and "CLAIM" in out

    code, _ = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "link",
        instruction_id,
        "--claim",
        "idp#7901",
    )
    assert code == 0
    code, _ = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "move",
        instruction_id,
        "--state",
        "verified",
        "--note",
        "claim, plan and proof linked",
    )
    assert code == 0


def test_sync_plan_refuses_an_incomplete_plan(tmp_path, monkeypatch, capsys):
    instruction_id = _new(tmp_path, monkeypatch, capsys)
    plans = _write_plan(tmp_path, instruction_id, complete=False)
    monkeypatch.setenv("ESTATE_PLAN_LEDGER_DIR", str(plans))

    code, out = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "sync-plan",
        instruction_id,
        "--session",
        "session-1",
    )

    assert code == 2
    assert "BDD" in out or "edge case" in out or "second-order" in out


def test_link_records_claim_ticket_pr_and_failing_test(tmp_path, monkeypatch, capsys):
    instruction_id = _new(tmp_path, monkeypatch, capsys)

    code, _ = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "link",
        instruction_id,
        "--claim",
        "idp#7844",
        "--ticket",
        "https://github.com/chidionyema/idp/issues/7844",
        "--pr",
        "https://github.com/chidionyema/idp/pull/7900",
        "--test",
        "tests/test_instruction_tracker.py::test_link_records_claim_ticket_pr_and_failing_test",
    )
    assert code == 0

    code, out = _run(tmp_path, monkeypatch, capsys, "board", "--json")
    assert code == 0
    row = json.loads(out)["instructions"][0]
    assert row["claims"] == ["idp#7844"]
    assert row["tickets"] == ["https://github.com/chidionyema/idp/issues/7844"]
    assert row["prs"] == ["https://github.com/chidionyema/idp/pull/7900"]
    assert row["tests"] == [
        "tests/test_instruction_tracker.py::test_link_records_claim_ticket_pr_and_failing_test"
    ]


def test_board_marks_missing_claim_and_evidence_blind(tmp_path, monkeypatch, capsys):
    _new(tmp_path, monkeypatch, capsys)

    code, out = _run(tmp_path, monkeypatch, capsys, "board")

    assert code == 0
    assert "CLAIM BLIND" in out
    assert "PLAN BLIND" in out
    assert "EVIDENCE BLIND" in out
    assert "ship the founder tracker" in out


def test_board_can_show_everything_assigned_in_one_session(
    tmp_path, monkeypatch, capsys
):
    code, first = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "new",
        "--text",
        "first session task",
        "--session",
        "session-1",
    )
    assert code == 0
    first_id = first.strip()
    code, _ = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "new",
        "--text",
        "second session task",
        "--session",
        "session-2",
    )
    assert code == 0

    code, out = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "board",
        "--session",
        "session-1",
        "--json",
    )

    assert code == 0
    rows = json.loads(out)["instructions"]
    assert [row["id"] for row in rows] == [first_id]


def test_markdown_board_keeps_claim_and_ticket_links(tmp_path, monkeypatch, capsys):
    instruction_id = _new(tmp_path, monkeypatch, capsys)
    code, _ = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "link",
        instruction_id,
        "--claim",
        "idp#7844",
        "--ticket",
        "https://github.com/chidionyema/idp/issues/7844",
    )
    assert code == 0
    code, _ = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "move",
        instruction_id,
        "--state",
        "executing",
        "--note",
        "tracker work started",
    )
    assert code == 0

    code, out = _run(tmp_path, monkeypatch, capsys, "board", "--markdown")

    assert code == 0
    assert "[idp#7844](https://github.com/chidionyema/idp/issues/7844)" in out
    assert "| INS-00001 | executing | UNPROVEN · EVIDENCE BLIND |" in out
    assert "EVIDENCE BLIND" in out


def test_markdown_board_can_write_the_founder_surface(tmp_path, monkeypatch, capsys):
    instruction_id = _new(tmp_path, monkeypatch, capsys)
    code, _ = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "link",
        instruction_id,
        "--ticket",
        "https://github.com/chidionyema/idp/issues/7844",
    )
    assert code == 0
    destination = tmp_path / "FOUNDER-INSTRUCTIONS.md"

    code, out = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "board",
        "--markdown",
        "--out",
        str(destination),
    )

    assert code == 0
    assert out.strip() == ""
    assert "[ticket](https://github.com/chidionyema/idp/issues/7844)" in (
        destination.read_text()
    )


def test_verified_instruction_reports_proof_and_latest_update(
    tmp_path, monkeypatch, capsys
):
    instruction_id = _new(tmp_path, monkeypatch, capsys)
    plans = _write_plan(tmp_path, instruction_id)
    monkeypatch.setenv("ESTATE_PLAN_LEDGER_DIR", str(plans))
    for args in (
        ("move", instruction_id, "--state", "executing", "--note", "implementing"),
        ("sync-plan", instruction_id, "--session", "session-1"),
        ("link", instruction_id, "--claim", "idp#7901"),
        (
            "evidence",
            instruction_id,
            "--kind",
            "test",
            "--ref",
            "tests/test_instruction_tracker.py",
        ),
        ("move", instruction_id, "--state", "verified", "--note", "proof passed"),
    ):
        code, _ = _run(tmp_path, monkeypatch, capsys, *args)
        assert code == 0

    code, out = _run(tmp_path, monkeypatch, capsys, "board", "--json")

    assert code == 0
    row = json.loads(out)["instructions"][0]
    assert row["state"] == "verified"
    assert row["verification"] == "PROVEN"
    assert row["last_note"] == "proof passed"
    assert row["evidence"][0]["ref"] == "tests/test_instruction_tracker.py"
    assert row["plan"]["goal"].startswith("Track every founder instruction")
    assert row["plan"]["edgecases"]["g1"] == ["missing instruction id is refused"]
    assert row["plan_digest"]
    code, rendered = _run(tmp_path, monkeypatch, capsys, "board")
    assert code == 0
    assert "goal: Track every founder instruction end to end" in rendered
    assert "g1: join the instruction and claim" in rendered


def test_import_prompts_is_machine_owned_and_idempotent(tmp_path, monkeypatch, capsys):
    prompt_ledger = tmp_path / "founder-prompts.jsonl"
    prompt_ledger.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "id": "founder-a",
                    "raw_sha256": "a" * 64,
                    "session": "session-a",
                    "source": "codex",
                    "occurred_at": "2026-11-10T10:00:00Z",
                    "text": "fix the router and link idp#7844",
                },
                {
                    "id": "founder-b",
                    "raw_sha256": "b" * 64,
                    "session": "session-b",
                    "source": "claude",
                    "occurred_at": "2026-11-10T10:01:00Z",
                    "text": "show me the cloud and local traffic",
                },
            )
        )
        + "\n"
    )
    monkeypatch.setenv("ESTATE_FOUNDER_PROMPTS", str(prompt_ledger))

    code, first = _run(tmp_path, monkeypatch, capsys, "import-prompts")
    code2, second = _run(tmp_path, monkeypatch, capsys, "import-prompts")

    assert code == 0 and code2 == 0
    assert "imported 2" in first
    assert "imported 0" in second
    _, listing = _run(tmp_path, monkeypatch, capsys, "list", "--json")
    rows = json.loads(listing)
    assert len(rows) == 2
    assert {row["source_id"] for row in rows} == {"founder-a", "founder-b"}
    assert all(row["machine_imported"] is True for row in rows)


def test_import_prompts_can_be_scoped_to_the_current_session(
    tmp_path, monkeypatch, capsys
):
    prompt_ledger = tmp_path / "founder-prompts.jsonl"
    prompt_ledger.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "id": "founder-a",
                    "raw_sha256": "a" * 64,
                    "session": "session-a",
                    "source": "codex",
                    "occurred_at": "2026-11-10T10:00:00Z",
                    "text": "first session",
                },
                {
                    "id": "founder-b",
                    "raw_sha256": "b" * 64,
                    "session": "session-b",
                    "source": "claude",
                    "occurred_at": "2026-11-10T10:01:00Z",
                    "text": "second session",
                },
            )
        )
        + "\n"
    )
    monkeypatch.setenv("ESTATE_FOUNDER_PROMPTS", str(prompt_ledger))

    code, out = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "import-prompts",
        "--session",
        "session-a",
    )

    assert code == 0
    assert "imported 1" in out
    _, listing = _run(tmp_path, monkeypatch, capsys, "list", "--json")
    rows = json.loads(listing)
    assert [row["session"] for row in rows] == ["session-a"]
    _, scoped = _run(
        tmp_path,
        monkeypatch,
        capsys,
        "board",
        "--session",
        "session-a",
        "--json",
    )
    assert [row["session"] for row in json.loads(scoped)["instructions"]] == [
        "session-a"
    ]


def test_import_prompts_repairs_a_cleaned_prompt_without_duplicating_it(
    tmp_path, monkeypatch, capsys
):
    prompt_ledger = tmp_path / "founder-prompts.jsonl"
    prompt_ledger.write_text(
        json.dumps(
            {
                "id": "founder-a",
                "raw_sha256": "a" * 64,
                "session": "session-a",
                "source": "codex",
                "occurred_at": "2026-11-11T00:00:00Z",
                "text": "old polluted text",
            }
        )
        + "\n"
    )
    monkeypatch.setenv("ESTATE_FOUNDER_PROMPTS", str(prompt_ledger))
    assert _run(tmp_path, monkeypatch, capsys, "import-prompts")[0] == 0

    prompt_ledger.write_text(
        json.dumps(
            {
                "id": "founder-a",
                "raw_sha256": "a" * 64,
                "session": "session-a",
                "source": "codex",
                "occurred_at": "2026-11-11T00:00:00Z",
                "text": "clean founder instruction",
            }
        )
        + "\n"
    )
    code, out = _run(tmp_path, monkeypatch, capsys, "import-prompts")
    assert code == 0 and "imported 0" in out

    _, listing = _run(tmp_path, monkeypatch, capsys, "list", "--json")
    rows = json.loads(listing)
    assert len(rows) == 1
    assert rows[0]["text"] == "clean founder instruction"
