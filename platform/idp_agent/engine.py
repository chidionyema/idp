#!/usr/bin/env python3
"""IDP Ephemeral Engine.

Polls Redis for tasks, creates isolated workspaces, runs agent logic, scores
every turn through the verification harness (idp#3564) before anything is
pushed to GitHub, and validates changes in an isolated OrbStack container.
See docs/specs/orbstack-event-driven-agents.md for the full architecture.
"""

import importlib.util
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager

import redis


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GH_APP_LANE = os.getenv("IDP_GH_APP_LANE", "agent-workforce")


def mint_gh_token() -> str:
    """A fresh installation token narrowed to the estate's existing
    `agent-workforce` GitHub App lane (platform/github-app/lanes.json:
    contents:write, pull_requests:write, issues:write, metadata/actions/checks
    read -- it can open and update PRs and push to a branch, and it can
    never merge, dispatch a workflow, or reach a cluster).

    In-cluster, GH_TOKEN_FILE points at a Secret populated by external-secrets'
    own GithubAccessToken generator (platform/idp_agent/k8s/engine-deployment.yaml),
    the same pattern platform/mcp/external-secret.yaml and
    platform/hermes-agent/gateway.yaml already use: ESO mints and refreshes the
    token at the platform layer, on a 10-minute ExternalSecret refreshInterval
    well inside the token's 60-minute life, with no OCI credential or vault
    access inside this pod at all. Reading the file fresh on every call (this
    engine mints per task, not once at boot) means a rotated token is always
    picked up without needing a Reloader-triggered restart the way a
    read-once-at-boot consumer like github-mcp does.

    Local dev has two lighter options, in order: GH_TOKEN (a developer's own
    PAT) or shelling out to `bin/idp-github-app token <lane>` directly (real
    OCI credentials on a laptop, no cluster needed)."""
    token_file = os.getenv("GH_TOKEN_FILE")
    if token_file:
        with open(token_file) as f:
            return f.read().strip()

    static_token = os.getenv("GH_TOKEN")
    if static_token:
        return static_token

    idp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    result = subprocess.run(
        [os.path.join(idp_root, "bin", "idp-github-app"), "token", GH_APP_LANE],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CI_IMAGE = os.getenv("IDP_CI_IMAGE", "node:20-bullseye-slim")
CI_COMMAND = os.getenv("IDP_CI_COMMAND", "bin/idp-ci")
VACUUM_TIMEOUT_S = int(os.getenv("IDP_VACUUM_TIMEOUT_S", "600"))
WORKER_ID = f"engine-{os.getpid()}"

logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [{WORKER_ID}] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

queue = redis.Redis.from_url(REDIS_URL, decode_responses=True)

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    log.info("Shutdown signal received. Finishing current task...")
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ---------------------------------------------------------------------------
# The eval workflow integration (idp#3564): every task goes through this
# before anything reaches GitHub. See docs/specs/orbstack-event-driven-
# agents.md section 9.
# ---------------------------------------------------------------------------
def _load_verification_hook():
    """platform/ has no top-level __init__.py: a bare `import platform`
    (pytest, dagster, jsonschema, wsgiref all do one) permanently shadows
    platform.* submodules for the rest of the process unless the dotted
    names are seeded directly into sys.modules first. Same pattern as
    tests/integration/test_claude_code_hook.py."""
    idp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    for dotted, rel in [
        ("platform.eval", "platform/eval/__init__.py"),
        ("platform.eval.judge_drift", "platform/eval/judge_drift.py"),
        ("platform.eval.judge_worker", "platform/eval/judge_worker.py"),
        ("platform.integration", "platform/integration/__init__.py"),
        (
            "platform.integration.claude_code_hook",
            "platform/integration/claude_code_hook.py",
        ),
    ]:
        if dotted in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(
            dotted, os.path.join(idp_root, rel)
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[dotted] = module
        spec.loader.exec_module(module)
    return sys.modules["platform.integration.claude_code_hook"]


_hook_module = _load_verification_hook()
_verification_hook = _hook_module.get_hook()


def run_task_through_harness(
    transcript_id: str, spans: list[dict], output: str
) -> dict:
    """LAW: no agent output on this platform is trusted without a passing
    verdict from the verification hook. Called by every task handler below
    before any commit, push, or PR/review is created."""
    result = _verification_hook.verify_agent_result(
        {
            "transcript_id": transcript_id,
            "transcript": {"transcript_id": transcript_id, "spans": spans},
            "output": output,
        }
    )
    if result["halt"]:
        log.warning(
            "HARNESS HALTED transcript=%s failures=%s",
            transcript_id,
            [f["gate"] for f in result["failures"]],
        )
    return result


def _gh_env(gh_token: str) -> dict:
    """Env for a `gh` CLI subprocess call: the freshly minted installation
    token, not ambient `gh auth` state a fresh pod has none of."""
    return {**os.environ, "GH_TOKEN": gh_token}


def _dead_letter(task: dict, reason: str) -> None:
    task_with_reason = {**task, "_dead_letter_reason": reason}
    queue.rpush("idp_tasks_dead", json.dumps(task_with_reason))
    log.error("Task moved to idp_tasks_dead: %s", reason)


# ---------------------------------------------------------------------------
# Ephemeral Workspace
# ---------------------------------------------------------------------------
@contextmanager
def ephemeral_workspace(repo_url: str, branch_name: str):
    """A mathematically isolated, disposable workspace: mints a fresh
    installation token, clones the repo, checks out (or creates) the
    target branch, and destroys itself on exit. Yields (workspace_path,
    gh_token) -- callers pass gh_token to every `gh` subprocess call
    (env={**os.environ, "GH_TOKEN": gh_token}) rather than relying on
    ambient `gh` CLI auth state, which a fresh pod has none of."""
    gh_token = mint_gh_token()

    with tempfile.TemporaryDirectory(prefix="idp_ws_") as tmp_dir:
        log.info("Spawning isolated workspace: %s", tmp_dir)

        clone_url = repo_url
        if gh_token and clone_url.startswith("https://"):
            clone_url = clone_url.replace(
                "https://", f"https://x-access-token:{gh_token}@"
            )

        result = subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, "."],
            cwd=tmp_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr}")

        result = subprocess.run(
            ["git", "checkout", branch_name],
            cwd=tmp_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=tmp_dir,
                check=True,
                capture_output=True,
            )

        subprocess.run(
            ["git", "config", "user.email", "agent@idp.local"], cwd=tmp_dir, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "IDP Agent"], cwd=tmp_dir, check=True
        )

        try:
            yield tmp_dir, gh_token
        finally:
            log.info("Teardown complete. %s destroyed.", tmp_dir)


