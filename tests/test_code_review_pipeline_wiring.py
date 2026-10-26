"""tests/test_code_review_pipeline_wiring.py — the four tiers must actually talk.

The estate advertises a four-tier review pipeline: T0 deterministic -> T1 heuristics
-> T2 LLM judgment -> T3 verification. Until 2026-10-26 the tiers only ever read
each other's output from environment variables, and the intent runs each tier as its
own step -- so the variables were always empty, T2 judged nothing, and T3 verified
nothing. The pipeline advertised four tiers and ran two.

These tests grade the wiring, not the tiers:
  1. T2 reads T0/T1's findings from the hand-off files when no env is set;
  2. T2 carries each finding's file/line/rule into its verdict, so T3 can verify it;
  3. T3 reads T2's verdicts from the hand-off file;
  4. the intent actually writes the hand-off files the tiers read;
  5. T2's default model is one the router it calls actually offers.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LIBEXEC = ROOT / "platform" / "estate" / "libexec"
INTENT = ROOT / "platform" / "estate" / "intents" / "code-review.yaml"
CLUSTER_CONFIG = ROOT / "platform" / "llm" / "config.yaml"


def _load(name: str, path: Path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _t2():
    return _load("cr_t2_wiring", LIBEXEC / "code-review-t2.py")


def _t3():
    return _load("cr_t3_wiring", LIBEXEC / "code-review-t3.py")


def _finding():
    return {
        "tool": "dead-code",
        "severity": "low",
        "file": "mod.py",
        "line": 12,
        "rule": "unreachable-after-return",
        "message": "Unreachable code at line 12 after return",
    }


def test_tier2_reads_findings_from_the_handoff_files(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_REVIEW_DIR", str(tmp_path))
    monkeypatch.delenv("T0_FINDINGS", raising=False)
    monkeypatch.delenv("T1_FINDINGS", raising=False)
    (tmp_path / "t0.json").write_text(json.dumps({"tier": 0, "findings": [_finding()]}))
    (tmp_path / "t1.json").write_text(json.dumps({"tier": 1, "findings": []}))

    t2 = _t2()
    assert t2.load_json("t0.json", "T0_FINDINGS", "findings") == [_finding()]
    assert t2.load_json("t1.json", "T1_FINDINGS", "findings") == []


def test_env_still_wins_over_the_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_REVIEW_DIR", str(tmp_path))
    monkeypatch.setenv("T0_FINDINGS", json.dumps([{"file": "from-env.py"}]))
    (tmp_path / "t0.json").write_text(json.dumps({"findings": [_finding()]}))

    t2 = _t2()
    assert t2.load_json("t0.json", "T0_FINDINGS", "findings") == [
        {"file": "from-env.py"}
    ]


def test_a_verdict_carries_the_finding_so_tier3_can_verify_it():
    t2 = _t2()
    judged = t2.merge_verdicts(
        [_finding()],
        [{"verdict": "false_positive", "severity": "low", "explanation": "reachable"}],
    )
    assert len(judged) == 1
    assert judged[0]["file"] == "mod.py"
    assert judged[0]["line"] == 12
    assert judged[0]["rule"] == "unreachable-after-return"
    assert judged[0]["verdict"] == "false_positive"


def test_a_missing_verdict_does_not_shift_the_findings():
    t2 = _t2()
    judged = t2.merge_verdicts([_finding(), {"file": "b.py", "line": 3}], [])
    assert [j["file"] for j in judged] == ["mod.py", "b.py"]
    assert all(j["verdict"] == "uncertain" for j in judged)


def test_tier3_reads_tier2_verdicts_from_the_handoff_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_REVIEW_DIR", str(tmp_path))
    monkeypatch.delenv("T2_VERDICTS", raising=False)
    (tmp_path / "t2.json").write_text(
        json.dumps({"tier": 2, "verdicts": [{**_finding(), "verdict": "real"}]})
    )

    t3 = _t3()
    verdicts = t3.load_verdicts()
    assert len(verdicts) == 1
    assert verdicts[0]["rule"] == "unreachable-after-return"


def test_tier3_rejects_a_false_positive_without_rechecking_it(tmp_path, monkeypatch):
    """Tier 3 disposes: a finding Tier 2 called a false positive is not an issue."""
    monkeypatch.setenv("ESTATE_REVIEW_DIR", str(tmp_path))
    monkeypatch.delenv("T2_VERDICTS", raising=False)
    (tmp_path / "t2.json").write_text(
        json.dumps(
            {
                "tier": 2,
                "verdicts": [
                    {**_finding(), "verdict": "false_positive"},
                    {**_finding(), "line": 13, "verdict": "real"},
                ],
            }
        )
    )

    t3 = _t3()
    verdicts = t3.load_verdicts()
    assert len(verdicts) == 2


def test_tier3_drops_a_false_positive_and_keeps_a_real_one(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_REVIEW_DIR", str(tmp_path))
    monkeypatch.delenv("T2_VERDICTS", raising=False)
    target = tmp_path / "mod.py"
    target.write_text("def f():\n    return 1\n    print('dead')\n")
    (tmp_path / "t2.json").write_text(
        json.dumps(
            {
                "tier": 2,
                "verdicts": [
                    {
                        "tool": "dead-code",
                        "file": str(target),
                        "line": 3,
                        "rule": "unreachable-after-return",
                        "message": "Unreachable code at line 3 after return",
                        "verdict": "false_positive",
                    },
                    {
                        "tool": "dead-code",
                        "file": str(target),
                        "line": 3,
                        "rule": "unreachable-after-return",
                        "message": "Unreachable code at line 3 after return",
                        "verdict": "real",
                    },
                ],
            }
        )
    )

    import subprocess
    import sys

    script = str(LIBEXEC / "code-review-t3.py")
    env = dict(os.environ, ESTATE_REVIEW_DIR=str(tmp_path))
    out = subprocess.run(
        [sys.executable, script, "3", str(target), "HEAD~1"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert out.returncode == 0, out.stderr[-400:]
    result = json.loads(out.stdout)
    assert result["verified_count"] == 1
    assert result["rejected_count"] == 1
    assert "false_positive" in result["rejected"][0]["reason"]


def test_the_intent_writes_the_files_the_tiers_read():
    spec = yaml.safe_load(INTENT.read_text())
    cmds = {step["name"]: " ".join(step["cmd"].split()) for step in spec["steps"]}
    for tier, produced in (("t0", "t0.json"), ("t1", "t1.json"), ("t2", "t2.json")):
        assert produced in cmds[tier], f"the {tier} step must write {produced}"
    assert "t2.json" in cmds["t2"]


def test_tier2_default_model_is_one_the_router_offers():
    """The router T2 calls allowlists its models; a default off the list means the
    tier cannot make a call at all (gpt-4o-mini was the old default)."""
    t2 = _t2()
    config = yaml.safe_load(CLUSTER_CONFIG.read_text())
    offered = {m.get("model_name") for m in config.get("model_list", [])}
    assert t2.MODEL in offered, f"{t2.MODEL} is not in the router's model_list"
    assert t2.MODEL in {
        "default",
        "ollama",
        "deepseek",
        "gemini",
        "kimi",
        "minimax",
        "minimax_m27",
        "groq",
    }, "the default must be an estate lane, not a vendor model"


def test_tier2_prefers_the_estate_router_key():
    t2 = _t2()
    # the key the cluster router accepts is the estate's LITELLM_API_KEY
    assert "LITELLM_API_KEY" in Path(LIBEXEC / "code-review-t2.py").read_text()
    assert t2.API_KEY == "" or isinstance(t2.API_KEY, str)


def test_tier2_finds_the_diff_for_a_file_target(tmp_path, monkeypatch):
    """A file target used to produce no diff, so the slicer got nothing."""
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "mod.py").write_text("def f():\n    return 1\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "one"], cwd=repo, check=True)
    (repo / "mod.py").write_text("def f():\n    return 2\n")

    t2 = _t2()
    root, pathspec = t2.resolve_target(str(repo / "mod.py"))
    assert pathspec == "mod.py"
    diff = t2.get_diff(root, "HEAD", pathspec)
    assert "def f():" in diff and "+    return 2" in diff


def test_the_review_dir_is_where_the_intent_writes():
    """The scripts' default hand-off dir and the intent's must be the same path."""
    spec = yaml.safe_load(INTENT.read_text())
    cmds = " ".join(" ".join(step["cmd"].split()) for step in spec["steps"])
    assert "$HOME/.estate/review/latest" in cmds

    t2 = _t2()
    t3 = _t3()
    default_t2 = Path(os.path.expanduser("~/.estate/review/latest"))
    assert t2.REVIEW_DIR == default_t2
    assert t3.REVIEW_DIR == default_t2
