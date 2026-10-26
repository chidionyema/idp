"""The sandboxed ``match_logic`` evaluator.

A pack's ``match_logic`` is a deterministic expression over
``artifact.raw_evidence``. It is not code: there is no ``eval`` anywhere in
this module, no import, no attribute access on arbitrary objects, no
filesystem, no network. The grammar is small enough to read in one sitting:

    expression := or
    or         := and (('or' | '||') and)*
    and        := unary (('and' | '&&') unary)*
    unary      := 'not' unary | '(' expression ')' | comparison
    comparison := operand (('==' | '!=' | '<' | '<=' | '>' | '>=' |
                           'contains' | 'matches') operand)?
    operand    := path | string | number | 'true' | 'false'
    path       := IDENT ('.' IDENT | '[*]' | '[' NUMBER ']')*

``matches`` is a regex search, and the regex is the only place a pack can be
expensive. It is fenced three ways: a complexity ceiling, a subject length
cap, and a step budget that the whole evaluation runs under. A pack that
trips any of them is recorded as ``BUDGET_EXCEEDED`` and the next signature
is tried -- one bad pack cannot starve the reasoning layer.
"""

from __future__ import annotations

import re
import time

COMPLEXITY_ORDER = {"low": 0, "moderate": 1, "high": 2}

MAX_SUBJECT_CHARS = 4096
MAX_PATTERN_CHARS = 256
MAX_STEPS = 20000

_TOKEN_RE = re.compile(
    r"""
    (?P<string>"[^"]*"|'[^']*')
  | (?P<number>-?\d+(?:\.\d+)?)
  | (?P<op>==|!=|<=|>=|&&|\|\||contains|matches|and|or|not)
  | (?P<punct>[()\[\].,*<>])
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
    """,
    re.VERBOSE,
)


class MatchError(Exception):
    """The expression does not parse."""


class BudgetExceeded(Exception):
    """The evaluation ran past a declared ceiling."""


class Budget:
    """The ceilings a pack declares, loaded by the reasoning layer."""

    def __init__(
        self,
        max_wall_clock_ms=5000,
        max_steps=MAX_STEPS,
        max_regex_complexity="moderate",
    ):
        self.max_wall_clock_ms = int(max_wall_clock_ms)
        self.max_steps = int(max_steps)
        self.max_regex_complexity = max_regex_complexity
        self.deadline = time.monotonic() + (self.max_wall_clock_ms / 1000.0)
        self.steps = 0

    def tick(self):
        self.steps += 1
        if self.steps > self.max_steps:
            raise BudgetExceeded(f"step budget exceeded ({self.max_steps} steps)")
        if time.monotonic() > self.deadline:
            raise BudgetExceeded(
                f"wall clock budget exceeded ({self.max_wall_clock_ms} ms)"
            )


def tokenize(source: str):
    tokens = []
    index = 0
    while index < len(source):
        match = _TOKEN_RE.match(source, index)
        if not match:
            if source[index].isspace():
                index += 1
                continue
            raise MatchError(f"unexpected character {source[index]!r} at {index}")
        index = match.end()
        kind = match.lastgroup
        value = match.group()
        if kind == "string":
            tokens.append(("lit", value[1:-1]))
        elif kind == "number":
            tokens.append(("lit", float(value) if "." in value else int(value)))
        elif kind == "op":
            lowered = value.lower()
            if lowered in ("and", "&&"):
                tokens.append(("and", None))
            elif lowered in ("or", "||"):
                tokens.append(("or", None))
            elif lowered == "not":
                tokens.append(("not", None))
            else:
                tokens.append(("op", value))
        elif kind == "punct":
            tokens.append((value, None))
        elif kind == "ident":
            if value in ("true", "false"):
                tokens.append(("lit", value == "true"))
            else:
                tokens.append(("ident", value))
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else (None, None)

    def take(self):
        token = self.peek()
        self.pos += 1
        return token

    def expect(self, kind):
        token = self.take()
        if token[0] != kind:
            raise MatchError(f"expected {kind!r}, found {token[0]!r}")
        return token

    def parse(self):
        node = self.parse_or()
        if self.pos != len(self.tokens):
            raise MatchError("trailing tokens after the expression")
        return node

    def parse_or(self):
        node = self.parse_and()
        while self.peek()[0] == "or":
            self.take()
            node = ("or", node, self.parse_and())
        return node

    def parse_and(self):
        node = self.parse_unary()
        while self.peek()[0] == "and":
            self.take()
            node = ("and", node, self.parse_unary())
        return node

    def parse_unary(self):
        if self.peek()[0] == "not":
            self.take()
            return ("not", self.parse_unary())
        if self.peek()[0] == "(":
            self.take()
            node = self.parse_or()
            self.expect(")")
            return node
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_operand()
        kind, value = self.peek()
        if kind == "op":
            self.take()
            right = self.parse_operand()
            return ("cmp", value, left, right)
        return ("truthy", left)

    def parse_operand(self):
        kind, value = self.take()
        if kind == "lit":
            return ("lit", value)
        if kind == "ident":
            return ("path", self.parse_path(value))
        if kind == "(":
            node = self.parse_or()
            self.expect(")")
            return node
        raise MatchError(f"unexpected token {kind!r}")

    def parse_path(self, first):
        segments = [("key", first)]
        while True:
            kind, value = self.peek()
            if kind == ".":
                self.take()
                name_kind, name = self.take()
                if name_kind != "ident":
                    raise MatchError("a path segment must be a name")
                segments.append(("key", name))
            elif kind == "[":
                self.take()
                inner_kind, inner = self.take()
                if inner_kind == "*":
                    segments.append(("star", None))
                elif inner_kind == "lit" and isinstance(inner, int):
                    segments.append(("index", inner))
                else:
                    raise MatchError("a path index must be [*] or a number")
                self.expect("]")
            else:
                break
        return segments


