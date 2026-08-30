"""crew#684 CP3: every alert rule and every drill names an owner, and an unowned red pages.

Founder, 2026-08-30: "A red with no owner is itself a red." Before this, none of the nine
alert rules and none of the fourteen drills said who was on them, so the Ops page's open-reds
table (CP2) would have shown `No owner` on every row and nobody would have been paged.

The gate: an alert rule without `labels.owner`, or a drill without `owner`, is refused; the
owner is a session lane or a human, from one list; and the Alertmanager route that pages an
unowned alert after ten minutes must exist, or the rule is a wish (LAW 44).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULES = sorted((ROOT / "platform/monitoring/rules").glob("*.yaml"))
CATALOGUE = ROOT / "drills/catalogue.yaml"
ALERTMANAGER = ROOT / "platform/monitoring/alertmanager-config.yaml"

# Lanes as the feed names them, plus the one human. A new lane is added here on purpose.
OWNERS = {"idp", "science", "crew", "founder"}


def _alerts():
    for f in RULES:
        for doc in yaml.safe_load_all(f.read_text()):
            if not doc or doc.get("kind") != "PrometheusRule":
                continue
            for group in doc["spec"].get("groups", []):
                for rule in group.get("rules", []):
                    if "alert" in rule:
                        yield f.name, rule


def test_every_alert_rule_names_an_owner_from_the_list():
    alerts = list(_alerts())
    assert alerts, "no alert rules found"
    bad = [
        f"{f}:{r['alert']}"
        for f, r in alerts
        if (r.get("labels") or {}).get("owner") not in OWNERS
    ]
    assert not bad, f"alert rules with no owner from {sorted(OWNERS)}: {bad}"


def test_every_drill_names_an_owner_from_the_list():
    drills = yaml.safe_load(CATALOGUE.read_text())["drills"]
    assert len(drills) >= 14
    bad = [d["name"] for d in drills if d.get("owner") not in OWNERS]
    assert not bad, f"drills with no owner from {sorted(OWNERS)}: {bad}"


def test_an_unowned_alert_pages_after_ten_minutes():
    # The config is a go-template inside an ExternalSecret, so it is read as text.
    text = ALERTMANAGER.read_text()
    route = re.search(
        r"- receiver: telegram-p1-page\n(?:\s+.*\n)*?\s+matchers: \['owner = \"\"'.*\n(?:\s+.*\n)*?\s+group_wait: 10m",
        text,
    )
    assert route, 'a route for owner="" to telegram-p1-page with group_wait 10m'
    assert re.search(r"- name: telegram-p1-page\n\s+telegram_configs:", text)
    assert "P1 page" in text
