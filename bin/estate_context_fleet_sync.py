#!/usr/bin/env python3
"""estate_context_fleet_sync -- the Turn-1 rule budget: compose the fleet contract, gate the bloat.

WHY. Every harness auto-injects a repository's instruction files (AGENTS.md, CLAUDE.md,
CLINE.md, .clinerules, copilot instructions) into the first turn of every session, before the
agent has read anything it chose. On idp that tax was measured 2026-11-27 at 60,354 bytes
(AGENTS.md 58,150 + CLAUDE.md 2,204): 14,439 cl100k_base tokens, every session, every turn
that re-sends the prefix. The policy's cap is 1,500 (policy/context-policy.v1.json).

WHAT CHANGED FROM THE KIT (MERIDIAN_ESTATE_CONTEXT_GOVERNANCE_V1.zip, sha256 cb13e9f7...).
  Hold #1: the kit's `--compile` wrote AGENTS.md from scratch -- `p_agents.write_text(...)` --
  replacing the estate's constitution with a six-line summary. That is deletion of founder law
  by a code generator. This compiler COMPOSES: it owns exactly one marked block
  (ESTATE_FLEET_CONTEXT_CONTRACT) and never writes a byte outside it, the way the estate's
  other generated blocks (ESTATE_SUBSTRATE_AUTHORITY, ESTATE_CAPABILITY_ADVERTISING) already
  live inside AGENTS.md. A file it did not find is not created; a malformed marker pair is
  refused, not repaired.
  The kit also refused any rule file that mentions `~/.estate` or `launchctl` ("Zone A"). No
  current law says that: AGENTS.md 7 puts every intent in `~/.estate`. That check is removed,
  not loosened. The kit's compiled text named a gateway host; the estate's two documents name
  two different hosts, so this block names none -- the gateway is the policy file's to declare.
  The kit's estimator was bytes/3.2 x 1.15, which over-counted idp's AGENTS.md by 50%
  (20,898 vs 13,907 cl100k_base). This one is bytes/4 x the policy's default multiplier,
  calibrated against cl100k_base on the three files the fleet actually loads (4.18, 4.14 and
  4.03 bytes per token), so it errs high by a margin that is stated, not hidden.

THE GATE (`--audit`). Exit 43 when the auto-injected rule total is over the cap AND it grew.
  * total <= cap                          -> PASS
  * total > cap, --base given, total <= base total -> PASS with OVER_CAP (a ratchet: a tree
    already over the cap may shrink or hold, never grow)
  * total > cap, and no base or it grew   -> FAIL 43 FC_TURN1_BLOATED_RULES
  A base that cannot be read is a refusal (exit 2), never a pass: a gate that cannot judge
  does not get to say yes (AGENTS.md 9 R1).
  MCP: an explicit `always_on_tools` / `tools` list over the ceiling fails 43; a raw provider
  host in an MCP config fails 43. A config that declares servers but no tool list is reported
  `mcp_tools_unmeasured` -- named, not counted as checked.

`--self-test` runs every check against a known-bad and a known-good input and exits 0 only
when each bad input is refused and each good input admitted (AGENTS.md 9, principle 1).

`--optimus` prints exactly `optimus.context.turn1_rule_tokens=<n>`, the measure registered in
catalog/optimus-metrics.json. A tree it cannot read prints nothing and exits 2: UNKNOWN, never 0.

Usage:
  bin/estate_context_fleet_sync.py --audit [--base <git-ref>]
  bin/estate_context_fleet_sync.py --compile [--check]    # compose the block (or prove it is current)
  bin/estate_context_fleet_sync.py --self-test
  bin/estate_context_fleet_sync.py --optimus
Exit: 0 pass, 43 CONTEXT_GOVERNANCE_VIOLATION, 2 refused (unreadable base, malformed markers).
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = ROOT / "policy" / "context-policy.v1.json"

EXIT_PASS = 0
EXIT_VIOLATION = 43
EXIT_REFUSED = 2
OPTIMUS_METRIC = "context.turn1_rule_tokens"

# Files a harness injects on Turn 1 without being asked. CLAUDE.md and GEMINI.md are here
# because Claude Code and the gemini CLI load them exactly as Codex/OpenCode load AGENTS.md;
# the kit left them out, which undercounted every Claude session.
AUTO_INJECTED = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "CLINE.md",
    ".clinerules",
    ".github/copilot-instructions.md",
)
MCP_CONFIGS = (".mcp.json", "mcp.json", ".meridian/mcp-servers.json")

BLOCK_START = "<!-- ESTATE_FLEET_CONTEXT_CONTRACT_START -->"
BLOCK_END = "<!-- ESTATE_FLEET_CONTEXT_CONTRACT_END -->"
# The block goes after the last generated block already at the top of the file, so the
# authority block stays first (the context compiler and every reader expect it there).
ANCHORS_END = (
    "<!-- ESTATE_CAPABILITY_ADVERTISING_END -->",
    "<!-- ESTATE_SUBSTRATE_AUTHORITY_END -->",
)
HISTORICAL_PREFIX = "<!-- estate:historical"

BYTES_PER_TOKEN = 4.0


class Refused(Exception):
    """The tool cannot judge or cannot write safely; exit 2, never a pass."""


def est_tokens(data: bytes, multiplier: float) -> int:
    if not data:
        return 0
    return max(1, math.ceil(len(data) / BYTES_PER_TOKEN * multiplier))


GIT = shutil.which("git") or "/usr/bin/git"


def _git(root: Path, *args: str) -> "subprocess.CompletedProcess[bytes]":
    # argv only, never a shell; every argument is a ref or a repo-relative path from this tool.
    return subprocess.run([GIT, "-C", str(root), *args], capture_output=True)  # noqa: S603


def multiplier(policy: Dict[str, Any]) -> float:
    return float(policy.get("tokenizer_safety_multipliers", {}).get("default", 1.15))


def load_policy(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refused(f"policy unreadable: {path}: {exc}") from exc


# ---------------------------------------------------------------- reading a tree or a ref


class Tree:
    """The files of a working tree, or of a git ref, behind one read interface."""

    def __init__(self, root: Path, ref: Optional[str] = None):
        self.root = root
        self.ref = ref
        self._listing: Optional[List[str]] = None
        if ref is not None:
            rc = _git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{tree}}")
            if rc.returncode != 0:
                raise Refused(
                    f"base ref unreadable: {ref!r} (git rev-parse exit {rc.returncode})"
                )

    def _ls(self) -> List[str]:
        if self._listing is None:
            rc = _git(self.root, "ls-tree", "-r", "--name-only", str(self.ref))
            if rc.returncode != 0:
                raise Refused(
                    f"cannot list {self.ref!r} (git ls-tree exit {rc.returncode})"
                )
            self._listing = rc.stdout.decode("utf-8", errors="replace").splitlines()
        return self._listing

    def rule_files(self) -> List[str]:
        found: List[str] = []
        for rel in AUTO_INJECTED:
            if self.ref is None:
                p = self.root / rel
                if p.is_file():
                    found.append(rel)
                elif p.is_dir():
                    found.extend(
                        q.relative_to(self.root).as_posix()
                        for q in sorted(p.rglob("*.md"))
                    )
            else:
                listing = self._ls()
                if rel in listing:
                    found.append(rel)
                else:
                    found.extend(
                        sorted(
                            x
                            for x in listing
                            if x.startswith(rel + "/") and x.endswith(".md")
                        )
                    )
        return found

    def read(self, rel: str) -> Optional[bytes]:
        if self.ref is None:
            p = self.root / rel
            return p.read_bytes() if p.is_file() else None
        rc = _git(self.root, "show", f"{self.ref}:{rel}")
        return rc.stdout if rc.returncode == 0 else None


def measure(tree: Tree, multiplier: float) -> Tuple[int, Dict[str, Dict[str, int]]]:
    files: Dict[str, Dict[str, int]] = {}
    total = 0
    for rel in tree.rule_files():
        data = tree.read(rel) or b""
        toks = est_tokens(data, multiplier)
        files[rel] = {"bytes": len(data), "tokens": toks}
        total += toks
    return total, files


# ---------------------------------------------------------------- the audit


def audit(
    policy: Dict[str, Any], root: Path, base: Optional[str]
) -> Tuple[int, Dict[str, Any]]:
    inv = policy["global_invariants"]
    cap = int(inv["max_auto_injected_rules_tokens"])
    max_tools = int(inv["max_always_on_mcp_tools"])
    hosts = tuple(inv["forbidden_direct_provider_hosts"])
    mult = multiplier(policy)

    head = Tree(root)
    total, files = measure(head, mult)
    violations: List[str] = []
    notes: List[str] = []
    base_total: Optional[int] = None

    if total > cap:
        if base is not None:
            base_total, _ = measure(Tree(root, base), mult)
            if total > base_total:
                violations.append(
                    f"FC_TURN1_BLOATED_RULES:total_{total}_exceeds_cap_{cap}_and_grew_from_{base_total}"
                )
            else:
                notes.append(
                    f"OVER_CAP:total_{total}_cap_{cap}_held_or_shrank_from_{base_total}"
                )
        else:
            violations.append(f"FC_TURN1_BLOATED_RULES:total_{total}_exceeds_cap_{cap}")

    for name in MCP_CONFIGS:
        raw = head.read(name)
        if raw is None:
            continue
        text = raw.decode("utf-8", errors="replace")
        for host in hosts:
            if host in text:
                violations.append(f"FC_GATEWAY_BYPASS_RAW_PROVIDER:{name}:{host}")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            violations.append(f"ERR_MALFORMED_CONFIG_JSON:{name}")
            continue
        tools = data.get("always_on_tools") or data.get("tools")
        if isinstance(tools, list):
            if len(tools) > max_tools:
                violations.append(
                    f"FC_MCP_TOOL_CEILING_EXCEEDED:{name}:got_{len(tools)}_max_{max_tools}"
                )
        elif data.get("mcpServers"):
            notes.append(
                f"mcp_tools_unmeasured:{name}:{len(data['mcpServers'])}_servers_no_tool_list"
            )

    report = {
        "passed": not violations,
        "estimator": f"ceil(bytes/{BYTES_PER_TOKEN:g} x {mult:g}), calibrated to cl100k_base",
        "auto_injected_rule_tokens_total": total,
        "auto_injected_rule_tokens_cap": cap,
        "base": base,
        "base_total": base_total,
        "files": files,
        "violations": sorted(set(violations)),
        "notes": notes,
    }
    return (EXIT_PASS if not violations else EXIT_VIOLATION), report


# ---------------------------------------------------------------- the composing compiler


def contract_block(policy: Dict[str, Any]) -> str:
    inv = policy["global_invariants"]
    return (
        f"{BLOCK_START}\n"
        "## Fleet context contract (compiled from policy/context-policy.v1.json; edit the policy, not this block)\n\n"
        f"- Turn-1 auto-injected rules (AGENTS.md, CLAUDE.md, CLINE.md, .clinerules, copilot): at most "
        f"{inv['max_auto_injected_rules_tokens']} tokens in total. A change that grows a file already over the cap is "
        "refused with exit 43 by `bin/estate_context_fleet_sync.py --audit`.\n"
        f"- Always-on MCP tools: at most {inv['max_always_on_mcp_tools']}.\n"
        f"- Tool output over {inv['externalize_tool_result_bytes']} bytes goes to a file pointer; keep the last 15 lines "
        "of a failure trace verbatim.\n"
        f"- A sub-agent brief is at most {inv['subagent_max_brief_tokens']} tokens; never forward a parent transcript.\n"
        "- Do not change the system prompt or tool schemas mid-session: that keeps the KV-cache prefix stable.\n"
        f"- Rollout phase: {policy.get('rollout_phase', 'SHADOW')}. Router clamps and CHECKPOINT_AND_ROTATE are "
        "declared, not operating, until the router proves them.\n"
        f"{BLOCK_END}\n"
    )


def compose(text: str, block: str) -> str:
    """Return `text` with `block` in place. Bytes outside the block are never changed."""
    starts, ends = text.count(BLOCK_START), text.count(BLOCK_END)
    if (starts, ends) == (1, 1):
        i, j = text.index(BLOCK_START), text.index(BLOCK_END)
        if j < i:
            raise Refused("fleet contract markers are out of order")
        j += len(BLOCK_END)
        if text[j : j + 1] == "\n":
            j += 1
        return text[:i] + block + text[j:]
    if (starts, ends) != (0, 0):
        raise Refused(f"fleet contract markers malformed: {starts} start, {ends} end")
    lines = text.splitlines(keepends=True)
    at = 0
    if lines and lines[0].startswith(HISTORICAL_PREFIX):
        at = 1  # the historical marker must stay the first line (AGENTS.md, capability law)
    for anchor in ANCHORS_END:
        hit = [n for n, line in enumerate(lines) if line.strip() == anchor]
        if hit:
            at = hit[-1] + 1
            break
    head, tail = "".join(lines[:at]), "".join(lines[at:])
    sep_before = (
        ""
        if not head or head.endswith("\n\n")
        else ("\n" if head.endswith("\n") else "\n\n")
    )
    return (
        head
        + sep_before
        + block
        + ("\n" if tail and not tail.startswith("\n") else "")
        + tail
    )


def compile_tree(
    policy: Dict[str, Any], root: Path, check: bool
) -> Tuple[int, Dict[str, Any]]:
    block = contract_block(policy)
    changed: List[str] = []
    for rel in (
        "AGENTS.md",
    ):  # the fleet's shared contract file; others are not created
        p = root / rel
        if not p.is_file():
            continue
        old = p.read_text(encoding="utf-8")
        new = compose(old, block)
        if new != old:
            changed.append(rel)
            if not check:
                p.write_text(new, encoding="utf-8")
    rc = EXIT_VIOLATION if (check and changed) else EXIT_PASS
    return rc, {"mode": "check" if check else "compile", "changed": changed}


# ---------------------------------------------------------------- falsifiers


def self_test(policy: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    cap = int(policy["global_invariants"]["max_auto_injected_rules_tokens"])
    results: Dict[str, bool] = {}

    def git(root: Path, *args: str) -> None:
        # Hermetic: the machine's global hooks and signing config must not decide a falsifier.
        hermetic = ("-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false")
        rc = _git(root, *hermetic, *args)
        if rc.returncode != 0:
            err = rc.stderr.decode("utf-8", errors="replace").strip()[-200:]
            raise Refused(f"self-test git {args[0]} exit {rc.returncode}: {err}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        git(root, "init", "-q")
        git(root, "config", "user.email", "selftest@estate.invalid")
        git(root, "config", "user.name", "selftest")
        small = "# rules\n" + "- keep it short\n" * 20
        (root / "AGENTS.md").write_text(small, encoding="utf-8")
        results["good: a small rule file passes"] = (
            audit(policy, root, None)[0] == EXIT_PASS
        )

        # ~2,000 tokens of rules: the plan's synthetic bloat PR, judged with and without a base.
        bloat = "x" * (2000 * 4)
        (root / "AGENTS.md").write_text(bloat, encoding="utf-8")
        results["bad: a 2,000-token rule file with no base is refused 43"] = (
            audit(policy, root, None)[0] == EXIT_VIOLATION
        )
        git(root, "add", "-A")
        git(root, "commit", "-qm", "base")
        results["good: an over-cap file that did not grow passes the ratchet"] = (
            audit(policy, root, "HEAD")[0] == EXIT_PASS
        )
        (root / "AGENTS.md").write_text(bloat + "y" * 400, encoding="utf-8")
        results["bad: an over-cap file that grew is refused 43"] = (
            audit(policy, root, "HEAD")[0] == EXIT_VIOLATION
        )
        (root / "CLAUDE.md").write_text("z" * 4000, encoding="utf-8")
        (root / "AGENTS.md").write_text(bloat, encoding="utf-8")
        results["bad: growth moved into CLAUDE.md is still refused 43"] = (
            audit(policy, root, "HEAD")[0] == EXIT_VIOLATION
        )
        (root / "CLAUDE.md").unlink()
        try:
            audit(policy, root, "no-such-ref")
            results["bad: an unreadable base is refused, never passed"] = False
        except Refused:
            results["bad: an unreadable base is refused, never passed"] = True

        (root / "AGENTS.md").write_text(small, encoding="utf-8")
        (root / ".mcp.json").write_text(
            json.dumps({"tools": [f"t{i}" for i in range(11)]}), encoding="utf-8"
        )
        results["bad: 11 always-on MCP tools are refused 43"] = (
            audit(policy, root, None)[0] == EXIT_VIOLATION
        )
        (root / ".mcp.json").write_text(
            json.dumps({"url": "https://api.openai.com/v1"}), encoding="utf-8"
        )
        results["bad: a raw provider host in MCP config is refused 43"] = (
            audit(policy, root, None)[0] == EXIT_VIOLATION
        )
        (root / ".mcp.json").write_text(
            json.dumps({"mcpServers": {}}), encoding="utf-8"
        )
        (root / "AGENTS.md").write_text(
            small + "Intents live in ~/.estate/intents; launchctl is a door.\n",
            encoding="utf-8",
        )
        results["good: current law naming ~/.estate is not refused"] = (
            audit(policy, root, None)[0] == EXIT_PASS
        )

    law = "<!-- ESTATE_SUBSTRATE_AUTHORITY_START -->\nA\n<!-- ESTATE_SUBSTRATE_AUTHORITY_END -->\n\n## 1. Law\nbody\n"
    block = contract_block(policy)
    once = compose(law, block)
    results["good: compose keeps every byte outside the block"] = (
        once.replace(block, "", 1).replace("\n\n\n", "\n\n") == law
    )
    results["good: compose is idempotent"] = compose(once, block) == once
    results["good: the authority block stays first"] = once.startswith(
        "<!-- ESTATE_SUBSTRATE_AUTHORITY_START -->"
    )
    hist = "<!-- estate:historical current=docs/x.md -->\nold\n"
    results["good: the historical marker stays line 1"] = compose(
        hist, block
    ).startswith(hist.splitlines()[0] + "\n")
    try:
        compose(law + BLOCK_START + "\n", block)
        results["bad: a lone start marker is refused"] = False
    except Refused:
        results["bad: a lone start marker is refused"] = True

    ok = all(results.values())
    return (EXIT_PASS if ok else 1), {
        "self_test": "pass" if ok else "fail",
        "cap": cap,
        "results": results,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--policy", default=str(DEFAULT_POLICY))
    ap.add_argument("--repo-root", default=str(ROOT))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit", action="store_true")
    mode.add_argument("--compile", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--optimus", action="store_true")
    ap.add_argument("--base", default=None, help="git ref to ratchet against (audit)")
    ap.add_argument(
        "--check",
        action="store_true",
        help="with --compile: exit 43 if the block is not current",
    )
    args = ap.parse_args(argv)
    try:
        policy = load_policy(Path(args.policy))
        root = Path(args.repo_root).resolve()
        if args.optimus:
            total, files = measure(Tree(root), multiplier(policy))
            if not files:
                raise Refused(f"no auto-injected rule file under {root}: cannot judge")
            print(f"optimus.{OPTIMUS_METRIC}={total}")
            return EXIT_PASS
        if args.self_test:
            rc, report = self_test(policy)
        elif args.compile:
            rc, report = compile_tree(policy, root, args.check)
        else:
            rc, report = audit(policy, root, args.base)
    except Refused as exc:
        print(json.dumps({"refused": str(exc)}))
        return EXIT_REFUSED
    print(json.dumps(report, indent=2, sort_keys=True))
    return rc


if __name__ == "__main__":
    sys.exit(main())
