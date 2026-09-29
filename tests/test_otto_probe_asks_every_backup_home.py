"""Otto's answer-probe must ask every backup home the in-pod brain can fail over to."""

import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _probe(tmp_path, monkeypatch):
    docs = yaml.safe_load_all(
        (ROOT / "platform/otto-gateway/answer-probe.yaml").read_text()
    )
    script = next(d for d in docs if d and d.get("kind") == "ConfigMap")["data"][
        "probe.py"
    ]
    homes = next(
        d
        for d in yaml.safe_load_all(
            (ROOT / "platform/otto-gateway/three-homes.yaml").read_text()
        )
        if d and d.get("kind") == "ConfigMap"
    )["data"]["config.yaml"]
    (tmp_path / "config.yaml").write_text(homes)
    (tmp_path / "probe.py").write_text(script)
    monkeypatch.setenv("OTTO_HOMES_CONFIG", str(tmp_path / "config.yaml"))
    monkeypatch.setenv("OTTO_HOMES_SECRETS", str(tmp_path / "sec"))
    spec = importlib.util.spec_from_file_location("otto_probe", tmp_path / "probe.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, yaml.safe_load(homes)


def test_every_off_cluster_home_is_probed(tmp_path, monkeypatch):
    probe, cfg = _probe(tmp_path, monkeypatch)
    want = {
        m["model_name"]
        for m in cfg["model_list"]
        if m["model_name"].startswith("home-")
        and str(m["litellm_params"].get("api_base", "")).startswith("https://")
    }
    got = {h["name"] for h in probe.backup_homes()}
    assert want and got == want


def test_home_key_reads_the_mounted_file(tmp_path, monkeypatch):
    probe, _ = _probe(tmp_path, monkeypatch)
    (tmp_path / "sec" / "floor").mkdir(parents=True)
    (tmp_path / "sec" / "floor" / "GROQ_API_KEY").write_text("k\n")
    assert probe.home_key("GROQ_API_KEY") == "k"
    assert probe.home_key("MINIMAX_API_KEY") == ""
