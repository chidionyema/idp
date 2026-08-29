"""crew#506 CP4 (2026-08-27): adding the free Groq lane needed one key in the vault entry
`litellm-upstream`, and the only writer, bin/idp-vault-put, replaced the whole JSON from the env
file it was given; the oke-check apply step also exited n/a unless SEED_LITELLM_MASTER_KEY was set,
which it was not. So one new provider meant re-seeding every key. Both ways: on main the --merge
path does not exist and the groq lane is in neither router config."""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUT = ROOT / "bin" / "idp-vault-put"
CONFIGS = [ROOT / "platform" / "llm" / "config.yaml", ROOT / "llm" / "config.yaml"]


def _merge_block() -> str:
    text = PUT.read_text()
    start = text.index("<<'PY'\n") + len("<<'PY'\n")
    return text[start : text.index("\nPY\n", start)]


def _run(env_lines: str, current: dict | None, merge: bool, pairs: list[str], tmp_path: pathlib.Path) -> subprocess.CompletedProcess:
    envf = tmp_path / "seed.env"
    envf.write_text(env_lines)
    env = dict(os.environ, MERGE="1" if merge else "0")
    env["CURRENT"] = json.dumps(current) if current is not None else ""  # crew#66 CP4: plain JSON, read in-process
    return subprocess.run([sys.executable, "-", str(envf), *pairs], input=_merge_block(), env=env, capture_output=True, text=True)


def test_merge_overlays_one_key_and_keeps_the_rest(tmp_path: pathlib.Path) -> None:
    held = {"MINIMAX_API_KEY": "m", "DEEPSEEK_API_KEY": "d", "LITELLM_MASTER_KEY": "k"}
    r = _run("GROQ_API_KEY=g\n", held, True, ["MINIMAX_API_KEY=MINIMAX_API_KEY", "GROQ_API_KEY=GROQ_API_KEY"], tmp_path)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[0])
    assert out == {**held, "GROQ_API_KEY": "g"}
    # names only on stderr, never a value
    assert "keys set: GROQ_API_KEY" in r.stderr and "kept:" in r.stderr and "g" not in r.stderr.split("kept:")[0].replace("GROQ_API_KEY", "")


def test_without_merge_an_unset_key_is_still_an_error(tmp_path: pathlib.Path) -> None:
    r = _run("GROQ_API_KEY=g\n", None, False, ["MINIMAX_API_KEY=MINIMAX_API_KEY"], tmp_path)
    assert r.returncode != 0 and "missing MINIMAX_API_KEY" in r.stderr


def test_merge_with_nothing_set_writes_nothing(tmp_path: pathlib.Path) -> None:
    r = _run("", {"MINIMAX_API_KEY": "m"}, True, ["GROQ_API_KEY=GROQ_API_KEY"], tmp_path)
    assert r.returncode != 0 and r.stdout == ""


def test_every_writer_of_the_router_entry_merges_and_no_seed_secret_remains() -> None:
    """crew#66 root trust (crew#575, crew#579): the SEED_* step is gone; the entry is now written by
    bin/idp-estate-seed (master key) and bin/idp-bootstrap-vendors (provider keys). Both must --merge,
    or one new provider would again re-seed every key -- the incident this file closes."""
    wf = (ROOT / ".github" / "workflows" / "oke-check.yml").read_text()
    # R52: SEED_GROQ_API_KEY is the vendor's one root and rides the bin/idp-bootstrap-vendors step only;
    # no step writes litellm-upstream whole from it.
    assert wf.count("SEED_GROQ_API_KEY") == 2 and "bin/idp-vault-put --merge litellm-upstream" not in wf
    assert re.search(r"^\s+run: bin/idp-estate-seed\s*$", wf, re.M)
    seed = (ROOT / "bin" / "idp-estate-seed").read_text()
    assert "--merge" in seed, "estate-seed writes one key at a time on top of what the vault holds"
    vendors = (ROOT / "bin" / "idp-bootstrap-vendors").read_text()
    assert '"--merge", entry' in vendors, "a vendor key lands beside the others, never over them"


def test_groq_lane_in_both_router_configs_with_the_key_documented() -> None:
    for cfg in CONFIGS:
        models = {m["model_name"]: m for m in yaml.safe_load(cfg.read_text())["model_list"]}
        assert models["groq"]["litellm_params"]["api_key"] == "os.environ/GROQ_API_KEY", cfg
        assert models["groq"]["litellm_params"]["model"] == "groq/openai/gpt-oss-120b", cfg
        assert models["groq"]["model_info"]["max_input_tokens"] == 131072, cfg
        chains = {k: v for e in yaml.safe_load(cfg.read_text())["router_settings"]["fallbacks"] for k, v in e.items()}
        # a rate-limited free lane falls to a paid direct lane first, never to another free lane
        assert chains["groq"][0] == "minimax" and chains["groq"][-1] == "deepseek", cfg
    es = (ROOT / "platform" / "llm" / "external-secret.yaml").read_text()
    assert re.search(r"GROQ_API_KEY=GROQ_API_KEY", es) and "--merge" in es