def parse(source: str):
    """Parse a match expression into an AST."""
    if not isinstance(source, str) or not source.strip():
        raise MatchError("match_logic is empty")
    return _Parser(tokenize(source)).parse()


def regex_complexity(pattern: str) -> str:
    """Grade a regex: low, moderate or high.

    The dangerous shape is a quantifier inside a quantified group
    (``(a+)+``), which backtracks exponentially. A backreference or a
    lookaround is high too: both are ways to write the same trap.
    """
    if len(pattern) > MAX_PATTERN_CHARS:
        return "high"
    if re.search(r"\\[1-9]", pattern):
        return "high"
    if re.search(r"\(\?<?[=!]", pattern):
        return "high"
    for group in re.findall(r"\(([^()]*)\)\s*[*+{]", pattern):
        if re.search(r"[*+}]", group):
            return "high"
        if "|" in group:
            return "moderate"
    if len(pattern) > 64:
        return "moderate"
    return "low"


def _resolve(root, segments):
    """Resolve a path to a single value or a list of values."""
    current = [root]
    for kind, name in segments:
        nxt = []
        for value in current:
            if kind == "key":
                if isinstance(value, dict) and name in value:
                    nxt.append(value[name])
            elif kind == "star":
                if isinstance(value, list):
                    nxt.extend(value)
            elif kind == "index":
                if isinstance(value, list) and -len(value) <= name < len(value):
                    nxt.append(value[name])
        current = nxt
        if not current:
            return []
    return current


def _as_list(value):
    return value if isinstance(value, list) else [value]


def _compare(op, left, right):
    """One comparison, applied element-wise when either side is a list."""
    lefts = _as_list(left)
    rights = _as_list(right)
    for lval in lefts:
        for rval in rights:
            if op == "==":
                if lval == rval:
                    return True
            elif op == "!=":
                if lval != rval:
                    return True
            elif op == "<":
                if (
                    isinstance(lval, (int, float))
                    and isinstance(rval, (int, float))
                    and lval < rval
                ):
                    return True
            elif op == "<=":
                if (
                    isinstance(lval, (int, float))
                    and isinstance(rval, (int, float))
                    and lval <= rval
                ):
                    return True
            elif op == ">":
                if (
                    isinstance(lval, (int, float))
                    and isinstance(rval, (int, float))
                    and lval > rval
                ):
                    return True
            elif op == ">=":
                if (
                    isinstance(lval, (int, float))
                    and isinstance(rval, (int, float))
                    and lval >= rval
                ):
                    return True
            elif op == "contains":
                if isinstance(lval, str) and isinstance(rval, str) and rval in lval:
                    return True
                if isinstance(lval, (list, tuple)) and rval in lval:
                    return True
            elif op == "matches":
                if isinstance(lval, str) and isinstance(rval, str):
                    if re.search(rval, lval[:MAX_SUBJECT_CHARS]):
                        return True
    return False


def evaluate(node, root, budget: Budget) -> bool:
    """Evaluate an AST against ``root`` (the artifact) under ``budget``."""
    budget.tick()
    kind = node[0]
    if kind == "lit":
        return bool(node[1])
    if kind == "truthy":
        value = evaluate_value(node[1], root, budget)
        if isinstance(value, list):
            return bool(value)
        return bool(value)
    if kind == "not":
        return not evaluate(node[1], root, budget)
    if kind == "and":
        return evaluate(node[1], root, budget) and evaluate(node[2], root, budget)
    if kind == "or":
        return evaluate(node[1], root, budget) or evaluate(node[2], root, budget)
    if kind == "cmp":
        op = node[1]
        left = evaluate_value(node[2], root, budget)
        right = evaluate_value(node[3], root, budget)
        if op == "matches":
            pattern = right if isinstance(right, str) else ""
            level = regex_complexity(pattern)
            ceiling = COMPLEXITY_ORDER.get(budget.max_regex_complexity, 1)
            if COMPLEXITY_ORDER[level] > ceiling:
                raise BudgetExceeded(
                    f"regex complexity {level} exceeds the declared ceiling {budget.max_regex_complexity}"
                )
        return _compare(op, left, right)
    raise MatchError(f"unknown node {kind!r}")


def evaluate_value(node, root, budget: Budget):
    """Resolve an operand to a value (or list of values)."""
    budget.tick()
    if node[0] == "lit":
        return node[1]
    if node[0] == "path":
        return _resolve(root, node[1])
    if node[0] == "truthy":
        return evaluate_value(node[1], root, budget)
    if node[0] in ("and", "or", "not", "cmp"):
        return evaluate(node, root, budget)
    raise MatchError(f"unknown operand {node[0]!r}")


def matches(source: str, artifact: dict, budget: Budget = None) -> bool:
    """Evaluate a match expression against an artifact.

    Raises ``MatchError`` for an expression that does not parse and
    ``BudgetExceeded`` when a declared ceiling is hit. The caller (the
    reasoning layer) turns the second into a recorded diagnostic outcome.
    """
    budget = budget or Budget()
    return evaluate(parse(source), artifact, budget)
