#!/usr/bin/env python3
"""delegate-build: artifact policy routes planning/building; a test decides.

WHY. On 2026-09-27 two builders went out on Opus with a spec and no plan. They explored the repo
on their own, made their own design calls, and burned tokens. The founder had asked for a cheap
builder from the start. Automatic routing starts ordinary planning at mid tier and gated
mechanical builds at cheap tier; deep/high-risk work uses frontier. Two failed gated attempts
require frontier re-planning before another build. Explicit planner/builder names remain a
manual override. A step is done when its done-check exits 0, not when the builder says so.

Every model call is a `claude -p` child. It reads the estate harness configuration, whose settings
carry the estate gateway (ANTHROPIC_BASE_URL, litellm-local on :4000) like this session does, so
the call arrives at the router and the artifact policy decides its tier.

Measured 2026-10-24, two ways a delegated call used to die before the model was ever reached.
(1) The child was refused by the estate's interactive plan gate: it has no plan tools, so every
tool call was refused and the delegated planner spent its turns arguing with the gate instead of
writing a plan. The delegate is the plan authority for its own children -- it validates every step
(files named, done-check named) and the dispatcher decides a step is done by the done-check exiting
0 -- so the child runs with the interactive plan gate off. (2) The child failed at startup
("error: An unknown error occurred (Unexpected)", exit 1, no output at all) for forty minutes in
one door and not in another; the environment was identical, so the cause was the CLI's own
startup, not the estate's. A startup failure costs nothing (the model never ran), so the call is
retried with backoff and every failure is kept in the usage record: a silent outage became a
bounded, diagnosable one.

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

import hashlib
import importlib.util
import json
import os
import re
import selectors
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
ROOT = Path(os.environ.get("ESTATE_DELEGATE_ROOT", str(HOME / ".estate" / "delegate")))
TREES = Path(os.environ.get("ESTATE_DELEGATE_TREES", str(HOME / "Documents" / "code")))
MAX_PARALLEL = 3  # the estate's agent spawn budget

# The estate harness configuration. Its settings carry the router address, so a delegated call
# that reads it arrives at the router -- and a delegated call that does not arrive at the router
# is not routed by the artifact policy at all.
HARNESS_CC = HOME / ".estate" / "harness" / "cc"
# A CLI that dies at startup is retried: the failure costs nothing (no model ran) and it clears
# on its own. Three attempts over about 85 seconds, then the failure is reported, not hidden.
CHILD_STARTUP_ATTEMPTS = 3
CHILD_STARTUP_BACKOFF_S = (5, 20, 60)


def startup_backoff():
    """Seconds to wait before each retry. Overridable so a test does not wait for the clock."""
    raw = os.environ.get("ESTATE_DELEGATE_STARTUP_BACKOFF", "")
    try:
        values = [float(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        values = []
    return tuple(values) if values else CHILD_STARTUP_BACKOFF_S


PLAN_SHAPE = """{
  "branch": "delegate/<slug>",
  "prior_art": {
    "searches": [
      {"kind": "prs", "query": "the exact command run", "found": ["#NNNN state title", "..."]},
      {"kind": "tickets", "query": "the exact command run", "found": ["docs/tickets/...", "..."]},
      {"kind": "code", "query": "the exact command run", "found": ["path -> the PR that added it"]}
    ],
    "verdict": "new | extend | exists",
    "reuse": ["what existing code/PR/ticket this plan builds on (required unless verdict is new)"]
  },
  "steps": [
    {
      "id": "s1",
      "title": "one line",
      "files": ["repo-relative paths this step may create or edit -- and nothing else"],
      "read": ["repo-relative paths the builder may read for context (keep it short)"],
      "depends_on": [],
      "artifact_class": "build | edit | author",
      "reasoning": "standard | deep",
      "risk": "standard | high",
      "instructions": "exact change: signatures, message shapes, names, edge cases. No design left to the builder.",
      "done_check": "shell command run from the repo root; exit 0 means the step is done (a real test that executes the new code)"
    }
  ]
}"""

PLANNER_PROMPT = """You are the planner. A cheaper model will build this, one step at a time, and it
must not explore the repository or make design decisions. Read the code you need now, then write
the plan.

FIRST, before any design: find what the estate already has. Run and record in "prior_art":
- prs: `gh pr list --state all -L 50 --search "<the capability's names>"` (merged and closed too);
- tickets: `rg -l -i "<names>" docs/tickets docs/specs docs/decisions`, and read the hits;
- code: `rg -l` for the capability, then trace each hit to the PR that added it
  (`git log --diff-filter=A --format=%s -- <path>`) and read that PR's ticket.
Files found on main are not the answer; their PR and ticket hold the scope and what is still open.
verdict "exists" means do not plan a build; "extend" means name what is reused in "reuse".

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
- Set artifact_class to build/edit for mechanical gated edits or author for new-file design.
  Use deep reasoning or high risk only with concrete evidence; standard is the default.
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

REPLAN_STEP_PROMPT = """You are the frontier re-planner. A gated builder failed twice.
Re-plan only step {step_id} from the original plan and the dispatcher's empirical output.
Do not trust or reproduce the builder's self-assessment. Preserve the step's id, files,
read scope, depends_on, done_check, artifact_class, reasoning, and risk exactly. You may
rewrite only its title and instructions to remove ambiguity and name the next hypothesis.
Read only the declared scope. Reply with ONLY the replacement step JSON object.

Original plan:
{plan}

Dispatcher-recorded failures:
{failures}
"""


def kv(argv):
    return dict(a.split("=", 1) for a in argv if "=" in a)


def empirical_block(attempt, check, rc, out, rewound=True):
    """The [EMPIRICAL_STATE] block: what reality said, never what the model said.

    A failed attempt is rewound out of the tree (only the step's files) and the next attempt
    gets the original instructions plus the raw check output, never the failed attempt's words.
    The generic launch path below uses the same block: the done-check is reality there too.
    """
    removed = (
        "Its changes were removed from the tree."
        if rewound
        else "Its changes were left in the worktree for the next attempt to build on."
    )
    return f"""

[EMPIRICAL_STATE] written by the dispatcher from the done-check, not by a model
Attempt {attempt} was rejected: `{check}` exited {rc}. {removed}
Output:
{out}
[/EMPIRICAL_STATE]
The previous attempt's reasoning was deleted on purpose. Form a new hypothesis from the instructions and this output alone."""


