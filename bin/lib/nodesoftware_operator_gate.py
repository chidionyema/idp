"""The RuntimeInstall CR validator the offline gate (bin/nodesoftware-operator-gate) runs.

Contract source of truth: platform/nodesoftware-operator/CRD-SPEC.md. Adding a
rule there without adding it here is a regression; adding it here without it
there is over-reach. The two stay in sync or the fixture pair's two-way grading
in bin/idp-ci fails.

The closed runtime set lives here (not in the bash wrapper) because the bash
file is intentionally a thin dispatcher and shellcheck warns on unused arrays.
Adding a runtime to CLOSED_RUNTIMES without adding the handler module at
platform/nodesoftware-operator/runtimes/<runtime>/ is a regression the
runtime-handler-importer catches separately; this module catches the CR side.
"""

from __future__ import annotations

import re
import sys

import yaml

CLOSED_RUNTIMES = {"runsc", "kata", "nvidia"}

# Mirror of Go's time.ParseDuration for the subset we accept (h/m/s combos only).
# The bash wrapper does not parse durations because the gate is python's job.
_DURATION_RE = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")

# CR must live in the operator's namespace; admission refuses otherwise.
OPERATOR_NAMESPACE = "nodesoftware-operator"

# Free-form rollback commands are forbidden by the lockdown; the Operator ships
# one /usr/local/bin/nodesoftware-<runtime>-uninstall script per runtime and the
# CR may only invoke that.
UNINSTALL_PATH_RE = re.compile(r"^/usr/local/bin/nodesoftware-[a-z0-9]+-uninstall$")

# version: free-form but constrained to a safe character set so the runtime's
# handler module can use it as a key without surprises.
_VERSION_RE = re.compile(r"^[A-Za-z0-9._+\-]{1,64}$")

ALLOWED_ROLLOUT_STRATEGIES = {"ProgressiveCanary", "AllAtOnce", "Manual"}
ALLOWED_FAILURE_POLICIES = {"FailClosed", "Ignore"}

# Hard limits from CRD-SPEC.md.
MIN_PAUSE_SECONDS = 30  # Operator's reconcile period is 15s
MIN_VERIFICATION_TIMEOUT = 30
MAX_VERIFICATION_TIMEOUT = 1800


def _err(name: str, msg: str) -> tuple[str, str]:
    return (name, msg)


