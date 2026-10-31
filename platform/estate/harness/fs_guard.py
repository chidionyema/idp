"""
platform/estate/harness/fs_guard.py
Enforces the Read/Patch boundary inside estate-execute before any shell command runs.

Scope: this guards commands estate-execute dispatches on behalf of an agent (the one
execution boundary, AGENTS.md section 7). It does not and cannot reach a human's own
shell, and it is a heuristic text filter -- not a sandbox -- so it is one layer, not the
only layer: bin/estate-read and bin/estate-patch are the real doors (receipt-gated,
AST-checked); this module exists so an agent cannot simply route around them with a raw
shell redirect in the same command string.

Two questions, two answers, one module.

`check_command_allowed(cmd)` is the whole-command answer: if the command contains a raw
read, a raw write, an in-place edit or a direct markdown read, it is refused. That is the
strict answer, and it stays the answer for a caller that has nothing better to say.

`check_intent_step(cmd, agent_spans)` is the provenance answer, and it is the one the
intent executor uses for the steps of a committed intent. A committed intent file is
reviewed estate source: the `cat` and the `>` inside it are the estate's own reviewed
operation, and a guard that refuses them is refusing the estate's own doors (measured:
139 of 601 committed steps across 83 installed intents, 31 of them unusable). What is not
trusted is the text the caller supplied. So a forbidden construct is refused when, and
only when, it overlaps a span of the command that came from the caller's own arguments.

The spans are character ranges in the final, interpolated command. "The agent chose this
path" is therefore decided by position, not by guessing which side of a template a token
came from.

The precision rules matter as much as the rules themselves:

  * a metacharacter that cannot reach the shell is not a violation (quoted text);
  * a pipeline consumer is not a file read (`| head -20` reads stdin, not a file);
  * a count is not a path (`head -20`);
  * a comparison operator is not a redirect (`>=`, `->`, `=>`, `> 10`);
  * a moved descriptor is not a write (`2>&1`), and neither is `/dev/null`.

Two constructs are deliberately kept at the ORIGINAL guard's strictness, so that the
whole-command answer does not become stricter than it was:

  * a heredoc delimiter is only a heredoc when it is an unquoted word (`<<EOF`). The
    original stripped quoted spans before matching, so `<<'PY'` and `<<<` were never
    flagged; a quoted delimiter is left alone here for the same reason.
  * `2>/dev/null` is a discard, including when the shell closes it with `)`.

_found live (not in a unit test) on the first real round trip through estate-execute:
a legitimate `bin/estate-patch` invocation piping a SEARCH/REPLACE payload whose
*replacement text* contained `if used >= limit:` was refused as a RAW_WRITE_REDIRECT, because
the original pattern scanned the whole command string for a bare `>` with no notion of
quoting -- a `>` inside a single-quoted printf payload has no shell effect at all, but the
regex could not tell the difference between that and a real redirect. Any patch touching a
comparison operator or a heredoc-looking string inside its own payload would have hit this.
_mask_quoted removes quoted spans before the redirect/cat/tail patterns run, since a
character that cannot reach the shell is not a redirect this layer needs to refuse.
"""

import re

_NUL = "\x00"

_SINGLE_QUOTED = re.compile(r"'[^']*'")
_DOUBLE_QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"')

# The doors themselves, and read-only verbs: allowed exactly as they are.
ALLOWED_PREFIXES = (
    "bin/estate-read",
    "bin/estate-patch",
    "git status",
    "git diff",
    "git log",
    "git commit",
    "git push",
    "bin/idp-ci",
    "pytest",
)

RAW_READ_REASON = (
    "RAW_READ_BANNED: Direct file reads via cat/head/tail are banned. "
    "Use `bin/estate-read <path> --lines START:END`."
)
INPLACE_REASON = "INPLACE_STREAM_EDIT_BANNED: Use `bin/estate-patch <path> --receipt <READ_RECEIPT>`."
WRITE_REASON = (
    "RAW_WRITE_REDIRECT_BANNED: Shell file overwrites and appends (> / >> / << / tee) "
    "are banned. Use `bin/estate-patch`."
)
MARKDOWN_REASON = (
    "STALE_MARKDOWN_ACCESS_BANNED: Direct access to static markdown rule/plan files is "
    "blocked. Query the timestamped memory ledger."
)

