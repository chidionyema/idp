"""The founder's instruction store must be runnable: it sat at mode 644 and failed 'Permission denied'."""

import json
import os
import subprocess
from pathlib import Path

BIN = Path(__file__).resolve().parents[1] / "bin" / "estate-founder-intake"


def test_intake_is_executable_and_classifies():
    assert os.access(BIN, os.X_OK), "bin/estate-founder-intake is not executable"
    r = subprocess.run(
        [
            str(BIN),
            "--json",
            "--no-publish",
            "--text",
            "Never repeat yourself. Close the loop.",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert '"fingerprint"' in r.stdout and '"sentences"' in r.stdout


def test_repeat_hit_is_reported_not_crashed(tmp_path):
    """Regression: the CLI read 'similarity'/'text' while find_repeat returns 'score'/'earlier'; any real hit crashed."""
    env = {**os.environ, "ESTATE_HOME": str(tmp_path), "HOME": str(tmp_path)}
    text = "Never repeat yourself and close the loop on every instruction."
    subprocess.run(
        [str(BIN), "--no-publish", "--text", text],
        env=env,
        capture_output=True,
        timeout=60,
    )
    r = subprocess.run(
        [str(BIN), "--repeat", text],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "Traceback" not in r.stderr, r.stderr
    assert r.returncode == 2 and r.stdout.startswith("REPEAT")



def test_case_retrieval_reuses_existing_prompt_memory_without_inventing_causes(tmp_path):
    env = {**os.environ, "ESTATE_GOVERNANCE_HOME": str(tmp_path / "state"),
           "ESTATE_HOME": str(tmp_path), "HOME": str(tmp_path)}
    original = "The founder says agent keeps narrating instead of fixing deployed work."
    entry = subprocess.run([str(BIN), "--no-publish", "--json", "--text", original],
                           env=env, capture_output=True, text=True, timeout=60)
    assert entry.returncode == 0, entry.stderr
    first = json.loads(entry.stdout)
    lookup = subprocess.run([str(BIN), "--cases", "--text", original],
                            env=env, capture_output=True, text=True, timeout=60)
    assert lookup.returncode == 0, lookup.stderr
    result = json.loads(lookup.stdout)
    assert result["authority"] == "CANDIDATE_RETRIEVAL_NOT_CAUSAL_PROOF"
    assert result["cases"][0]["case_id"] == first["id"]
    assert result["cases"][0]["correction_status"] == "UNVERIFIED"
    assert original not in lookup.stdout, "case lookup must not disclose a prior prompt's raw text"


def test_retrieved_case_does_not_upgrade_an_agent_claim_to_verified(tmp_path):
    import sys
    sys.path.insert(0, str(BIN.parent.parent / "platform" / "estate"))
    from governance import founder_intake

    history = [{
        "id": "case-prior", "text": "deploy keeps failing on unsigned branch",
        "failure_class": "unsigned-branch", "correction_status": "INDEPENDENTLY_VERIFIED",
    }]
    result = founder_intake.retrieve_precedents(history[0]["text"], history=history)
    assert result[0]["correction_status"] == "UNVERIFIED"
    assert founder_intake.retrieve_precedents(
        history[0]["text"], history=history,
        verify_external=lambda row: True,
    )[0]["correction_status"] == "INDEPENDENTLY_VERIFIED"
    assert founder_intake.retrieve_precedents(
        history[0]["text"], history=history,
        verify_external=lambda row: (_ for _ in ()).throw(RuntimeError("offline")),
    )[0]["correction_status"] == "UNVERIFIED"


def test_precedent_retrieval_is_bounded_and_handles_invalid_history():
    import sys
    sys.path.insert(0, str(BIN.parent.parent / "platform" / "estate"))
    from governance import founder_intake

    history = [{"id": f"case-{i:02}", "text": "repeated failure same symptom"}
               for i in range(31)] + [None, {"id": "invalid"}]
    rows = founder_intake.retrieve_precedents(
        "repeated failure same symptom", history=history, limit=100,
    )
    assert len(rows) == 20
    assert rows[0]["case_id"] == "case-00"



def test_authenticated_founder_issue_action_cannot_bypass_shared_memory():
    """IssueOps must institutionalise the founder case before waking a worker."""
    workflow = (BIN.parent.parent / ".github" / "workflows" / "estate-issueops.yml").read_text()
    assert 'github.actor == vars.ESTATE_FOUNDER_LOGIN' in workflow
    assert '[ -n "$FOUNDER" ] && [ "$AUTHOR" = "$FOUNDER" ]' in workflow
    assert 'bin/estate-founder-intake --file "$INPUT" --json' in workflow
    assert 'bin/estate-founder-intake --file "$INPUT" --no-publish' not in workflow
    assert 'publish.get("ok") is not True' in workflow
    assert 'raise SystemExit(2)' in workflow
    assert workflow.index('UNIFIED_MEMORY_NOT_PUBLISHED') < workflow.index(
        "Run the task on the estate (the executor door)"
    )
