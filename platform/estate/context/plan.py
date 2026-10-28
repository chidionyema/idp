"""plan -- the ContextPlan: the estate's ONE context compiler's output contract.

THE CONTRACT (C1, docs/specs/2026-10-26-context-compiler-and-execution-gateway.md):

    resolve(task, *, surface, budget_tokens, tier) -> ContextPlan

A ContextPlan is a DETERMINISTIC answer. For the same task, the same surface, the same tree
and the same budget, it is the same plan, byte for byte. Three properties make that true, and
each one is a place where a plausible implementation would have broken it:

1. THE ENGINE RANKS. The working set -- which files, in which order -- comes from the one
   context engine (gortex v0.64.11). This module never scores, never weights, never reorders.
   It filters, and it says what it filtered. A second ranker here would be the stitching
   AGENTS.md 6 forbids: the estate already owns the ranking layer, and it is the engine's.

2. THE BUDGET IS A CEILING, MEASURED. `used_tokens` is the sum of MEASURED token counts of the
   excerpts actually in the plan -- never an estimate presented as a measurement. The tokenizer
   is named in the plan, so a reader knows which one produced the number. An item that does not
   fit is dropped and NAMED in `dropped`, with the reason.

3. EVERY ITEM CARRIES ITS PROVENANCE. The file, the commit it was read at, the lines, the
   SHA-256 of the file's bytes, the SHA-256 of the excerpt's bytes, the engine's rank, the
   impact evidence behind it, and a sentence saying why it is in the plan. A plan whose items
   cannot be checked against a commit is a rumour, not context.

DETERMINISM, CONCRETELY. `plan_hash` is the SHA-256 of the plan's ordered items and the
parameters that produced them. It deliberately excludes everything volatile -- the engine's
etag, its retrieval note, timings -- because those change without the answer changing. It
deliberately INCLUDES the tokenizer's name, because a plan measured with a different tokenizer
is a different measurement, and hiding that would be a lie by omission.

WHAT IS NOT HERE. No retrieval, no ranking, no embedding, no second index, no model call.
The engine answers; this file decides what to keep, what to drop, what to say, and how to
prove it.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from typing import Any, Mapping

# The plan's own limits. They are stated here, not scattered in the callers, so there is one
# place to look when a plan comes back too big.
MAX_EXCERPT_LINES = 120
MAX_EXCERPT_CHARS = 6000
# The engine is asked for this many tokens of working set. It is a request to the engine, not
# a promise about the plan: the plan's own ceiling is `budget_tokens`.
ENGINE_TOKEN_BUDGET = 12000

# The tiers, exactly as the contract names them (C1): "free" | "standard" | "frontier".
# What each one adds is STATED, because a tier that silently changes the answer is a tier
# nobody can reason about. The tiers are the SPEC's ladder, and each one is pinned to a
# retrieval depth:
#
#   free      the engine's working set, and nothing else. No subprocess, no second graph.
#   standard  + the estate's own impact map (bin/idp-affected-graph).
#   frontier  + the estate's catalog projection (bin/catalog-projection), the slowest and
#              the widest evidence layer.
#
# The tiers are EVIDENCE levels, not rankers: the engine's order is the plan's order at
# every tier.
TIERS = ("free", "standard", "frontier")

# Which evidence each tier is allowed to consult. "engine" is in every tier -- it is the
# answer, not an extra.
TIER_EVIDENCE: dict[str, tuple[str, ...]] = {
    "free": ("engine",),
    "standard": ("engine", "estate"),
    "frontier": ("engine", "estate", "catalog"),
}

# The agent surface the plan was built for. It is RECORDED in the plan, not enforced by a
# list: the estate has ONE per-request ceiling (platform/llm/request_ceiling.py) and the
# plan may never exceed it, whatever the surface is called.
DEFAULT_SURFACE = "pi"

# The doors. The cluster broker is the default route (the cloud is the default, the laptop
# is the fallback); "auto" tries the cluster first and falls back to the laptop, recording
# which door actually answered.
DOORS = ("auto", "cluster", "local")


class PlanError(RuntimeError):
    """The plan could not be built. The caller turns this into a refusal, never a guess."""


# --- tokens ------------------------------------------------------------------------------------
def measure_tokens(text: str, *, chars_per_token: int) -> tuple[int, str]:
    """The MEASURED size of a text, and the name of the ruler that measured it.

    THE ESTATE'S RULER IS THE ROUTER'S. platform/llm/request_ceiling.py counts a request as
    `chars // CHARS_PER_TOKEN`, because that is the count the router REFUSES on. A context plan
    measured by a different ruler would not be comparable with the ceiling it has to fit under,
    so the compiler measures with the same one and says which ruler it used.

    tiktoken was the earlier choice here, and it was wrong for this job, for a measured reason:
    on a cold cache it DOWNLOADS its BPE file over the network (4.3 seconds, measured
    2026-10-27), so measuring a plan would need the network -- and it would disagree with the
    router about what a token is. The estate has one ruler; the plan uses it.
    """
    if chars_per_token < 1:
        raise PlanError(
            f"a ruler of {chars_per_token} characters per token is not a ruler"
        )
    name = f"estate/chars-per-token:{chars_per_token}"
    if not text:
        return 0, name
    return len(text) // chars_per_token, name


# --- paths -------------------------------------------------------------------------------------
def normalize_path(raw: str, repo_root: str) -> str | None:
    """The repo-relative path of an engine path, or None if it is not in this tree.

    The engine reports paths as they are in ITS store, which is prefixed with the tracked
    repository's NAME -- "agent-surface/platform/estate/context/broker.py" for this worktree,
    "repo/pkg/broker.py" for the deployment's /data/repo. The prefix is the engine's storage
    detail, not the repository's, so it is stripped -- and only that prefix: the first
    segment is stripped when it IS the tracked repository's name, or when the remainder is
    really on disk. A first segment is never stripped on a guess, because "platform/..." is
    not a prefix, it is the path.

    A path that resolves to nothing is dropped rather than guessed at.
    """
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("/"):
        candidate = os.path.relpath(raw, repo_root)
    else:
        candidate = raw
    candidate = candidate.replace("\\", "/")
    if candidate.startswith("./"):
        candidate = candidate[2:]
    if os.path.exists(os.path.join(repo_root, candidate)):
        return candidate
    parts = candidate.split("/", 1)
    if len(parts) == 2:
        stripped = parts[1]
        if parts[0] == repo_name(repo_root) or os.path.exists(
            os.path.join(repo_root, stripped)
        ):
            return stripped
    return None


def repo_name(repo_root: str) -> str:
    """The name the engine stores this repository's files under: the tracked directory's name."""
    if not repo_root:
        return ""
    return os.path.basename(os.path.normpath(repo_root))


# --- excerpts ----------------------------------------------------------------------------------
def _read_excerpt(repo_root: str, rel_path: str) -> tuple[str, int, int]:
    """The head of a file, bounded, with the lines it covers.

    A file is a source when the engine says it is. Its HEAD is the excerpt, because the head
    of a file is where its contract lives, and a bounded head keeps a plan inside its budget.
    """
    full = os.path.join(repo_root, rel_path)
    try:
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            lines = []
            for i, line in enumerate(fh):
                if i >= MAX_EXCERPT_LINES:
                    break
                lines.append(line.rstrip("\n"))
    except OSError:
        return "", 0, 0
    text = "\n".join(lines)
    if len(text) > MAX_EXCERPT_CHARS:
        text = text[:MAX_EXCERPT_CHARS]
    end = len(lines)
    return text, 1, end


def _file_digest(repo_root: str, rel_path: str) -> str | None:
    """SHA-256 of a file's bytes in the tree the plan was read from."""
    try:
        h = hashlib.sha256()
        with open(os.path.join(repo_root, rel_path), "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


# --- the engine's answer, read -----------------------------------------------------------------
def engine_candidates(payload: Mapping[str, Any]) -> list[str]:
    """The engine's RANKED candidate files, in its order, without duplicates.

    `working_set` is the engine's ranking. `files_to_edit` is the engine's own view of what
    the task touches. Both are the engine's; this function only reads them, in that order,
    and never scores anything.
    """
    out: list[str] = []
    for entry in payload.get("working_set") or []:
        if isinstance(entry, dict) and entry.get("file"):
            out.append(str(entry["file"]))
    for entry in payload.get("files_to_edit") or []:
        if isinstance(entry, str):
            out.append(entry)
    seen: set[str] = set()
    ordered: list[str] = []
    for item in out:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def engine_symbols_by_file(
    payload: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """The engine's symbols, grouped by the file they live in."""
    out: dict[str, list[dict[str, Any]]] = {}
    for sym in payload.get("relevant_symbols") or []:
        if not isinstance(sym, dict):
            continue
        path = sym.get("file_path") or sym.get("path") or sym.get("file")
        if not path:
            continue
        out.setdefault(str(path), []).append(sym)
    return out


def engine_blast(payload: Mapping[str, Any]) -> dict[str, list[str]]:
    """The engine's blast radius: which file is called by what, and which tests cover it."""
    blast = payload.get("blast_radius") or {}
    callers: dict[str, list[str]] = {}
    if isinstance(blast, dict):
        for row in blast.get("callers_by_file") or []:
            if not isinstance(row, dict) or not row.get("file"):
                continue
            callers[str(row["file"])] = [str(c) for c in (row.get("callers") or [])]
    covering = (
        [str(t) for t in (blast.get("covering_tests") or [])]
        if isinstance(blast, dict)
        else []
    )
    return {"callers_by_file": callers, "covering_tests": covering}


# --- the estate's own impact layer -------------------------------------------------------------
def catalog_dependents(catalog: Mapping[str, Any] | None) -> dict[str, list[str]]:
    """The estate's catalog projection as a reverse dependency map: path -> dependents.

    bin/catalog-projection emits the estate's module graph as Backstage entities: each one
    carries its repo-relative source path in `metadata.annotations.estate/source-path` and
    the modules it imports in `spec.dependsOn`. The REVERSE is impact evidence -- given a
    file in the plan, which other modules depend on it. It is evidence, not ranking:
    nothing here reorders the plan, and a plan without this layer is still a plan.
    """
    if not catalog:
        return {}
    entities = catalog.get("entities") if isinstance(catalog, Mapping) else catalog
    by_slug: dict[str, str] = {}
    for entity in entities or []:
        if not isinstance(entity, dict):
            continue
        meta = entity.get("metadata") or {}
        ann = meta.get("annotations") or {}
        name = meta.get("name")
        source = ann.get("estate/source-path")
        if name and source:
            by_slug[str(name)] = str(source)
    reverse: dict[str, list[str]] = {}
    for entity in entities or []:
        if not isinstance(entity, dict):
            continue
        meta = entity.get("metadata") or {}
        ann = meta.get("annotations") or {}
        source = ann.get("estate/source-path")
        spec = entity.get("spec") or {}
        if not source or not isinstance(spec, dict):
            continue
        for dep in spec.get("dependsOn") or []:
            if not isinstance(dep, str):
                continue
            target = by_slug.get(dep.rsplit("/", 1)[-1])
            if target:
                reverse.setdefault(target, []).append(str(source))
    return {key: sorted(set(values)) for key, values in reverse.items()}


def estate_impact(affected: Mapping[str, Any] | None) -> dict[str, list[str]]:
    """The estate's own three-layer impact map, flattened to path -> relations.

    This is bin/idp-affected-graph's answer: layer 1 (code edges), layer 2 (prompt and
    schema), layer 3 (graph topology). It is the estate's IMPACT EVIDENCE -- what a change to
    a file would reach. It is not a ranker: nothing here decides order.
    """
    if not affected:
        return {"downstream": [], "tests": [], "changed": []}
    layers = affected.get("layers") or {}
    code = layers.get("code") or {}
    downstream = [str(x) for x in (code.get("downstream") or [])]
    tests = [str(x) for x in (code.get("tests") or [])]
    changed = [str(x) for x in (code.get("changed") or [])]
    if not changed:
        changed = [str(x) for x in (affected.get("changed") or [])]
    return {"downstream": downstream, "tests": tests, "changed": changed}


# --- the plan ----------------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class PlanInput:
    """Everything the assembler needs, and nothing it has to guess."""

    task: str
    surface: str
    tier: str
    budget_tokens: int
    repo_root: str
    commit: str
    index_commit: str
    engine_payload: Mapping[str, Any]
    # The estate's ruler, in characters per token, as the router counts it. There is no default:
    # a plan measured by a guessed ruler is a plan measured by nobody's rule.
    chars_per_token: int
    affected: Mapping[str, Any] | None = None
    engine_info: Mapping[str, Any] = dataclasses.field(default_factory=dict)
    catalog: Mapping[str, Any] | None = None
    # The estate's one per-request token ceiling for this surface. A budget above it is
    # refused, not clamped: a plan that quietly shrank would report a budget it never had.
    ceiling: int = 0
    door: str = ""


def _item_for(
    raw_path: str,
    rank: int,
    symbols: Mapping[str, list[dict[str, Any]]],
    blast: Mapping[str, list[str]],
    impact_map: Mapping[str, list[str]],
    dependents: Mapping[str, list[str]],
    repo_root: str,
) -> dict[str, Any] | None:
    """One item of the plan: a source, with everything needed to check it.

    Returns None when the engine's path is not in this tree -- a path that resolves to nothing
    is not a source, and inventing one would be worse than dropping it.
    """
    rel = normalize_path(raw_path, repo_root)
    if rel is None:
        return None

    # The engine's own symbols for this file, if it named any: their source is better than a
    # blind head-of-file, because the engine chose those symbols.
    excerpt = ""
    start_line, end_line = 0, 0
    chosen: list[str] = []
    for sym in symbols.get(raw_path, []) or symbols.get(rel, []):
        source = sym.get("source")
        if not source:
            continue
        excerpt = str(source)
        start_line = int(sym.get("start_line") or 0)
        end_line = start_line + excerpt.count("\n") + 1
        chosen.append(str(sym.get("name") or sym.get("id") or "symbol"))
        break
    if not excerpt:
        excerpt, start_line, end_line = _read_excerpt(repo_root, rel)
    if len(excerpt) > MAX_EXCERPT_CHARS:
        excerpt = excerpt[:MAX_EXCERPT_CHARS]

    # Impact evidence: the engine's blast radius for this file, plus the estate's own layer.
    engine_callers = list(blast.get("callers_by_file", {}).get(raw_path, []))
    if not engine_callers:
        engine_callers = list(blast.get("callers_by_file", {}).get(rel, []))
    estate_downstream = [
        x for x in impact_map.get("downstream", []) if x in (raw_path, rel)
    ]
    estate_tests = [x for x in impact_map.get("tests", []) if x in (raw_path, rel)]
    covering_tests = [
        t for t in blast.get("covering_tests", []) if t in (raw_path, rel)
    ]

    catalog_dependents_of = sorted(
        set(dependents.get(rel, []) or dependents.get(raw_path, []))
    )

    relations = sorted(
        set(engine_callers)
        | set(estate_downstream)
        | set(estate_tests)
        | set(covering_tests)
        | set(catalog_dependents_of)
    )
    if relations:
        why_impact = (
            f"{len(engine_callers)} engine caller(s), {len(estate_downstream)} estate downstream node(s), "
            f"{len(estate_tests)} estate test(s), {len(covering_tests)} covering test(s), "
            f"{len(catalog_dependents_of)} catalog dependent(s)"
        )
    else:
        why_impact = "no impact relation found for this file in the engine's blast radius or the estate's layer"

    symbols_named = ", ".join(chosen) if chosen else "file"
    why = f"engine rank {rank}: {rel} ({symbols_named}); impact: {why_impact}"

    return {
        "rank": rank,
        # The contract's names (spec C1): source, sha256, tokens, impact_score, rank, why.
        "source": rel,
        "sha256": _file_digest(repo_root, rel),
        "impact_score": len(relations),
        "why": why,
        # The detail behind them. The contract does not forbid it and an agent needs it: which
        # engine path the file came from, the lines, the text, and the evidence itself.
        "file": rel,
        "engine_path": raw_path,
        "excerpt": excerpt,
        "start_line": start_line,
        "end_line": end_line,
        "impact": {
            "score": len(relations),
            "why": why_impact,
            "engine_callers": sorted(set(engine_callers)),
            "estate_downstream": sorted(set(estate_downstream)),
            "estate_tests": sorted(set(estate_tests)),
            "covering_tests": sorted(set(covering_tests)),
            "catalog_dependents": catalog_dependents_of,
        },
    }


def assemble(inp: PlanInput) -> dict[str, Any]:
    """Build the ContextPlan from the engine's answer.

    Deterministic by construction: the engine's order is the plan's order, the budget filter
    is a prefix-sum over measured tokens, and the hash covers the items and the parameters
    that produced them -- never a timestamp, never an etag, never a timing.
    """
    if inp.ceiling and inp.budget_tokens > inp.ceiling:
        raise PlanError(
            f"the budget of {inp.budget_tokens} tokens is above the surface's per-request "
            f"ceiling of {inp.ceiling}; the plan is refused rather than silently shrunk"
        )
    payload = inp.engine_payload
    symbols = engine_symbols_by_file(payload)
    blast = engine_blast(payload)
    impact_map = estate_impact(inp.affected)
    dependents = catalog_dependents(inp.catalog)

    items: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    used = 0
    tokenizer = f"estate/chars-per-token:{inp.chars_per_token}"
    rank = 0
    for raw_path in engine_candidates(payload):
        rank += 1
        item = _item_for(
            raw_path, rank, symbols, blast, impact_map, dependents, inp.repo_root
        )
        if item is None:
            dropped.append(
                {
                    "source": raw_path,
                    "reason": "not-in-tree",
                    "detail": "the engine named a path this tree does not have",
                }
            )
            continue
        tokens, tokenizer = measure_tokens(
            item["excerpt"], chars_per_token=inp.chars_per_token
        )
        item["tokens"] = tokens
        if used + tokens > inp.budget_tokens:
            dropped.append(
                {
                    "source": item["source"],
                    "reason": "budget",
                    "detail": f"{tokens} tokens would take the plan to {used + tokens}, over the budget of {inp.budget_tokens}",
                }
            )
            continue
        used += tokens
        items.append(item)

    # The impact nodes the plan did NOT cover, named. A plan that silently drops the blast
    # radius is a plan that hides its own gaps.
    included = {i["file"] for i in items}
    included_raw = {i["engine_path"] for i in items}
    uncovered: list[dict[str, str]] = []

    def _uncovered(node: str, why: str) -> None:
        if node in included or node in included_raw:
            return
        entry = {"node": node, "why": why}
        if entry not in uncovered:
            uncovered.append(entry)

    for _path, callers in sorted(blast.get("callers_by_file", {}).items()):
        for caller in callers:
            _uncovered(
                caller, "a caller of an indexed file that the plan does not carry"
            )
    for node in impact_map.get("downstream", []):
        _uncovered(node, "an estate downstream node the plan does not carry")
    for node in impact_map.get("tests", []):
        _uncovered(node, "an estate test the plan does not carry")
    for _node, dependents_of in sorted(dependents.items()):
        for dependent in dependents_of:
            _uncovered(
                dependent,
                "a catalog dependent of an indexed file that the plan does not carry",
            )
    for path in payload.get("files_to_edit") or []:
        if isinstance(path, str):
            _uncovered(
                path,
                "the engine expects this file to be edited, and the plan does not carry it",
            )
    for path in payload.get("related_test_files") or []:
        if isinstance(path, str):
            _uncovered(
                path,
                "the engine named this related test, and the plan does not carry it",
            )

    plan: dict[str, Any] = {
        "task": inp.task,
        "surface": inp.surface,
        "tier": inp.tier,
        "door": inp.door,
        "evidence": list(TIER_EVIDENCE.get(inp.tier, ("engine",))),
        "ceiling": inp.ceiling,
        "budget_tokens": inp.budget_tokens,
        "used_tokens": used,
        "tokenizer": tokenizer,
        "items": items,
        "dropped": dropped,
        "coverage": {
            "uncovered_impact_nodes": uncovered,
            "engine_files_to_edit": [
                p for p in (payload.get("files_to_edit") or []) if isinstance(p, str)
            ],
            "related_test_files": [
                p
                for p in (payload.get("related_test_files") or [])
                if isinstance(p, str)
            ],
            "engine_note": payload.get("retrieval_note") or {},
        },
        "provenance": {
            "commit": inp.commit,
            "index_commit": inp.index_commit,
            "engine": dict(inp.engine_info),
        },
    }
    plan["plan_hash"] = plan_hash(plan)
    return plan


def plan_hash(plan: Mapping[str, Any]) -> str:
    """The SHA-256 of the plan's ordered items and the parameters that produced them.

    Volatile fields are excluded on purpose: the engine's etag, its retrieval note and any
    timing change without the answer changing, and a hash that moved for those reasons would
    be a hash nobody could use. The tokenizer IS included: a plan measured with a different
    tokenizer is a different measurement.
    """
    canonical = {
        "task": plan.get("task"),
        "surface": plan.get("surface"),
        "tier": plan.get("tier"),
        "budget_tokens": plan.get("budget_tokens"),
        "tokenizer": plan.get("tokenizer"),
        "items": [
            {
                "rank": i.get("rank"),
                "source": i.get("source"),
                "sha256": i.get("sha256"),
                "start_line": i.get("start_line"),
                "end_line": i.get("end_line"),
                "tokens": i.get("tokens"),
                "impact_score": i.get("impact_score"),
            }
            for i in plan.get("items") or []
        ],
    }
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def redact_plan(
    plan: Mapping[str, Any],
    scrub: Any,
    secrets: Mapping[str, str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Scrub every excerpt in the plan with the BROKER's rule, and say what was removed.

    One rule about what a secret is (AGENTS.md 4): the broker owns it, and the compiler calls
    it rather than growing its own -- so the scrubber is passed in, never re-implemented here.
    """
    removed: set[str] = set()
    for item in plan.get("items") or []:
        clean, hits = scrub(str(item.get("excerpt") or ""), secrets)
        item["excerpt"] = clean
        item["content_sha256"] = hashlib.sha256(clean.encode("utf-8")).hexdigest()
        removed.update(hits)
    return plan, sorted(removed)
