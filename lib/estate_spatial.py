"""CP6 spatial intent resolver: turn a phrase like 'the one on the left',
'the second from the right', or 'the red one' into a concrete sha from a
list of comets.

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
  - 'the red one' / 'the green one' -> first comet whose status matches
    the colour. Red = failed, green = merged, blue = in_flight, grey =
    abandoned. Voice leads with colour because a glance at the river gives
    the colour before the name; the resolver reads status, not pixels.
  - unresolvable intent -> BLIND with a named error, never a guess

INPUT SHAPE.
  `comets` may be a flat Sequence[str] (legacy: shas only) or a
  Sequence[dict] with at least {'sha': str, 'status': str | None}. Colour
  resolution requires the dict form; positional rules work for both.
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
_ORIDINAL_FROM_LEFT = re.compile(r"the\s+(\w+)\s+from\s+the\s+left", re.IGNORECASE)
_ORDINAL_FROM_RIGHT = re.compile(r"the\s+(\w+)\s+from\s+the\s+right", re.IGNORECASE)
_PLAIN_ORDINAL = re.compile(r"^(?:the\s+)?(\w+)(?:\s+one)?\s*$", re.IGNORECASE)

_WORD_ORDINALS = {
    "first": 1,
    "1st": 1,
    "second": 2,
    "2nd": 2,
    "third": 3,
    "3rd": 3,
    "fourth": 4,
    "4th": 4,
    "fifth": 5,
    "5th": 5,
    "sixth": 6,
    "6th": 6,
    "seventh": 7,
    "7th": 7,
    "eighth": 8,
    "8th": 8,
    "ninth": 9,
    "9th": 9,
    "tenth": 10,
    "10th": 10,
}

# Status -> colour. Voice and the river use the same names so a colour
# phrase maps directly to status without a translation table.
_COLOR_STATUS = {
    "red": "failed",
    "green": "merged",
    "blue": "in_flight",
    "amber": "in_flight",  # CP3 narrate uses amber for partial
    "grey": "abandoned",
    "gray": "abandoned",
}


def _comets_as_dicts(comets: Sequence) -> list[dict]:
    """Normalise comets into a list of {'sha': ..., 'status': ...} dicts.

    Legacy call sites pass a Sequence[str]; new ones pass Sequence[dict].
    The colour branch needs status, so we keep a normalised view internally."""
    out: list[dict] = []
    for c in comets:
        if isinstance(c, str):
            out.append({"sha": c, "status": None})
        elif isinstance(c, dict):
            out.append(
                {"sha": c.get("sha"), "status": c.get("state") or c.get("status")}
            )
        else:
            out.append(
                {"sha": getattr(c, "sha", None), "status": getattr(c, "status", None)}
            )
    return out


def _parse_ordinal(token: str) -> int | None:
    """Parse '2' / '2nd' / 'second' -> 2. Returns None if not an ordinal."""
    token = (token or "").strip().lower()
    if token in _WORD_ORDINALS:
        return _WORD_ORDINALS[token]
    m = re.match(r"^(\d+)(?:st|nd|rd|th)?$", token)
    if m:
        return int(m.group(1))
    return None


def resolve(intent: str, comets: Sequence) -> dict:
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
            "error": "empty intent; expected a spatial phrase",
        }

    normalised = _comets_as_dicts(comets)
    shas = [c["sha"] for c in normalised]

    # ---- exact-match sets -------------------------------------------------
    if phrase in _LEFTMOST:
        return {"available": True, "sha": shas[0], "index": 0, "rule": "leftmost"}
    if phrase in _RIGHTMOST:
        return {
            "available": True,
            "sha": shas[-1],
            "index": len(shas) - 1,
            "rule": "rightmost",
        }

    # ---- colour phrases ---------------------------------------------------
    # "the red one" / "the red" / "the green one" -> first comet whose status
    # matches the colour. Status info is required, so this branch silently
    # degrades to the generic miss when the caller passed shas-only.
    m = re.match(r"^the\s+(\w+)(?:\s+one)?$", phrase)
    if m:
        word = m.group(1).lower()
        if word in _COLOR_STATUS:
            target = _COLOR_STATUS[word]
            for i, c in enumerate(normalised):
                if c["status"] == target:
                    return {
                        "available": True,
                        "sha": c["sha"],
                        "index": i,
                        "rule": f"colour:{word}",
                    }
            return {
                "available": True,
                "sha": None,
                "error": f"no {word} comets visible (have {len(shas)})",
            }

    # ---- ordinals from the left / right ----------------------------------
    # Ordinals run BEFORE the bare-word substring match below: a phrase like
    # "the 2nd from the right" contains "the right" too, and the substring
    # match would grab that and answer "rightmost" instead of the correct
    # "second from the right".
    m = _ORIDINAL_FROM_LEFT.search(phrase)
    if m:
        n = _parse_ordinal(m.group(1))
        if n is None:
            pass  # fall through to other rules
        elif 1 <= n <= len(shas):
            return {
                "available": True,
                "sha": shas[n - 1],
                "index": n - 1,
                "rule": f"{n}th from left",
            }
        else:
            return {
                "available": True,
                "sha": None,
                "error": f"{n}th from left out of range (have {len(shas)})",
            }

    m = _ORDINAL_FROM_RIGHT.search(phrase)
    if m:
        n = _parse_ordinal(m.group(1))
        if n is None:
            pass
        elif 1 <= n <= len(shas):
            return {
                "available": True,
                "sha": shas[-n],
                "index": len(shas) - n,
                "rule": f"{n}th from right",
            }
        else:
            return {
                "available": True,
                "sha": None,
                "error": f"{n}th from right out of range (have {len(shas)})",
            }

    m = _PLAIN_ORDINAL.search(phrase)
    if m:
        n = _parse_ordinal(m.group(1))
        if n is not None and 1 <= n <= len(shas):
            return {
                "available": True,
                "sha": shas[n - 1],
                "index": n - 1,
                "rule": f"the {n}th one",
            }
        if n is not None:
            return {
                "available": True,
                "sha": None,
                "error": f"the {n}th one out of range (have {len(shas)})",
            }

    # ---- verb-wrapped substring match ------------------------------------
    # Voice phrases arrive with verb wrappers ("tell the one on the left to
    # stop", "focus the rightmost comet"); the resolver finds the spatial
    # token WITHIN the phrase as a last resort, after every more-specific
    # rule above has been tried.
    #
    # Only multi-word candidates are matched here, never the bare words "left"
    # / "right" / "top" / "bottom" -- those would falsely match incidental
    # words ("halt the one on the right" would also match the "to" in "stop").
    _LEFT_PHRASES = {"the one on the left", "leftmost", "the first", "the top one"}
    _RIGHT_PHRASES = {"the one on the right", "rightmost", "the last", "the bottom one"}
    for candidate in _LEFT_PHRASES:
        if candidate in phrase:
            return {"available": True, "sha": shas[0], "index": 0, "rule": "leftmost"}
    for candidate in _RIGHT_PHRASES:
        if candidate in phrase:
            return {
                "available": True,
                "sha": shas[-1],
                "index": len(shas) - 1,
                "rule": "rightmost",
            }

    return {
        "available": True,
        "sha": None,
        "error": f"unrecognised spatial intent: {intent!r}",
    }
