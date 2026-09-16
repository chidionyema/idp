#!/usr/bin/env python3
"""IDP Event Gateway.

Receives GitHub and Flux webhooks, normalizes them into tasks, and pushes
them onto the Redis queue (`idp_tasks`) that platform/idp_agent/engine.py
polls. See docs/specs/orbstack-event-driven-agents.md for the full
architecture.
"""

import hashlib
import hmac
import json
import logging
import os

import redis
import uvicorn
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [gateway] %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

app = FastAPI(title="IDP Event Gateway")


def _read_webhook_secret() -> str:
    """GITHUB_WEBHOOK_SECRET for local dev; GITHUB_WEBHOOK_SECRET_FILE
    in-cluster, where it arrives as a 0400 file from an ExternalSecret
    (gateway-deployment.yaml) rather than an env var a crash dump or
    `kubectl describe pod` would print."""
    secret_file = os.getenv("GITHUB_WEBHOOK_SECRET_FILE")
    if secret_file:
        with open(secret_file) as f:
            return f.read().strip()
    return os.getenv("GITHUB_WEBHOOK_SECRET", "")


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
GITHUB_WEBHOOK_SECRET = _read_webhook_secret()

queue = redis.Redis.from_url(REDIS_URL, decode_responses=True)

if not GITHUB_WEBHOOK_SECRET:
    log.warning(
        "GITHUB_WEBHOOK_SECRET is unset -- webhook signature verification is OFF. "
        "This is only safe for local dev; production deployments must set it "
        "(docs/specs/orbstack-event-driven-agents.md#5-security-model)."
    )


def verify_github_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """Verify GitHub's HMAC-SHA256 webhook signature. Always True when no
    secret is configured (local dev only -- see the startup warning above)."""
    if not GITHUB_WEBHOOK_SECRET:
        return True
    if not signature_header or "=" not in signature_header:
        return False
    hash_algorithm, github_signature = signature_header.split("=", 1)
    if hash_algorithm != "sha256":
        return False
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), payload_body, hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), github_signature)


def push_to_queue(task: dict) -> None:
    """Atomically push a task onto the Redis queue."""
    queue.rpush("idp_tasks", json.dumps(task))
    log.info("queued task=%s repo=%s", task["type"], task.get("repo_url", "unknown"))


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    bg_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    """Normalize GitHub issue/PR/check_run events into tasks."""
    raw_body = await request.body()
    if not verify_github_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = json.loads(raw_body)
    event_type = x_github_event
    task = None

    if event_type == "issues" and payload.get("action") == "opened":
        task = {
            "type": "worker_feature",
            "repo_url": payload["repository"]["clone_url"],
            "issue_id": payload["issue"]["number"],
            "goal": payload["issue"]["body"],
        }

    elif event_type == "pull_request" and payload.get("action") in (
        "opened",
        "reopened",
    ):
        task = {
            "type": "judge_review",
            "repo_url": payload["repository"]["clone_url"],
            "pr_num": payload["pull_request"]["number"],
            "branch": payload["pull_request"]["head"]["ref"],
        }

    elif event_type == "check_run" and payload.get("action") == "completed":
        if payload["check_run"]["conclusion"] == "failure":
            task = {
                "type": "sre_revert",
                "repo_url": payload["repository"]["clone_url"],
                "error_log": payload["check_run"].get("output", {}).get("summary", ""),
                "commit_sha": payload["check_run"]["head_sha"],
            }

    if task:
        bg_tasks.add_task(push_to_queue, task)
        return {"status": "accepted", "task_type": task["type"]}

    return {"status": "ignored", "reason": "unhandled event"}


@app.post("/webhook/flux")
async def flux_webhook(request: Request, bg_tasks: BackgroundTasks):
    """Normalize a Flux reconciliation-failure alert into an sre_revert task."""
    payload = await request.json()

    if payload.get("severity") == "error":
        task = {
            "type": "sre_revert",
            "repo_url": os.getenv(
                "FLUX_REPO_URL", "https://github.com/chidionyema/idp.git"
            ),
            "error_log": payload.get("message", ""),
            "commit_sha": payload.get("metadata", {}).get("revision", ""),
        }
        bg_tasks.add_task(push_to_queue, task)
        return {"status": "accepted", "task_type": "sre_revert"}

    return {"status": "ignored"}


@app.get("/health")
async def health():
    return {"status": "ok", "queue_length": queue.llen("idp_tasks")}


if __name__ == "__main__":
    # 0.0.0.0 is correct here: this process runs behind a container/K8s
    # Service boundary that owns the actual network exposure decision, not
    # a developer's own machine. Override via IDP_GATEWAY_HOST for local dev.
    uvicorn.run(
        app,
        host=os.getenv("IDP_GATEWAY_HOST", "0.0.0.0"),  # noqa: S104
        port=int(os.getenv("IDP_GATEWAY_PORT", "8000")),
    )
