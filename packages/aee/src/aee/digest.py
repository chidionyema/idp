"""The graph's content address, over the estate's ONE canonical serialisation.

``sovereign.config.canonical_json`` is the exact serialisation every receipt
line is hashed over (cp19). The work graph uses it too, so a graph digest and
a receipt digest are the same kind of address and there is only one of them.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict


def canonical_bytes(obj: Dict[str, Any]) -> bytes:
    """The bytes an address is computed over."""
    from sovereign.config import canonical_json

    return canonical_json(obj)


def digest_of(obj: Dict[str, Any]) -> str:
    """The content address of a graph state."""
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()