_READ_RE = re.compile(
    r"(?<![A-Za-z0-9_.\-])(?:cat|head|tail|less|more)(?![A-Za-z0-9_\-])"
)
_TEE_RE = re.compile(r"\btee\b")
_INPLACE_RE = re.compile(r"(?:sed\s+-i|perl\s+-pi|awk\s+-i\s+inplace)\b")
_MARKDOWN_RE = re.compile(r"\b(?:AGENTS\.md|docs/NEXT\.md|docs/FOUNDER\.md)\b")

# The readers that take a count: for them a bare number is a count, not a path.
_COUNTED_READERS = ("head", "tail", "less", "more")
# Options whose value is the next token.
_VALUE_OPTIONS = ("-n", "-c", "-q", "-m", "-b")


def _mask_quoted(cmd):
    """The command with the CONTENT of every quoted span blanked, keeping its length.

    A metacharacter inside quotes never reaches the shell as an operator, so it is not a
    violation this layer needs to refuse. But the offsets of everything around it must not
    move: the provenance answer compares a forbidden match's position with the position of
    the agent-supplied text that caused it.
    """

    def _blank(match):
        text = match.group(0)
        return text[0] + _NUL * (len(text) - 2) + text[-1]

    masked = _SINGLE_QUOTED.sub(_blank, cmd)
    masked = _DOUBLE_QUOTED.sub(_blank, masked)
    return masked


def _at_command_start(cmd, pos):
    """True when the word at `pos` begins a command (start of the string, or after ; | &)."""
    i = pos - 1
    while i >= 0 and cmd[i] in " \t":
        i -= 1
    if i < 0:
        return True
    return cmd[i] in ";|&\n"


def _next_token(text, i):
    """The next whitespace-delimited token at or after `i`: (text, start, end)."""
    n = len(text)
    while i < n and text[i].isspace():
        i += 1
    if i >= n:
        return None
    start = i
    while i < n and not text[i].isspace():
        i += 1
    return text[start:i], start, i


def _read_operand(masked, word, after):
    """The file operand of a read command, and its span, or None.

    `cat FILE` reads a file. `head -20` counts lines and reads stdin. `tail -n 5 FILE`
    reads a file; `tail -n 5` does not. A count is not a path, and a pipeline consumer
    is not a read of a file at all.
    """
    i = after
    while True:
        token = _next_token(masked, i)
        if token is None:
            return None
        text, start, i = token
        if text.startswith("-"):
            if text in _VALUE_OPTIONS:
                nxt = _next_token(masked, i)
                if nxt is not None and nxt[0].isdigit():
                    i = nxt[2]
            continue
        if text[0] in "><":
            # The read has no file operand; a redirect owns that position.
            return None
        if word in _COUNTED_READERS and text.isdigit():
            return None
        return (start, i)


def _segment_end(masked, start):
    """The end of the command segment that begins at `start`."""
    n = len(masked)
    i = start
    while i < n and masked[i] not in ";|&\n":
        i += 1
    return i


def _read_matches(masked):
    out = []
    for match in _READ_RE.finditer(masked):
        if not _at_command_start(masked, match.start()):
            continue
        word = match.group(0)
        operand = _read_operand(masked, word, match.end())
        if operand is None:
            # No file operand: `cat` alone, `head -20`, `| tail -n 5`. Nothing is read
            # from a file, so there is no read to refuse.
            continue
        out.append((match.start(), operand[1], RAW_READ_REASON))
    return out


_HEREDOC_DELIMITER = re.compile(r"\w+")


