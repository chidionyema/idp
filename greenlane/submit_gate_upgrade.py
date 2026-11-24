"""Stage 2 Lane 3 submit-gate upgrades for all web surfaces (#7794, #8061).

Provides three deterministic mechanisms:
1. Pre-gate mechanical hygiene normalization (ASCII cleanup + pinned Ruff).
2. Failure-carries-its-own-evidence comment builder (exact annotation + redacted
   last 20 lines of failing output inline in the issue comment).
3. 2-strike failure-fingerprint circuit breaker per (issue_id, owner) that halts
   blind retries and emits a structured lease reassignment payload.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SECRET_REDACT = (
    re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
    re.compile(r"\b(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\b(sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,})\b"),
    re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
)

ASCII_MAP = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "--",
    "\u00a0": " ",
    "\u2192": "->",
    "\u2264": "<=",
    "\u2265": ">=",
}


def redact_log(text: str) -> str:
    cleaned = text
    for pat in SECRET_REDACT:
        cleaned = pat.sub(
            lambda m: (
                m.group(1) + "[REDACTED]"
                if m.group(1).lower().startswith("bearer")
                else "[REDACTED]"
            ),
            cleaned,
        )
    return cleaned


def sanitize_ascii(text: str) -> str:
    """Replace common smart punctuation with ASCII while preserving semantics."""
    out = text
    for src, dst in ASCII_MAP.items():
        out = out.replace(src, dst)
    return unicodedata.normalize("NFKD", out).encode("ascii", "ignore").decode("ascii")


def normalize_python_files(
    paths: list[Path],
    run_ruff: bool = True,
    ruff_bin: str = "ruff",
) -> dict[str, Any]:
    """Normalize non-ASCII punctuation and optionally run pinned Ruff format/fix."""
    changed: list[str] = []
    py_files = [p for p in paths if p.suffix == ".py" and p.is_file()]
    for path in py_files:
        raw = path.read_text(encoding="utf-8")
        cleaned = sanitize_ascii(raw)
        if cleaned != raw:
            path.write_text(cleaned, encoding="utf-8")
            changed.append(str(path))

    ruff_ran = False
    ruff_error = ""
    if run_ruff and py_files:
        str_paths = [str(p) for p in py_files]
        try:
            for cmd in (
                [ruff_bin, "check", "--fix", "--quiet", *str_paths],
                [ruff_bin, "format", "--quiet", *str_paths],
            ):
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if proc.returncode != 0:
                    ruff_error = redact_log(proc.stderr or proc.stdout).strip()
                    break
            else:
                ruff_ran = True
        except OSError as exc:
            ruff_error = str(exc)

    return {
        "files_checked": [str(p) for p in py_files],
        "ascii_normalized": changed,
        "ruff_ran": ruff_ran,
        "ruff_error": ruff_error,
        "ok": ruff_error == "",
    }


def fingerprint_failure(job: str, annotation: str, log_tail: list[str]) -> str:
    """Stable 16-char fingerprint ignoring volatile run IDs and timestamps."""
    raw = "\n".join([job.strip(), annotation.strip(), *log_tail[-5:]])
    normalized = re.sub(r"/?runs/\d+(/job/\d+)?", "/runs/<id>", raw)
    normalized = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[0-9.Z+-]*", "<ts>", normalized
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def build_failure_comment(
    branch: str,
    owner: str,
    head_sha: str,
    run_url: str,
    failing_job: str,
    failing_step: str,
    annotation: str,
    raw_log: str,
    circuit_state: dict[str, Any] | None = None,
) -> str:
    """Build a tell-the-owner comment carrying exact failure evidence inline."""
    redacted_lines = [
        ln.rstrip() for ln in redact_log(raw_log).splitlines() if ln.strip()
    ][-20:]
    fp = fingerprint_failure(failing_job, annotation, redacted_lines)
    lines = [
        f"<!-- submit-gate head={head_sha} fingerprint={fp} -->",
        f"**submit door: `{branch}` failed `{failing_job}`** -- owner `{owner}`.",
        "",
        f"- head: `{head_sha}`",
        f"- failing run: {run_url}",
        f"- failing step: `{failing_step}`",
        f"- annotation: `{redact_log(annotation).strip() or 'none'}`",
        f"- failure_fingerprint: `{fp}`",
        "",
        "Redacted last 20 log lines:",
        "```text",
        *(redacted_lines or ["(no log lines captured)"]),
        "```",
    ]
    if circuit_state and circuit_state.get("tripped"):
        lines.extend(
            [
                "",
                "**CIRCUIT BREAKER TRIPPED:** Further pushes from "
                f"`{owner}` on this issue are blocked "
                f"({circuit_state['reason']}). Lease reassigned to "
                f"`{circuit_state['reassign_to']}`.",
            ]
        )
    return "\n".join(lines) + "\n"


@dataclass
class BreakerDecision:
    tripped: bool
    reason: str
    same_fingerprint_count: int
    total_issue_failures: int
    reassign_to: str = "lane3-cli-executor"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tripped": self.tripped,
            "reason": self.reason,
            "same_fingerprint_count": self.same_fingerprint_count,
            "total_issue_failures": self.total_issue_failures,
            "reassign_to": self.reassign_to if self.tripped else "",
        }


class SubmitCircuitBreaker:
    """2-strike identical-fingerprint or 3-failure per-issue circuit breaker."""

    def __init__(
        self,
        state_path: Path,
        max_same_fingerprint: int = 2,
        max_total_per_issue: int = 3,
    ) -> None:
        self.state_path = state_path
        self.max_same_fingerprint = max_same_fingerprint
        self.max_total_per_issue = max_total_per_issue

    def _load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"records": {}}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def record_failure(
        self, issue_id: str, owner: str, failure_fp: str
    ) -> BreakerDecision:
        data = self._load()
        key = f"{issue_id}::{owner}"
        entry = data["records"].setdefault(
            key, {"total": 0, "fingerprints": {}, "blocked": False}
        )
        entry["total"] += 1
        fp_count = int(entry["fingerprints"].get(failure_fp, 0)) + 1
        entry["fingerprints"][failure_fp] = fp_count

        tripped = False
        reason = "within budget"
        if fp_count >= self.max_same_fingerprint:
            tripped = True
            reason = f"identical failure fingerprint {failure_fp} hit {fp_count}x"
        elif entry["total"] >= self.max_total_per_issue:
            tripped = True
            reason = f"issue failure budget exhausted ({entry['total']} failures)"

        entry["blocked"] = tripped
        self._save(data)
        return BreakerDecision(
            tripped=tripped,
            reason=reason,
            same_fingerprint_count=fp_count,
            total_issue_failures=entry["total"],
        )

    def is_blocked(self, issue_id: str, owner: str) -> bool:
        data = self._load()
        return bool(data["records"].get(f"{issue_id}::{owner}", {}).get("blocked"))
