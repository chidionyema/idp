"""The pure half of vendor self-setup: row schema, templates, shapes, scrub, and the vault write.

No value is ever printed, on argv, or in an exception message.
"""

from __future__ import annotations

import base64
import contextlib
import datetime
import os
import re
import subprocess
import tempfile

import yaml

ROADS = ("browser", "oidc", "assisted")
ACTIONS = ("goto", "wait", "click", "fill", "capture")

_BRACE_RE = re.compile(r"\{[^{}]*\}?|\}")
_VAULT_FIELD_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class SetupError(Exception):
    pass


def load_row(consoles_path, vendor: str) -> dict:
    with open(consoles_path) as f:
        data = yaml.safe_load(f)
    vendors = (data or {}).get("vendors") or {}
    if vendor not in vendors:
        raise SetupError(f"{vendor}: no row in {consoles_path}")
    return vendors[vendor]


def road(row: dict) -> str:
    return (row.get("setup") or {}).get("road", "assisted")


def pattern(s: str) -> re.Pattern:
    if s.startswith("(?i)"):
        return re.compile(s[4:], re.IGNORECASE)
    return re.compile(s)


def render(template: str, vendor: str, today: datetime.date) -> str:
    text = template.replace("{vendor}", vendor).replace(
        "{date}", today.strftime("%Y%m%d")
    )
    m = _BRACE_RE.search(text)
    if m:
        raise SetupError(
            f"unknown template brace {m.group()}; only {{vendor}} and {{date}}"
        )
    return text


def validate(vendor: str, row: dict) -> list[str]:
    errors: list[str] = []
    prefix = f"{vendor}: "

    setup = row.get("setup")
    if setup is None:
        return errors
    if not isinstance(setup, dict):
        errors.append(prefix + "setup is not a mapping")
        return errors

    r = setup.get("road", "assisted")
    if r not in ROADS:
        errors.append(
            prefix + f"setup.road {r!r} is not one of browser, oidc, assisted"
        )
        return errors

    if r == "oidc":
        if setup.get("steps"):
            errors.append(prefix + "setup.road oidc carries no steps")
        return errors

    if r != "browser":
        return errors

    if row.get("store_default") != "estate-vault":
        errors.append(
            prefix + "setup.road browser needs store_default: estate-vault "
            "(the estate cannot write Bitwarden, decision 0020)"
        )
    if not setup.get("entry"):
        errors.append(prefix + "setup.entry is required for setup.road browser")
    if not isinstance(row.get("verify"), dict):
        errors.append(
            prefix
            + "setup.road browser needs a verify: block; a key is proved before it is written"
        )

    steps = setup.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append(prefix + "setup.steps is empty")
        return errors

    targets = row.get("targets") or []
    target_fields = {t.get("field") for t in targets if not t.get("derived")}

    has_capture = False
    for i, step in enumerate(steps, start=1):
        if (
            not isinstance(step, dict)
            or len(step) != 1
            or next(iter(step)) not in ACTIONS
        ):
            errors.append(
                prefix
                + f"setup.steps[{i}] must have exactly one of goto, wait, click, fill, capture"
            )
            continue
        action = next(iter(step))
        value = step[action]

        if action == "goto":
            if not isinstance(value, str) or not value.startswith(
                ("http://", "https://")
            ):
                errors.append(prefix + f"setup.steps[{i}].goto is not a URL")
            continue

        if action in ("wait", "click", "fill"):
            if not isinstance(value, dict) or not (
                isinstance(value.get("label"), str)
                or isinstance(value.get("role"), str)
            ):
                errors.append(prefix + f"setup.steps[{i}].{action} needs role or label")
            else:
                for key in ("name", "label"):
                    v = value.get(key)
                    if isinstance(v, str):
                        try:
                            pattern(v)
                        except re.error:
                            errors.append(
                                prefix
                                + f"setup.steps[{i}].{action} regex does not compile"
                            )

        if action == "wait" and isinstance(value, dict) and "wait_s" in value:
            wait_s = value["wait_s"]
            if not isinstance(wait_s, int) or isinstance(wait_s, bool) or wait_s <= 0:
                errors.append(
                    prefix + f"setup.steps[{i}].wait.wait_s must be a positive integer"
                )

        if action == "fill":
            if not isinstance(value, dict) or not isinstance(value.get("value"), str):
                errors.append(prefix + f"setup.steps[{i}].fill needs value")
            else:
                try:
                    render(value["value"], vendor, datetime.date(2026, 1, 1))
                except SetupError as e:
                    errors.append(prefix + f"setup.steps[{i}].fill.value: {e}")

        if action == "capture":
            has_capture = True
            if not isinstance(value, dict) or not isinstance(value.get("field"), str):
                errors.append(prefix + f"setup.steps[{i}].capture needs field")
            else:
                field = value["field"]
                regex = value.get("regex")
                if not isinstance(regex, str):
                    errors.append(prefix + f"setup.steps[{i}].capture needs regex")
                else:
                    try:
                        re.compile(regex)
                    except re.error:
                        errors.append(
                            prefix + f"setup.steps[{i}].capture regex does not compile"
                        )
                if field not in target_fields:
                    errors.append(
                        prefix
                        + f"setup.steps[{i}].capture.field {field} is not the field of any target"
                    )

    if not has_capture:
        errors.append(prefix + "setup.steps capture nothing")

    return errors


def check_shapes(row: dict, captured: dict) -> list[str]:
    errors = []
    targets = row.get("targets") or []
    by_field = {t.get("field"): t for t in targets}
    for field, value in sorted(captured.items()):
        target = by_field.get(field) or {}
        shape = target.get("shape") or row.get("shape")
        if shape and not re.fullmatch(shape, value):
            errors.append(f"{field} does not match the registry shape")
    return errors


def scrub(text: str, values) -> str:
    variants = set()
    for value in values:
        if not value:
            continue
        variants.add(value)
        b64 = base64.b64encode(value.encode()).decode()
        ub64 = base64.urlsafe_b64encode(value.encode()).decode()
        variants.add(b64)
        variants.add(ub64)
        variants.add(b64.rstrip("="))
        variants.add(ub64.rstrip("="))

    out = text
    for variant in sorted(variants, key=len, reverse=True):
        out = out.replace(variant, "<redacted>")
    return out


def write_vault(entry: str, captured: dict, idp_root: str) -> None:
    for field, value in captured.items():
        if not _VAULT_FIELD_RE.match(field):
            raise SetupError(f"{field} is not a vault key name")
        if "\n" in value or "\r" in value:
            raise SetupError(f"{field} holds a line break; refused")

    binary = os.environ.get("IDP_VAULT_PUT") or os.path.join(
        idp_root, "bin", "idp-vault-put"
    )

    fd, path = tempfile.mkstemp(prefix="vendor-setup-", suffix=".env")
    os.fchmod(fd, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            for field in sorted(captured):
                f.write(f"V_{field}={captured[field]}\n")

        r = subprocess.run(  # noqa: S603 -- argv holds key names only; values travel in ESTATE_ENV_FILE
            [binary, "--merge", entry, *[f"{f}=V_{f}" for f in sorted(captured)]],
            env={**os.environ, "ESTATE_ENV_FILE": path},
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(path)

    if r.returncode != 0:
        raise SetupError(
            f"vault write to {entry} refused (exit {r.returncode}): "
            + scrub(r.stderr.strip()[-200:], captured.values())
        )
