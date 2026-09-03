"""Incident guard (founder 2026-09-03: the router had no shared cache): two router
pods without a shared store each keep their own cooldowns, rate counts and spend
windows, and an identical call is paid for twice. This guard holds the wiring both
ways (LAW 15): the shared-state rows and the bounded answer cache are in the served
config, the cache service ships with a minted — never typed — password, and the
router pod mounts it, so the os.environ reference in the config resolves.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LLM = ROOT / "platform" / "llm"


def served():
    return yaml.safe_load((LLM / "config.yaml").read_text())


def test_router_state_is_shared_across_replicas():
    rs = served()["router_settings"]
    assert rs["redis_host"] == "litellm-cache.llm.svc"
    assert rs["redis_port"] == 6379
    ref = rs["redis_password"]
    assert ref.startswith("os.environ/"), (
        "the password must be an environment reference, never a value in git"
    )
    assert ref.split("/", 1)[1] == "REDIS_PASSWORD"


def test_answer_cache_is_on_and_bounded():
    ls = served()["litellm_settings"]
    assert ls["cache"] is True
    cp = ls["cache_params"]
    assert cp["type"] == "redis"
    assert cp["password"].startswith("os.environ/")
    assert isinstance(cp["ttl"], int) and 0 < cp["ttl"] <= 600, (
        "a reused answer must die within ten minutes"
    )


def test_cache_service_ships_with_a_minted_password_and_no_literal():
    text = (LLM / "redis.yaml").read_text()
    assert "kind: Password" in text, "the password is minted in-cluster, no vault hand"
    assert 'requirepass "$(cat /run/secrets/litellm/cache/REDIS_PASSWORD)"' in text
    assert "redis.yaml" in (LLM / "kustomization.yaml").read_text()


def test_router_pod_mounts_the_cache_secret():
    text = (LLM / "litellm.yaml").read_text()
    assert "/run/secrets/litellm/cache" in text
    assert "secretName: litellm-cache" in text
