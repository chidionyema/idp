"""Bounded, typed I/O adapters; Temporal owns workflow decisions.

The existing GitHub recovery job owns OCI, vault, bundle and tunnel operations.
Only candidate restoration is supported; no untested production cutover.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

from temporalio import activity

from sovereign.automation.contracts import sha256

REPOSITORY = "chidionyema/idp"
CANDIDATE = "https://llm-recovery.mumchimp.com"
GH_API = "https://api.github.com/repos/chidionyema/idp"
GH_WORKFLOW = "router-recovery.yml"


class ExternalFailure(RuntimeError):
    pass


def _request(url: str, *, method: str = "GET", body: dict[str, Any] | None = None,
             token: str | None = None, timeout: int = 15) -> Any:
    # No arbitrary hosts (SSRF), including redirect targets.
    if not (url.startswith(GH_API + "/") or url.startswith(CANDIDATE + "/")):
        raise ValueError("endpoint not allowed by automation policy")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "estate-automation-v1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body, sort_keys=True).encode()
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)  # noqa: S310 -- both allowed origins are pinned to HTTPS above

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ExternalFailure("provider redirect refused")

    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()), NoRedirect()
    )
    with opener.open(req, timeout=timeout) as response:
        payload = response.read(1_048_577)
        if len(payload) > 1_048_576:
            raise ExternalFailure("provider response exceeded limit")
        if response.status == 204:
            return None
        try:
            return json.loads(payload)
        except (ValueError, UnicodeError):
            return {"text_digest": sha256(payload.decode("utf-8", "replace")),
                    "http_200": response.status == 200}


def _github_token() -> str:
    token = os.environ.get("ESTATE_AUTOMATION_GITHUB_TOKEN", "")
    if not token:
        raise ExternalFailure("BLIND: github credential not provisioned")
    return token


def _probe_key() -> str:
    token = os.environ.get("ESTATE_AUTOMATION_ROUTER_PROBE_KEY", "")
    if not token:
        raise ExternalFailure("BLIND: independent model-completion probe key absent")
    return token


def _runs(token: str) -> list[dict[str, Any]]:
    result = _request(
        f"{GH_API}/actions/workflows/{GH_WORKFLOW}/runs?event=workflow_dispatch&per_page=100",
        token=token,
    )
    return result.get("workflow_runs", [])


def _candidate_run(runs: list[dict[str, Any]], marker: str) -> dict[str, Any] | None:
    matching = [r for r in runs if r.get("head_branch") == f"auto-run-{marker}"]
    if len(matching) > 1:
        raise ExternalFailure("duplicate delivery: multiple GitHub runs for one automation")
    return matching[0] if matching else None


def router_dispatch(inp: dict[str, Any]) -> dict[str, Any]:
    """One POST at most; ambiguous deliveries require reconciliation, not retries."""
    token = _github_token()
    marker = sha256({"workflow_id": inp["workflow_id"], "plan_hash": inp["plan_hash"]})[:32]
    found = _candidate_run(_runs(token), marker)
    if found:
        return {"marker": marker, "github_run_id": found["id"], "recovered": True}
    # A dedicated pinned run branch gives the legacy workflow exact correlation.
    # An orphaned ref after a failed POST is ambiguous; never dispatch twice.
    branch = "auto-run-" + marker
    try:
        ref = _request(f"{GH_API}/git/ref/heads/{branch}", token=token)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        ref = None
    if ref:
        if ref.get("object", {}).get("sha") != inp["source_sha"]:
            raise ExternalFailure("existing run branch has wrong source SHA")
        raise ExternalFailure("AMBIGUOUS_DISPATCH: existing run ref needs reconciliation " + branch)
    _request(f"{GH_API}/git/refs", method="POST",
             body={"ref": "refs/heads/" + branch, "sha": inp["source_sha"]}, token=token)
    payload = {"ref": branch, "inputs": {"cutover": "false"}}
    try:
        _request(f"{GH_API}/actions/workflows/{GH_WORKFLOW}/dispatches",
                 method="POST", body=payload, token=token)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ExternalFailure("AMBIGUOUS_DISPATCH: reconcile marker " + marker) from exc
    return {"marker": marker, "submitted": True}


def router_observe(inp: dict[str, Any]) -> dict[str, Any]:
    token = _github_token()
    marker = inp["dependencies"]["dispatch"]["marker"]
    deadline = time.monotonic() + 540
    while time.monotonic() < deadline:
        activity.heartbeat({"marker": marker, "stage": "observing"})
        found = _candidate_run(_runs(token), marker)
        if found and found.get("status") == "completed":
            if found.get("conclusion") != "success":
                raise ExternalFailure("recovery workflow did not succeed: " + str(found.get("conclusion")))
            if found.get("head_sha") != inp["source_sha"]:
                raise ExternalFailure("observed execution SHA does not equal plan source SHA")
            return {"github_run_id": found["id"], "head_sha": found["head_sha"],
                    "conclusion": "success"}
        time.sleep(12)
    raise ExternalFailure("candidate workflow did not finish inside observation budget")


def router_health(inp: dict[str, Any]) -> dict[str, Any]:
    response = _request(CANDIDATE + "/health/liveliness", timeout=10)
    return {"http_200": True, "probe": "candidate-liveliness", "body_digest": sha256(response)}


def router_models(inp: dict[str, Any]) -> dict[str, Any]:
    response = _request(CANDIDATE + "/v1/models", token=_probe_key(), timeout=15)
    models = sorted(m["id"] for m in response.get("data", [])
                    if isinstance(m, dict) and isinstance(m.get("id"), str))
    if not models:
        raise ExternalFailure("candidate lists zero models")
    return {"models_count": len(models), "model": models[0], "models_digest": sha256(models)}


def router_completion(inp: dict[str, Any]) -> dict[str, Any]:
    model = inp["dependencies"]["models"]["model"]
    response = _request(CANDIDATE + "/v1/chat/completions", method="POST", token=_probe_key(),
                        body={"model": model, "max_tokens": 8,
                              "messages": [{"role": "user", "content": "Reply OK"}]}, timeout=45)
    choices = response.get("choices") or []
    content = (choices[0].get("message") or {}).get("content") if choices else None
    if not isinstance(content, str) or not content.strip():
        raise ExternalFailure("model returned no generated content")
    return {"generated": True, "requested_model": model,
            "reported_model": response.get("model"), "response_digest": sha256(content)}


_ACTIONS = {
    "github.router_dispatch": router_dispatch,
    "github.router_observe": router_observe,
    "router.health": router_health,
    "router.models": router_models,
    "router.completion": router_completion,
}


@activity.defn(name="automation_activity")
async def automation_activity(inp: dict[str, Any]) -> dict[str, Any]:
    actual_release = {k: os.environ.get("ESTATE_AUTOMATION_" + k.upper(), "")
                      for k in ("source_sha", "artifact_digest", "config_digest")}
    if inp.get("release") != actual_release:
        raise ExternalFailure("BLIND: worker release identity mismatch")
    action = inp["action"]
    if action not in _ACTIONS:
        raise ValueError("unsupported automation action")
    if inp["inputs"] != {"repository": REPOSITORY, "candidate_url": CANDIDATE}:
        raise ValueError("unapproved adapter inputs")
    if not re.fullmatch(r"[a-f0-9]{40}", inp["source_sha"]):
        raise ExternalFailure("BLIND: workflow source SHA invalid")
    return await asyncio.to_thread(_ACTIONS[action], inp)
