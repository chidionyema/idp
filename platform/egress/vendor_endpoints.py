"""The vendor hostname control plane: which endpoints an agent may reach, and through what.

THE PRINCIPLE (founder, 2026-09-20, verbatim mode): an agent's traffic is GUILTY UNTIL PROVEN
INNOCENT. The default is DENY. Identification is by IDENTITY -- the agent, the user it acts for, the
workload -- never by IP address, which is fragile and changes with every CDN edge.

WHY THIS FILE EXISTS AT ALL, measured on this machine 2026-09-20:

    dig llm.mumchimp.com    -> 193.123.184.22        the estate's own edge, correct
    dig api.deepseek.com    -> d3bbv8sr76az5s.cloudfront.net / 3.173.21.63
    dig api.anthropic.com   -> 160.79.104.10
    dig api.openai.com      -> 162.159.140.245 / 172.66.0.243
    dig api.minimax.io      -> api.minimax.io.edgesuite.net / 32.dscb.akamai.net / 62.252.115.32

Every vendor name resolved STRAIGHT TO THE VENDOR. And a session reached them without any of that
being a decision: `~/.pi/agent/models-store.json` carried `"baseUrl": "https://api.deepseek.com"`
and `"https://api.minimax.io/anthropic"` -- vendor endpoints chosen in a local file the agent owns
and can rewrite.

So the estate's cages held by ACCIDENT OF CONFIGURATION, not by architecture. The router ceiling,
the execution decree, the spend breaker and the ledger are all behind a base URL that one edited
line redirects. That is "a control that shares an identity with what it controls", surviving every
one of the seven previous fixes because every previous fix was a guard INSIDE the thing it guards.

WHY DNS IS THE LAYER THAT DOES NOT NAME A TOOL. Every process -- pi, Claude Code, Codex, a Rust
binary, a LangGraph node, a cron job, a harness nobody has written yet -- resolves a hostname
through the resolver. A tool does not choose where a name goes; the resolver does. So policy set
here holds for every caller that will ever exist, and no local file can override it. That is the
portability the founder asked for (work anywhere, local or cloud) and the independence from third
party tools (nothing here is expressed in a vendor's vocabulary).

WHAT THIS MODULE IS. The DATA half: the single list of vendor endpoints and the one destination
each is allowed to resolve to. `bin/idp-egress-plane` reads it to generate the Cloudflare records
that implement it, and to grade the live zone against it. The list is data so that adding a vendor
is a line here, never a new code path -- the same rule that makes a model addition configuration
rather than code (platform philosophy 0.1).

THE THREE STATES A HOSTNAME MAY BE IN, and each is deliberate:

  intercept   resolve to the estate's edge, which forwards through the router. The caller reaches
              the model; the estate sees, authorises, logs and counts the call. This is the answer
              for every vendor the estate legitimately uses.
  sinkhole    resolve to a non-routable address, so the connection fails fast and visibly. For
              vendors nobody has approved: an agent that reaches for one gets a refusal, not a
              silent success and not a hang.
  (absent)    no record generated. NOT the same as sinkhole, and the difference is the whole
              fail-closed rule below.

FAIL-CLOSED, AND SAYING WHICH WAY. A vendor in a client's config that is not in this list is a
FINDING, not a pass -- the estate's own model-serving config is graded against this file, so a new
base URL cannot appear silently. That is the control that would have caught the models-store.json
defect on the day it appeared.

WHAT THIS DOES NOT DO, stated because a control that overstates its scope cannot be trusted on the
cases it does cover:
  * It is a DNS control plane. A caller that connects to a HARDCODED IP bypasses it entirely --
    `curl --resolve` or a bare address reaches the vendor whatever the zone says. Closing that is
    the OS egress layer (pf / Network Extension), which needs root and is a separate piece.
  * A record change propagates at TTL, so it is not instant revocation for a live session. Closing
    that is the in-line gateway's job, which can invalidate a token on the next request.
  * It governs names, not identities. Which AGENT may reach which model is the gateway's policy,
    keyed on the router virtual key (LAW 34). This file decides where a name points; it does not
    decide who may ask.

Those three carve-outs are the three layers of the architecture, named as layers rather than
implied as done. This file is layer one.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The estate's own edge, which the intercepted names point at. Derived from the same value the
# cluster uses (ESTATE_ZONE) rather than typed, so a zone migration is one change (LAW 46).
ESTATE_ZONE = "mumchimp.com"
EDGE_HOST = f"llm.{ESTATE_ZONE}"

# A sinkhole address. RFC 5737 TEST-NET-1: reserved for documentation, never routable, so a
# connection to it fails immediately and obviously instead of hanging the session for its ceiling.
SINKHOLE = "192.0.2.1"

# ---------------------------------------------------------------------------------------------------
# THE LIST. One row per vendor hostname. `via` is the estate endpoint each resolves to.
#
# `intercept` means: this name points at the estate edge, so the call crosses the router where the
# ceiling, the decree, the ledger and the spend breaker all apply. Every model vendor the estate
# actually uses appears here, because a vendor that is used but not listed is exactly the bypass.
# ---------------------------------------------------------------------------------------------------
VENDORS: dict[str, dict[str, str]] = {
    # --- the vendors whose endpoints were found in client config, measured 2026-09-20 ---
    "api.deepseek.com": {
        "state": "intercept",
        "note": "found in ~/.pi/agent/models-store.json as a base URL; reached the vendor directly",
    },
    "api.minimax.io": {
        "state": "intercept",
        "note": "found in ~/.pi/agent/models-store.json; Anthropic-shaped path /anthropic",
    },
    "api.anthropic.com": {
        "state": "intercept",
        "note": "the harness default when no base URL is set; the largest silent bypass",
    },
    "api.openai.com": {
        "state": "intercept",
        "note": "harness default for the OpenAI-shaped lanes",
    },
    "openrouter.ai": {"state": "intercept", "note": "aggregator; one name reaches many vendors"},
    "api.groq.com": {"state": "intercept", "note": "pool deployment (config.yaml consoles)"},
    "api.cerebras.ai": {"state": "intercept", "note": "mounted as human-cerebras"},
    "api.nvidia.com": {"state": "intercept", "note": "mounted as human-nvidia"},
    "api.sambanova.ai": {"state": "intercept", "note": "mounted as human-sambanova"},
    "api.cohere.com": {"state": "intercept", "note": "embed chain"},
    "generativelanguage.googleapis.com": {"state": "intercept", "note": "mounted as human-gemini"},
    "api.moonshot.cn": {"state": "intercept", "note": "mounted as human-kimi"},
    "api-inference.huggingface.co": {"state": "intercept", "note": "model artifacts"},
    "api.kaggle.com": {"state": "intercept", "note": "forge training lane"},
    "router.huggingface.co": {"state": "intercept", "note": "HF routed inference"},
    # --- sinkholed: aggregators and unapproved endpoints nobody has reason to use ---
    "api.perplexity.ai": {
        "state": "sinkhole",
        "note": "no estate lane uses this; agent research going here is the defect, not the feature",
    },
    "api.together.xyz": {"state": "sinkhole", "note": "unapproved; one-off vendor keys are refused (LAW 34)"},
    "api.fireworks.ai": {"state": "sinkhole", "note": "unapproved"},
    "api.mistral.ai": {"state": "sinkhole", "note": "unapproved; reaches the estate through the router if ever approved"},
    "api.x.ai": {"state": "sinkhole", "note": "unapproved"},
    "api.cohere.ai": {"state": "sinkhole", "note": "the singular typo-shape of api.cohere.com; a hostname that only a mistake reaches"},
}

# What every intercepted name resolves to. One value, so a migration is one edit.
INTERCEPT_TARGET = EDGE_HOST
SINKHOLE_TARGET = SINKHOLE


def records() -> list[dict[str, str]]:
    """The DNS records this list asks for, oldest shape: name, type, content, comment.

    Generated, never hand-written -- editing a zone by hand is how a name drifts from the policy
    that claims to govern it, and the generator is byte-identical when this file is unchanged.
    """
    out: list[dict[str, str]] = []
    for host, spec in sorted(VENDORS.items()):
        target = INTERCEPT_TARGET if spec["state"] == "intercept" else SINKHOLE_TARGET
        out.append(
            {
                "name": host,
                "type": "CNAME" if spec["state"] == "intercept" else "A",
                "content": target,
                "comment": f"idp-egress-plane {spec['state']}: {spec['note']}",
            }
        )
    return out


def is_intercepted(host: str) -> bool:
    spec = VENDORS.get(host)
    return bool(spec and spec["state"] == "intercept")


if __name__ == "__main__":
    print(json.dumps({"zone": ESTATE_ZONE, "edge": EDGE_HOST, "records": records()}, indent=2))
