"""bin/idp-hypothesize: the spec it emits must be the spec the race runner reads.

These tests are the falsifier for the tool.  A green run here means the emitted
file parses as JSON, every probe obeys the 0/1/2 exit contract the runner relies
on, the mandatory catch-all bucket is present and identified by its layer (not by
its position in the list), the output is deterministic, and the real runner in
~/.estate/libexec/hypotheses-race.py consumes the file and returns a ranking.
"""

from __future__ import annotations

import importlib.util
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "bin" / "idp-hypothesize"
RACE_RUNNER = Path.home() / ".estate" / "libexec" / "hypotheses-race.py"
ERROR_TEXT = (
    "Error: Connection error. status code 503 from http://127.0.0.1:4000/health "
    "(no body)"
)


def _load():
    loader = SourceFileLoader("idh", str(SCRIPT))
    spec = importlib.util.spec_from_loader("idh", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["idh"] = mod
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load()


def _run(args, cwd=None):
    return subprocess.run(
        [str(SCRIPT)] + args, capture_output=True, text=True, timeout=120, cwd=cwd
    )


def _generate(tmp_path, extra=None, error=ERROR_TEXT):
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    out = tmp_path / "race.json"
    metrics = tmp_path / "metrics.json"
    args = ["--error", error, "--out", str(out), "--metrics-out", str(metrics)]
    args += extra or []
    res = _run(args)
    spec = json.loads(out.read_text()) if out.exists() else None
    return res, spec, metrics


# ------------------------------------------------------------------ the contract


def test_help_exits_zero_and_is_fast():
    # The script's own cost is CPU; wall clock measures the machine, not the script.
    # A loaded laptop once made --help look 9.2s slow at 0.21s CPU, and the old
    # wall-clock bound failed the suite on that. The ceiling below is the estate's
    # own (LAW 43/45: a bare --help must exit 0 within 60s).
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.time()
    res = _run(["--help"])
    wall = time.time() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    assert res.returncode == 0, res.stderr
    assert cpu < 2.0, f"--help must cost almost no CPU, took {cpu:.2f}s"
    assert wall < 60, f"--help must exit within 60s (LAW 43/45), took {wall:.1f}s"


def test_the_emitted_spec_is_what_the_race_runner_reads(tmp_path):
    res, spec, _ = _generate(tmp_path)
    assert res.returncode == 0, res.stderr
    assert isinstance(spec["hypotheses"], list) and spec["hypotheses"]
    for key in ("parallel", "timeout", "eps"):
        assert key in spec, f"the runner reads spec[{key!r}]"
    for h in spec["hypotheses"]:
        assert h["id"]
        assert isinstance(h["falsified_if"], dict), "falsified_if must be a dict"
        assert "exit_code" in h["falsified_if"]
        assert h["evidence_exits"] == [0, 1]
        assert h["probe"].strip()
        assert 0.0 < h["prior"] <= 1.0


def test_every_probe_answers_exit_0_1_or_2(tmp_path):
    _, spec, _ = _generate(tmp_path)
    if not shutil.which("bash"):
        pytest.skip("bash is required to run the probes")
    for h in spec["hypotheses"]:
        res = subprocess.run(
            ["bash", "-c", h["probe"]], capture_output=True, text=True, timeout=60
        )
        assert res.returncode in (0, 1, 2), (
            f"{h['id']} answered exit {res.returncode}; the runner treats anything "
            f"outside evidence_exits as unknown, so the probe never votes"
        )


def test_the_catch_all_bucket_is_present_and_found_by_its_layer(tmp_path):
    res, spec, _ = _generate(tmp_path)
    assert res.returncode == 0, res.stderr
    catch = [h for h in spec["hypotheses"] if h["id"] == "H_unmodeled"]
    assert catch, "the mandatory catch-all bucket is missing"
    assert catch[0]["prior"] > 0, "the catch-all carries probability mass"
    # the catch-all is found by its layer, not by its position: H_unmodeled sorts
    # before H_upstream, so a positional check would have missed it.
    ids = [h["id"] for h in spec["hypotheses"]]
    assert ids.index("H_unmodeled") != len(ids) - 1 or len(ids) == 1
    assert spec["meta"]["noise"]["alpha"] == 0.05
    assert spec["meta"]["noise"]["beta"] == 0.10


def test_the_catch_all_probe_measures_the_error_not_a_file_nobody_writes(tmp_path):
    _, spec, _ = _generate(tmp_path)
    probe = next(h["probe"] for h in spec["hypotheses"] if h["id"] == "H_unmodeled")
    assert "race_fired_ids" not in probe, (
        "the old meta-probe read a file the runner never creates, so it always "
        "answered 0 and the catch-all always looked confirmed"
    )


def test_the_output_is_deterministic(tmp_path):
    _, first, _ = _generate(tmp_path / "a")
    _, second, _ = _generate(tmp_path / "b")
    assert first == second


def test_a_missing_root_is_reported_as_degraded(tmp_path):
    missing = tmp_path / "not-a-checkout"
    res, spec, metrics = _generate(tmp_path, ["--root", str(missing)])
    assert res.returncode == 4, "every root missing must degrade, not silently pass"
    m = json.loads(metrics.read_text())
    assert m["degraded_roots"] == 1
    assert spec["meta"]["degraded_roots"] == 1


def test_a_config_error_is_a_usage_error(tmp_path):
    bad = tmp_path / "priors.json"
    bad.write_text(json.dumps({"caller": 5.0}))
    res, spec, _ = _generate(tmp_path, ["--prior-file", str(bad)])
    assert res.returncode == 2, res.stderr
    assert spec is None

    bad_noise = tmp_path / "noise.json"
    bad_noise.write_text(json.dumps({"alpha": 0.9}))
    res, _, _ = _generate(tmp_path, ["--noise-file", str(bad_noise)])
    assert res.returncode == 2, res.stderr


def test_custom_priors_and_noise_are_honoured(tmp_path):
    priors = tmp_path / "priors.json"
    priors.write_text(
        json.dumps(
            {
                "caller": 0.05,
                "checkout": 0.05,
                "script": 0.05,
                "config": 0.05,
                "daemon": 0.05,
                "upstream": 0.75,
            }
        )
    )
    noise = tmp_path / "noise.json"
    noise.write_text(json.dumps({"alpha": 0.02, "beta": 0.20}))
    res, spec, metrics = _generate(
        tmp_path, ["--prior-file", str(priors), "--noise-file", str(noise)]
    )
    assert res.returncode == 0, res.stderr
    m = json.loads(metrics.read_text())
    assert m["error_parse"]["status"] == "503"
    assert spec["meta"]["noise"] == {"alpha": 0.02, "beta": 0.20}
    total = sum(h["prior"] for h in spec["hypotheses"])
    assert abs(total - 1.0) < 1e-6, "priors must be renormalised to 1"
    upstream = next(h for h in spec["hypotheses"] if h["id"] == "H_upstream")
    assert upstream["prior"] > 0.6, "the dominant prior must dominate the posterior"


def test_max_probes_caps_the_probe_set(tmp_path):
    res, spec, metrics = _generate(tmp_path, ["--max-probes", "3"])
    assert res.returncode == 0, res.stderr
    assert len(spec["hypotheses"]) == 3
    m = json.loads(metrics.read_text())
    assert m["probes_selected"] == 3


def test_the_catch_all_survives_the_probe_budget(tmp_path):
    """A capped spec stays MECE: the catch-all is never traded for budget."""
    res, spec, _ = _generate(tmp_path, ["--max-probes", "3"])
    assert res.returncode == 0, res.stderr
    ids = [h["id"] for h in spec["hypotheses"]]
    assert "H_unmodeled" in ids, f"the catch-all was dropped by the budget: {ids}"
    assert len(ids) == 3


def test_a_probe_budget_without_room_for_a_layer_is_a_usage_error(tmp_path):
    res, spec, _ = _generate(tmp_path, ["--max-probes", "1"])
    assert res.returncode == 2, res.stderr
    assert spec is None


def test_an_unknown_prior_layer_is_a_config_error(tmp_path):
    bad = tmp_path / "priors.json"
    bad.write_text(json.dumps({"H_caller": 0.5, "H_checkout": 0.5}))
    res, spec, _ = _generate(tmp_path, ["--prior-file", str(bad)])
    assert res.returncode == 2, res.stderr
    assert "unknown prior layer" in res.stderr
    assert spec is None


def test_the_seed_reaches_the_collapse_simulation(tmp_path):
    """--seed was parsed and then ignored: the simulation always ran on seed 7."""
    res, spec, metrics = _generate(tmp_path, ["--seed", "123"])
    assert res.returncode == 0, res.stderr
    m = json.loads(metrics.read_text())
    assert m["seed"] == 123, "the seed must be recorded in the metrics"
    assert spec["meta"]["seed"] == 123, "the seed must be recorded in the spec"

    res2, _, metrics2 = _generate(tmp_path / "same", ["--seed", "123"])
    assert res2.returncode == 0, res2.stderr
    m2 = json.loads(metrics2.read_text())
    assert (m2["sim_map_accuracy"], m2["sim_collapse_prob"]) == (
        m["sim_map_accuracy"],
        m["sim_collapse_prob"],
    ), "the same seed must reproduce the simulation exactly"

    res3, _, metrics3 = _generate(tmp_path / "other", ["--seed", "124"])
    assert res3.returncode == 0, res3.stderr
    m3 = json.loads(metrics3.read_text())
    assert (m3["sim_map_accuracy"], m3["sim_collapse_prob"]) != (
        m["sim_map_accuracy"],
        m["sim_collapse_prob"],
    ), "a different seed must move the simulation"


def test_an_error_without_structure_still_yields_the_chain(tmp_path):
    res, spec, metrics = _generate(tmp_path, error="something went wrong")
    assert res.returncode == 0, res.stderr
    m = json.loads(metrics.read_text())
    assert m["parse_confidence"] == "low"
    assert len(spec["hypotheses"]) >= 2


def test_the_metrics_file_carries_the_measurements(tmp_path):
    res, _, metrics = _generate(tmp_path)
    assert res.returncode == 0, res.stderr
    m = json.loads(metrics.read_text())
    for key in (
        "expected_ig_bits",
        "ig_per_token",
        "selection",
        "sim_map_accuracy",
        "sim_collapse_prob",
        "catch_all_present",
        "spec_sha256",
    ):
        assert key in m, key
    assert m["catch_all_present"] is True
    assert m["expected_ig_bits"] > 0
    assert m["selection"] in ("exact", "greedy")


class _Lcg:
    """A deterministic pseudo-random source.

    The estate's python-strict rung runs ruff over E9,F,B,S, and S311 flags the
    `random` module -- so the test draws from this instead: reproducible, and
    nothing for the gate to refuse.
    """

    def __init__(self, seed: int) -> None:
        self.state = seed

    def next(self) -> float:
        self.state = (1103515245 * self.state + 12345) % (2**31)
        return self.state / (2**31)

    def randint(self, low: int, high: int) -> int:
        return low + int(self.next() * (high - low + 1))


def test_exact_selection_is_the_true_optimum(mod):
    noise = {"alpha": 0.05, "beta": 0.10}
    rng = _Lcg(3)
    for _ in range(5):
        n = rng.randint(4, 6)
        priors = mod.normalize({f"H{i}": rng.next() + 0.01 for i in range(n)})
        hyps = [
            mod.Hypothesis(
                id=k,
                layer="x",
                prior=v,
                probe="true",
                falsified_if={},
                evidence="",
                dedup_key=k,
            )
            for k, v in priors.items()
        ]
        k = 2
        chosen = mod.exact_select(hyps, noise, k)
        got = mod.info_gain(chosen, priors, noise)
        best = -1.0
        ids = list(priors)
        for mask in range(1 << n):
            if bin(mask).count("1") != k:
                continue
            sub = [ids[i] for i in range(n) if mask >> i & 1]
            best = max(best, mod.info_gain(sub, priors, noise))
        assert got >= best - 1e-9, "exact selection must reach the brute-force optimum"


@pytest.mark.skipif(
    not RACE_RUNNER.exists(), reason="the real race runner is not installed"
)
def test_the_real_race_runner_consumes_the_spec(tmp_path):
    res, spec, _ = _generate(tmp_path)
    assert res.returncode == 0, res.stderr
    out = tmp_path / "race_result.json"
    run = subprocess.run(
        [sys.executable, str(RACE_RUNNER), str(tmp_path / "race.json")],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr
    result = json.loads(out.read_text()) if out.exists() else json.loads(run.stdout)
    assert result["ranked"], "the runner must return a ranking"
    assert set(result["posteriors"]) == {h["id"] for h in spec["hypotheses"]}
    assert abs(sum(result["posteriors"].values()) - 1.0) < 1e-6


def test_the_script_is_executable_and_declares_a_shebang():
    assert os.access(SCRIPT, os.X_OK), "bin/idp-hypothesize must be executable"
    assert SCRIPT.read_text().startswith("#!/usr/bin/env python3")
