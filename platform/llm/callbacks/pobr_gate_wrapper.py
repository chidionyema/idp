"""
pobr_gate_wrapper.py — imports pobr_gate cleanly inside the LiteLLM pod.

The pobr_gate module lives in this directory alongside this file.
We use exec_module and manually register the module in sys.modules so that
cls.__module__ lookups (used by dataclass decorators) resolve correctly.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

_CALLBACK_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(_CALLBACK_DIR))

_KEY_DIR = Path(os.environ.get("POBR_KEY_DIR", str(_CALLBACK_DIR / "keys")))
_ANCHOR_DIR = Path(os.environ.get("POBR_ANCHOR_DIR", str(_CALLBACK_DIR / "anchors")))
_KEY_PATH = _KEY_DIR / "agent.pub.pem"

# ---------------------------------------------------------------------------
# Load gate module using exec_module with proper sys.modules registration
# ---------------------------------------------------------------------------

_gate_module = None


def _load_gate():
    global _gate_module
    if _gate_module is not None:
        return _gate_module

    gate_path = _CALLBACK_DIR / "pobr_gate.py"
    schema_path = _CALLBACK_DIR / "pobr_schema.py"

    # Load schema first (gate imports from it)
    schema_spec = importlib.util.spec_from_file_location("pobr_schema", schema_path)
    if schema_spec is None or schema_spec.loader is None:
        raise ImportError(f"Could not load schema from {schema_path}")
    schema_module = importlib.util.module_from_spec(schema_spec)
    # Register BEFORE exec so cls.__module__ lookups inside dataclass decorators resolve
    sys.modules["pobr_schema"] = schema_module
    schema_spec.loader.exec_module(schema_module)

    # Load gate (it imports from pobr_schema)
    gate_spec = importlib.util.spec_from_file_location("pobr_gate", gate_path)
    if gate_spec is None or gate_spec.loader is None:
        raise ImportError(f"Could not load gate from {gate_path}")
    gate_module = importlib.util.module_from_spec(gate_spec)
    sys.modules["pobr_gate"] = gate_module
    gate_spec.loader.exec_module(gate_module)

    _gate_module = gate_module
    return gate_module


def verify_receipt(receipt_str: str) -> bool:
    """
    Verify a PoBR receipt string.
    Returns True if ADMITTED, False if REJECTED or any error.
    Fails safe: missing keys mean no signature check, but structure still validated.
    """
    try:
        receipt_data = json.loads(receipt_str)
    except (json.JSONDecodeError, TypeError):
        return False

    gate = _load_gate()

    try:
        r = gate.receipt_from_dict(receipt_data)
    except Exception:
        return False

    # Load public key if mounted
    pubkey: bytes | None = None
    if _KEY_PATH.exists():
        try:
            pubkey = _KEY_PATH.read_bytes()
        except OSError:
            pass  # no key mounted — signature check will fail gracefully

    anchor_path = _ANCHOR_DIR if _ANCHOR_DIR.exists() else None

    try:
        result = gate.gate(r, pubkey, anchor_path)
        return result.decision.value == "ADMITTED"
    except Exception:
        return False
