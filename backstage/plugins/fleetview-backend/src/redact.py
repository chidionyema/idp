"""Redact likely secrets from free text before it reaches the board.

WHY THIS EXISTS, AND WHAT IT IS NOT.

Measured by review 2026-09-20: the pi extension posts each assistant turn's text to `/replies`,
unredacted, and the board renders it. The extension's own comment claimed a reply "must not leak a
command line, a token or a file path" -- true of *tool arguments*, which it excludes, but NOT of
assistant text, which routinely quotes a path and can quote a credential the agent just read.

VERIFIED: the estate already has `handoff.assert_no_secret`, which is the right tool for a
STRUCTURED payload -- it walks keys and values and RAISES. That is exactly wrong here:

  * a reply is free text, not a keyed structure, so there is nothing to walk;
  * raising would DROP the message, and a conversation that silently loses turns is worse than one
    that shows a redacted line. The board's rule everywhere else is to say what happened.

So this replaces the match with a visible marker instead of refusing. It is a MITIGATION, not a
guarantee, and it says so: a pattern list cannot recognise a credential that looks like an ordinary
sentence, and it will occasionally redact something innocent (a long hex string in a commit hash is
caught by the same rule as a key). Both failures are named here rather than papered over.

WHY NOT RENDER-SIDE ONLY. Redaction at the writer means the secret never enters the database, never
appears in the audit trail, and is not readable by anything else that reads `fleetview_replies` --
including the fleet-wide feed the panel shows.
"""
from __future__ import annotations

import re

# Ordered longest-prefix-first inside each family so a specific case is never half-matched by a
# general one. Every pattern is anchored to a distinctive prefix or shape: a bare 32-hex string is
# NOT redacted, because git short hashes and build ids are ordinary in this estate's answers and
# redacting them would make the board useless.
# ORDER MATTERS, and the ASSIGNMENT rule runs FIRST.
#
# `LITELLM_API_KEY=sk-abc...` matches two rules: the value looks like a vendor key, and the name
# says it is a secret. Running the vendor rule first replaced only `sk-abc...`, leaving the tail of
# the assignment capture (` key]`) stranded in the output -- a cosmetic bug with a real cause, the
# same span matched twice. The assignment rule consumes the WHOLE `NAME=value` unit, so the vendor
# patterns never see the value at all.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Assignments. The NAME is the signal; the value is hidden and the name kept, so a reader still
    # learns which variable was present without seeing it.
    (
        "assigned secret",
        re.compile(
            r"(?i)\b((?:[A-Za-z0-9_]*_)?(?:SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|ACCESS_?KEY|"
            r"PRIVATE_?KEY|CLIENT_?SECRET|BEARER|CREDENTIAL)[A-Za-z0-9_]*)\s*[=:]\s*"
            # The value stops at whitespace, a quote, a comma, a semicolon, or a closing bracket --
            # and an unbalanced `]` at the end of a token is dropped by the trailing guard, so
            # `sk-abc]` inside prose does not carry the bracket into the marker.
            r"[\"']?([^\s\"',;\]]{8,})[\"']?"
        ),
    ),
    # Vendor keys with unmistakable prefixes.
    ("openai/anthropic-style key", re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}\b")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("github fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b")),
    ("slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("aws access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("google api key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")),
    # An Authorization header, which is the shape a curl transcript produces.
    ("authorization header", re.compile(r"(?i)\bauthorization\s*:\s*(?:bearer|basic|token)\s+\S+")),
    # A URL with credentials embedded: scheme://user:pass@host
    ("credentials in a URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@")),
)

# What replaces a match. Deliberately ugly and greppable: a reader must be able to tell that
# something was removed, and a search for `REDACTED` must find every case.
MARK = "[REDACTED:{why}]"
SECRET_MARK_RE = re.compile(r"\[REDACTED:[^\]]+\]")


def redact(text: str) -> tuple[str, list[str]]:
    """Return (safe text, the kinds of thing that were removed).

    The second value is returned rather than logged so the CALLER decides what to do with it -- for
    a reply, the count goes into the response so the board can say a message was redacted rather
    than quietly showing an edited one.
    """
    if not text:
        return text, []
    found: list[str] = []
    out = text
    for why, pattern in _PATTERNS:
        def _sub(m: re.Match[str], why: str = why) -> str:
            found.append(why)
            # PRESERVE THE NAME in an assignment, so `TOKEN=abc` becomes `TOKEN=[REDACTED:...]` and
            # the reader still learns which variable was present.
            if m.re.groups >= 2 and m.group(1):
                return f"{m.group(1)}={MARK.format(why=why)}"
            return MARK.format(why=why)

        out = pattern.sub(_sub, out)
    return out, found
