"""The idp side of the research engine: which objective it researches, and the report it posts.

The engine knows nothing about objectives (research-engine SPEC-v1 §2); a consumer's adapter
lives in the consumer's repository (§8). This is that adapter. It runs inside the engine's pod,
before and after `python -m engine.cli run`, mounted from a ConfigMap like the subjects file was.

  pick                 print the issue (owner/repo#N) and research subject of the objective to
                       research now, or nothing when none is waiting. Highest rank first; an
                       objective the founder wrote by hand outranks every mined one.
  report REF RUN_LOG   post the run's admitted claims on objective issue REF, ending with the
                       two choices the founder makes in the report itself.

Founder, 2026-10-19, on how often an objective is re-researched: "in the report provided, option
to continue researching or park research". So an objective is researched once; its report ends
with two task-list boxes, Continue and Park. The next pass happens only when Continue is ticked,
Park stops it, and an unticked report waits. A pass also stops once the passes already reported
have spent the objective's USD cap, ticked or not.

GitHub is reached as the estate's App: the installation token is minted in-cluster by the
GithubAccessToken generator (github-app.yaml) and mounted here as a file, refreshed every 10m.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
OWNER = os.environ.get("ESTATE_GITHUB_OWNER", "chidionyema")
REPO = os.environ.get("OBJECTIVE_REPO", f"{OWNER}/idp")
# Where objectives live. The miner files measured problems in idp; the founder states product
# objectives (mumchimp, prospector) in crew and prospector issues. Reading only idp meant the
# founder's own objectives were never researched. Repositories are listed, not discovered, so the
# engine spends money only where the estate named.
REPOS = [
    r.strip()
    for r in os.environ.get(
        "OBJECTIVE_REPOS", f"{REPO},{OWNER}/crew,{OWNER}/prospector"
    ).split(",")
    if r.strip()
]
TOKEN_FILE = os.environ.get("GITHUB_TOKEN_FILE", "/secrets/github-app/token")
LABEL = "objective"
# An objective the founder wrote by hand carries no miner text (no rank, no cap). It outranks every
# mined one (mined ranks are pain per USD) and gets the miner's default cap, so a hand-written
# objective can neither starve behind mined ones nor run unbounded.
FOUNDER_RANK = 1000.0
DEFAULT_CAP_USD = 5.0
REF = re.compile(r"^(?:([\w.-]+/[\w.-]+)#)?([0-9]+)$")
REPORT = re.compile(r"<!-- research-report request=(\S+) cost=([0-9.]+) -->")
CONTINUE = re.compile(r"^- \[[xX]\] Continue researching", re.M)
PARK = re.compile(r"^- \[[xX]\] Park this research", re.M)


def _call(method: str, path: str, token: str, data: dict | None = None):
    req = urllib.request.Request(  # noqa: S310 -- the URL is the fixed GitHub API base, never user input
        API + path,
        method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "research-engine-adapter",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 -- the URL is the fixed GitHub API base, never user input
        return json.load(r)


def installation_token() -> str:
    with open(TOKEN_FILE, encoding="utf-8") as f:
        return f.read().strip()


def rank(body: str) -> float:
    m = re.search(r"rank ([0-9.]+) min per USD", body or "")
    return float(m.group(1)) if m else FOUNDER_RANK


def cap_usd(body: str) -> float:
    m = re.search(r"\*\*cap:\*\* \$([0-9.]+)", body or "")
    cap = float(m.group(1)) if m else 0.0
    return cap if cap > 0 else DEFAULT_CAP_USD


def ref(issue: dict) -> str:
    """owner/repo#number: an issue number alone is ambiguous across repositories."""
    return f"{issue.get('_repo') or REPO}#{int(issue['number'])}"


def parse_ref(text: str) -> tuple[str, int]:
    m = REF.match((text or "").strip())
    if not m:
        raise ValueError(f"not an objective reference: {text!r}")
    repo = m.group(1) or REPO
    if repo not in REPOS:
        raise ValueError(f"{repo} is not one of the objective repositories {REPOS}")
    return repo, int(m.group(2))


