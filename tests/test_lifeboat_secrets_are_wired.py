"""Every secret the lifeboat reads must be wired where the lifeboat is deployed.

#8260 landed the off-host founder seal in platform/lifeboat/src/seal.js, which reads
FOUNDER_SEAL_TOKEN and FOUNDER_SEAL_KEY_PEM. Neither name existed in the deploy
command (bin/idp-otto-homes) or wrangler.toml, so the Worker could never receive
them: /seal answered 401 unauthorized for every caller and the guarded-path seal
had no off-host producer at all.

This test is the falsifier. It fails on main and passes once the names are wired.
Variables that are not secrets (URLs, optional lanes) are listed as exempt on
purpose, so adding a genuinely new secret cannot slip in unwired.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Not secrets: public endpoints, optional lanes and per-request inputs.
EXEMPT = {
    "AI",
    "GENESIS_REALTIME_URL",
    "MACBOOK_WEBHOOK_URL",
    "OMNIFLOW_RELAY_URL",
    "ORIGIN_WEBHOOK_URL",
}


def _read_env_names() -> set[str]:
    names: set[str] = set()
    for path in (ROOT / "platform/lifeboat/src").glob("*.js"):
        names.update(
            re.findall(r"env\.([A-Z][A-Z0-9_]+)", path.read_text(encoding="utf-8"))
        )
    return names


def _wired_names() -> set[str]:
    text = (ROOT / "bin/idp-otto-homes").read_text(encoding="utf-8")
    return set(re.findall(r"^\s+\(\"([A-Z][A-Z0-9_]+)\", \[", text, re.M))


def test_every_secret_the_lifeboat_reads_is_wired() -> None:
    missing = sorted(_read_env_names() - _wired_names() - EXEMPT - set(ALIASES))
    assert not missing, (
        "the lifeboat reads secrets its deploy never sets, so the feature that "
        f"needs them cannot work: {missing}"
    )


ALIASES = {
    "GITHUB_TOKEN": "OMNIFLOW_GH_TOKEN"
}  # alternate name for the same credential
