"""idp#6604: a Greenlane candidate (queue/**) hands bin/idp-ci a base, so offline-gate grades its diff.

offline-gate is skipped on pull requests, and IDP_CI_BASE was read only from `github.base_ref`,
which is set only on pull requests -- so wherever the job actually ran, the base was empty and
every path-gated rung swept everything. On run 39298091203 the kyverno rung judged all 62
platform dirs: 268 of bin/idp-ci's 367 s, on a candidate that touched none of them.

The expression is evaluated here, not pattern-matched: a small evaluator for the subset of the
GitHub expression language the line uses (&&, ||, startsWith, format, literals, github.*), with
GitHub's semantics -- `a && b` yields b when a is truthy else a, `a || b` yields a when truthy.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"

TOKEN = re.compile(r"\s*(&&|\|\||\(|\)|,|'(?:[^']|'')*'|[A-Za-z_][\w.]*)")


def evaluate(expr: str, github: dict):
    toks = TOKEN.findall(expr)
    assert "".join(toks).replace(" ", "") == expr.replace(" ", ""), (
        f"untokenised: {expr}"
    )
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def take(want=None):
        nonlocal pos
        t = toks[pos]
        assert want is None or t == want, (want, t)
        pos += 1
        return t

    def primary():
        t = take()
        if t == "(":
            v = disjunction()
            take(")")
            return v
        if t.startswith("'"):
            return t[1:-1].replace("''", "'")
        if peek() == "(":
            take("(")
            args = [disjunction()]
            while peek() == ",":
                take(",")
                args.append(disjunction())
            take(")")
            if t == "startsWith":
                return str(args[0] or "").lower().startswith(str(args[1]).lower())
            if t == "format":
                return re.sub(
                    r"\{(\d+)\}", lambda m: str(args[1 + int(m.group(1))]), args[0]
                )
            raise AssertionError(f"function not modelled: {t}")
        assert t.startswith("github."), f"context not modelled: {t}"
        return github.get(t.split(".", 1)[1], "")

    def conjunction():
        v = primary()
        while peek() == "&&":
            take()
            rhs = primary()
            v = rhs if v else v
        return v

    def disjunction():
        v = conjunction()
        while peek() == "||":
            take()
            rhs = conjunction()
            v = v if v else rhs
        return v

    out = disjunction()
    assert pos == len(toks), f"trailing tokens in {expr}"
    return out


def offline_gate():
    return yaml.safe_load(CI.read_text())["jobs"]["offline-gate"]


def base_expression() -> str:
    run = next(s for s in offline_gate()["steps"] if s.get("run") == "bin/idp-ci")
    m = re.fullmatch(r"\$\{\{(.*)\}\}", run["env"]["IDP_CI_BASE"].strip(), re.S)
    assert m, run["env"]["IDP_CI_BASE"]
    return m.group(1).strip()


@pytest.mark.parametrize(
    "github,want",
    [
        # the Greenlane candidate: graded on its diff against main, like a pull request
        ({"ref": "refs/heads/queue/b3221", "base_ref": ""}, "origin/main"),
        # the merged state: no base, so every path-gated rung sweeps everything
        ({"ref": "refs/heads/main", "base_ref": ""}, ""),
        # a pull request keeps its own base
        ({"ref": "refs/pull/1/merge", "base_ref": "main"}, "origin/main"),
        # a branch merely containing "queue" is not a candidate
        ({"ref": "refs/heads/lane/queue/x", "base_ref": ""}, ""),
    ],
)
def test_offline_gate_base(github, want):
    assert (evaluate(base_expression(), github) or "") == want


def test_offline_gate_fetches_the_base_it_diffs_against():
    # `origin/main...HEAD` needs main's history on the runner; on a shallow clone the diff fails,
    # touched() answers "yes" to everything, and the sweep silently comes back.
    checkout = next(
        s for s in offline_gate()["steps"] if "checkout" in s.get("uses", "")
    )
    assert checkout["with"]["fetch-depth"] == 0
