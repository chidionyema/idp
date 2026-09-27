#!/usr/bin/env python3
"""ci-status — structured CI status for a PR or SHA."""

import json, subprocess, sys


def gh_json(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        print(json.dumps({"error": r.stderr.strip()}))
        sys.exit(1)
    return json.loads(r.stdout)


repo = "chidionyema/idp"
sha = ""
pr_num = 0

for arg in sys.argv[1:]:
    if arg.startswith("pr="):
        pr_num = int(arg.split("=", 1)[1])
    elif arg.startswith("sha="):
        sha = arg.split("=", 1)[1]
    elif arg.startswith("repo="):
        repo = arg.split("=", 1)[1]

if pr_num and not sha:
    d = gh_json(f"repos/{repo}/pulls/{pr_num}")
    sha = d["head"]["sha"]
    branch = d["head"]["ref"]
    title = d["title"]
    is_draft = d.get(
        "draft", False
    )  # REST says "draft"; "isDraft" is the GraphQL/gh name
elif not sha:
    print(json.dumps({"error": "pr= or sha= required"}))
    sys.exit(1)
else:
    branch = "?"
    title = "?"
    is_draft = False

# per_page=100: the default page is 30, and a PR here carries more checks than that
runs = gh_json(f"repos/{repo}/commits/{sha}/check-runs?per_page=100")["check_runs"]
pending = [r for r in runs if r.get("conclusion") is None]
failed = [r for r in runs if r.get("conclusion") == "failure"]
skipped = [r for r in runs if r.get("conclusion") == "skipped"]
passed = [r for r in runs if r.get("conclusion") == "success"]

result = {
    "sha": sha[:8],
    "branch": branch,
    "title": title,
    "draft": is_draft,
    "repo": repo,
    "total": len(runs),
    "passed": len(passed),
    "failed": len(failed),
    "skipped": len(skipped),
    "running": len(pending),
    "failures": [{"name": r["name"], "url": r.get("html_url", "")} for r in failed],
    "running_names": [r["name"] for r in pending],
    "merge_ready": len(failed) == 0 and len(pending) == 0,
}
print(json.dumps(result, indent=2))
