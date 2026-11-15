"""Founder, 2026-11-14: two cloud homes for every critical service, period.

The laptop may only ever be a DR home, with an expiry. A service with one cloud home is refused --
a single home is not a home, and a shared provider dressed as three services is one provider.

This reads the same catalogue the drill reads, so the rule and the runtime cannot disagree.
"""

import json
from pathlib import Path


LANES = Path(__file__).resolve().parents[1] / "platform/ladder/critical-lanes.json"
LAPTOP = {"laptop", "macbook", "darwin-local", "localhost"}


def services() -> list[dict]:
    return json.loads(LANES.read_text()).get("services", [])


def cloud_providers(service: dict) -> set[str]:
    provs = set()
    for leg in service.get("legs", []):
        p = str(leg.get("provider", "")).lower()
        if p and p not in LAPTOP:
            provs.add(p)
    return provs


def test_every_critical_service_names_two_cloud_homes():
    thin = [
        f"{s['service']}: {len(cloud_providers(s))} cloud home(s) "
        f"({', '.join(sorted(cloud_providers(s))) or 'none'})"
        for s in services()
        if len(cloud_providers(s)) < 2
    ]
    assert not thin, (
        "every critical service needs two cloud homes; refused:\n  " + "\n  ".join(thin)
    )


def test_no_critical_service_is_hosted_on_the_laptop():
    """A laptop leg is allowed only as a DR lifeline, and only with an expiry."""
    offenders = []
    for s in services():
        for leg in s.get("legs", []):
            if str(leg.get("provider", "")).lower() not in LAPTOP:
                continue
            if leg.get("role") != "dr" or not leg.get("expires_at"):
                offenders.append(
                    f"{s['service']}: laptop leg '{leg.get('name')}' "
                    f"role={leg.get('role', 'home')} expires_at={leg.get('expires_at', '-')}"
                )
    assert not offenders, (
        "the laptop may only ever be a DR home with an expiry:\n  "
        + "\n  ".join(offenders)
    )


def test_the_catalogue_is_not_empty():
    assert services(), "an empty catalogue proves nothing"
