"""The idp side of the research engine: which objective it researches, and the report it posts.

The engine knows nothing about objectives (research-engine SPEC-v1 §2); a consumer's adapter
lives in the consumer's repository (§8). This is that adapter. It runs inside the engine's pod,
before and after `python -m engine.cli run`, mounted from a ConfigMap like the subjects file was.

  pick                 print the issue number and research subject of the objective to research
                       now, or nothing when none is waiting. Highest rank (pain per USD) first.
  report N RUN_LOG     post the run's admitted claims on objective issue N, ending with the
                       two choices the founder makes in the report itself.

Founder, 2026-10-19, on how often an objective is re-researched: "in the report provided, option
to continue researching or park research". So an objective is researched once; its report ends
with two task-list boxes, Continue and Park. The next pass happens only when Continue is ticked,
Park stops it, and an unticked report waits. A pass also stops once the passes already reported
have spent the objective's USD cap, ticked or not.

GitHub is reached as the estate's App (vault entry `github-app`, the same entry nine other
namespaces read), with an installation token minted here and never written to disk.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
import urllib.request

API = "https://api.github.com"
OWNER = os.environ.get("ESTATE_GITHUB_OWNER", "chidionyema")
REPO = os.environ.get("OBJECTIVE_REPO", f"{OWNER}/idp")
APP_DIR = os.environ.get("GITHUB_APP_DIR", "/secrets/github-app")
LABEL = "objective"
REPORT = re.compile(r"<!-- research-report request=(\S+) cost=([0-9.]+) -->")
CONTINUE = re.compile(r"^- \[[xX]\] Continue researching", re.M)
PARK = re.compile(r"^- \[[xX]\] Park this research", re.M)


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def app_jwt(app_id: str, pem: bytes, now: int | None = None) -> str:
    """RS256 JWT for the App, signed with `cryptography` (already in the engine image)."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    now = int(now if now is not None else time.time())
    head = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    body = _b64url(
        json.dumps({"iat": now - 60, "exp": now + 540, "iss": app_id}).encode()
    )
    key = serialization.load_pem_private_key(pem, password=None)
    sig = key.sign(f"{head}.{body}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{head}.{body}.{_b64url(sig)}"


def _read(name: str) -> bytes:
    with open(os.path.join(APP_DIR, name), "rb") as f:
        return f.read().strip()


def _call(
    method: str, path: str, token: str, scheme: str = "token", data: dict | None = None
):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers={
            "Authorization": f"{scheme} {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "research-engine-adapter",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def installation_token() -> str:
    jwt = app_jwt(_read("app_id").decode(), _read("private_key"))
    inst = _read("installation_id").decode()
    return _call(
        "POST", f"/app/installations/{inst}/access_tokens", jwt, scheme="Bearer"
    )["token"]


def rank(body: str) -> float:
    m = re.search(r"rank ([0-9.]+) min per USD", body or "")
    return float(m.group(1)) if m else 0.0


def cap_usd(body: str) -> float:
    m = re.search(r"\*\*cap:\*\* \$([0-9.]+)", body or "")
    return float(m.group(1)) if m else 0.0


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
    cap = cap_usd(issue.get("body") or "")
    return ("cap" if cap and spent >= cap else "continue"), spent


def choose(candidates: list[tuple[dict, list[dict]]]) -> dict | None:
    """The highest-ranked objective whose state lets it run now."""
    ready = [i for i, cs in candidates if decision(i, cs)[0] in ("new", "continue")]
    return max(
        ready,
        key=lambda i: (rank(i.get("body") or ""), -int(i["number"])),
        default=None,
    )


def pick(token: str) -> dict | None:
    issues = _call(
        "GET", f"/repos/{REPO}/issues?labels={LABEL}&state=open&per_page=100", token
    )
    issues = [i for i in issues if "pull_request" not in i]
    return choose(
        [
            (
                i,
                _call(
                    "GET",
                    f"/repos/{REPO}/issues/{i['number']}/comments?per_page=100",
                    token,
                ),
            )
            for i in issues
        ]
    )


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


def report(token: str, number: int, run: dict, dsn: str) -> str:
    issue = _call("GET", f"/repos/{REPO}/issues/{number}", token)
    comments = _call(
        "GET", f"/repos/{REPO}/issues/{number}/comments?per_page=100", token
    )
    _, spent = decision(issue, comments)
    admitted, rejected = claims_for(dsn, run["request_id"])
    body = report_body(run, admitted, rejected, spent, cap_usd(issue.get("body") or ""))
    return _call(
        "POST", f"/repos/{REPO}/issues/{number}/comments", token, data={"body": body}
    )["html_url"]


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
            print(chosen["number"])
            print(subject(chosen))
        return 0
    if len(argv) == 3 and argv[0] == "report":
        with open(argv[2], encoding="utf-8") as f:
            run = load_run(f.read())
        print(
            report(
                installation_token(), int(argv[1]), run, os.environ["RESEARCH_PG_DSN"]
            )
        )
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
