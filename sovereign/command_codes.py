"""CC1 deterministic intent compilation and conservative advisory preflight.

Compilation never authenticates, authorizes, executes or signs. Existing Instruction
Gateway, DoF action door, QUAD and signed receipts remain authoritative.
"""
import hashlib
import json
import re
import shlex

VERSION = "estate.command.v1"
REQUIRED = {"ACT", "TARGET", "EFFECT", "WORK", "RESERVE", "PROTO"}
OPTIONAL = {"MODE", "CLASS", "PARENT"}
ACTIONS = {"OBSERVE", "DIAGNOSE", "REPAIR", "RELEASE", "CORRECT_PROTOCOL"}
EFFECTS = {"READ", "PATCH", "PRIVILEGED"}
ATOM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+#-]*$")


class CommandError(ValueError):
    pass


def atom(value, field):
    if not 0 < len(value) <= 128 or not ATOM.fullmatch(value):
        raise CommandError(f"{field}: invalid canonical atom")
    return value


def number(value, field, zero=False):
    if not value.isascii() or not value.isdecimal():
        raise CommandError(f"{field}: expected unsigned integer")
    n = int(value)
    if n > 100000000 or (n == 0 and not zero):
        raise CommandError(f"{field}: out of range")
    return n


def compile_code(raw):
    if not isinstance(raw, str) or len(raw) > 2048:
        raise CommandError("command missing or too long")
    try:
        parts = shlex.split(raw)
    except ValueError as exc:
        raise CommandError("unbalanced command") from exc
    if not parts or parts[0] != "CC1":
        raise CommandError("unsupported version")
    fields = {}
    for part in parts[1:]:
        if "=" not in part:
            raise CommandError("expected KEY=value")
        key, val = part.split("=", 1)
        if key not in REQUIRED | OPTIONAL or key in fields or not val:
            raise CommandError(f"unknown/duplicate/empty field: {key}")
        fields[key] = val
    missing = REQUIRED - fields.keys()
    if missing:
        raise CommandError(f"missing fields: {sorted(missing)}")
    action = atom(fields["ACT"], "ACT")
    effect = atom(fields["EFFECT"], "EFFECT")
    if action not in ACTIONS or effect not in EFFECTS:
        raise CommandError("unknown action/effect")
    if action in {"OBSERVE", "DIAGNOSE"} and effect != "READ":
        raise CommandError("observation is read-only")
    if action == "RELEASE" and effect != "PRIVILEGED":
        raise CommandError("release requires privileged effect classification")
    if action == "CORRECT_PROTOCOL" and not all(k in fields for k in ("CLASS", "PARENT")):
        raise CommandError("governance recursion requires parent and failure class")
    result = {
        "schema": VERSION,
        "action": action,
        "target": atom(fields["TARGET"], "TARGET"),
        "effect": effect,
        "planned_tokens": number(fields["WORK"], "WORK"),
        "recovery_reserve_tokens": number(fields["RESERVE"], "RESERVE", zero=True),
        "protocol": atom(fields["PROTO"], "PROTO"),
        "failure_class": atom(fields["CLASS"], "CLASS") if "CLASS" in fields else None,
        "parent_obligation": atom(fields["PARENT"], "PARENT") if "PARENT" in fields else None,
        "mode": atom(fields.get("MODE", "NORMAL"), "MODE"),
    }
    payload = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result.update(
        digest_sha256=hashlib.sha256(payload).hexdigest(),
        state="COMPILED_NOT_AUTHORIZED",
        signed_by="UNKNOWN",
        verified_yield="UNKNOWN",
    )
    return result


def preflight(
    command, observation, *, now_epoch, authority_oracle=None,
    observation_oracle=None, ttl_seconds=120
):
    """Trusted-caller advisory only; never an executable capability token.

    The existing independent gateway must supply genuine QUAD/lease and
    capacity verification oracles. Caller claimed signed=True is worthless.
    The downstream DoF action door must independently enforce at effect time.
    """
    reasons = []
    if not isinstance(command, dict) or command.get("schema") != VERSION:
        reasons.append("UNKNOWN_COMMAND_CONTRACT")
    if authority_oracle is None or authority_oracle(command) is not True:
        reasons.append("AUTHORITY_UNVERIFIED")
    if not isinstance(observation, dict) or observation_oracle is None:
        reasons.append("CAPACITY_UNVERIFIED")
    elif observation_oracle(observation) is not True:
        reasons.append("CAPACITY_SIGNATURE_UNVERIFIED")
    else:
        try:
            at = observation["observed_at_epoch"]
            provider = observation["provider_remaining_tokens"]
            account = observation["account_remaining_tokens"]
            if any(type(x) is not int for x in (at, provider, account, now_epoch, ttl_seconds)):
                raise ValueError("non-integer")
            if ttl_seconds <= 0 or at > now_epoch or now_epoch - at > ttl_seconds:
                reasons.append("CAPACITY_STALE")
            if provider < 0 or account < 0:
                reasons.append("CAPACITY_UNKNOWN")
            needed = command["planned_tokens"] + command["recovery_reserve_tokens"]
            if type(needed) is not int or needed <= 0:
                reasons.append("INVALID_PLAN_BUDGET")
            elif provider < needed or account < needed:
                reasons.append("INSUFFICIENT_HEADROOM")
            if observation.get("rate_limited") is not False:
                reasons.append("PROVIDER_RATE_LIMIT_UNKNOWN_OR_ACTIVE")
        except (KeyError, TypeError, ValueError):
            reasons.append("CAPACITY_MALFORMED")
    return {
        "verdict": "BLOCKED" if reasons else "PREFLIGHT_ELIGIBLE_NOT_AUTHORIZED",
        "reasons": reasons,
        "effect_authorized": False,
        "next_boundary": "TRUSTED_DOF_ACTION_DOOR",
    }