def subject(issue: dict) -> str:
    m = re.search(r"\*\*Research subject:\*\* (.+)", issue.get("body") or "")
    if m:
        return m.group(1).strip()
    return re.sub(r"^objective:\s*", "", issue.get("title") or "").strip()


def decision(issue: dict, comments: list[dict]) -> tuple[str, float]:
    """(state, USD spent so far). state is `new`, `continue`, `park`, `waiting` or `cap`."""
    reports = [c for c in comments if REPORT.search(c.get("body") or "")]
    spent = sum(float(REPORT.search(c["body"]).group(2)) for c in reports)
    if not reports:
        return "new", spent
    last = reports[-1]["body"]
    if PARK.search(last):
        return "park", spent
    if not CONTINUE.search(last):
        return "waiting", spent
    return ("cap" if spent >= cap_usd(issue.get("body") or "") else "continue"), spent


def choose(candidates: list[tuple[dict, list[dict]]]) -> dict | None:
    """The highest-ranked objective whose state lets it run now."""
    ready = [i for i, cs in candidates if decision(i, cs)[0] in ("new", "continue")]
    return max(
        ready,
        key=lambda i: (rank(i.get("body") or ""), -int(i["number"]), ref(i)),
        default=None,
    )


def _paged(path: str, token: str) -> list[dict]:
    """Every page of a list endpoint: a short read of comments would lose a Park tick and respend."""
    sep = "&" if "?" in path else "?"
    out: list[dict] = []
    for page in range(1, 31):
        got = _call("GET", f"{path}{sep}per_page=100&page={page}", token)
        out += got
        if len(got) < 100:
            return out
    raise RuntimeError(f"{path} has more than 3000 entries")


def _call_retry(method: str, path: str, token: str, data: dict | None = None):
    """The report is written after the money is spent: a transient 5xx must not lose it."""
    for attempt in range(4):
        try:
            return _call(method, path, token, data)
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:
                raise
        except (urllib.error.URLError, TimeoutError):
            pass
        if attempt < 3:
            time.sleep(2**attempt)
    raise RuntimeError(f"{method} {path} failed after 4 attempts")


def candidates(token: str) -> list[tuple[dict, list[dict]]]:
    """(issue, comments) for every open objective in every objective repository.

    A repository that cannot be read (App not installed, 403, 404, rate limit) is named on stderr
    and skipped, so one bad repository does not blind the others. An issue whose comments cannot
    be read is skipped too: guessing it has no report would research it again and respend. When
    no repository could be read at all this raises, so the job goes red instead of reporting
    "no objective awaiting research".
    """
    out: list[tuple[dict, list[dict]]] = []
    readable = 0
    for repo in REPOS:
        try:
            issues = _paged(f"/repos/{repo}/issues?labels={LABEL}&state=open", token)
        except (urllib.error.URLError, RuntimeError, TimeoutError) as e:
            print(
                f"research-engine: cannot read objectives in {repo}: {e}",
                file=sys.stderr,
            )
            continue
        readable += 1
        for i in issues:
            if "pull_request" in i:
                continue
            i["_repo"] = repo
            try:
                comments = _paged(f"/repos/{repo}/issues/{i['number']}/comments", token)
            except (urllib.error.URLError, RuntimeError, TimeoutError) as e:
                print(
                    f"research-engine: skipping {ref(i)}, comments unreadable: {e}",
                    file=sys.stderr,
                )
                continue
            out.append((i, comments))
    if not readable:
        raise RuntimeError(f"no objective repository could be read: {REPOS}")
    return out


def pick(token: str) -> dict | None:
    return choose(candidates(token))


