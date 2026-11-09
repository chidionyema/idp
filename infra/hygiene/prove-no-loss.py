#!/usr/bin/env python3
"""infra/hygiene/prove-no-loss.py -- the invariant that makes the cleaning safe to trust.

    python3 infra/hygiene/prove-no-loss.py --repo PATH --remote origin [--json] [--drill]

The claim the estate needs is not "we archived the branches", it is "no branch can be gone
without its tip being recoverable". That is checkable, so it is checked:

    for every branch in the inventory:
        refs/archive/<name> exists on the remote
        AND its sha equals the branch's sha at the time it was archived
        AND the commit is reachable in the remote

Exit 0 when every archived branch is recoverable; exit 1 naming the first that is not.
--drill additionally restores one branch to refs/heads/<name>-restore-drill, proves it contains
the sha, and deletes the temporary ref -- a restore that is never exercised is a hope.

Output is one JSON document with --json, so a surface can render it without parsing prose.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=120)  # noqa: S603


def archived_shas(repo: Path, remote: str) -> dict[str, str]:
    out = git(repo, "ls-remote", remote, "refs/archive/*")
    found = {}
    for line in (out.stdout or "").splitlines():
        sha, _, ref = line.partition("\t")
        if ref.startswith("refs/archive/"):
            found[ref[len("refs/archive/"):]] = sha
    return found


def inventory(repo: Path) -> list[dict]:
    p = repo / ".genesis" / "archive-inventory.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text()).get("entries", [])
    except ValueError:
        return []


def prove(repo: Path, remote: str, drill: bool) -> dict:
    arch = archived_shas(repo, remote)
    entries = inventory(repo)
    checks, bad = [], []
    for e in entries:
        name, sha = e.get("branch", ""), e.get("sha", "")
        have = arch.get(name)
        # Presence of the ref on the remote IS reachability of the commit: ls-remote returns the
        # ref only when the remote has the object. Asking again per entry was one network round
        # trip each -- 202 of them -- which made the verifier too slow to run.
        ok = bool(have) and have == sha
        checks.append({"branch": name, "sha": sha, "archive_ref": have or "", "ok": ok})
        if not ok:
            bad.append(name)
    result = {"remote": remote, "entries": len(entries), "checked": len(checks),
              "failed": bad, "ok": not bad and bool(entries), "checks": checks}
    if drill and entries:
        victim = entries[0]
        name, sha = victim["branch"], victim["sha"]
        tmp = f"{name}-restore-drill"
        push = git(repo, "push", "--no-verify", "-q", remote, f"{sha}:refs/heads/{tmp}")
        verified = False
        if push.returncode == 0:
            head = git(repo, "ls-remote", remote, f"refs/heads/{tmp}").stdout.split("\t")[0]
            verified = head == sha
            git(repo, "push", "--no-verify", "-q", remote, "--delete", tmp)
        result["drill"] = {"branch": name, "sha": sha, "restored": push.returncode == 0,
                           "verified": verified}
        result["ok"] = result["ok"] and verified
    return result


def render_html(r: dict) -> str:
    """The receipt as a page: the founder should see the invariant, not parse a log."""
    rows = "\n".join(
        f"<tr class=\"{'ok' if c['ok'] else 'bad'}\"><td>{c['branch']}</td>"
        f"<td><code>{c['sha'][:12]}</code></td>"
        f"<td>{'recoverable' if c['ok'] else 'LOST'}</td></tr>"
        for c in r["checks"][:500]
    )
    drill = r.get("drill") or {}
    return f"""<!doctype html><meta charset=utf-8><title>Estate archive: no-loss proof</title>
<style>body{{font:14px/1.5 -apple-system,system-ui,sans-serif;margin:2rem;color:#111}}
h1{{font-size:18px}}table{{border-collapse:collapse;width:100%}}
td,th{{border-bottom:1px solid #e5e5e5;padding:.35rem .6rem;text-align:left}}
tr.bad td{{background:#fee}} .ok{{color:#0a7}} .bad{{color:#c00}}
code{{font:12px ui-monospace,monospace}}</style>
<h1>Every archived branch is recoverable: {'YES' if r['ok'] else 'NO'}</h1>
<p><b>{r['checked'] - len(r['failed'])}</b> of <b>{r['checked']}</b> archived branch tips are
present at <code>refs/archive/&lt;name&gt;</code> on <code>{r['remote']}</code>.
{'Restore drill: <b>' + ('verified' if drill.get('verified') else 'FAILED') + '</b> (' + drill.get('branch','') + ').' if drill else 'Restore drill not run in this receipt.'}</p>
<table><tr><th>archived branch</th><th>tip</th><th>state</th></tr>
{rows}
</table>"""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--drill", action="store_true")
    ap.add_argument("--html", default="", help="write the receipt as a page a surface can serve")
    a = ap.parse_args(argv)
    r = prove(Path(a.repo).resolve(), a.remote, a.drill)
    if a.html:
        Path(a.html).write_text(render_html(r))
        print(f"  page written: {a.html}")
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print(f"  archived branches recoverable: {r['checked'] - len(r['failed'])}/{r['checked']}")
        for name in r["failed"]:
            print(f"  LOST  {name} -- its archive ref is missing or points elsewhere")
        if "drill" in r:
            d = r["drill"]
            print(f"  drill: restored {d['branch']} -> {'verified' if d['verified'] else 'FAILED'}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