def _redirect_matches(masked):
    out = []
    i = 0
    n = len(masked)
    while i < n:
        if masked[i : i + 2] == "<<":
            j = i + 2
            while j < n and masked[j].isspace():
                j += 1
            start = j
            while j < n and not masked[j].isspace() and masked[j] not in ";|&":
                j += 1
            # Only an unquoted word is a heredoc delimiter: `<<EOF`. A quoted delimiter
            # (`<<'PY'`) and a here-string (`<<<`) are not the write construct the
            # original pattern matched, and the original's quote-stripping let them pass.
            if _HEREDOC_DELIMITER.fullmatch(masked[start:j]):
                out.append((i, j, WRITE_REASON))
            i = max(j, i + 2)
            continue
        if masked[i] != ">":
            i += 1
            continue
        if masked[i : i + 3] == ">>=":
            i += 3
            continue
        if masked[i + 1 : i + 2] == "=":
            # `>=` is a comparison, not a redirect.
            i += 2
            continue
        if i > 0 and masked[i - 1] in "-=":
            # `->` and `=>` are arrows, not redirects.
            i += 1
            continue
        op_len = 2 if masked[i : i + 2] == ">>" else 1
        j = i + op_len
        while j < n and masked[j].isspace():
            j += 1
        start = j
        while j < n and not masked[j].isspace() and masked[j] not in ";|&":
            j += 1
        target = masked[start:j]
        if not target:
            i += 1
            continue
        if target.startswith("&"):
            # `2>&1` and `>&2` move a descriptor; no file is written.
            i = j
            continue
        if re.split(r"[)\]},:;]", target, 1)[0].rstrip("'\"") == "/dev/null":
            # `2>/dev/null` is a discard, whether or not the shell closes it with `)`.
            i = j
            continue
        if target.isdigit():
            # `> 10` is a comparison, not a redirect.
            i = j
            continue
        out.append((i, j, WRITE_REASON))
        i = max(j, i + 1)
    return out


def _tee_matches(masked):
    out = []
    for match in _TEE_RE.finditer(masked):
        operand = _read_operand(masked, "tee", match.end())
        if operand is None:
            continue
        out.append((match.start(), operand[1], WRITE_REASON))
    return out


def _inplace_matches(masked):
    out = []
    for match in _INPLACE_RE.finditer(masked):
        # The span covers the whole segment, so the operator may be trusted while the
        # file it edits may not: an agent-supplied path inside a committed `sed -i` is
        # still refused.
        out.append((match.start(), _segment_end(masked, match.start()), INPLACE_REASON))
    return out


def _markdown_matches(masked):
    return [
        (m.start(), m.end(), MARKDOWN_REASON) for m in _MARKDOWN_RE.finditer(masked)
    ]


def _forbidden(cmd):
    """Every forbidden construct in the command, with the span it occupies."""
    masked = _mask_quoted(cmd)
    found = []
    found.extend(_read_matches(masked))
    found.extend(_redirect_matches(masked))
    found.extend(_tee_matches(masked))
    found.extend(_inplace_matches(masked))
    found.extend(_markdown_matches(masked))
    found.sort(key=lambda item: item[0])
    return found


def _overlaps(start, end, spans):
    for span_start, span_end in spans or ():
        if start < span_end and span_start < end:
            return True
    return False


def check_command_allowed(cmd):
    """Returns (allowed, reason). `reason` is "OK" when allowed, otherwise the exact
    reason naming the door to use instead.

    The whole-command answer: any forbidden construct anywhere in the command refuses it.
    This is the compatibility API for direct callers, and its behaviour is unchanged.
    """
    stripped = (cmd or "").strip()
    if not stripped:
        return True, "OK"
    for prefix in ALLOWED_PREFIXES:
        if stripped.startswith(prefix):
            return True, "OK"
    for _start, _end, reason in _forbidden(cmd):
        return False, reason
    return True, "OK"


def check_intent_step(cmd, agent_spans):
    """The provenance answer, for one step of a committed intent.

    `agent_spans` is the list of (start, end) character ranges in `cmd` that came from
    the caller's own arguments. A forbidden construct is refused only when it overlaps
    one of them: the estate's own committed text is trusted, the caller's contribution
    is not. Returns (allowed, reason) exactly like `check_command_allowed`.
    """
    stripped = (cmd or "").strip()
    if not stripped:
        return True, "OK"
    for _start, _end, reason in _forbidden(cmd):
        if _overlaps(_start, _end, agent_spans):
            return False, reason
    return True, "OK"
