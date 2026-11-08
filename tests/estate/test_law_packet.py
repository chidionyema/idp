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
    training = tmp_path / "docs/training/2026-10-30-founder-judgement.md"
    training.parent.mkdir(parents=True)
    training.write_text(
        "\n".join(
            f"## J{i} -- Recorded case {i}\n"
            f"**Rule.** A verifiable rule {i}.\n"
            f"**Trigger.** Applicable risk {i}.\n"
            f"**Enforcement.** Rerun independent effect verification {i}.\n"
            for i in range(1, 9)
        )
    )
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


def test_founder_judgements_are_training_records_not_laws(tmp_path):
    packet = compile_packet(tree(tmp_path))
    cases = packet["founder_judgement_training"]
    assert [item["id"] for item in cases] == [f"J{i}" for i in range(1, 9)]
    assert packet["fleet_drills_executed"] is False
    assert packet["competence_certified"] is False
    for record in cases:
        assert record["source_line"] > 0
        assert len(record["source_digest"]) == 64
        assert record["historical_issuer_authenticated"] is False
        assert record["constitutional_authority_granted"] is False
        assert record["drill"]["execution_proof"] is None
        assert record["drill"]["competence_certified"] is False
        assert record["applicability_trigger"]
        assert record["documented_enforcement"]


def test_missing_founder_training_is_visible_not_implicitly_healthy(tmp_path):
    root = tree(tmp_path)
    (root / "docs/training/2026-10-30-founder-judgement.md").unlink()
    packet = compile_packet(root)
    assert packet["status"] == "CONFLICTED"
    assert "FOUNDER_TRAINING_SOURCE_UNAVAILABLE" in {
        problem["code"] for problem in packet["problems"]
    }


def test_incomplete_judgement_refuses_static_readiness(tmp_path):
    root = tree(tmp_path)
    src = root / "docs/training/2026-10-30-founder-judgement.md"
    src.write_text(
        src.read_text().replace(
            "**Enforcement.** Rerun independent effect verification 2.",
            "Enforcement missing for J2",
        )
    )
    packet = compile_packet(root)
    assert packet["status"] == "CONFLICTED"
    assert "INCOMPLETE_FOUNDER_JUDGEMENT" in {
        problem["code"] for problem in packet["problems"]
    }


def test_duplicate_judgements_do_not_silently_override(tmp_path):
    root = tree(tmp_path)
    src = root / "docs/training/2026-10-30-founder-judgement.md"
    src.write_text(
        src.read_text() + "\n## J1 -- rewritten\n"
        "**Rule.** New rule.\n**Trigger.** Always.\n"
        "**Enforcement.** Assume green.\n"
    )
    assert "DUPLICATE_FOUNDER_JUDGEMENT" in {
        problem["code"] for problem in compile_packet(root)["problems"]
    }


def test_new_unexercised_judgement_never_auto_certifies(tmp_path):
    root = tree(tmp_path)
    src = root / "docs/training/2026-10-30-founder-judgement.md"
    src.write_text(
        src.read_text() + "\n## J9 -- proposal\n"
        "**Rule.** A possible improvement.\n"
        "**Trigger.** Unknown conditions.\n"
        "**Enforcement.** A later test.\n"
    )
    packet = compile_packet(root)
    assert "UNEXERCISED_FOUNDER_JUDGEMENT" in {
        problem["code"] for problem in packet["problems"]
    }
    assert packet["status"] == "CONFLICTED"


def test_real_founder_judgements_are_present_and_source_bound():
    repo = Path(__file__).resolve().parents[2]
    packet = compile_packet(repo)
    assert [r["id"] for r in packet["founder_judgement_training"]] == [
        f"J{i}" for i in range(1, 9)
    ]
    assert packet["status"] == "SOURCE_CONSISTENT_UNVERIFIED_RUNTIME", packet[
        "problems"
    ]


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


def test_state_page_broadcasts_source_conflicts_without_claiming_authority(
    tmp_path, monkeypatch
):
    """Existing estate-state broadcast, not a new agent endpoint."""
    from governance import state_page

    root = tree(tmp_path)
    (root / "AGENTS.md").write_text(
        AGENTS
        + "Every action the agent performs goes through an **intent YAML** in old folder.\n"
    )
    monkeypatch.setattr(
        state_page.registry,
        "evaluate_all",
        lambda _root, falsify=False: {
            "ok": True,
            "results": [],
            "failing": [],
            "warning": [],
            "audit": {"count": 0},
        },
    )
    monkeypatch.setattr(
        state_page.registry,
        "evaluate_specs",
        lambda _root: {"specs": [], "open": [], "done": []},
    )
    monkeypatch.setattr(state_page.provider_renewal, "status", lambda: {})
    monkeypatch.setattr(state_page.provider_renewal, "denied_providers", lambda: [])
    monkeypatch.setattr(state_page, "_focus_rows", lambda: [])
    monkeypatch.setattr(state_page.ledger, "sessions_dir", lambda: str(root / "absent"))
    monkeypatch.setattr(state_page.ledger, "violations", lambda: [])
    facts = state_page.compute(str(root))
    assert facts["law_gate"]["ok"] is True  # the old gate may be green
    assert facts["law_source"]["status"] == "CONFLICTED"
    assert "LEGACY_INTENT_MANDATE" in facts["law_source"]["problem_codes"]
    assert facts["law_source"]["is_admission_decision"] is False
    assert facts["law_source"]["runtime_freshness"] == "BLIND"
    text = state_page.render(facts)
    assert "source: CONFLICTED" in text
    assert "LEGACY_INTENT_MANDATE" in text
    assert "no execution authority granted" in text
    assert "drills NOT independently certified" in text
    assert "NOT VERIFIED" in text


def test_old_state_page_without_new_projection_renders_blind():
    from governance import state_page

    facts = {
        "ts": "2026-11-08T12:00Z",
        "law_gate": {
            "ok": True,
            "laws": 1,
            "failing": [],
            "warning": [],
            "audit_count": 0,
        },
        "specs": {"total": 0, "open": [], "done": []},
        "renewals": {},
        "claims": {"live": 0, "total": 0},
        "violations": {"total": 0, "by_class": {}},
        "locked_sessions": [],
    }
    text = state_page.render(facts)
    assert "BLIND: law-source projection unavailable" in text
    assert "NOT an admission pass" in text
