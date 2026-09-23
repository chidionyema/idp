"""CP6 spatial intent resolver: turn a phrase like 'the one on the left' or
'the second from the right' into a concrete sha from a list of comets.

This is the smallest piece of CP6: a pure function with no I/O, no LLM. The
voice service (backstage/plugins/fleetview-backend/src/voice.py) calls this
when the user's intent is spatial rather than named.

Rules (locked in here):
  - 'the one on the left' / 'leftmost'  -> index 0 of comets
  - 'the one on the right' / 'rightmost' -> index -1 of comets
  - 'the second from the left' / '2nd from left' -> index 1
  - 'the Nth from the right' -> index -N
  - 'the topmost' / 'top' -> index 0 (same as left; the list order is
    defined upstream by estate-river-data, oldest-newest by started_at)
  - unresolvable intent -> BLIND with a named error, never a guess
"""

from __future__ import annotations

import re
from typing import Sequence

_LEFTMOST = {
    "the one on the left",
    "leftmost",
    "left",
    "the first",
    "the top one",
    "the top",
    "top",
    "topmost",
}
_RIGHTMOST = {
    "the one on the right",
    "rightmost",
    "right",
    "the last",
    "the bottom one",
    "the bottom",
    "bottom",
    "bottommost",
}
_ORIDINAL_FROM_LEFT = re.compile(r"the\s+(\d+)(?:st|nd|rd|th)\s+from\s+the\s+left")
_ORDINAL_FROM_RIGHT = re.compile(r"the\s+(\d+)(?:st|nd|rd|th)\s+from\s+the\s+right")
_PLAIN_ORDINAL = re.compile(
    r"^(?:the\s+)?(\d+)(?:st|nd|rd|th)?\s+one\s*$", re.IGNORECASE
)


def resolve(intent: str, comets: Sequence[str]) -> dict:
    """Resolve a spatial-intent phrase to a sha from `comets`.

    Returns one of:
      {"available": True,  "sha": ..., "index": N}            (resolved)
      {"available": True,  "sha": None, "error": "..."}       (unresolvable
                                                               but honest)
      {"available": False, "sha": None, "error": "..."}       (BLIND: empty
                                                               list)
    """
    if not comets:
        return {
            "available": False,
            "sha": None,
            "error": "no comets visible; cannot resolve spatial intent",
        }
    phrase = (intent or "").strip().lower().rstrip(".")
    if not phrase:
        return {
            "available": True,
            "sha": None,
            "error": f"empty intent; expected a spatial phrase",
        }

    if phrase in _LEFTMOST:
        return {"available": True, "sha": comets[0], "index": 0, "rule": "leftmost"}
    if phrase in _RIGHTMOST:
        return {
            "available": True,
            "sha": comets[-1],
            "index": len(comets) - 1,
            "rule": "rightmost",
        }

    m = _ORIDINAL_FROM_LEFT.search(phrase)
    if m:
        n = int(m.group(1))
        if 1 <= n <= len(comets):
            return {
                "available": True,
                "sha": comets[n - 1],
                "index": n - 1,
                "rule": f"{n}th from left",
            }
        return {
            "available": True,
            "sha": None,
            "error": f"{n}th from left out of range (have {len(comets)})",
        }

    m = _ORDINAL_FROM_RIGHT.search(phrase)
    if m:
        n = int(m.group(1))
        if 1 <= n <= len(comets):
            return {
                "available": True,
                "sha": comets[-n],
                "index": len(comets) - n,
                "rule": f"{n}th from right",
            }
        return {
            "available": True,
            "sha": None,
            "error": f"{n}th from right out of range (have {len(comets)})",
        }

    m = _PLAIN_ORDINAL.match(phrase)
    if m:
        n = int(m.group(1))
        if 1 <= n <= len(comets):
            return {
                "available": True,
                "sha": comets[n - 1],
                "index": n - 1,
                "rule": f"the {n}th one",
            }
        return {
            "available": True,
            "sha": None,
            "error": f"the {n}th one out of range (have {len(comets)})",
        }

    return {
        "available": True,
        "sha": None,
        "error": f"unrecognised spatial intent: {intent!r}",
    }