def claims_for(dsn: str, request_id: str) -> tuple[list[dict], dict[str, int]]:
    """Admitted claims for the request, with their question and first source; and rejection counts."""
    import psycopg

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT q.text, c.statement, c.confidence, c.sources, c.status, c.rejection_reason "
            "FROM claims c JOIN questions q ON q.id = c.question_id WHERE q.request_id = %s "
            "ORDER BY q.id, c.created_at",
            (request_id,),
        )
        rows = cur.fetchall()
    admitted, rejected = [], {}
    for qtext, stmt, conf, sources, status, reason in rows:
        if status == "admitted":
            src = sources if isinstance(sources, list) else json.loads(sources or "[]")
            admitted.append(
                {
                    "question": qtext,
                    "statement": stmt,
                    "confidence": conf,
                    "url": (src[0] or {}).get("url") if src else None,
                }
            )
        else:
            rejected[reason or "unknown"] = rejected.get(reason or "unknown", 0) + 1
    return admitted, rejected


def report_body(
    run: dict,
    admitted: list[dict],
    rejected: dict[str, int],
    spent_before: float,
    cap: float,
) -> str:
    delivery = run.get("delivery") or {}
    cost = float((run.get("worker") or {}).get("cost_usd") or 0.0)
    lines = [
        f"<!-- research-report request={run.get('request_id')} cost={cost:.4f} -->",
        f"### Research report: {len(admitted)} admitted claim(s)",
        f"Lane `objective`, request `{run.get('request_id')}`, status `{delivery.get('status')}`, "
        f"cost ${cost:.2f} (spent ${spent_before + cost:.2f} of the ${cap:g} cap).",
        "",
    ]
    if admitted:
        lines.append(
            "Each claim cites a snapshotted source and was checked by a model from a "
            "different provider than the one that wrote it.\n"
        )
        q = None
        for c in admitted:
            if c["question"] != q:
                q = c["question"]
                lines.append(f"**{q}**")
            src = f" ([source]({c['url']}))" if c.get("url") else ""
            lines.append(f"- {c['statement']} _{c['confidence']}_{src}")
        lines.append("")
    else:
        lines.append(
            "No claim survived citation and cross-provider verification on this pass.\n"
        )
    if rejected:
        lines.append(
            "Rejected: "
            + ", ".join(f"{n} {r}" for r, n in sorted(rejected.items()))
            + "."
        )
    if delivery.get("unanswered"):
        lines.append(f"Unanswered: {len(delivery['unanswered'])} question(s).")
    lines += [
        "",
        "**What next?** Tick one. The engine reads this on its next run; with neither "
        "ticked, it waits.",
        "- [ ] Continue researching",
        "- [ ] Park this research",
        "",
    ]
    return "\n".join(lines)


def report(token: str, target: str, run: dict, dsn: str) -> str:
    repo, number = parse_ref(target)
    issue = _call("GET", f"/repos/{repo}/issues/{number}", token)
    comments = _paged(f"/repos/{repo}/issues/{number}/comments", token)
    _, spent = decision(issue, comments)
    admitted, rejected = claims_for(dsn, run["request_id"])
    body = report_body(run, admitted, rejected, spent, cap_usd(issue.get("body") or ""))
    try:
        return _call_retry(
            "POST",
            f"/repos/{repo}/issues/{number}/comments",
            token,
            data={"body": body},
        )["html_url"]
    except Exception:
        # The research is paid for: keep the report in the job log if it cannot be posted.
        print(body, file=sys.stderr)
        raise


def load_run(text: str) -> dict:
    """The result `engine.cli run` prints last (indent=2), out of a log gpt-researcher also writes to."""
    starts = [m.start() for m in re.finditer(r"^\{$", text, re.M)]
    for s in reversed(starts):
        try:
            return json.loads(text[s:])
        except json.JSONDecodeError:
            continue
    raise ValueError("no run result in the engine's output")


def main(argv: list[str]) -> int:
    if argv[:1] == ["pick"]:
        chosen = pick(installation_token())
        if chosen:
            print(ref(chosen))
            print(subject(chosen))
        return 0
    if len(argv) == 3 and argv[0] == "report":
        with open(argv[2], encoding="utf-8") as f:
            run = load_run(f.read())
        print(report(installation_token(), argv[1], run, os.environ["RESEARCH_PG_DSN"]))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
