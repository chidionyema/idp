"""Ratchet: no new file may name the Telegram API. The one door to the founder is estate-founder-gate."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
ALLOW = ROOT / "catalog" / "founder-telegram-senders.json"
NEEDLE = "api.telegram.org"
SKIP = ("docs/", "rescued_patches2/")
SELF = {
    "catalog/founder-telegram-senders.json",
    "tests/test_founder_telegram_ratchet.py",
    "bin/estate-founder-gate",
}


def offenders(files, read, allowed):
    """Files that name the API and are neither allowed nor exempt. Pure, so the falsifier can feed it."""
    bad = []
    for name in files:
        if name in SELF or name.startswith(SKIP) or name in allowed:
            continue
        try:
            text = read(name)
        except (OSError, UnicodeDecodeError):
            continue
        if NEEDLE in text:
            bad.append(name)
    return sorted(bad)


def test_falsifier_a_new_sender_is_caught_and_an_allowed_one_is_not():
    files = ["bin/new-notifier", "bin/estate-fleet-telegram", "docs/x.md", "README.md"]
    text = {
        "bin/new-notifier": f"https://{NEEDLE}/bot",
        "bin/estate-fleet-telegram": f"https://{NEEDLE}/bot",
        "docs/x.md": NEEDLE,
        "README.md": "no",
    }
    assert offenders(files, text.__getitem__, {"bin/estate-fleet-telegram"}) == [
        "bin/new-notifier"
    ]
    assert offenders(files, text.__getitem__, set()) == [
        "bin/estate-fleet-telegram",
        "bin/new-notifier",
    ]


def test_allowlist_is_sorted_unique_and_every_entry_exists():
    senders = json.loads(ALLOW.read_text())["senders"]
    assert senders == sorted(set(senders)) and senders
    missing = [s for s in senders if not (ROOT / s).exists()]
    assert missing == [], f"allowlist names files that are gone, shrink it: {missing}"


def test_no_file_outside_the_allowlist_names_the_telegram_api():
    allowed = set(json.loads(ALLOW.read_text())["senders"])
    listing = subprocess.run(  # noqa: S603
        [shutil.which("git") or "git", "-C", str(ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=True,  # noqa: S607
    ).stdout.splitlines()
    bad = offenders(listing, lambda n: (ROOT / n).read_text(encoding="utf-8"), allowed)
    assert bad == [], (
        f"route founder messages through bin/estate-founder-gate, not the API: {bad}"
    )
