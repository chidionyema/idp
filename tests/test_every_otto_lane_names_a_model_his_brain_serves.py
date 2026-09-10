"""A lane Otto routes on names a model group his brain actually serves.

Measured in the live gateway pod on 2026-09-10, from inside the container
that answers the founder:

    ROUTER_BASE http://127.0.0.1:4010/v1
    SERVED ['deepseek', 'embed', 'gemini', 'home-direct', 'home-estate',
            'home-floor', 'home-floor-2', 'home-floor-3', 'home-floor-4',
            'home-floor-5', 'minimax']
    KIMI_FAIL HTTP 400 {"error":{"message":"/chat/completions: Invalid model
            name passed in model=kimi..."}}

Otto's door does not call the estate router. It calls the otto-brain sidecar
in its own pod, and that brain serves the eleven groups above. The deep lane
-- the one a `/think` message reaches -- had no row in the ConfigMap, so
``otto/router/config.py`` fell back to its own default, ``kimi``, a name the
brain has never served. Every `/think` turn therefore ended
``needs_human``, and the founder read "I could not reach the model, so I have
not answered." Fourteen of his turns ended that way on 2026-09-10 alone.

Two ways for that to happen, and this closes both: a lane naming a group the
brain does not serve, and a lane with no row at all -- which is the same
defect wearing a default.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
LANES = ROOT / "platform" / "otto-gateway" / "router-lanes.yaml"
BRAIN = ROOT / "platform" / "otto-gateway" / "three-homes.yaml"

#: The lanes ``_DEFAULT_LANE_MODELS`` in otto/router/config.py declares. Each
#: one carries a vendor default the estate cannot call ("anthropic/claude",
#: "kimi", "google/gemini"), so a lane missing from the ConfigMap is not an
#: unused lane -- it is a lane pointed at a vendor with no key and no row.
LANES_THE_ROUTER_DEFINES = {"judgment", "bulk", "verify", "deep"}


def _config_map(path):
    for doc in yaml.safe_load_all(path.read_text()):
        if doc and doc.get("kind") == "ConfigMap":
            return doc
    raise AssertionError(f"no ConfigMap in {path}")


def _lane_models():
    data = _config_map(LANES)["data"]
    out = {}
    for key, value in data.items():
        if key.startswith("OTTO_ROUTER_LANE_") and key.endswith("_MODEL"):
            out[key[len("OTTO_ROUTER_LANE_") : -len("_MODEL")].lower()] = value
    return out


def _served_groups():
    brain = yaml.safe_load(_config_map(BRAIN)["data"]["config.yaml"])
    served = {row["model_name"] for row in brain["model_list"]}
    aliases = (brain.get("router_settings") or {}).get("model_group_alias") or {}
    # An alias resolves only when its target is itself a served group.
    served |= {name for name, target in aliases.items() if target in served}
    return served


def test_every_lane_names_a_group_the_brain_serves():
    served = _served_groups()
    unserved = {
        lane: model for lane, model in _lane_models().items() if model not in served
    }
    assert not unserved, (
        f"lanes pointed at groups otto-brain does not serve: {unserved}; "
        f"served: {sorted(served)}"
    )


def test_no_lane_is_left_on_the_library_default():
    missing = LANES_THE_ROUTER_DEFINES - set(_lane_models())
    assert not missing, (
        f"lanes with no row in {LANES.name}: {sorted(missing)}; each falls back "
        "to a vendor default the brain does not serve"
    )


def test_the_brain_serves_more_than_one_home():
    # The founder's standing order: three homes, no single point of failure.
    homes = {g for g in _served_groups() if g.startswith("home-")}
    assert len(homes) >= 3, f"only {sorted(homes)}"
