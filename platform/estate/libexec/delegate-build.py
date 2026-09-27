#!/usr/bin/env python3
"""delegate-build: a strong model plans, a cheap model builds, and a test decides.

WHY. On 2026-09-27 two builders went out on Opus with a spec and no plan. They explored the repo
on their own, made their own design calls, and burned tokens. The founder had asked for a cheap
builder from the start. This makes the right way the only way: the planner (default Opus) reads
the code once and writes a plan in which every step names its files and its done-check; builders
(default Sonnet) open only those files; a step is done when its done-check exits 0, not when the
builder says so.

Every model call is a `claude -p` child. It reads ~/.claude/settings.json, so it goes through the
estate gateway (ANTHROPIC_BASE_URL, litellm-local on :4000) like this session does.

The reality interface (docs/tickets/2026-09-27-reality-interface.md): a builder's attempt is a
hypothesis; the done-check is reality. A failed attempt is rewound out of the tree (only the
step's files) and the next attempt gets the original instructions plus the raw check output in an
[EMPIRICAL_STATE] block, never the failed attempt's words. results.json keeps 'empirical'
(dispatcher-written) apart from 'scratchpad' (model-written).

  plan      spec=<md> repo=<dir> slug=<name> planner=<model>
            -> ~/.estate/delegate/<slug>/plan.json, validated
  dispatch  slug=<name> repo=<dir> builder=<model> parallel=<n> max_turns=<n> attempts=<n>
            -> one worktree ~/Documents/code/wt-<slug> on branch delegate/<slug>; steps run in
               waves (depends_on); steps in one wave touch disjoint files, so they share the tree
  status    slug=<name>
"""

import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HOME = Path.home()
ROOT = Path(os.environ.get("ESTATE_DELEGATE_ROOT", str(HOME / ".estate" / "delegate")))
TREES = Path(os.environ.get("ESTATE_DELEGATE_TREES", str(HOME / "Documents" / "code")))
MAX_PARALLEL = 3  # the estate's agent spawn budget

PLAN_SHAPE = """{
  "branch": "delegate/<slug>",
  "steps": [
    {
      "id": "s1",
      "title": "one line",
      "files": ["repo-relative paths this step may create or edit -- and nothing else"],
      "read": ["repo-relative paths the builder may read for context (keep it short)"],
      "depends_on": [],
      "instructions": "exact change: signatures, message shapes, names, edge cases. No design left to the builder.",
      "done_check": "shell command run from the repo root; exit 0 means the step is done (a real test that executes the new code)"
    }
  ]
}"""

PLANNER_PROMPT = """You are the planner. A cheaper model will build this, one step at a time, and it
must not explore the repository or make design decisions. Read the code you need now, then write
the plan.

Rules for the plan:
- Every step names the exact files it creates or edits ("files") and the few files it may read
  ("read"). A builder opens nothing else.
- Steps that can run at the same time (same depends_on wave) must not share a file.
- "instructions" fixes every decision: function and endpoint signatures, JSON shapes, names,
  error handling, and which existing code to reuse (AGENTS.md section 6: never build a second copy).
- "done_check" is a real command that runs the new code and exits non-zero if it is wrong
  (go test -run X, pytest path::test, CI=1 yarn backstage-cli package test --watchAll=false file).
  A check that cannot fail is not a check.
- Small steps: each one a builder can finish in under 30 tool calls.
- The last step opens nothing; opening the PR is the dispatcher's job.

Reply with ONLY the JSON, in this shape:
{shape}

The spec:
---
{spec}
---"""

BUILDER_PROMPT = """You are a builder. Do exactly this one step and nothing else.

Step {id}: {title}

Instructions:
{instructions}

You may create or edit ONLY these files: {files}
You may read ONLY these files (plus the ones above): {read}
Do not search the repository, do not refactor, do not touch anything else.

When you are done, this must exit 0 from the repo root:
  {done_check}
Run it yourself and fix your change until it passes. Never use --no-verify. Never print secrets.
Reply with one line: what you changed."""


def kv(argv):
    return dict(a.split("=", 1) for a in argv if "=" in a)


