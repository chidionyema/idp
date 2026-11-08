"""Adversarial tests for the read-only law packet and live-instruction hygiene."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "platform" / "estate"))
from governance.law_packet import compile_packet, encoded

LAWS = """laws:
  - id: GOV-001
    source: founder, 2026-10-29
    severity: block
    founder_law: LAW-3
    check: {type: grep_present, path: guard, pattern: fence}
    falsifier: {files: {guard: 'no fence'}}
"""
AGENTS = (
    "# One canonical entry\n"
    + chr(96) * 3
    + "toml\n[capabilities]\nread=[]\n[fsm]\n[budget.usd_per_day]\ntest=1\n[cost]\n[routing]\n[merge]\n[invariants]\n[jev]\n"
    + chr(96) * 3
    + "\n"
)


def tree(tmp_path):
    (tmp_path / "platform/estate/governance").mkdir(parents=True)
    (tmp_path / "platform/estate/governance/laws.yaml").write_text(LAWS)
    (tmp_path / "AGENTS.md").write_text(AGENTS)
    (tmp_path / "CLAUDE.md").write_text("@AGENTS.md\n")
    return tmp_path


def test_valid_packet_never_grants_admission(tmp_path):
    packet = compile_packet(tree(tmp_path))
    assert packet["status"] == "SOURCE_CONSISTENT_UNVERIFIED_RUNTIME"
    assert packet["is_admission_decision"] is False
    assert packet["grants_execution"] is False
    assert packet["runtime_freshness"] == "BLIND"
    assert packet["laws"][0]["founder_law_ref"] == "LAW-3"
    assert packet["laws"][0]["classification"] == "ESTATE_ENFORCEMENT_CONTROL"
    assert packet["laws"][0]["issuer_authenticated_by_packet"] is False
    assert packet["laws"][0]["runtime_enforcement_verified"] is False
    assert packet["laws"][0]["check_grade"] == "STRUCTURAL_ONLY"
    assert packet["wrappers"]["CLAUDE.md"] == "POINTER_ONLY"


def test_contradictory_legacy_intents_are_refused(tmp_path):
    root = tree(tmp_path)
    with (root / "AGENTS.md").open("a") as out:
        out.write(
            "Every action the agent performs goes through an **intent YAML** in old folder.\n"
        )
    packet = compile_packet(root)
    assert packet["status"] == "CONFLICTED"
    assert "LEGACY_INTENT_MANDATE" in [x["code"] for x in packet["problems"]]


def test_stale_status_is_refused(tmp_path):
    root = tree(tmp_path)
    with (root / "AGENTS.md").open("a") as out:
        out.write("## 13. The estate's state right now\n")
    assert "STATIC_ESTATE_STATUS" in [
        x["code"] for x in compile_packet(root)["problems"]
    ]


def test_duplicate_harness_rules_are_refused(tmp_path):
    root = tree(tmp_path)
    (root / "CLAUDE.md").write_text("@AGENTS.md\nAlways use obsolete infrastructure\n")
    packet = compile_packet(root)
    assert packet["status"] == "CONFLICTED"
    assert "DUPLICATE_HARNESS_POLICY" in [x["code"] for x in packet["problems"]]


def test_missing_laws_cannot_be_certified(tmp_path):
    root = tree(tmp_path)
    (root / "platform/estate/governance/laws.yaml").unlink()
    packet = compile_packet(root)
    assert packet["status"] == "CONFLICTED"
    assert "LAW_SOURCE_MISSING_OR_EMPTY" in [x["code"] for x in packet["problems"]]


def test_missing_runtime_policy_fence_fails_static_readiness(tmp_path):
    root = tree(tmp_path)
    (root / "AGENTS.md").write_text("Read AGENTS.md\n")
    assert "EMBEDDED_RUNTIME_POLICY_MISSING" in [
        x["code"] for x in compile_packet(root)["problems"]
    ]


def test_duplicate_gov_ids_cannot_hide(tmp_path):
    root = tree(tmp_path)
    (root / "platform/estate/governance/laws.yaml").write_text(
        LAWS + LAWS.replace("laws:\n", "")
    )
    assert "DUPLICATE_LAW_ID" in [x["code"] for x in compile_packet(root)["problems"]]


def test_deterministic_packet_bytes_not_signature(tmp_path):
    root = tree(tmp_path)
    assert encoded(compile_packet(root)) == encoded(compile_packet(root))
    assert "signature" not in compile_packet(root)
    assert all(len(v) == 64 for v in compile_packet(root)["source_digests"].values())


def test_law_check_without_falsifier_refused(tmp_path):
    root = tree(tmp_path)
    (root / "platform/estate/governance/laws.yaml").write_text(
        LAWS.replace("    falsifier: {files: {guard: 'no fence'}}\n", "")
    )
    assert "UNDECIDABLE_LAW" in [x["code"] for x in compile_packet(root)["problems"]]


def test_empty_or_malformed_yaml_is_not_healthy(tmp_path):
    root = tree(tmp_path)
    (root / "platform/estate/governance/laws.yaml").write_text("laws: {}\n")
    assert compile_packet(root)["status"] == "CONFLICTED"


def test_no_file_system_mutation(tmp_path):
    root = tree(tmp_path)
    before = {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }
    compile_packet(root)
    after = {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }
    assert before == after


def test_real_repository_fixes_the_superseded_directives():
    repo = Path(__file__).resolve().parents[2]
    packet = compile_packet(repo)
    assert packet["status"] == "SOURCE_CONSISTENT_UNVERIFIED_RUNTIME", packet[
        "problems"
    ]
    assert packet["wrappers"]["CLAUDE.md"] == "POINTER_ONLY"
    assert packet["laws"], "No active GOV enforcement inventory"


def test_malformed_toml_is_not_safe(tmp_path):
    root = tree(tmp_path)
    (root / "AGENTS.md").write_text(AGENTS.replace("read=[]", "read=["))
    assert "MALFORMED_RUNTIME_POLICY" in [
        x["code"] for x in compile_packet(root)["problems"]
    ]


def test_symlinked_policy_source_not_accepted(tmp_path):
    root = tree(tmp_path)
    law = root / "platform/estate/governance/laws.yaml"
    original = law.read_text()
    law.unlink()
    alternate = root.parent / "secret-source.yaml"
    alternate.write_text(original)
    law.symlink_to(alternate)
    assert compile_packet(root)["status"] == "CONFLICTED"
