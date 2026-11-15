"""Canonical JSON and digests shared by the custody modules (ESTATE-P0)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_of(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()