def validate(doc: dict) -> list[tuple[str, str]]:
    """Return a list of (name, message) refusals. Empty list means pass."""
    name = doc.get("metadata", {}).get("name", "<unnamed>")
    errors: list[tuple[str, str]] = []

    if doc.get("kind") != "RuntimeInstall":
        return errors  # only RuntimeInstall CRs are graded by this gate

    api = doc.get("apiVersion", "")
    if api != "nodesoftware.estate.io/v1alpha1":
        errors.append(
            _err(name, f"apiVersion {api!r} != nodesoftware.estate.io/v1alpha1")
        )
        return errors  # further checks depend on apiVersion; bail out

    ns = doc.get("metadata", {}).get("namespace", "")
    if ns != OPERATOR_NAMESPACE:
        errors.append(
            _err(
                name,
                f"metadata.namespace {ns!r} != {OPERATOR_NAMESPACE!r} "
                "(CR must live in the operator's namespace, admission refuses otherwise)",
            )
        )

    spec = doc.get("spec") or {}

    runtime = spec.get("runtime")
    if not runtime:
        errors.append(_err(name, "spec.runtime: required"))
    elif runtime not in CLOSED_RUNTIMES:
        errors.append(
            _err(
                name,
                f"spec.runtime: Forbidden: {runtime} (closed set is {sorted(CLOSED_RUNTIMES)})",
            )
        )

    version = spec.get("version")
    if not version:
        errors.append(_err(name, "spec.version: required"))
    elif not _VERSION_RE.match(str(version)):
        errors.append(_err(name, f"spec.version: invalid characters: {version!r}"))

    sel = spec.get("selector") or {}
    if not sel.get("nodeSelector"):
        errors.append(
            _err(
                name,
                "spec.selector.nodeSelector: required (a CR with no selector would "
                "match every node; the lockdown refuses that)",
            )
        )

    rs = spec.get("rolloutStrategy", "ProgressiveCanary")
    if rs not in ALLOWED_ROLLOUT_STRATEGIES:
        errors.append(
            _err(
                name,
                f"spec.rolloutStrategy: {rs!r} not in "
                f"{sorted(ALLOWED_ROLLOUT_STRATEGIES)}",
            )
        )

    cr = spec.get("canaryReplicas")
    if rs != "AllAtOnce":
        if cr is None:
            errors.append(
                _err(
                    name,
                    "spec.canaryReplicas: required when rolloutStrategy != AllAtOnce",
                )
            )
        elif not isinstance(cr, int) or cr < 1:
            errors.append(_err(name, f"spec.canaryReplicas: must be >= 1 (got {cr!r})"))

    if rs == "ProgressiveCanary":
        pd = spec.get("pauseDuration")
        if pd is None:
            errors.append(
                _err(
                    name,
                    "spec.pauseDuration: required when rolloutStrategy=ProgressiveCanary",
                )
            )
        else:
            m = _DURATION_RE.fullmatch(str(pd))
            if not m or not (m.group(1) or m.group(2) or m.group(3)):
                errors.append(
                    _err(
                        name,
                        f"spec.pauseDuration: unparseable {pd!r} "
                        "(expected h/m/s combos like 15m)",
                    )
                )
            else:
                secs = (
                    int(m.group(1) or 0) * 3600
                    + int(m.group(2) or 0) * 60
                    + int(m.group(3) or 0)
                )
                if secs < MIN_PAUSE_SECONDS:
                    errors.append(
                        _err(
                            name,
                            f"spec.pauseDuration: below minimum {MIN_PAUSE_SECONDS}s "
                            f"(got {pd!r} = {secs}s; the Operator's reconcile period is "
                            "15s so <30s means the canary pause is a no-op)",
                        )
                    )

    fp = spec.get("failurePolicy")
    if fp not in ALLOWED_FAILURE_POLICIES:
        errors.append(
            _err(
                name,
                f"spec.failurePolicy: {fp!r} not in {sorted(ALLOWED_FAILURE_POLICIES)}",
            )
        )

    ver = spec.get("verification") or {}
    pp = ver.get("probePod")
    sc = ver.get("successCondition")
    if not pp:
        errors.append(_err(name, "spec.verification.probePod: required"))
    if not sc:
        errors.append(
            _err(
                name,
                "spec.verification.successCondition: required (without it the Operator "
                "cannot tell Verified from Failed)",
            )
        )
    ts = ver.get("timeoutSeconds", 300)
    if (
        not isinstance(ts, int)
        or ts < MIN_VERIFICATION_TIMEOUT
        or ts > MAX_VERIFICATION_TIMEOUT
    ):
        errors.append(
            _err(
                name,
                f"spec.verification.timeoutSeconds: must be "
                f"{MIN_VERIFICATION_TIMEOUT}..{MAX_VERIFICATION_TIMEOUT} (got {ts!r})",
            )
        )

    rb = spec.get("rollback")
    if rb is not None:
        cmds = rb.get("commands") or []
        for c in cmds:
            if not UNINSTALL_PATH_RE.match(str(c)):
                errors.append(
                    _err(
                        name,
                        f"spec.rollback.commands: {c!r} must use the runtime's "
                        "shipped uninstall script (free-form host commands are forbidden "
                        "by the lockdown)",
                    )
                )

    return errors


def grade_file(path: str) -> int:
    """Grade one file. Print refusals to stdout, return 0 (pass) or 1 (refused)."""
    try:
        with open(path) as f:
            docs = list(yaml.safe_load_all(f))
    except OSError as e:
        print(f"FAIL  nodesoftware-operator-gate  cannot read {path}: {e}")
        return 1

    total_runtime_installs = 0
    refusals: list[tuple[str, str]] = []
    for doc in docs:
        if not doc:
            continue
        if doc.get("kind") != "RuntimeInstall":
            continue
        total_runtime_installs += 1
        refusals.extend(validate(doc))

    for name, msg in refusals:
        print(f"REFUSED  {name}: {msg}")

    if refusals:
        return 1
    print(f"ok    {total_runtime_installs} RuntimeInstall doc(s) pass")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(
            "usage: nodesoftware_operator_gate.py <file> [<file> ...]", file=sys.stderr
        )
        return 2
    rc = 0
    for path in argv:
        if not __import__("os").path.isfile(path):
            print(f"FAIL  nodesoftware-operator-gate  no such file: {path}")
            rc = 1
            continue
        if grade_file(path) != 0:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