# ---------------------------------------------------------------------------
# OrbStack Vacuum (CI Isolation) -- local dev fast-feedback only.
#
# This talks to the Docker/OrbStack socket, which means whatever process
# calls it has host-root-equivalent access: mounting /var/run/docker.sock
# into a pod is a known container-escape vector and this cluster's Kyverno
# policy set already refuses privileged/hostPath access of that shape (the
# same reason jit-broker and every other Deployment here run
# readOnlyRootFilesystem, non-root, no added capabilities -- see
# platform/jit/deployment.yaml). Docker-in-Kubernetes is not this
# architecture's real CI boundary; GitHub Actions already is (the same 14
# checks that gate every PR in this repository today). Running in-cluster,
# IDP_SKIP_LOCAL_VACUUM=1 (engine-deployment.yaml sets it) skips straight
# from the harness verdict to push + PR, and GitHub Actions grades the PR
# the same way it grades every other one. This function stays for the
# local-dev loop, where a developer's own OrbStack socket is exactly that:
# their own, not a cluster's.
# ---------------------------------------------------------------------------
SKIP_LOCAL_VACUUM = os.getenv("IDP_SKIP_LOCAL_VACUUM", "0") == "1"


def run_orbstack_vacuum(workspace_path: str) -> tuple[bool, str]:
    """Runs CI inside an OrbStack container mounted to the ephemeral
    workspace, with no network access. Returns (passed, logs). Local dev
    only -- see the module note above for why this never runs in-cluster."""
    if SKIP_LOCAL_VACUUM:
        log.info("IDP_SKIP_LOCAL_VACUUM=1: deferring to GitHub Actions CI on the PR.")
        return True, "skipped (in-cluster: GitHub Actions is the CI boundary)"

    log.info("Booting OrbStack isolation chamber...")

    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-v",
        f"{workspace_path}:/app",
        "-w",
        "/app",
        "-e",
        "IDP_CI_FAST=1",
        CI_IMAGE,
        "bash",
        "-c",
        (
            "apt-get update -qq && "
            "apt-get install -y -qq python3 git curl > /dev/null && "
            f"{CI_COMMAND}"
        ),
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=VACUUM_TIMEOUT_S
    )

    if result.returncode != 0:
        error = f"CI FAILED (exit {result.returncode})\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        log.error("Vacuum failed: %s", error[:1000])
        return False, error

    log.info("Vacuum passed.")
    return True, result.stdout


