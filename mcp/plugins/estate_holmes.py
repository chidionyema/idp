"""Datasette plugin: the `ask_holmes` MCP tool -- the estate's investigator, on tap.

WHY THIS FILE EXISTS. HolmesGPT has run in this cluster since 2026-09-05 with its own
router key, and until now the only thing that could ask it anything was a person with a
terminal. A Dagster sensor now investigates on its own when an alert fires, but the
founder's answer to that was "no i would need to be able to ask it fron telegrn and
backstage also" -- an autonomous investigator that cannot be asked a question is half a
capability. This is the asking half, written once, so that every front door calls the same
implementation rather than each growing its own.

The one door, not a second one (ADR 0006). A question about the estate is one
`mcp__estate__*` call, and this is one more file the existing estate MCP server loads from
`--plugins-dir` through datasette-mcp's `register_mcp_tools(datasette, mcp)`, exactly like
estate_inventory.py, estate_state.py, workload_state.py and workload_logs.py. No new
server, no new deployment, no new port. Anything that already speaks to this MCP server --
an agent session, Otto, the agentgateway route at /estate/mcp -- gains the tool the moment
this lands, with no change of its own.

WHAT HOLMES CAN ACTUALLY SEE, so a caller does not expect more. Its toolsets are declared
in platform/robusta/robusta.yaml: Kubernetes objects, pod logs, Prometheus metrics, the
Robusta findings and a connectivity check. `bash` and `internet` are both false there, on
purpose -- an AI tool inside this cluster gets no shell and no arbitrary fetch. So Holmes
answers questions about what is happening in the cluster and why, and cannot look anything
up on the web or run a command for you.

Cost is a real constraint here and the reason this tool is deliberately dull: Holmes thinks
with the estate router, whose ceiling is $3 a day (AGENTS.md [budget.usd_per_day]). One
call, no retry loop, no fan-out over namespaces -- a caller that wants three questions
answered asks three times and can see itself doing it.

No subprocess and no shell: one HTTP POST and a clock.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request

# See mcp/plugins/estate_inventory.py for why this import is guarded: the offline CI venv
# that runs the tests has no datasette installed.
try:
    from datasette import hookimpl
except ImportError:  # pragma: no cover - exercised only in the datasette-less CI venv

    def hookimpl(fn):
        return fn


def config() -> dict:
    return {
        # The in-cluster Service in front of HolmesGPT (port 80 -> container 5050,
        # selector app: holmes). Never a host typed at a call site.
        "url": os.environ.get(
            "ESTATE_HOLMES_URL", "http://robusta-holmes.robusta.svc.cluster.local"
        ).strip(),
        # An investigation reads objects, pulls logs and queries Prometheus before it
        # answers; a minute is normal and three is not alarming. Well under the ceiling a
        # caller would otherwise hit, and far above the 5s the memory tool uses, because
        # this is a model call and that is a database read.
        "timeout_s": float(os.environ.get("ESTATE_HOLMES_TIMEOUT_S", "180")),
        # The same ceiling estate_inventory.py applies, and for the same reason: a tool
        # result goes into somebody's context window, and an unbounded one evicts the
        # conversation that asked for it.
        "byte_ceiling": int(os.environ.get("ESTATE_HOLMES_BYTE_CEILING", "8000")),
    }


CUT_NOTE = "\n\n[cut here: the answer was longer than this tool's byte ceiling]"


def fit_under_ceiling(text: str, ceiling: int) -> str:
    """The answer, trimmed to fit, saying so when it did not.

    Silence about a truncation is the defect: a reader who cannot see that the last
    paragraph was removed will act on a conclusion that was never delivered.
    """
    if len(text.encode("utf-8")) <= ceiling:
        return text
    room = max(ceiling - len(CUT_NOTE.encode("utf-8")), 0)
    return text.encode("utf-8")[:room].decode("utf-8", "ignore") + CUT_NOTE


def ask(cfg: dict, question: str) -> "tuple[dict | None, str | None]":
    """One POST to Holmes' own chat API. Returns (body, error); never both, never raises.

    The URL comes from ESTATE_HOLMES_URL and is refused unless it is http(s), so the
    schemes urllib would otherwise honour (file:, ftp:) cannot be reached from config --
    the same guard estate_memory.py applies to its own configured endpoint.
    """
    base = cfg["url"].rstrip("/")
    if not base.startswith(("http://", "https://")):
        return None, "ESTATE_HOLMES_URL is not an http(s) URL"
    # noqa justified: the scheme is refused above, so file:/ftp: cannot reach either call
    request = urllib.request.Request(  # noqa: S310
        f"{base}/api/chat",
        data=json.dumps({"ask": question}).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(  # noqa: S310
            request, timeout=cfg["timeout_s"]
        ) as response:
            raw = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return None, f"HolmesGPT refused the question: HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"HolmesGPT unreachable: {type(exc).__name__}"
    try:
        body = json.loads(raw)
    except ValueError:
        return None, "HolmesGPT returned a body that is not JSON"
    if not isinstance(body, dict):
        return None, "HolmesGPT returned JSON that is not an object"
    return body, None


def build_answer(question: str, cfg: "dict | None" = None) -> dict:
    """The tool's whole response, degraded rather than raised on every failure."""
    cfg = cfg or config()
    asked_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    envelope = {
        "question": question,
        "asked_at": asked_at,
        "answered": False,
        "analysis": "",
        "tool_calls": 0,
        "error": None,
    }
    if not question.strip():
        envelope["error"] = "ask_holmes needs a question"
        return envelope

    body, error = ask(cfg, question.strip())
    if error:
        envelope["error"] = error
        return envelope

    analysis = str(body.get("analysis") or "").strip()
    if not analysis:
        # The failure that would otherwise be invisible: Robusta's own Telegram sink
        # posts a title with an empty body when it cannot render an investigation, and
        # that silence is what made this tool necessary. It is never repeated here.
        envelope["error"] = "HolmesGPT answered without an analysis"
        return envelope

    calls = body.get("tool_calls")
    envelope.update(
        answered=True,
        analysis=fit_under_ceiling(analysis, cfg["byte_ceiling"]),
        tool_calls=len(calls) if isinstance(calls, list) else 0,
    )
    return envelope


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def ask_holmes(question: str) -> dict:
        """Ask HolmesGPT, the estate's investigator, what is happening in the cluster
        and why. It reads Kubernetes objects, pod logs, Prometheus metrics and Robusta's
        findings for itself before answering, so ask it the real question ("why is the
        llm namespace unhealthy", "why did otto-gateway restart") rather than asking it
        to run a command -- it has no shell and no internet access, deliberately.

        Returns `analysis` (its answer, trimmed to ESTATE_HOLMES_BYTE_CEILING and saying
        so when trimmed), `tool_calls` (how many things it went and looked at) and
        `answered`. Degrades with an `error` field and never raises: an unreachable or
        silent investigator is reported as unknown, never as nothing being wrong.

        One call costs one investigation on the estate's router, which has a daily
        ceiling. Ask one good question rather than sweeping."""
        return build_answer(question)
