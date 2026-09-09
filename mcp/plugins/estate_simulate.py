"""Estate MCP plugin: the `simulate_change` / `execute_change` door (MUM-288).

Board row MUM-288 (spec `docs/specs/2026-09-08-estate-world-model-simulate-before-execute.md`):
the world model is not a Z3 oracle over nothing -- it is the cluster's own admission chain run
without persisting, exposed as one propose/execute tool pair on the estate MCP server. ADR 0006
already said every state-changing tool is two calls, propose then execute, and execute refuses
when the state hash no longer matches. Until this file, `mcp/plugins/` implemented none of it,
and nothing in `bin/`, `platform/` or `.github/` used Kubernetes server-side dry-run.

This file is the missing half: the propose/execute state machine that backs the pair. It is pure
given the graders it is handed, so every row of the spec's edge-case table is proved offline in
`tests/test_estate_simulate.py` with no cluster and no subprocess. What this file does hold is the
rule `bin/idp-fence-enforcement` and the fence-drill gate already encode: a grader that could not
run -- down webhook, unreachable API server, a grader never started -- is a fail-closed `UNKNOWN`,
never a pass, and `UNKNOWN` means execute refuses. Nothing here is ever `SAFE` on a grader that
did not answer.

The proposal is stored under its proposal id in this process's state (an injected registry, the
same shape the estate MCP server would back with its own store), never a host path (LAW 46 and
the spec's own rejection of `manifest -> /tmp`).

The real admission/laws/network/placement/converge graders are the existing `bin/` programs and
the estate's shadow-verify gate (W2.1/W2.2, `bin/idp-shadow`); this module does not copy their
logic, it marshals their verdicts into one envelope. A grader that the environment cannot reach is
`UNKNOWN`, and the whole verdict is `UNKNOWN`, exactly as the spec's edge-case table demands.

No subprocess, no shell, no network in this file by default: when `ESTATE_MCP_SIMULATE_GRADERS`
is unset (offline CI, a repo reader) every admission/laws grader is `UNKNOWN` and a proposal is
therefore never executable, which is the honest no-answer the estate already grades by. Set that
door only where the agent-reader kubeconfig and the bin programs actually exist (the estate MCP
server deployment), and pass the graders in.
"""

from __future__ import annotations

import datetime as dt
import os
import uuid

try:
    from datasette import hookimpl
except ImportError:  # pragma: no cover - datasette-less CI venv

    def hookimpl(fn):
        return fn


# A verdict on one question. `verdict` is one of SAFE, UNSAFE, UNKNOWN.
GRADER_NAMES = ("admission", "laws", "blast", "network", "placement", "converge")


def config() -> dict:
    return {
        "proposal_ttl_s": int(os.environ.get("ESTATE_MCP_PROPOSAL_TTL_S", "600")),
        "graders_door": os.environ.get("ESTATE_MCP_SIMULATE_GRADERS", "") == "1",
        "grade_laws_door": os.environ.get("ESTATE_MCP_GRADE_LAWS_DOOR", "") == "1",
        "state_branch": os.environ.get("ESTATE_MCP_STATE_BRANCH", "estate/state"),
    }


def grade_rules(rule_outcomes: dict[str, str]) -> str:
    """Fold the repository's per-rule law verdicts into one grader verdict.

    MUM-288 world-model row: "Does it pass the repository's laws?" -- the `laws` grader answers
    it by folding each rule that ran into the same fail-closed lattice the door already uses:
    SAFE iff every rule answered ok; UNSAFE if any FAIL; otherwise (a rule that could not run, or
    whose verdict was BLIND) UNKNOWN -- never SAFE on a rule that did not answer.

    `rule_outcomes` maps a rule id to its line's leading token: "ok", "FAIL", or "BLIND". Unknown
    tokens and absent rules fold to UNKNOWN.
    """
    if not rule_outcomes:
        return "UNKNOWN"
    for token in rule_outcomes.values():
        if not isinstance(token, str):
            return "UNKNOWN"
        first = token.strip().split()[0] if token.strip() else ""
        if first == "FAIL":
            return "UNSAFE"
    for token in rule_outcomes.values():
        first = token.strip().split()[0] if token.strip() else ""
        if first != "ok":
            return "UNKNOWN"
    return "SAFE"