def artifact_policy(repo):
    """The estate's artifact policy: the installed copy first, then the checkout.

    The installed copy is ~/.estate/llm/artifact_tier.py -- the bytes bin/estate-runtime-sync
    stages from main, the same bytes the live router runs -- so a delegated call is routed by the
    policy in force, not by whatever a stale checkout happens to hold. The checkout copy
    (platform/llm/artifact_tier.py) is the fallback for a repo that has not been staged yet.
    """
    candidates = [
        Path(__file__).resolve().parents[1] / "llm/artifact_tier.py",
        Path(repo) / "platform/llm/artifact_tier.py",
        Path(__file__).resolve().parents[2] / "llm/artifact_tier.py",
    ]
    source = next((c for c in candidates if c.is_file()), None)
    if source is None:
        raise RuntimeError(
            "cannot load artifact routing policy from "
            + ", ".join(str(c) for c in candidates)
        )
    spec = importlib.util.spec_from_file_location("_estate_artifact_tier", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load artifact routing policy from {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.default_policy()


def resolve_model(value, request, policy):
    if value != "auto":
        return value, None
    decision = policy.route(request)
    if decision.alias is None:
        raise RuntimeError(f"{request.artifact_class} requires no model call")
    return decision.alias, decision


def step_request(step, policy):
    return policy.request(
        artifact_class=step.get("artifact_class", "build"),
        reasoning=step.get("reasoning", "standard"),
        risk=step.get("risk", "standard"),
        deterministic_gate=bool(step.get("done_check")),
    )


def find_step(texts, step_id):
    for text in reversed(texts):
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            continue
        try:
            step = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(step, dict) and step.get("id") == step_id:
            return step
    return None


def validate_replan(original, replacement):
    if replacement is None:
        return ["frontier re-planner wrote no replacement step JSON"]
    errors = []
    protected = {
        field: original.get(field)
        for field in ("id", "files", "read", "depends_on", "done_check")
    }
    protected["read"] = original.get("read", [])
    protected["depends_on"] = original.get("depends_on", [])
    protected.update(
        artifact_class=original.get("artifact_class", "build"),
        reasoning=original.get("reasoning", "standard"),
        risk=original.get("risk", "standard"),
    )
    for field, expected in protected.items():
        actual = replacement.get(field)
        if field in ("artifact_class", "reasoning", "risk"):
            actual = replacement.get(field, expected)
        if actual != expected:
            errors.append(f"replan changed protected field {field}")
    for field in ("title", "instructions"):
        if not replacement.get(field):
            errors.append(f"replan missing {field}")
    return errors


def child_env():
    """The environment a delegated model call runs in.

    ESTATE_PLAN_LOCK=off: the estate's plan gate refuses every tool until an interactive agent
    has declared a plan with a BDD scenario. A delegated child has no plan tools, so the gate
    refuses it forever -- measured 2026-10-24, the delegated planner spent its whole turn budget
    arguing with the gate and never wrote a plan. The delegate is the plan authority for its own
    children (every step names its files and a done-check; validate_plan refuses the rest) and the
    dispatcher decides a step is done when the done-check exits 0, so the interactive gate is off
    for the child.

    CLAUDE_CONFIG_DIR: pinned to the estate harness, whose settings carry the router address. A
    delegated call that does not arrive at the router is not routed by the artifact policy.
    """
    env = dict(os.environ)
    env["ESTATE_PLAN_LOCK"] = "off"
    if HARNESS_CC.is_dir():
        env["CLAUDE_CONFIG_DIR"] = str(HARNESS_CC)
    return env


def claude(
    prompt, model, cwd, max_turns, tools, stream=False, attempts=CHILD_STARTUP_ATTEMPTS
):
    """One headless model call. Returns (final reply, usage dict, every assistant text).

    stream=True reads --output-format stream-json, so every text the model wrote is kept, not
    only the last reply. Measured 2026-09-27 (vendor-self-setup): the planner wrote its plan, then
    a cross-session message arrived and its LAST reply answered that message, so the plan was lost
    though the model had written it.

    A child that dies at startup (exit non-zero, no model output) is retried with backoff: the
    model never ran, so nothing was spent, and the failure clears on its own. Every startup
    failure is kept in the usage record under "startup_failures"; when every attempt fails the
    error names the CLI startup failure instead of returning an empty reply.
    """
    fmt = ["stream-json", "--verbose"] if stream else ["json"]
    env = child_env()
    startup_failures = []
    for attempt in range(1, max(1, attempts) + 1):
        r = subprocess.run(  # noqa: S603 -- fixed argv (git/claude), no shell
            [  # noqa: S607 -- git and claude resolve from PATH on purpose
                "claude",
                "-p",
                prompt,
                "--model",
                model,
                "--output-format",
                *fmt,
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
            env=env,
        )
        texts, out = [], None
        for line in r.stdout.splitlines() if stream else [r.stdout]:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("type") == "assistant":
                texts += [
                    c.get("text", "")
                    for c in e.get("message", {}).get("content", [])
                    if c.get("type") == "text"
                ]
            elif not stream or e.get("type") == "result":
                out = e
        if out is not None:
            usage = out.get("usage", {})
            return (
                out.get("result", ""),
                {
                    "cost_usd": out.get("total_cost_usd"),
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "turns": out.get("num_turns"),
                    "startup_failures": startup_failures,
                },
                texts or [out.get("result", "")],
            )
        if r.returncode == 0:
            # The child answered and the answer could not be read. Not a startup failure: the
            # caller decides what to do with an unreadable reply.
            return (
                "",
                {
                    "error": (r.stderr or r.stdout)[-2000:],
                    "startup_failures": startup_failures,
                },
                texts,
            )
        failure = {
            "attempt": attempt,
            "exit": r.returncode,
            "stderr": (r.stderr or r.stdout)[-800:],
        }
        startup_failures.append(failure)
        print(
            f"warn  delegated model call failed at startup "
            f"(attempt {attempt}/{max(1, attempts)}, exit {r.returncode}): "
            f"{failure['stderr'][-200:].strip()}",
            file=sys.stderr,
        )
        if attempt < max(1, attempts):
            backoff = startup_backoff()
            delay = backoff[min(attempt - 1, len(backoff) - 1)]
            time.sleep(delay)
    return (
        "",
        {
            "error": (
                f"the claude CLI failed at startup {len(startup_failures)} times "
                f"(exit {startup_failures[-1]['exit']}): {startup_failures[-1]['stderr'][-400:]}"
            ),
            "startup_failures": startup_failures,
        },
        [],
    )


def find_plan(texts):
    """The last text that parses as a plan (a JSON object with steps), newest first."""
    for t in reversed(texts):
        m = re.search(r"\{.*\}", t, re.S)
        if not m:
            continue
        try:
            plan = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if isinstance(plan, dict) and "steps" in plan:
            return plan
    return None


PRIOR_ART_KINDS = ("prs", "tickets", "code")
PRIOR_ART_VERDICTS = ("new", "extend", "exists")


def validate_prior_art(pa):
    """A plan that did not look for what the estate already has is refused (AGENTS.md section 6)."""
    if not isinstance(pa, dict):
        return ["prior_art: missing -- search PRs, tickets and code before planning"]
    errors = []
    searches = pa.get("searches") or []
    kinds = {x.get("kind") for x in searches if isinstance(x, dict) and x.get("query")}
    for k in PRIOR_ART_KINDS:
        if k not in kinds:
            errors.append(f"prior_art: no {k} search recorded")
    verdict = pa.get("verdict")
    if verdict not in PRIOR_ART_VERDICTS:
        errors.append(
            f"prior_art: verdict must be one of {PRIOR_ART_VERDICTS}, got {verdict!r}"
        )
    if verdict in ("extend", "exists") and not pa.get("reuse"):
        errors.append(
            "prior_art: verdict says the capability exists but reuse names nothing"
        )
    if verdict == "exists":
        errors.append(
            "prior_art: verdict 'exists' -- nothing to build; use what is there"
        )
    return errors


def validate(plan):
    errors, ids = validate_prior_art(plan.get("prior_art")), set()
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


PLANNER_TOOLS = (
    "Read,Grep,Glob,Bash(rg:*),Bash(git log:*),Bash(git show:*),Bash(ls:*),"
    "Bash(gh pr list:*),Bash(gh pr view:*)"
)


def cmd_plan(a):
    slug, repo = a["slug"], os.path.expanduser(a.get("repo", "~/Documents/code/idp"))
    spec = Path(os.path.expanduser(a["spec"])).read_text()
    d = ROOT / slug
    d.mkdir(parents=True, exist_ok=True)
    policy = artifact_policy(repo)
    planner, routing = resolve_model(
        a.get("planner", "auto"),
        policy.request(
            "plan", a.get("reasoning", "standard"), a.get("risk", "standard")
        ),
        policy,
    )
    text, usage, texts = claude(
        PLANNER_PROMPT.replace("{shape}", PLAN_SHAPE).replace("{spec}", spec),
        planner,
        repo,
        int(a.get("max_turns", 60)),
        PLANNER_TOOLS,
        stream=True,
    )
    if routing:
        usage["routing"] = routing.as_dict()
    # Every text the planner wrote, kept: a lost plan is read back from here, not re-bought.
    (d / "plan-raw.txt").write_text("\n\n---\n\n".join(texts))
    # The usage record is written before the plan is judged: a failed call is exactly the record
    # that says why (a CLI that died at startup, a model that answered nothing).
    (d / "plan-usage.json").write_text(json.dumps(usage))
    plan = find_plan(texts)
    if plan is None:
        print(
            f"planner wrote no plan JSON in {len(texts)} text(s); see {d / 'plan-raw.txt'}: {usage}",
            file=sys.stderr,
        )
        return 1
    plan.setdefault("branch", f"delegate/{slug}")
    errors = validate(plan)
    (d / "plan.json").write_text(json.dumps(plan, indent=2))
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
        subprocess.run(["git", "-C", repo, "fetch", "-q", "origin", "main"], check=True)  # noqa: S603, S607 -- fixed argv (git/claude), no shell; git and claude resolve from PATH on purpose
        subprocess.run(  # noqa: S603 -- fixed argv (git/claude), no shell
            [  # noqa: S607 -- git and claude resolve from PATH on purpose
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
    builder = a.get("builder", "auto")
    replanner = a.get("planner", "auto")
    policy = artifact_policy(repo) if builder == "auto" else None
    turns = int(a.get("max_turns", 30))
    par = min(int(a.get("parallel", MAX_PARALLEL)), MAX_PARALLEL)
    results = (
        json.loads((d / "results.json").read_text())
        if (d / "results.json").exists()
        else {}
    )

    def check(s):
        r = subprocess.run(  # noqa: S602 -- the done-check is a shell command from the reviewed plan, by design
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
                subprocess.run(  # noqa: S603 -- fixed argv (git/claude), no shell
                    ["git", "-C", tree, "checkout", base, "--", f],  # noqa: S607 -- git resolves from PATH on purpose
                    check=True,
                )
            elif (tree / f).exists():
                (tree / f).unlink()

    attempts = int(a.get("attempts", 3))

    def run(s):
        if results.get(s["id"], {}).get("done"):
            return s["id"], results[s["id"]]
        base = subprocess.run(  # noqa: S603 -- fixed argv (git/claude), no shell
            ["git", "-C", tree, "rev-parse", "HEAD"],  # noqa: S607 -- git and claude resolve from PATH on purpose
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        existed = {
            f: subprocess.run(  # noqa: S603 -- fixed argv (git/claude), no shell
                ["git", "-C", tree, "cat-file", "-e", f"{base}:{f}"],  # noqa: S607 -- git and claude resolve from PATH on purpose
                capture_output=True,
            ).returncode
            == 0
            for f in s["files"]
        }
        request = step_request(s, policy) if policy else None
        step_builder, routing = (
            resolve_model(builder, request, policy) if policy else (builder, None)
        )
        usage_all, empirical, replanning = [], [], []
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
                prompt += empirical_block(n, s["done_check"], rc, out)
            text, usage, _ = claude(
                prompt, step_builder, tree, turns, "Read,Edit,Write,Bash"
            )
            if routing:
                usage["routing"] = routing.as_dict()
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
                    "replanning": replanning,
                }
            rewind(s["files"], existed, base)
            if policy and attempt == policy.document["gated_attempts_before_replan"]:
                replan_decision = policy.replan_after_failures(request, attempt)
                replan_model = (
                    replan_decision.alias if replanner == "auto" else replanner
                )
                replan_prompt = REPLAN_STEP_PROMPT.format(
                    step_id=s["id"],
                    plan=json.dumps(plan, indent=2),
                    failures=json.dumps(empirical, indent=2),
                )
                _, replan_usage, replan_texts = claude(
                    replan_prompt,
                    replan_model,
                    tree,
                    int(a.get("max_turns", 60)),
                    PLANNER_TOOLS,
                    stream=True,
                )
                replan_usage["routing"] = replan_decision.as_dict()
                usage_all.append(replan_usage)
                replacement = find_step(replan_texts, s["id"])
                replan_errors = validate_replan(s, replacement)
                record = {
                    "after_attempt": attempt,
                    "routing": replan_decision.as_dict(),
                    "valid": not replan_errors,
                }
                if replan_errors:
                    record["errors"] = replan_errors
                    replanning.append(record)
                    break  # no blind third attempt when frontier re-planning fails
                s = replacement
                record["step"] = replacement
                replanning.append(record)
        return s["id"], {
            "done": False,
            "attempts": len(empirical),
            "empirical": empirical,
            "scratchpad": {
                "said": text[-300:],
                "note": "the builder's own words; unverified, never used as evidence",
            },
            "usage": usage_all,
            "replanning": replanning,
        }

    for wave in waves(plan["steps"]):
        with ThreadPoolExecutor(par) as pool:
            for sid, res in pool.map(run, wave):
                results[sid] = res
                print(
                    f"{sid}: {'done' if res['done'] else 'FAILED'} attempts={res['attempts']} check_rc={last_rc(res)} usage={res['usage']}"
                )
                valid_replans = [r for r in res.get("replanning", []) if r.get("valid")]
                if valid_replans:
                    plan["steps"] = [
                        valid_replans[-1]["step"] if step["id"] == sid else step
                        for step in plan["steps"]
                    ]
        (d / "plan.json").write_text(json.dumps(plan, indent=2))
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
    if (d / "state.json").exists():
        state = json.loads((d / "state.json").read_text())
        print(
            f"{state.get('slug')} {state.get('state')} "
            f"harness={state.get('harness')} "
            f"route={state.get('provider')}/{state.get('model')} "
            f"milestone={state.get('last_verified_milestone')} "
            f"attempts={state.get('attempt_count')} "
            f"tokens_since_milestone={state.get('tokens_since_milestone')} "
            f"blocker={state.get('blocker')}"
        )
        return 0
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


# =============================================================================
# GENERIC ROUTED DELEGATION -- one boundary, any harness, measured progress
# =============================================================================
#
# WHY. The plan/dispatch verbs above are Claude-specific: every model call is a `claude -p`
# child and the caller cannot choose the harness. The founder asked for delegation that is
# model/harness independent and prefers routed headless Pi. This section is that path, and it
# reuses what is already here instead of building a second supervisor:
#
#   * the done-check is reality (the empirical interface above): a launch succeeds when the
#     independent check passes, never when the model says it is done;
#   * the [EMPIRICAL_STATE] rebuild-from-evidence retry (empirical_block above): the next
#     attempt sees what reality said, never the failed attempt's words;
#   * one state directory (ROOT/<slug>), which the existing Fleet reader already reads.
#
# WHAT IS NEW, and why it belongs here:
#   * a task packet: the caller supplies the task, the worktree, the identity, the route and
#     the bounds. The common path names no vendor.
#   * a harness adapter: pi first (routed through the estate router), claude is the same
#     contract. An unsupported harness is refused, never silently substituted.
#   * preflight before the first model call: the child identity must match a live claim, the
#     worktree must exist and be a git root, the route must exist, the output must be writable.
#     A missing worktree or an identity mismatch is a refusal, not a long exploration.
#   * progress that is measured, not narrated: milestones are declared against the actual
#     deliverable and verified by this dispatcher. Heartbeats and tool calls are liveness.
#   * a bounded lifecycle: wall time, tokens and steps, and only this launch's own process
#     group is ever terminated.
#
# DECISION (extend, not add a second supervisor). The generic path lives in this file. A new
# module would have been a rival delegation boundary carrying its own copy of the done-check
# and its own state; the estate has one of each layer (AGENTS.md section 6). The plan and
# dispatch verbs are unchanged.

DELEGATE_STATES = ("queued", "running", "succeeded", "failed", "cancelled")

# A retry of these changes nothing: the same input would fail the same way (context overflow,
# missing permission, wrong identity, unsupported tool schema).
TERMINAL_FAILURES = ("context_overflow", "permission", "identity", "schema")

PACKET_REQUIRED = (
    "task_id",
    "spec",
    "worktree",
    "identity",
    "claim_issue",
    "done_check",
)

DEFAULT_BUDGET = {
    "max_wall_s": 75,
    "max_tokens": 200000,
    "max_attempts": 2,
    "max_steps": 32,
}

CLAIM_COMMENT = re.compile(
    r"^CLAIM\s+agent=(?P<agent>\S+)\s+paths=(?P<paths>\S+)\s+heartbeat=(?P<heartbeat>\S+)"
)
CLAIM_MAX_AGE_S = 2 * 3600
LOG_MAX_BYTES = 2_000_000

PI_MODELS = Path(
    os.environ.get("ESTATE_PI_MODELS", str(HOME / ".pi" / "agent" / "models.json"))
)
PI_BIN = os.environ.get("ESTATE_PI_BIN", "pi")


def _now():
    return datetime.now(timezone.utc)


def _iso(moment=None):
    return (moment or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str))
    tmp.replace(path)


def _claims_for(issue, cwd):
    """The live CLAIM comments on an issue.

    gh is the source of truth. ESTATE_DELEGATE_CLAIM_FILE points at a local mirror of the same
    records (the shape bin/claim-open writes) for a launcher that runs where gh is not
    available: a test, or a delegated child on a host without a session.
    """
    mirror = os.environ.get("ESTATE_DELEGATE_CLAIM_FILE")
    if mirror:
        data = json.loads(Path(mirror).read_text())
        return [
            r for r in data.get("claims", []) if int(r.get("issue", -1)) == int(issue)
        ], None
    p = subprocess.run(
        [
            "gh",
            "issue",
            "view",
            str(issue),
            "--json",
            "state,comments",
            "--jq",
            '{"state":.state,"comments":[.comments[].body]}',
        ],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=60,
    )
    if p.returncode != 0:
        return [], f"the issue {issue} could not be read: {p.stderr.strip()[:200]}"
    data = json.loads(p.stdout or "{}")
    if data.get("state") != "OPEN":
        return [], f"issue {issue} is {data.get('state')}, not OPEN"
    records = []
    for body in data.get("comments", []):
        m = CLAIM_COMMENT.search(body or "")
        if not m:
            continue
        records.append(
            {
                "issue": int(issue),
                "agent": m.group("agent"),
                "paths": [p for p in m.group("paths").split(",") if p],
                "heartbeat": m.group("heartbeat"),
            }
        )
    return records, None


def _heartbeat_age_s(record):
    raw = str(record.get("heartbeat", "")).replace("Z", "+00:00")
    try:
        when = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (_now() - when).total_seconds()


def route_for(packet):
    """Validate the model route without ever reading or printing a credential.

    The pi catalogue is ~/.pi/agent/models.json: the provider must exist, must carry a baseUrl
    (a route) and must offer the model id. A model the provider does not carry is refused --
    the route is never swapped silently.
    """
    harness = packet.get("harness", "pi")
    provider = packet.get("provider", "estate")
    model = packet.get("model", "minimax_m27")
    if harness == "claude":
        if not model:
            return None, "the claude harness needs a model name"
        return {"provider": "claude", "model": model, "base_url": None}, None
    if harness != "pi":
        return None, f"harness {harness!r} is not supported (pi, claude)"
    if not PI_MODELS.is_file():
        return None, f"no pi model catalogue at {PI_MODELS}"
    try:
        data = json.loads(PI_MODELS.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"the pi model catalogue at {PI_MODELS} cannot be read: {exc}"
    prov = (data.get("providers") or {}).get(provider)
    if prov is None:
        return None, f"the pi provider {provider!r} is not configured"
    base = prov.get("baseUrl")
    if not base:
        return None, f"the pi provider {provider!r} carries no route (baseUrl)"
    ids = {m.get("id") for m in (prov.get("models") or []) if isinstance(m, dict)}
    if model not in ids:
        return None, (
            f"the model {model!r} is not on the {provider!r} route ({len(ids)} models are); "
            "the route is never swapped silently"
        )
    return {"provider": provider, "model": model, "base_url": base}, None


def preflight(packet, caller_identity, cwd, outdir):
    """Everything that must be true BEFORE the first model call.

    Each refusal is explicit and names what was missing. Nothing here talks to a model, so a
    refused preflight costs nothing.
    """
    errors = []
    identity = packet.get("identity")
    if not caller_identity:
        errors.append(
            "the launcher has no ESTATE_AGENT identity; it cannot bind a child"
        )
    elif caller_identity != identity:
        errors.append(
            f"identity mismatch: the launcher is {caller_identity!r}, "
            f"the task names {identity!r}"
        )
    issue = packet.get("claim_issue")
    records, problem = _claims_for(issue, cwd)
    if problem:
        errors.append(problem)
    else:
        mine = [r for r in records if r.get("agent") == identity]
        if not mine:
            errors.append(f"no CLAIM by {identity!r} on issue {issue}")
        else:
            age = _heartbeat_age_s(mine[-1])
            if age is None:
                errors.append(
                    f"the CLAIM on issue {issue} carries no readable heartbeat"
                )
            elif age > CLAIM_MAX_AGE_S:
                errors.append(
                    f"the CLAIM on issue {issue} is stale ({int(age)}s old); refresh it first"
                )
    worktree = Path(os.path.expanduser(str(packet.get("worktree", ""))))
    if not str(worktree):
        errors.append("the task names no worktree")
    elif not worktree.exists():
        errors.append(f"the worktree {worktree} does not exist")
    elif not worktree.is_dir():
        errors.append(f"the worktree {worktree} is not a directory")
    else:
        top = subprocess.run(
            ["git", "-C", str(worktree), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if top.returncode != 0:
            errors.append(f"the worktree {worktree} is not a git checkout")
        elif Path(top.stdout.strip()).resolve() != worktree.resolve():
            errors.append(
                f"the worktree {worktree} sits inside a checkout rooted at "
                f"{top.stdout.strip()}"
            )
    route, route_error = route_for(packet)
    if route_error:
        errors.append(route_error)
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        probe = outdir / ".writable"
        probe.write_text("ok")
        probe.unlink()
    except OSError as exc:
        errors.append(f"the output directory {outdir} is not writable: {exc}")
    return errors, route


def _run_check(command, worktree, timeout=600):
    """Run the caller's check. Shell on purpose: the check is a command from a reviewed task
    packet, exactly like the done-check of a plan step."""
    if not command:
        return None, "no check"
    try:
        r = subprocess.run(  # noqa: S602 -- the check is a shell command from the task packet, by design
            command,
            shell=True,
            cwd=str(worktree),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, f"the check did not finish within {timeout}s"
    return r.returncode, (r.stdout + r.stderr)[-3000:]


def evaluate_milestones(packet, worktree):
    """Check the declared checkpoints against the actual deliverable.

    A milestone is a predicate the dispatcher runs, not a claim the worker makes: a file that
    must exist, a command that must exit 0.
    """
    results = {}
    for milestone in packet.get("milestones") or []:
        kind = milestone.get("kind")
        if kind == "file":
            target = Path(worktree) / str(milestone.get("path", ""))
            ok = target.exists()
            detail = f"file {milestone.get('path')} {'exists' if ok else 'is absent'}"
        elif kind == "command":
            rc, _out = _run_check(str(milestone.get("cmd", "")), worktree)
            ok = rc == 0
            detail = f"command exited {rc}"
        else:
            ok, detail = False, f"unknown milestone kind {kind!r}"
        results[str(milestone.get("id"))] = {"verified": ok, "detail": detail}
    return results


def classify_failure(rc, out):
    """What kind of failure this is. Some kinds cannot be retried at all."""
    text = (out or "").lower()
    if "context" in text and (
        "overflow" in text or "too long" in text or "exceeds" in text
    ):
        return "context_overflow"
    if "permission" in text or "not allowed" in text or "eacces" in text:
        return "permission"
    if "schema" in text or "unknown tool" in text:
        return "schema"
    if "identity" in text and "claim" in text:
        return "identity"
    return "check_failed"


def failure_signature(out):
    """A normalized signature of a failure: the same shape of failure, the same signature."""
    text = re.sub(r"/[^\s]+", "<path>", out or "")
    text = re.sub(r"[0-9a-f]{7,40}", "<hash>", text)
    text = re.sub(r"\d+", "<n>", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    digest = hashlib.sha256(text[:400].encode("utf-8")).hexdigest()[:16]
    return f"{digest}:{text[:160]}"


class Harness:
    """One harness, one contract. The common path names no vendor."""

    name = "base"

    def argv(self, packet, prompt_file, run_id, session_dir):
        raise NotImplementedError

    def event(self, obj):
        """Map one JSONL event from the child to the common shape."""
        return {}


class PiHarness(Harness):
    """Headless Pi, routed through the estate router (provider/model), never a vendor key.

    The session id carries the run id, so the launcher can prove a pid is its own child before
    it ever signals a process group.
    """

    name = "pi"

    def argv(self, packet, prompt_file, run_id, session_dir):
        return [
            PI_BIN,
            "--offline",
            "--provider",
            str(packet.get("provider", "estate")),
            "--model",
            str(packet.get("model", "minimax_m27")),
            "--mode",
            "json",
            "--print",
            "--no-skills",
            "--no-prompt-templates",
            "--session-dir",
            str(session_dir),
            "--session-id",
            run_id,
            "@" + str(prompt_file),
        ]

    def event(self, obj):
        kind = obj.get("type")
        if kind == "tool_execution_start":
            return {"step": True, "tool": obj.get("toolName")}
        if kind in ("message_end", "message", "assistant"):
            message = (
                obj.get("message") if isinstance(obj.get("message"), dict) else obj
            )
            if not isinstance(message, dict):
                return {}
            usage = message.get("usage") or {}
            tokens = usage.get("totalTokens")
            if tokens is None:
                tokens = usage.get("total_tokens")
            text = "".join(
                c.get("text", "")
                for c in (message.get("content") or [])
                if isinstance(c, dict) and c.get("type") == "text"
            )
            return {"tokens": tokens, "text": text}
        return {}


class ClaudeHarness(Harness):
    """The existing claude -p child on the same contract (the generic path only)."""

    name = "claude"

    def argv(self, packet, prompt_file, run_id, session_dir):
        return [
            "claude",
            "-p",
            "@" + str(prompt_file),
            "--model",
            str(packet.get("model", "claude-sonnet-5")),
            "--output-format",
            "stream-json",
            "--verbose",
            "--max-turns",
            str(packet.get("max_turns", 30)),
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            "Read,Edit,Write,Bash",
        ]

    def event(self, obj):
        kind = obj.get("type")
        if kind == "assistant":
            text = "".join(
                c.get("text", "")
                for c in (obj.get("message") or {}).get("content", [])
                if isinstance(c, dict) and c.get("type") == "text"
            )
            return {"text": text}
        if kind == "result":
            usage = obj.get("usage") or {}
            tokens = None
            if usage:
                tokens = (usage.get("input_tokens") or 0) + (
                    usage.get("output_tokens") or 0
                )
            return {"tokens": tokens, "text": obj.get("result", "")}
        return {}


HARNESSES = {"pi": PiHarness, "claude": ClaudeHarness}


def _terminate_group(proc, grace=5.0):
    """Stop the process group this launcher started. Nobody else's."""
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        return
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, grace)):
        try:
            os.killpg(pgid, sig)
        except OSError:
            return
        try:
            proc.wait(timeout=wait)
            return
        except subprocess.TimeoutExpired:
            continue


def run_child(harness, packet, prompt_file, run_id, session_dir, budget, log_path):
    """Run one bounded child.

    Bounds: wall time, tokens and steps. The child is started in its own session, so the only
    processes this launcher can terminate are the ones it started. Unknown token usage stays
    unknown (None), never zero: an unknown spend is not a free spend.
    """
    argv = harness.argv(packet, prompt_file, run_id, session_dir)
    env = child_env()
    env["ESTATE_AGENT"] = str(packet.get("identity", ""))
    env["ESTATE_DELEGATE_RUN_ID"] = run_id
    proc = subprocess.Popen(  # noqa: S603 -- fixed argv (the harness), no shell
        argv,
        cwd=str(packet["worktree"]),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
        bufsize=0,
    )
    deadline = time.monotonic() + float(budget.get("max_wall_s", 90))
    tokens, steps, texts = 0, 0, []
    tokens_known = False
    terminated = None
    written = 0
    buf = b""
    selector = selectors.DefaultSelector()
    assert proc.stdout is not None
    selector.register(proc.stdout, selectors.EVENT_READ)
    log = open(log_path, "a", encoding="utf-8")
    try:
        while True:
            if proc.poll() is not None and not selector.get_map():
                break
            if time.monotonic() > deadline:
                terminated = "wall_clock"
                break
            if tokens_known and tokens > int(budget.get("max_tokens", 0)):
                terminated = "tokens"
                break
            if steps > int(budget.get("max_steps", 0)):
                terminated = "steps"
                break
            for key, _ in selector.select(timeout=0.5):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    text = line.decode("utf-8", "replace").strip()
                    if not text:
                        continue
                    if written < LOG_MAX_BYTES:
                        log.write(text + "\n")
                        written += len(text)
                    try:
                        obj = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    event = harness.event(obj)
                    if event.get("step"):
                        steps += 1
                    usage = event.get("tokens")
                    if usage is not None:
                        tokens += int(usage)
                        tokens_known = True
                    if event.get("text"):
                        texts.append(str(event["text"]))
    finally:
        log.close()
        selector.close()
    if terminated:
        _terminate_group(proc)
    else:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _terminate_group(proc)
    return {
        "pid": proc.pid,
        "exit_code": proc.returncode,
        "tokens": tokens if tokens_known else None,
        "steps": steps,
        "terminated": terminated,
        "texts": texts,
        "argv": argv,
    }


def _command_line(pid):
    p = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if p.returncode != 0:
        return None
    return p.stdout.strip()


def owns_child(pid, run_id):
    """Prove a pid is this launcher's child before it is ever signalled.

    The run id is in the child's argv (the pi session id), so a pid that does not carry it is
    somebody else's process and is left alone.
    """
    command = _command_line(pid)
    if not command:
        return False
    return run_id in command


LAUNCH_PROMPT = """You are a delegated worker. Do exactly the task below and nothing else.

Work only inside the directory you were started in. Do not search the repository, do not
refactor, do not touch anything else. Never print secrets. The dispatcher's check decides
whether you are done, not your own say-so.

The task:
---
{spec}
---"""


def build_prompt(packet, attempt, previous):
    spec = Path(os.path.expanduser(str(packet["spec"]))).read_text()
    parts = [LAUNCH_PROMPT.format(spec=spec)]
    if packet.get("prompt"):
        parts.append(str(packet["prompt"]))
    if attempt > 1 and previous:
        parts.append(
            empirical_block(
                previous["attempt"],
                packet["done_check"],
                previous.get("check_rc"),
                previous.get("check_output", ""),
                rewound=False,
            )
        )
        parts.append(
            "This attempt uses a different strategy from the last one: "
            f"{packet['strategies'][attempt - 1]!r}. "
            "Name the checkpoint you expect to reach before you start."
        )
    return "\n\n".join(parts)


def _budget_of(packet):
    budget = dict(DEFAULT_BUDGET)
    budget.update(packet.get("budget") or {})
    return budget


def cmd_launch(a):
    slug = str(a.get("slug") or "")
    if not slug:
        print("launch needs a slug (the task identity)", file=sys.stderr)
        return 1
    d = ROOT / slug
    packet_path = os.path.expanduser(str(a.get("task") or (d / "task.json")))
    try:
        packet = json.loads(Path(packet_path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read the task packet {packet_path}: {exc}", file=sys.stderr)
        return 1
    missing = [f for f in PACKET_REQUIRED if not packet.get(f)]
    if missing:
        print("INVALID task packet: missing " + ", ".join(missing), file=sys.stderr)
        return 1
    # The CLI may narrow the packet. It may never take another agent's identity: the preflight
    # below refuses any identity that is not the launcher's own.
    for key, arg in (
        ("harness", "harness"),
        ("provider", "provider"),
        ("model", "model"),
        ("identity", "agent"),
        ("worktree", "worktree"),
    ):
        if a.get(arg):
            packet[key] = (
                os.path.expanduser(str(a[arg])) if key == "worktree" else str(a[arg])
            )
    if a.get("done_check"):
        packet["done_check"] = str(a["done_check"])
    packet["worktree"] = os.path.expanduser(str(packet["worktree"]))
    # The launcher's identity: ESTATE_AGENT when the caller set it, otherwise the name the
    # governed intent call carried. If both are present and disagree, that is a refusal, not
    # a preference: the child identity must be one identity.
    env_identity = os.environ.get("ESTATE_AGENT", "")
    arg_identity = str(a.get("agent") or "")
    if env_identity and arg_identity and env_identity != arg_identity:
        print(
            f"IDENTITY CONFLICT: the launcher runs as {env_identity!r} but the intent names "
            f"{arg_identity!r}; the child identity must be one identity",
            file=sys.stderr,
        )
        return 1
    caller = env_identity or arg_identity
    errors, route = preflight(packet, caller, d, d)
    budget = _budget_of(packet)
    state = {
        "task_id": packet["task_id"],
        "slug": slug,
        "state": "queued",
        "harness": packet.get("harness", "pi"),
        "provider": packet.get("provider", "estate"),
        "model": packet.get("model", "minimax_m27"),
        "identity": packet.get("identity"),
        "worktree": packet["worktree"],
        "done_check": packet.get("done_check"),
        "claim_issue": packet.get("claim_issue"),
        "route": route or {},
        "preflight": {"errors": errors},
        "attempts": [],
        "attempt_count": 0,
        "milestones": {},
        "last_verified_milestone": None,
        "tokens_since_milestone": None,
        "elapsed_since_milestone_s": None,
        "failure_signatures": [],
        "blocker": None,
        "next_recovery": None,
        "budget": budget,
        "evidence": {
            "task": str(packet_path),
            "events": [],
            "results": str(d / "results.json"),
        },
        "started_at": _iso(),
        "updated_at": _iso(),
    }
    if errors:
        state["state"] = "failed"
        state["blocker"] = "preflight: " + "; ".join(errors)
        state["next_recovery"] = "fix what preflight named, then launch again"
        _write_json(d / "state.json", state)
        print(f"preflight refused: {state['blocker']}", file=sys.stderr)
        return 1
    harness_cls = HARNESSES.get(str(packet.get("harness", "pi")))
    if harness_cls is None:
        state["state"] = "failed"
        state["blocker"] = f"harness {packet.get('harness')!r} is not supported"
        _write_json(d / "state.json", state)
        print(f"preflight refused: {state['blocker']}", file=sys.stderr)
        return 1
    harness = harness_cls()
    run_id = f"delegate-{slug}-{int(time.time())}"
    session_dir = d / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    _write_json(d / "task.json", packet)
    strategies = [str(s) for s in (packet.get("strategies") or [])]
    state["state"] = "running"
    state["run_id"] = run_id
    _write_json(d / "state.json", state)
    started = time.monotonic()
    total_tokens = 0
    tokens_known = False
    signatures = []
    records = []
    blocker = None
    succeeded = False
    last_text = ""
    attempt = 0
    while attempt < int(budget["max_attempts"]):
        attempt += 1
        strategy = strategies[attempt - 1] if attempt - 1 < len(strategies) else None
        if attempt > 1:
            previous_strategy = strategies[attempt - 2]
            if strategy is None:
                blocker = (
                    "needs-supervisor: no permitted changed strategy remains; "
                    "the task may not be retried unchanged"
                )
                state["next_recovery"] = "needs-supervisor"
                break
            if strategy == previous_strategy:
                blocker = (
                    f"needs-supervisor: the strategy did not change ({strategy!r}); "
                    "an identical retry is refused"
                )
                state["next_recovery"] = "needs-supervisor"
                break
        remaining_wall = float(budget["max_wall_s"]) - (time.monotonic() - started)
        if remaining_wall <= 0:
            blocker = f"budget: the wall-clock bound ({budget['max_wall_s']}s) is spent"
            break
        remaining_tokens = int(budget["max_tokens"]) - (
            total_tokens if tokens_known else 0
        )
        if tokens_known and remaining_tokens <= 0:
            blocker = f"budget: the token bound ({budget['max_tokens']}) is spent"
            break
        prompt_file = d / f"prompt-{attempt}.md"
        prompt_file.write_text(
            build_prompt(packet, attempt, records[-1] if records else None)
        )
        child_budget = {
            "max_wall_s": remaining_wall,
            "max_tokens": remaining_tokens,
            "max_steps": int(budget["max_steps"]),
        }
        log_path = d / f"events-{attempt}.jsonl"
        child = run_child(
            harness,
            packet,
            prompt_file,
            f"{run_id}-{attempt}",
            session_dir,
            child_budget,
            log_path,
        )
        state["pid"] = child["pid"]
        state["run_id"] = f"{run_id}-{attempt}"
        if child["tokens"] is not None:
            total_tokens += child["tokens"]
            tokens_known = True
        last_text = child["texts"][-1] if child["texts"] else ""
        rc, out = _run_check(str(packet["done_check"]), packet["worktree"])
        milestones = evaluate_milestones(packet, packet["worktree"])
        record = {
            "attempt": attempt,
            "strategy": strategy,
            "exit_code": child["exit_code"],
            "terminated": child["terminated"],
            "tokens": child["tokens"],
            "steps": child["steps"],
            "elapsed_s": round(time.monotonic() - started, 1),
            "check_rc": rc,
            "check_output": out,
            "milestones": milestones,
            "events": str(log_path),
            "said": last_text[-300:],
        }
        records.append(record)
        state["attempts"] = records
        state["attempt_count"] = attempt
        state["milestones"] = milestones
        state["tokens_since_milestone"] = total_tokens if tokens_known else None
        state["elapsed_since_milestone_s"] = round(time.monotonic() - started, 1)
        state["evidence"]["events"].append(str(log_path))
        # A milestone that turns green is progress. A file touched, a tool call or a heartbeat
        # is liveness, and liveness is not progress.
        for milestone_id, milestone in milestones.items():
            if milestone.get("verified") and milestone_id != state.get(
                "last_verified_milestone"
            ):
                state["last_verified_milestone"] = milestone_id
                state["tokens_since_milestone"] = 0 if tokens_known else None
                state["elapsed_since_milestone_s"] = 0.0
        _write_json(d / "state.json", state)
        if rc == 0:
            succeeded = True
            break
        signature = failure_signature(out)
        category = classify_failure(rc, out)
        record["failure_category"] = category
        record["failure_signature"] = signature
        repeated = signature in signatures
        if not repeated:
            signatures.append(signature)
        state["failure_signatures"] = signatures
        if category in TERMINAL_FAILURES:
            blocker = f"{category}: the same input would fail the same way; no retry"
            state["next_recovery"] = "needs-supervisor"
            break
        if repeated:
            blocker = (
                f"needs-supervisor: the same failure repeated ({signature}); "
                "a changed strategy is required"
            )
            state["next_recovery"] = "needs-supervisor"
            break
        state["next_recovery"] = (
            f"retry with a changed strategy ({strategies[attempt]!r})"
            if attempt < len(strategies)
            else "no permitted changed strategy remains"
        )
        _write_json(d / "state.json", state)
    if succeeded:
        state["state"] = "succeeded"
        state["blocker"] = None
        state["next_recovery"] = None
    else:
        state["state"] = "failed"
        state["blocker"] = blocker or "the task did not reach its done-check"
    state["finished_at"] = _iso()
    state["updated_at"] = _iso()
    state["elapsed_s"] = round(time.monotonic() - started, 1)
    state["tokens"] = total_tokens if tokens_known else None
    _write_json(d / "state.json", state)
    results = {
        str(packet["task_id"]): {
            "done": succeeded,
            "attempts": len(records),
            "empirical": [
                {
                    "attempt": r["attempt"],
                    "check_rc": r["check_rc"],
                    "check_output": r["check_output"],
                }
                for r in records
            ],
            "scratchpad": {
                "said": last_text[-300:],
                "note": "the worker's own words; unverified, never used as evidence",
            },
            "usage": [
                {
                    "tokens": r["tokens"],
                    "steps": r["steps"],
                    "elapsed_s": r["elapsed_s"],
                    "strategy": r["strategy"],
                }
                for r in records
            ],
        }
    }
    _write_json(d / "results.json", results)
    print(
        f"launch {slug}: {state['state']} attempts={len(records)} "
        f"milestone={state.get('last_verified_milestone')} "
        f"tokens={state.get('tokens')} blocker={state.get('blocker')}"
    )
    print(f"state: {d / 'state.json'}")
    return 0 if succeeded else 1


def cmd_cancel(a):
    """Stop this delegation's own child. Nobody else's process is ever signalled."""
    slug = str(a.get("slug") or "")
    d = ROOT / slug
    state_path = d / "state.json"
    if not state_path.exists():
        print(f"no delegation state for {slug}", file=sys.stderr)
        return 1
    state = json.loads(state_path.read_text())
    if state.get("state") != "running":
        print(f"{slug} is {state.get('state')}; nothing to cancel")
        return 1
    pid = state.get("pid")
    run_id = state.get("run_id") or ""
    if not pid:
        print(f"{slug} holds no pid", file=sys.stderr)
        return 1
    if not owns_child(int(pid), run_id):
        print(
            f"refusing to cancel: pid {pid} does not carry the run id, so it is not this "
            "delegation's child; only owned children are stopped",
            file=sys.stderr,
        )
        return 1
    try:
        pgid = os.getpgid(int(pid))
    except OSError:
        pgid = int(pid)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except OSError:
            break
        time.sleep(1)
        if not _command_line(pid):
            break
    state["state"] = "cancelled"
    state["blocker"] = "cancelled by the caller"
    state["finished_at"] = _iso()
    state["updated_at"] = _iso()
    _write_json(state_path, state)
    print(f"cancelled {slug} (pid {pid})")
    return 0


if __name__ == "__main__":
    verb, args = sys.argv[1], kv(sys.argv[2:])
    sys.exit(
        {
            "plan": cmd_plan,
            "dispatch": cmd_dispatch,
            "status": cmd_status,
            "launch": cmd_launch,
            "cancel": cmd_cancel,
        }[verb](args)
    )
