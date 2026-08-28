"""crew#539, 2026-08-27: the descheduler CronJob exited 1 on every run since it landed —
`failed to create new descheduler: unable to create "rebalance-after-node-swap" profile: unable
to build RemoveDuplicates plugin: unable to find "RemoveDuplicates" plugin config` (pod
descheduler-29797890-zkr5n Failed, oke-check receipt 33127558382). Descheduler 0.36 requires a
pluginConfig entry for every plugin a profile enables; the profile enabled RemoveDuplicates in
`balance` and configured four other plugins only. A healer that never runs is a paper healer
(LAW 28). Rule: every plugin enabled under any profile's plugins.* has a pluginConfig entry of
the same name. Rung 4, incident test both ways."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/healing/descheduler.yaml"


def _profiles(doc=None):
    if doc is None:
        docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
        doc = next(d for d in docs if d["kind"] == "HelmRelease")
    return doc["spec"]["values"]["deschedulerPolicy"]["profiles"]


def missing_config(profiles) -> list[str]:
    out = []
    for p in profiles:
        configured = {c["name"] for c in p.get("pluginConfig", [])}
        for stage, spec in (p.get("plugins") or {}).items():
            for name in spec.get("enabled", []):
                if name not in configured:
                    out.append(f"{p['name']}/{stage}/{name}")
    return out


def test_every_enabled_plugin_has_a_pluginconfig_entry():
    profiles = _profiles()
    assert "RemoveDuplicates" in profiles[0]["plugins"]["balance"]["enabled"], "the incident plugin is still enabled"
    assert missing_config(profiles) == []


def test_the_incident_shape_is_named():
    broken = [{"name": "rebalance-after-node-swap",
               "pluginConfig": [{"name": "DefaultEvictor"}, {"name": "LowNodeUtilization"}],
               "plugins": {"balance": {"enabled": ["RemoveDuplicates", "LowNodeUtilization"]}}}]
    assert missing_config(broken) == ["rebalance-after-node-swap/balance/RemoveDuplicates"]