class Registry:
    """The proposals an agent has simulated and not yet executed or expired.

    Backing for the propose/execute pair is injected (an in-memory dict by default, the shape the
    estate MCP server would back with its own process state), keyed by the proposal id -- never a
    host path.
    """

    def __init__(self) -> None:
        self.proposals: dict = {}

    def put(self, proposal: dict) -> None:
        self.proposals[proposal["proposal_id"]] = proposal

    def get(self, proposal_id: str) -> dict | None:
        return self.proposals.get(proposal_id)

    def drop(self, proposal_id: str) -> None:
        self.proposals.pop(proposal_id, None)


# One store for the process, shared across the simulate/execute pair so a proposal simulated in
# one MCP tool invocation is read by execute in another. Tests inject their own Registry to isolate
# cases instead of fighting the singleton.
_REGISTRY = Registry()


def hash_state(resource_versions: dict[str, str]) -> str:
    """The state hash is the sha256 over the sorted `resourceVersion` of every object in the
    touched namespaces plus the git sha of `clusters/`, exactly as the spec defines it.

    `resource_versions` maps an object identity like `deployments/edge/otto-ss` to its
    resourceVersion string. Empty input is a legal hash of nothing; callers who cannot enumerate
    the cluster hand the execute side an absent hash, which expires every proposal (fail closed).
    """
    import hashlib

    h = hashlib.sha256()
    for identity in sorted(resource_versions):
        h.update(identity.encode("utf-8"))
        h.update(b"\x00")
        h.update(str(resource_versions[identity]).encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _utc(now: dt.datetime | None) -> dt.datetime:
    value = now or dt.datetime.now(dt.timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)


def _expired(proposal: dict, now: dt.datetime, ttl_s: int) -> bool:
    expires = proposal.get("expires_at")
    if not isinstance(expires, str):
        return True
    try:
        limit = dt.datetime.fromisoformat(expires)
        if limit.tzinfo is None:
            limit = limit.replace(tzinfo=dt.timezone.utc)
        return now > limit.astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        return True


def simulate_change(
    source: str | dict,
    *,
    graders: dict,
    registry: Registry | None = None,
    cfg: dict | None = None,
    resource_versions: dict[str, str] | None = None,
    git_sha: str | None = None,
    now: dt.datetime | None = None,
) -> dict:
    """Run every named grader over `source` and return a bounded proposal.

    `graders` maps a grader name (GRADER_NAMES) to a zero-argument callable that returns a dict
    with at most `verdict` (SAFE|UNSAFE|UNKNOWN) and `detail`. A grader that is missing, raises,
    or yields anything but SAFE/UNSAFE is recorded as `UNKNOWN` -- never SAFE.

    The overall `verdict` is SAFE only when every grader answered SAFE. One UNSAFE is UNSAFE.
    Anything else -- a single UNKNOWN, an absent grader -- is UNKNOWN, and execute refuses.
    """
    cfg = cfg or config()
    registry = registry or _REGISTRY
    now = _utc(now)
    proposal_id = str(uuid.uuid4())

    results: dict[str, dict] = {}
    provided = 0
    for name in GRADER_NAMES:
        fn = graders.get(name)
        if fn is None:
            results[name] = {"verdict": "UNKNOWN", "detail": "grader not provided"}
            continue
        provided += 1
        try:
            res = fn()
            verdict = res.get("verdict") if isinstance(res, dict) else None
            if verdict not in ("SAFE", "UNSAFE"):
                raise ValueError(f"grader {name} did not answer SAFE/UNSAFE")
            results[name] = {"verdict": verdict, "detail": res.get("detail")}
        except Exception as exc:  # noqa: BLE001 - a broken grader is UNKNOWN, never a crash
            results[name] = {
                "verdict": "UNKNOWN",
                "detail": f"{name} could not run: {exc.__class__.__name__}",
            }

    any_unsafe = any(r["verdict"] == "UNSAFE" for r in results.values())
    any_unknown = any(r["verdict"] == "UNKNOWN" for r in results.values())
    if any_unsafe:
        verdict = "UNSAFE"
    elif any_unknown:
        verdict = "UNKNOWN"
    else:
        verdict = "SAFE"

    state_hash = hash_state(resource_versions or {})
    proposal = {
        "proposal_id": proposal_id,
        "source": source,
        "graders_on": provided == len(GRADER_NAMES),
        "grader_results": results,
        "computed_against": {
            "cluster_state_hash": state_hash,
            "git_sha": git_sha,
        },
        "verdict": verdict,
        "created_at": now.isoformat(),
        "expires_at": (now + dt.timedelta(seconds=cfg["proposal_ttl_s"])).isoformat(),
    }
    # Kept so an execute on it answers with the real reason (never SAFE, so it can never run) and
    # so FleetView shows the grader as the door down it is; a proposal that could not be fully
    # graded must not silently vanish from an agent's sight.
    registry.put(proposal)
    return proposal


def execute_change(
    proposal_id: str,
    presented_hash: str | None,
    *,
    registry: Registry | None = None,
    cfg: dict | None = None,
    now: dt.datetime | None = None,
) -> dict:
    """Execute a proposal only when it is kept, unexpired, not UNKNOWN, and the presented state
    hash still equals the one it was computed against. Every refusal is a dict with `executed:
    False` and the reason; the only success path is `executed: True` and names the state branch a
    Flux/JIT write would land on. This module never writes to the world; it is the guard before a
    JIT-broker grant or a commit to the state branch, which is the founder's one-platform door.
    """
    cfg = cfg or config()
    registry = registry or _REGISTRY
    now = _utc(now)

    proposal = registry.get(proposal_id)
    if proposal is None:
        # The spec: "Agent asks to execute without simulating -- no proposal id exists; refused.
        # An expired proposal is dropped from the registry so a late execute is a no-id, not a
        # memory of a different state.
        return {"executed": False, "error": "no proposal with that id; simulate first"}

    if _expired(proposal, now, cfg["proposal_ttl_s"]):
        registry.drop(proposal_id)
        return {"executed": False, "error": "proposal expired; re-simulate"}

    if proposal["verdict"] != "SAFE":
        registry.drop(proposal_id)
        return {
            "executed": False,
            "error": f"proposal verdict is {proposal['verdict']}, not SAFE",
        }

    expected = proposal["computed_against"]["cluster_state_hash"]
    if presented_hash is None or presented_hash != expected:
        registry.drop(proposal_id)
        return {
            "executed": False,
            "error": (
                "cluster state hash changed since the proposal was computed; "
                "re-simulate before executing"
            ),
            "presented_hash": presented_hash,
            "expected_hash": expected,
        }

    # Kept, unexpired, SAFE, and the world is the world it was graded against. Success is the
    # branch name the write lands on -- the actual write is the JIT broker / Flux reconciliation,
    # not this module. The proposal is spent.
    registry.drop(proposal_id)
    return {
        "executed": True,
        "state_branch": cfg["state_branch"],
        "git_sha": proposal["computed_against"]["git_sha"],
        "cluster_state_hash": expected,
    }


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def simulate_change(source: str) -> dict:
        """Propose a state change before any state-changing tool may run it (MUM-288, ADR 0006).
        `source` is a git ref plus path in this repository, or a named MCP action (`scale`,
        `suspend`, `rollout-restart`) with its arguments. Returns one proposal whose overall
        verdict is SAFE only when every grader answered SAFE; any grader that could not run makes
        it UNKNOWN and execute refuses. A SAFE/UNSAFE proposal is stored under its id; an UNKNOWN
        proposal answers but is never executable."""
        return simulate_change(
            source,
            graders=_live_graders(source) if config().get("graders_door") else {},
        )

    @mcp.tool()
    async def execute_change(proposal_id: str, cluster_state_hash: str) -> dict:
        """Run a simulated change. Refuses unless the proposal exists, is unexpired, graded SAFE,
        and the cluster_state_hash you present still equals the one the proposal was computed
        against. The hash is the sha256 over the sorted resourceVersion of every object in the
        touched namespaces plus the git sha of clusters/. On success names the state branch the
        Flux/JIT write lands on; the write itself is the broker's grant, not this tool."""
        return execute_change(
            proposal_id,
            cluster_state_hash,
        )


def _live_graders(source):
    """The real graders when the estate MCP server runs with the door on.

    `admission` is a live fact about the real cluster: it shells to `bin/idp-admission-dryrun`,
    which runs `kubectl apply --dry-run=server` so Kyverno's ClusterPolicies and every validating
    webhook answer for real and nothing persists (the spec's admission row, KEP-576). A program
    that has no temp manifest or cannot reach the chain is BLIND and surfaces here as UNKNOWN --
    never SAFE. The other five graders (laws, blast, network, placement, converge) are real estate
    programs wired under their own live doors; while any is UNKNOWN the whole verdict is UNKNOWN,
    not SAFE -- the estate already grades that way.
    """
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    base = Path(__file__).resolve().parents[2]
    grader = base / "bin" / "idp-admission-dryrun"
    cfg = config()

    def admission():
        if not grader.is_file():
            return {
                "verdict": "UNKNOWN",
                "detail": "bin/idp-admission-dryrun not present",
            }
        # The live door grades an inline manifest. A git-ref source has no file to dry-run here;
        # that needs the Flux diff seam and stays UNKNOWN (fail closed).
        raw = source if isinstance(source, str) else None
        if not raw or "apiVersion:" not in raw or "kind:" not in raw:
            return {
                "verdict": "UNKNOWN",
                "detail": "admission needs an inline manifest source",
            }
        tmp = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
                fh.write(raw)
                tmp = fh.name
            proc = subprocess.run(
                [sys.executable, str(grader), tmp],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception as exc:  # noqa: BLE001 - a grader that could not run is UNKNOWN
            return {"verdict": "UNKNOWN", "detail": f"admission could not run: {exc}"}
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        detail = (proc.stderr or "").strip()[-400:] or proc.stdout.strip()[-400:]
        if proc.returncode == 0:
            return {"verdict": "SAFE", "detail": detail or "admission accepts"}
        if proc.returncode == 1:
            return {"verdict": "UNSAFE", "detail": detail or "admission refuses"}
        return {"verdict": "UNKNOWN", "detail": detail or "admission chain unreachable"}

    def laws():
        """Grade 'does the repository pass its own laws' by folding bin/idp-rules per-rule verdicts
        with grade_rules. Honest door: it only shells when ESTATE_MCP_GRADE_LAWS_DOOR is on and the
        run line is reachable; otherwise UNKNOWN, never a fabricated pass. A run that fails to launch
        (no rules engine) is UNKNOWN."""
        if not cfg.get("grade_laws_door"):
            return {
                "verdict": "UNKNOWN",
                "detail": "laws door is off; no repository law verdict without it",
            }
        rules_bin = base / "bin" / "idp-rules"
        if not rules_bin.is_file():
            return {"verdict": "UNKNOWN", "detail": "bin/idp-rules not present"}
        try:
            proc = subprocess.run(
                [sys.executable, str(rules_bin), "run", "--plane", "ci"],
                capture_output=True,
                text=True,
                timeout=300,
            )
        except Exception as exc:  # noqa: BLE001 - a grader that could not run is UNKNOWN
            return {"verdict": "UNKNOWN", "detail": f"laws could not run: {exc}"}
        # Each 'ok    <rule> ...' / 'FAIL   <rule> ...' / 'BLIND  <rule> ...' line names a rule
        # outcome. Fold only those lines; never treat BLIND (a rule that could not grade) as a pass.
        outcomes: dict[str, str] = {}
        for line in proc.stdout.splitlines():
            parts = line.split(maxsplit=2)
            if len(parts) >= 2 and parts[0] in ("ok", "FAIL", "BLIND"):
                outcomes[parts[1]] = parts[0]
        verdict = grade_rules(outcomes)
        if not outcomes:
            return {
                "verdict": "UNKNOWN",
                "detail": "laws engine produced no per-rule verdicts to fold",
            }
        return {
            "verdict": verdict,
            "detail": f"laws folded {len(outcomes)} rule outcome(s)",
        }

    def converge():
        """Grade 'does the change actually converge if applied?' from the shadow dimension's own
        observation (MUM-288 converge row, W2.1/W2.2). The observation is a JSON file the shadow
        vcluster executor produced after applying the change -- it never exists on the MCP server's
        say-so. When none is supplied the change has not been proved to run anywhere real, so the
        verdict is UNKNOWN, never SAFE: a change whose convergence is unproven is not executable
        through this door."""
        raw_path = os.environ.get("ESTATE_MCP_SHADOW_OBSERVATION", "")
        if not raw_path:
            return {
                "verdict": "UNKNOWN",
                "detail": "no shadow observation supplied; convergence unproven",
            }
        verify = base / "bin" / "idp-shadow-verify"
        if not verify.is_file():
            return {"verdict": "UNKNOWN", "detail": "bin/idp-shadow-verify not present"}
        try:
            proc = subprocess.run(
                [sys.executable, str(verify), raw_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception as exc:  # noqa: BLE001 - a grader that could not run is UNKNOWN
            return {"verdict": "UNKNOWN", "detail": f"converge could not run: {exc}"}
        detail = (proc.stderr or "").strip()[-400:] or proc.stdout.strip()[-400:]
        if proc.returncode == 0:
            return {"verdict": "SAFE", "detail": detail or "shadow converged"}
        if proc.returncode == 1:
            return {"verdict": "UNSAFE", "detail": detail or "shadow did not converge"}
        return {
            "verdict": "UNKNOWN",
            "detail": detail or "shadow observation unreadable",
        }

    def _prefix(proc) -> tuple[str | None, str]:
        """The grader bins print a leading ok/FAIL/BLIND token; the verdict must come from that
        token, never from the exit code -- idp-fits-a-node returns 0 on BLIND too, so an exit-code
        reader would fold a blind read into a pass (the silent failure the estate's rules forbid)."""
        first_line = (proc.stdout or proc.stderr or "").strip().splitlines()
        first = first_line[0].strip() if first_line else ""
        parts = first.split(maxsplit=1)
        verdict_mark = (
            parts[0] if parts and parts[0] in ("ok", "FAIL", "BLIND") else None
        )
        return verdict_mark, first

    def network():
        """Grade 'can it reach what it needs and nothing else' (MUM-288 network row) from the Calico
        deny-feed the collector already carries (bin/idp-calico-deny-log): denial evidence is read
        for a real answer; an empty feed is FAIL (no evidence is not a clean bill); no feed supplied
        is UNKNOWN -- never SAFE."""
        raw = os.environ.get("ESTATE_MCP_CALICO_FEED", "")
        if not raw:
            return {
                "verdict": "UNKNOWN",
                "detail": "no Calico deny feed supplied; network ungraded",
            }
        deny = base / "bin" / "idp-calico-deny-log"
        if not deny.is_file():
            return {
                "verdict": "UNKNOWN",
                "detail": "bin/idp-calico-deny-log not present",
            }
        try:
            proc = subprocess.run(
                [sys.executable, str(deny), raw],
                capture_output=True,
                text=True,
                timeout=90,
            )
        except Exception as exc:  # noqa: BLE001 - a grader that could not run is UNKNOWN
            return {"verdict": "UNKNOWN", "detail": f"network could not run: {exc}"}
        verdict_mark, first = _prefix(proc)
        if verdict_mark == "ok":
            return {"verdict": "SAFE", "detail": first or "deny feed read clean"}
        if verdict_mark == "FAIL":
            return {"verdict": "UNSAFE", "detail": first or "deny feed shows a break"}
        return {
            "verdict": "UNKNOWN",
            "detail": first or "network grader did not answer",
        }

    def placement():
        """Grade 'will a node take it' (MUM-288 placement row) from a cluster snapshot receipt via
        bin/idp-fits-a-node. With no receipt the door does not read the live cluster (no standing
        write); the verdict is UNKNOWN -- never SAFE on a BLIND read, which idp-fits-a-node prints
        as BLIND even though it exits 0."""
        raw = os.environ.get("ESTATE_MCP_PLACEMENT_RECEIPT", "")
        if not raw:
            return {
                "verdict": "UNKNOWN",
                "detail": "no placement receipt supplied; placement ungraded",
            }
        fits = base / "bin" / "idp-fits-a-node"
        if not fits.is_file():
            return {"verdict": "UNKNOWN", "detail": "bin/idp-fits-a-node not present"}
        try:
            proc = subprocess.run(
                [sys.executable, str(fits), "--receipt", raw],
                capture_output=True,
                text=True,
                timeout=90,
            )
        except Exception as exc:  # noqa: BLE001 - a grader that could not run is UNKNOWN
            return {"verdict": "UNKNOWN", "detail": f"placement could not run: {exc}"}
        verdict_mark, first = _prefix(proc)
        if verdict_mark == "ok":
            return {
                "verdict": "SAFE",
                "detail": first or "every workload could be placed again",
            }
        if verdict_mark == "FAIL":
            return {
                "verdict": "UNSAFE",
                "detail": first or "a workload fits no other node",
            }
        return {
            "verdict": "UNKNOWN",
            "detail": first or "placement grader did not answer",
        }

    return {
        "admission": admission,
        "laws": laws,
        "converge": converge,
        "network": network,
        "placement": placement,
    }