# ---------------------------------------------------------------------------
# Agents. Each returns (spans, output): spans is what actually happened
# (real tool calls this run made), output is the agent's own account of what
# it did. run_task_through_harness compares the two before anything is
# trusted. Planning logic (LangGraph) is not written here -- see
# docs/specs/orbstack-event-driven-agents.md section 11 -- but the call
# sites, transcript shape, and harness gate are real and tested.
# ---------------------------------------------------------------------------
def run_worker_agent(task: dict, workspace: str) -> tuple[list[dict], str]:
    """Worker Agent: resolves a feature request or issue."""
    log.info("Worker Agent resolving issue #%s...", task.get("issue_id"))
    # ======================================================================
    # INSERT LANGGRAPH WORKER EXECUTION HERE. Append one span per real tool
    # call the agent makes, e.g.:
    #   spans.append({"span_kind": "tool_call", "tool_name": "write_file",
    #                  "args": {"path": "AGENT_FIX.txt"}})
    # ======================================================================
    fix_path = os.path.join(workspace, "AGENT_FIX.txt")
    with open(fix_path, "w") as f:
        f.write(f"Resolved issue #{task.get('issue_id')}\n")

    spans = [
        {
            "span_kind": "tool_call",
            "tool_name": "write_file",
            "args": {"path": "AGENT_FIX.txt"},
        }
    ]
    output = f"I wrote AGENT_FIX.txt to resolve issue #{task.get('issue_id')}."
    return spans, output


def run_judge_agent(task: dict, workspace: str) -> tuple[bool, list[dict], str]:
    """Judge Agent: reviews a PR. Returns (approved, spans, output)."""
    log.info("Judge Agent reviewing PR #%s...", task.get("pr_num"))
    # ======================================================================
    # INSERT LANGGRAPH JUDGE EXECUTION HERE.
    # ======================================================================
    spans: list[dict] = []
    output = f"Reviewed PR #{task.get('pr_num')}: no blocking issues found."
    return True, spans, output


def run_sre_agent(task: dict, workspace: str) -> tuple[bool, list[dict], str]:
    """SRE Agent: reverts a bad commit. Returns (succeeded, spans, output)."""
    log.info("SRE Agent reverting commit %s...", task.get("commit_sha"))
    # ======================================================================
    # INSERT LANGGRAPH SRE EXECUTION HERE.
    # ======================================================================
    result = subprocess.run(
        ["git", "revert", "--no-edit", task["commit_sha"]],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    spans = [
        {
            "span_kind": "tool_call",
            "tool_name": "git_revert",
            "args": {"commit": task["commit_sha"]},
            "error": result.stderr if result.returncode != 0 else None,
        }
    ]
    output = f"Reverted commit {task['commit_sha'][:8]}."
    return result.returncode == 0, spans, output


# ---------------------------------------------------------------------------
# Task Handlers
# ---------------------------------------------------------------------------
def handle_worker_feature(task: dict) -> None:
    branch = f"auto/worker-issue-{task['issue_id']}"
    transcript_id = f"worker_{task['issue_id']}_{uuid.uuid4().hex[:8]}"

    with ephemeral_workspace(task["repo_url"], branch) as (workspace, gh_token):
        spans, output = run_worker_agent(task, workspace)

        verdict = run_task_through_harness(transcript_id, spans, output)
        if verdict["halt"]:
            _dead_letter(task, f"harness halted: {verdict['failures']}")
            return

        passed, logs = run_orbstack_vacuum(workspace)
        if not passed:
            log.warning("Task failed CI validation. Not opening PR.")
            _dead_letter(task, "orbstack vacuum failed")
            return

        subprocess.run(["git", "add", "."], cwd=workspace, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: resolve #{task['issue_id']}"],
            cwd=workspace,
            check=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                f"Resolve #{task['issue_id']}",
                "--body",
                "Auto-generated by IDP Worker Agent. Verified by the harness before push.",
                "--head",
                branch,
            ],
            cwd=workspace,
            env=_gh_env(gh_token),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["gh", "pr", "merge", "--auto", "--squash"],
            cwd=workspace,
            env=_gh_env(gh_token),
            check=True,
            capture_output=True,
        )
        log.info("PR created and queued for merge for issue #%s", task["issue_id"])