def claude(prompt, model, cwd, max_turns, tools):
    """One headless model call. Returns (text, usage dict)."""
    r = subprocess.run(
        [
            "claude",
            "-p",
            prompt,
            "--model",
            model,
            "--output-format",
            "json",
            "--max-turns",
            str(max_turns),
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            tools,
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        return "", {"error": (r.stderr or r.stdout)[-2000:]}
    usage = out.get("usage", {})
    return out.get("result", ""), {
        "cost_usd": out.get("total_cost_usd"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "turns": out.get("num_turns"),
    }


def validate(plan):
    errors, ids = [], set()
    steps = plan.get("steps") or []
    if not steps:
        errors.append("no steps")
    for s in steps:
        sid = s.get("id", "?")
        for field in ("id", "title", "files", "instructions", "done_check"):
            if not s.get(field):
                errors.append(f"{sid}: missing {field}")
        ids.add(sid)
    for s in steps:
        for d in s.get("depends_on", []):
            if d not in ids:
                errors.append(f"{s.get('id')}: depends on unknown {d}")
    for wave in waves(steps) if not errors else []:
        seen = {}
        for s in wave:
            for f in s["files"]:
                if f in seen:
                    errors.append(
                        f"{s['id']} and {seen[f]} both edit {f} in the same wave"
                    )
                seen[f] = s["id"]
    return errors


def waves(steps):
    done, left, out = set(), list(steps), []
    while left:
        ready = [s for s in left if set(s.get("depends_on", [])) <= done]
        if not ready:
            raise SystemExit("plan has a dependency cycle")
        out.append(ready)
        done |= {s["id"] for s in ready}
        left = [s for s in left if s["id"] not in done]
    return out


def cmd_plan(a):
    slug, repo = a["slug"], os.path.expanduser(a.get("repo", "~/Documents/code/idp"))
    spec = Path(os.path.expanduser(a["spec"])).read_text()
    d = ROOT / slug
    d.mkdir(parents=True, exist_ok=True)
    text, usage = claude(
        PLANNER_PROMPT.replace("{shape}", PLAN_SHAPE).replace("{spec}", spec),
        a.get("planner", "claude-opus-5-5"),
        repo,
        int(a.get("max_turns", 60)),
        "Read,Grep,Glob,Bash(rg:*),Bash(git log:*),Bash(git show:*),Bash(ls:*)",
    )
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        print(f"planner returned no JSON: {usage}", file=sys.stderr)
        return 1
    plan = json.loads(m.group(0))
    plan.setdefault("branch", f"delegate/{slug}")
    errors = validate(plan)
    (d / "plan.json").write_text(json.dumps(plan, indent=2))
    (d / "plan-usage.json").write_text(json.dumps(usage))
    print(
        f"plan: {d / 'plan.json'}  steps={len(plan.get('steps', []))}  planner={usage}"
    )
    for e in errors:
        print(f"INVALID: {e}", file=sys.stderr)
    return 1 if errors else 0


def cmd_dispatch(a):
    slug, repo = a["slug"], os.path.expanduser(a.get("repo", "~/Documents/code/idp"))
    d = ROOT / slug
    plan = json.loads((d / "plan.json").read_text())
    errors = validate(plan)
    if errors:
        print("\n".join(f"INVALID: {e}" for e in errors), file=sys.stderr)
        return 1
    tree = TREES / f"wt-{slug}"
    if not tree.exists():
        subprocess.run(["git", "-C", repo, "fetch", "-q", "origin", "main"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                repo,
                "worktree",
                "add",
                "-b",
                plan["branch"],
                str(tree),
                "origin/main",
            ],
            check=True,
        )
    builder = a.get("builder", "claude-sonnet-5")
    turns = int(a.get("max_turns", 30))
    par = min(int(a.get("parallel", MAX_PARALLEL)), MAX_PARALLEL)
    results = (
        json.loads((d / "results.json").read_text())
        if (d / "results.json").exists()
        else {}
    )

    def check(s):
        r = subprocess.run(
            s["done_check"],
            shell=True,
            cwd=tree,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        return r.returncode == 0, r.returncode, (r.stdout + r.stderr)[-3000:]

    def rewind(files, existed, base):
        for f in files:
            if existed[f]:
                subprocess.run(
                    ["git", "-C", tree, "checkout", base, "--", f], check=True
                )
            elif (tree / f).exists():
                (tree / f).unlink()

    attempts = int(a.get("attempts", 3))

    def run(s):
        if results.get(s["id"], {}).get("done"):
            return s["id"], results[s["id"]]
        base = subprocess.run(
            ["git", "-C", tree, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        existed = {
            f: subprocess.run(
                ["git", "-C", tree, "cat-file", "-e", f"{base}:{f}"],
                capture_output=True,
            ).returncode
            == 0
            for f in s["files"]
        }
        usage_all, empirical = [], []
        rc, out = None, None
        for attempt in range(1, attempts + 1):
            prompt = BUILDER_PROMPT.format(
                id=s["id"],
                title=s["title"],
                instructions=s["instructions"],
                files=", ".join(s["files"]),
                read=", ".join(s.get("read", [])) or "none",
                done_check=s["done_check"],
            )
            if attempt > 1:
                n = attempt - 1
                prompt += f"""

[EMPIRICAL_STATE] written by the dispatcher from the done-check, not by a model
Attempt {n} was rejected: `{s["done_check"]}` exited {rc}. Its changes were removed from the tree.
Output:
{out}
[/EMPIRICAL_STATE]
The previous attempt's reasoning was deleted on purpose. Form a new hypothesis from the instructions and this output alone."""
            text, usage = claude(prompt, builder, tree, turns, "Read,Edit,Write,Bash")
            usage_all.append(usage)
            ok, rc, out = check(s)
            empirical.append({"attempt": attempt, "check_rc": rc, "check_output": out})
            if ok:
                return s["id"], {
                    "done": True,
                    "attempts": attempt,
                    "empirical": empirical,
                    "scratchpad": {
                        "said": text[-300:],
                        "note": "the builder's own words; unverified, never used as evidence",
                    },
                    "usage": usage_all,
                }
            rewind(s["files"], existed, base)
        return s["id"], {
            "done": False,
            "attempts": attempts,
            "empirical": empirical,
            "scratchpad": {
                "said": text[-300:],
                "note": "the builder's own words; unverified, never used as evidence",
            },
            "usage": usage_all,
        }

    for wave in waves(plan["steps"]):
        with ThreadPoolExecutor(par) as pool:
            for sid, res in pool.map(run, wave):
                results[sid] = res
                print(
                    f"{sid}: {'done' if res['done'] else 'FAILED'} attempts={res['attempts']} check_rc={last_rc(res)} usage={res['usage']}"
                )
        (d / "results.json").write_text(json.dumps(results, indent=2))
        if not all(results[s["id"]]["done"] for s in wave):
            print(
                f"stopped: a step in this wave failed; see {d / 'results.json'}",
                file=sys.stderr,
            )
            return 1
    print(
        f"all {len(plan['steps'])} steps done in {tree} on {plan['branch']}; commit and open the PR from there"
    )
    return 0


def last_rc(res):
    """The last done-check exit code; None for a result written before the reality interface."""
    return (res.get("empirical") or [{}])[-1].get("check_rc")


def cmd_status(a):
    d = ROOT / a["slug"]
    plan = json.loads((d / "plan.json").read_text())
    results = (
        json.loads((d / "results.json").read_text())
        if (d / "results.json").exists()
        else {}
    )
    for s in plan["steps"]:
        r = results.get(s["id"], {})
        line = f"{s['id']:6} {'done' if r.get('done') else ('FAILED' if r else 'pending'):8} {s['title']}"
        if s["id"] in results:
            line += f"  rc={last_rc(r)}"
        print(line)
    return 0


if __name__ == "__main__":
    verb, args = sys.argv[1], kv(sys.argv[2:])
    sys.exit(
        {"plan": cmd_plan, "dispatch": cmd_dispatch, "status": cmd_status}[verb](args)
    )
