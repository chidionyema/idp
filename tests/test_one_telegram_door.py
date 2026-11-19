"""The founder's Telegram has one door, and the set of files that knock on it directly only shrinks.

Founder, 2026-11-19 15:31: Telegram must be an ultra high net worth VIP experience and never another
source of noise and friction. The policy that makes it so (classes, at most three sounds an hour, quiet
hours, repeats silent, receipts folded into one silent digest) lives in ONE gateway: argon's
bin/genesis_tg.py, run by the one cloud door (argon genesis-outbox.yml). Measured the same day: idp held
22 tracked files naming the Bot API, each with its own idea of when to message the founder.

This is the ratchet (AC): every file below is named, the set may only shrink as senders move to the
outbox, and a NEW direct caller fails CI. Network/allow-list config that names the host is listed too,
because a fence that admits the host is how a new sender would reach it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KNOWN = {
    # senders: debt, to route through the one door
    ".github/workflows/otto-parity.yml",
    ".github/workflows/ping.yml",
    "bin/estate-fleet-telegram",
    "bin/estate-founder",
    "bin/pin-open",
    "factory/surfaces/telegram.py",
    "infra/recovery/telegram-digest.py",
    "platform/estate/governance/state_page.py",
    "platform/jit/broker/telegram.py",
    "platform/lifeboat/src/index.js",  # replies to the founder's own messages (the webhook door)
    "sovereign/otto/decision.py",
    "web/lib/contact.ts",
    # configuration and fences that name the host
    "bin/idp-ns-fence-gen",
    "platform/jit/fence.yaml",
    "platform/ns-fences/allowances.yaml",
    "platform/otto-gateway/registration-reconciler.yaml",
    "platform/otto-golden/network-policy.yaml",
    "platform/vendors/consoles.yaml",
    "sovereign/cockpit/config_keys.py",
    "sovereign/otto/config_keys.py",
}

EXCLUDE = (
    ":!*.md",
    ":!tests/**",
    ":!web/tests/**",
    ":!platform/lifeboat/test/**",
    ":!docs/**",
    ":!archive/**",
    ":!rescued_patches*/**",
    ":!forge/datasets/**",
    ":!catalog/estate-capability-registry.json",
    ":!.aevum/**",
)


def _callers() -> set[str]:
    out = subprocess.run(
        ["git", "grep", "-l", "api.telegram.org", "--", ".", *EXCLUDE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode in (0, 1), out.stderr
    return {line for line in out.stdout.splitlines() if line}


def test_no_new_direct_telegram_sender():
    new = sorted(_callers() - KNOWN)
    assert new == [], (
        "a new file reaches the founder's Telegram directly; write a turn packet to the outbox "
        f"(the one door, argon genesis-outbox.yml) instead: {new}"
    )


def test_the_known_list_only_shrinks():
    gone = sorted(KNOWN - _callers())
    assert gone == [], (
        f"these no longer call the Bot API: remove them from KNOWN so the ratchet holds: {gone}"
    )