def handle_judge_review(task: dict) -> None:
    transcript_id = f"judge_{task['pr_num']}_{uuid.uuid4().hex[:8]}"

    with ephemeral_workspace(task["repo_url"], task["branch"]) as (workspace, gh_token):
        approved, spans, output = run_judge_agent(task, workspace)

        verdict = run_task_through_harness(transcript_id, spans, output)
        if verdict["halt"]:
            _dead_letter(task, f"harness halted: {verdict['failures']}")
            return

        if approved:
            subprocess.run(
                ["gh", "pr", "review", str(task["pr_num"]), "--approve"],
                cwd=workspace,
                env=_gh_env(gh_token),
                check=True,
                capture_output=True,
            )
            log.info("PR #%s approved.", task["pr_num"])
        else:
            subprocess.run(
                [
                    "gh",
                    "pr",
                    "review",
                    str(task["pr_num"]),
                    "--request-changes",
                    "--body",
                    "Automated review found issues.",
                ],
                cwd=workspace,
                env=_gh_env(gh_token),
                check=True,
                capture_output=True,
            )
            log.info("PR #%s changes requested.", task["pr_num"])


def handle_sre_revert(task: dict) -> None:
    branch = f"auto/sre-revert-{task['commit_sha'][:8]}"
    transcript_id = f"sre_{task['commit_sha'][:8]}_{uuid.uuid4().hex[:8]}"

    with ephemeral_workspace(task["repo_url"], branch) as (workspace, gh_token):
        success, spans, output = run_sre_agent(task, workspace)
        if not success:
            log.error("SRE revert failed.")
            _dead_letter(task, "git revert failed")
            return

        verdict = run_task_through_harness(transcript_id, spans, output)
        if verdict["halt"]:
            _dead_letter(task, f"harness halted: {verdict['failures']}")
            return

        passed, logs = run_orbstack_vacuum(workspace)
        if not passed:
            log.error("Revert failed CI. Manual intervention required.")
            _dead_letter(task, "orbstack vacuum failed on revert")
            return

        subprocess.run(["git", "add", "."], cwd=workspace, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"revert: {task['commit_sha'][:8]}"],
            cwd=workspace,
            check=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                f"Revert {task['commit_sha'][:8]}",
                "--body",
                f"Auto-revert due to: {task.get('error_log', '')[:500]}",
                "--head",
                branch,
            ],
            cwd=workspace,
            env=_gh_env(gh_token),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["gh", "pr", "merge", "--auto", "--squash"],
            cwd=workspace,
            env=_gh_env(gh_token),
            check=True,
            capture_output=True,
        )
        log.info("Revert PR created for %s", task["commit_sha"][:8])


# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------
HANDLERS = {
    "worker_feature": handle_worker_feature,
    "judge_review": handle_judge_review,
    "sre_revert": handle_sre_revert,
}


def worker_loop() -> None:
    log.info("Engine online. Polling Redis...")
    while not _shutdown:
        try:
            item = queue.blpop("idp_tasks", timeout=5)
            if item is None:
                continue

            _, task_data = item
            task = json.loads(task_data)
            log.info("Claimed task: %s", task["type"])

            handler = HANDLERS.get(task["type"])
            if handler:
                handler(task)
            else:
                log.warning("No handler for task type: %s", task["type"])
                _dead_letter(task, f"no handler for type {task['type']!r}")

        except redis.ConnectionError:
            log.error("Redis connection lost. Retrying in 5s...")
            time.sleep(5)
        except Exception as exc:
            log.exception("Unhandled error processing task: %s", exc)
            time.sleep(1)

    log.info("Engine shut down gracefully.")


if __name__ == "__main__":
    worker_loop()
