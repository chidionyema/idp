#!/usr/bin/env python3
"""Configure the Linear workspace so it is a board, not a dump (crew#: founder 2026-09-06).

Founder, 2026-09-06, verbatim: "also i notice we dont have projecsts inl liner,, issues
arent linked, etc, need oriper setuo to endsure we are gettin gbest use of linear, epert
seto and rseach".

What it found: 210 issues, every one of them in Todo, none in a project, none linked to the
GitHub issue it was migrated from, 171 with no priority, cycles off and triage off. That is a
CSV with a nicer font.

What it sets, and why each one is the documented Linear practice rather than taste:

  Triage on          An issue filed by an integration or a non-member lands in a review
                     inbox instead of the backlog (Linear docs, "Triage"). Every bot alert
                     that made this board 484 issues long would have landed there.
  Cycles on, 2 weeks Linear's own guidance: two weeks is the common cadence, short enough to
                     keep other priorities in view, long enough to finish something.
  Auto-archive 1mo   The free plan counts *active* issues against 250, and Done and Canceled
                     both count. Archiving is what keeps the estate off a paid plan, so it
                     happens on a timer rather than when someone remembers.
  Auto-close 3mo     An issue nobody has touched in three months is not a plan.
  Initiatives        Three, matching how the estate is actually sold and run: the platform a
                     buyer inspects, the estate that keeps running, the products on top.
  Projects           Ten, one per theme the September board review found, each under one
                     initiative, so "what is this issue for" has an answer.
  GitHub links       attachmentLinkGitHubIssue against the migration map, so a Linear issue
                     opens the GitHub issue it came from. This needs no OAuth integration.
  Priority           P0/P1 were GitHub labels carried across. Linear has a priority field
                     that sorts and filters; the labels do not.

Idempotent: every object is looked up by name before it is created, and an attachment is
skipped when its URL is already on the issue. Run it twice, nothing changes the second time.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request

API = "https://api.linear.app/graphql"
TEAM_KEY = "MUM"


def token() -> str:
    """The API key, from the environment or the file the estate keeps it in.

    LAW 46: no path to a home directory or a machine is written here.
    """
    tok = os.environ.get("LINEAR_API_KEY")
    if tok:
        return tok.strip()
    path = os.environ.get("LINEAR_API_KEY_FILE")
    if path and os.path.exists(path):
        return open(path).read().strip()
    sys.exit("set LINEAR_API_KEY or LINEAR_API_KEY_FILE")


TOK = token()


def gql(query: str, variables: dict | None = None) -> dict:
    # The scheme is asserted rather than assumed: S310 exists because a urlopen whose URL can
    # come from outside will happily open file:// and read a local secret back to the caller.
    # API is a constant in this file, so the check costs nothing and earns the suppression.
    if not API.startswith("https://"):
        raise ValueError(f"refusing a non-https API endpoint: {API}")
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(  # noqa: S310 - scheme asserted above
        API,
        data=body,
        headers={"Authorization": TOK, "Content-Type": "application/json"},
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 - as above
                out = json.loads(r.read())
            if "errors" in out and out.get("data") is None:
                raise RuntimeError(out["errors"][0].get("message", "unknown"))
            return out.get("data") or {}
        except Exception as exc:  # noqa: BLE001 - retried, then raised
            if attempt == 4:
                raise
            time.sleep(2 * (attempt + 1))
            _ = exc
    return {}


# --- the taxonomy -----------------------------------------------------------------
#
# Initiative -> projects. The ten projects are the ten themes the board review of
# 2026-09-06 found by reading every open title; the counts there are what set the list.

INITIATIVES = {
    "Sell the platform": {
        "color": "#1F6F78",
        "description": "What a buyer's engineer opens on the day of diligence.",
        "projects": [
            "Portal and catalogue",
            "Identity and secrets",
            "Continuity and portability",
        ],
    },
    "Run the estate": {
        "color": "#5E6AD2",
        "description": "The layers underneath every product: one of each, and they stay up.",
        "projects": [
            "Agent runtime",
            "Release path",
            "Observability",
            "Crew discipline",
        ],
    },
    "Ship the products": {
        "color": "#2E7052",
        "description": "Prospector, Otto and the research that feeds them.",
        "projects": ["Prospector and commerce", "Otto", "Science and research"],
    },
}

PROJECT_BLURB = {
    "Portal and catalogue": "Backstage, the catalogue, every founder-facing page and the links on it.",
    "Identity and secrets": "One identity layer at the gateway, one secret store, no password held for a person.",
    "Continuity and portability": "Backup, restore, exit: the estate survives losing any one provider.",
    "Agent runtime": "The crew itself — sessions, routing, Cyrus, the harness the agents run inside.",
    "Release path": "Flux, GitOps, image automation and CI: a commit reaching the cluster unattended.",
    "Observability": "Traces, logs, metrics and the data map, in one collector.",
    "Crew discipline": "Laws, guards, gates and the definition of done — the rules the crew works by.",
    "Prospector and commerce": "The product being sold and the money path under it.",
    "Otto": "The voice door and the hands behind it.",
    "Science and research": "Experiments, the warehouse, and what the estate learns from its own runs.",
}

# An issue is placed by the first rule that matches: its own lane label, then its title.
# Order matters — the specific products are tested before the general platform words.
LANE_TO_PROJECT = {
    "lane:platform": "Portal and catalogue",
    "lane:security": "Identity and secrets",
    "lane:dr": "Continuity and portability",
    "lane:agents": "Agent runtime",
    "lane:observability": "Observability",
    "lane:process": "Crew discipline",
    "lane:money": "Prospector and commerce",
    "lane:science": "Science and research",
}

KEYWORDS = [
    ("Otto", r"\botto\b|voice|wake ?word|\bstt\b|\btts\b|speech|whisper"),
    # A law or rule number is the surest sign an issue is about how the crew works rather
    # than about anything the estate does. It is tested before every other word for that
    # reason: "Fast lane: patch the cluster directly (R55)" is discipline, not release.
    (
        "Crew discipline",
        r"\bR\d{1,3}\b|\bLAW ?\d+|kill ?switch|wip limit|hazard|showcase|register\b|fast lane|one push wave",
    ),
    (
        "Prospector and commerce",
        r"prospector|storefront|commerce|lago|billing|checkout|stripe|invoice|pricing|revenue|customer|paywall|subscription|\bstore\b|buyer|price|capabilit(y|ies) catalog",
    ),
    (
        "Science and research",
        r"\bscience\b|research|\bml\b|machine learning|warehouse|experiment|hypothesis|dataset|benchmark|eval\b|hindsight",
    ),
    (
        "Identity and secrets",
        r"secret|credential|vault|\boidc\b|\bsso\b|identity|auth|token|password|\brbac\b|keycloak|certificate|\btls\b|rotate|kyverno|policy|security|\bcve\b|vulnerab|api key|break.?glass|private repo|own runners",
    ),
    (
        "Continuity and portability",
        r"backup|restore|disaster|\bdr\b|continuity|portab|exit plan|failover|snapshot|recover|tailscale|remote desk|off the laptop|migration.?risk|fragile|house of cards|reachable from",
    ),
    (
        "Observability",
        r"observab|telemetry|trace|langfuse|signoz|prometheus|grafana|alertmanager|metric|log|datamap|data map|dashboard|monitor|\botel\b|collector|circuit breaker|self.?heal|k8sgpt|kube ?gpt|email flood|instrument|alert channel|slack|telegram",
    ),
    (
        "Release path",
        r"\bflux\b|gitops|kustomization|helmrelease|image ?automation|\bci\b|workflow|pipeline|deploy|release|reconcil|pull request|\bpr\b gate|merge|downshift|runner|messaging|\bnats\b|jetstream|outbox|github projects",
    ),
    (
        "Portal and catalogue",
        r"backstage|catalog|portal|\bui\b|page|surface|frontend|link|styl|design|navigation|docs site|techdocs|demo\b|visual demo",
    ),
    (
        "Agent runtime",
        r"\bagent|crew|session|cyrus|harness|router|llm|model|claude|codex|gemini|opencode|cursor|prompt|token budget|orchestrat|dagster|temporal|worker|provider agnostic|model stack|event bus",
    ),
    (
        "Crew discipline",
        r"\blaw\b|\blaws\b|guard|gate|process|protocol|definition of done|\bdod\b|board|checkpoint|standard|rule|discipline|audit|receipt|convention|governance",
    ),
]


def classify(title: str, labels: list[str]) -> str | None:
    for lab in labels:
        if lab in LANE_TO_PROJECT:
            return LANE_TO_PROJECT[lab]
    low = title.lower()
    for project, pattern in KEYWORDS:
        if re.search(pattern, low):
            return project
    return None


# --- steps ------------------------------------------------------------------------


def team_settings(team_id: str) -> None:
    """Triage, cycles, estimates and the two timers that keep the board under the cap."""
    gql(
        """mutation($id:String!, $in:TeamUpdateInput!) {
             teamUpdate(id:$id, input:$in) { success }
           }""",
        {
            "id": team_id,
            "in": {
                "triageEnabled": True,
                "requirePriorityToLeaveTriage": True,
                "cyclesEnabled": True,
                "cycleDuration": 2,
                "cycleStartDay": 1,
                "cycleCooldownTime": 0,
                "cycleIssueAutoAssignStarted": True,
                "cycleIssueAutoAssignCompleted": True,
                "cycleLockToActive": False,
                "issueEstimationType": "exponential",
                "issueEstimationAllowZero": True,
                "autoArchivePeriod": 1,
                "autoClosePeriod": 3,
            },
        },
    )
    print(
        "team: triage on, 2-week cycles, exponential estimates, archive 1mo, close 3mo"
    )


def ensure_initiatives() -> dict[str, str]:
    have = {
        n["name"]: n["id"]
        for n in gql("{ initiatives(first:50) { nodes { id name } } }")["initiatives"][
            "nodes"
        ]
    }
    for name, spec in INITIATIVES.items():
        if name in have:
            continue
        data = gql(
            """mutation($in:InitiativeCreateInput!) {
                 initiativeCreate(input:$in) { success initiative { id name } } }""",
            {
                "in": {
                    "name": name,
                    "description": spec["description"],
                    "color": spec["color"],
                }
            },
        )
        have[name] = data["initiativeCreate"]["initiative"]["id"]
        print(f"initiative created: {name}")
    return have


def ensure_projects(team_id: str, initiatives: dict[str, str]) -> dict[str, str]:
    have = {
        n["name"]: n["id"]
        for n in gql("{ projects(first:100) { nodes { id name } } }")["projects"][
            "nodes"
        ]
    }
    linked = {
        (n["initiative"]["id"], n["project"]["id"])
        for n in gql(
            """{ initiativeToProjects(first:200) {
               nodes { initiative { id } project { id } } } }"""
        )["initiativeToProjects"]["nodes"]
    }
    for init_name, spec in INITIATIVES.items():
        for pname in spec["projects"]:
            if pname not in have:
                data = gql(
                    """mutation($in:ProjectCreateInput!) {
                         projectCreate(input:$in) { success project { id name } } }""",
                    {
                        "in": {
                            "name": pname,
                            "description": PROJECT_BLURB[pname],
                            "teamIds": [team_id],
                            "color": spec["color"],
                        }
                    },
                )
                have[pname] = data["projectCreate"]["project"]["id"]
                print(f"project created: {pname}")
            pair = (initiatives[init_name], have[pname])
            if pair not in linked:
                gql(
                    """mutation($in:InitiativeToProjectCreateInput!) {
                         initiativeToProjectCreate(input:$in) { success } }""",
                    {
                        "in": {
                            "initiativeId": initiatives[init_name],
                            "projectId": have[pname],
                        }
                    },
                )
                print(f"  linked {pname} -> {init_name}")
    return have


# Four saved views, because a 206-issue board is only readable through a filter. Each one is
# a lever the founder or the crew actually pulls, not a slice for its own sake.
VIEWS = [
    (
        "Waiting on a priority",
        "Every issue nobody has graded. 171 of 206 on the day this was written, which is why "
        "the board reads as a pile: Linear sorts on the priority field and most rows have none.",
        {"priority": {"eq": 0}},
    ),
    (
        "Founder asks",
        "Everything he asked for directly. LAW 18: every founder request is a tracked item, so "
        "this view is the register.",
        {"labels": {"some": {"name": {"eq": "founder-request"}}}},
    ),
    (
        "Ready for an agent",
        "Scoped, unblocked, and labelled for a session to pick up. Cyrus routes on the engine "
        "labels; this is the queue it draws from.",
        {"labels": {"some": {"name": {"eq": "ready-for-agent"}}}},
    ),
    (
        "Not in a project",
        "An issue with no project has no answer to 'what is this for'. This view should stay "
        "empty; anything landing in it needs a project or does not belong on the board.",
        {"project": {"null": True}},
    ),
]


def ensure_views(team_id: str) -> None:
    have = {
        n["name"]
        for n in gql("{ customViews(first:50) { nodes { id name } } }")["customViews"][
            "nodes"
        ]
    }
    for name, blurb, flt in VIEWS:
        if name in have:
            continue
        gql(
            """mutation($in:CustomViewCreateInput!) {
                 customViewCreate(input:$in) { success customView { id name } } }""",
            {
                "in": {
                    "name": name,
                    "description": blurb,
                    "teamId": team_id,
                    "shared": True,
                    "filterData": flt,
                }
            },
        )
        print(f"view created: {name}")


def all_issues() -> list[dict]:
    out, cursor = [], None
    while True:
        data = gql(
            """query($c:String) {
                 issues(first:100, after:$c) {
                   pageInfo { hasNextPage endCursor }
                   nodes { id identifier title priority
                           project { id }
                           labels { nodes { id name } }
                           attachments { nodes { url } } } } }""",
            {"c": cursor},
        )["issues"]
        out += data["nodes"]
        if not data["pageInfo"]["hasNextPage"]:
            return out
        cursor = data["pageInfo"]["endCursor"]


def batch(mutations: list[str], size: int = 20) -> int:
    """Run aliased mutations in groups. Returns how many groups succeeded."""
    done = 0
    for i in range(0, len(mutations), size):
        chunk = mutations[i : i + size]
        body = (
            "mutation {\n"
            + "\n".join(f"m{i + j}: {m}" for j, m in enumerate(chunk))
            + "\n}"
        )
        try:
            gql(body)
            done += len(chunk)
        except Exception as exc:  # noqa: BLE001 - one bad id must not stop the pass
            print(f"  batch {i}: {exc}")
        time.sleep(0.3)
    return done


def place_and_prioritise(issues: list[dict], projects: dict[str, str]) -> None:
    muts, placed = [], {}
    for iss in issues:
        labels = [n["name"] for n in iss["labels"]["nodes"]]
        fields = []
        target = classify(iss["title"], labels)
        if target and (iss["project"] or {}).get("id") != projects[target]:
            fields.append(f'projectId:"{projects[target]}"')
        if target:
            placed[target] = placed.get(target, 0) + 1
        # P0 and P1 came from GitHub. Linear sorts on the priority field, not on a label.
        if iss["priority"] == 0:
            if "P0" in labels or "red-alert" in labels or "urgent" in labels:
                fields.append("priority:1")
            elif "P1" in labels or "founder-request" in labels:
                fields.append("priority:2")
        if fields:
            muts.append(
                f'issueUpdate(id:"{iss["id"]}", input:{{{",".join(fields)}}}) {{ success }}'
            )
    n = batch(muts)
    print(f"issues updated: {n} of {len(muts)} queued")
    for k in sorted(placed, key=lambda x: -placed[x]):
        print(f"  {placed[k]:>4}  {k}")
    print(f"  {len(issues) - sum(placed.values()):>4}  no project (left for triage)")


def link_github(issues: list[dict], state_path: str) -> None:
    """Attach the GitHub issue each Linear issue was migrated from."""
    if not os.path.exists(state_path):
        print(f"github links skipped: no migration map at {state_path}")
        return
    state = json.load(open(state_path))["issues"]
    by_linear_id = {v["id"]: url for url, v in state.items()}
    muts = 0
    todo = []
    for iss in issues:
        url = by_linear_id.get(iss["id"])
        if not url:
            continue
        if any(a["url"] == url for a in iss["attachments"]["nodes"]):
            continue
        todo.append(
            f'attachmentLinkGitHubIssue(issueId:"{iss["id"]}", url:"{url}") {{ success }}'
        )
        muts += 1
    n = batch(todo, size=10)
    print(f"github links: {n} of {muts} attached")


def main() -> None:
    team = gql(
        "query($k:String!){ teams(filter:{key:{eq:$k}}) { nodes { id key name } } }",
        {"k": TEAM_KEY},
    )["teams"]["nodes"][0]
    print(f"team {team['key']} {team['id']}")
    team_settings(team["id"])
    initiatives = ensure_initiatives()
    projects = ensure_projects(team["id"], initiatives)
    ensure_views(team["id"])
    issues = all_issues()
    print(f"active issues: {len(issues)}")
    place_and_prioritise(issues, projects)
    link_github(issues, os.environ.get("LINEAR_MIGRATION_STATE", "migrate-state.json"))


if __name__ == "__main__":
    main()
