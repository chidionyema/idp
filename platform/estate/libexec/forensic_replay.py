#!/usr/bin/env python3
"""forensic_replay.py - faithful replay of Pi and Cline file-mutation semantics.

Pure engine: no filesystem access of its own, no transcript parsing, no manifest.
The driver (forensic_extract.py) feeds it recorded tool calls and the state it
has reconstructed so far, and gets back exactly what the runtime would have
written.

Sources of truth:
  Pi   ~/.nvm/versions/node/v22.15.1/lib/node_modules/@earendil-works/
       pi-coding-agent/dist/core/tools/{edit.js,edit-diff.js,write.js,read.js,
       truncate.js,path-utils.js} and dist/utils/text.js
  Cline upstream github.com/cline/cline ->
       sdk/packages/core/src/extensions/tools/executors/{editor.ts,
       apply-patch.ts,apply-patch-parser.ts,line-endings.ts}

Every function that models a runtime call either returns the content the
runtime would have produced, or raises ReplayError with the runtime's own
error message. It never silently repairs, guesses, or partially applies.
"""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "ReplayError",
    "js_trim_end",
    "js_trim",
    "js_count_occurrences",
    "js_index_of",
    "pi_detect_line_ending",
    "pi_normalize_to_lf",
    "pi_restore_line_endings",
    "pi_normalize_for_fuzzy_match",
    "pi_split_bom",
    "pi_fuzzy_find_text",
    "pi_count_occurrences",
    "pi_prepare_edit_arguments",
    "pi_validate_edit_input",
    "pi_apply_edits_to_normalized_content",
    "pi_apply_edit",
    "pi_apply_write",
    "parse_unified_patch",
    "apply_unified_patch",
    "cline_detect_line_ending",
    "cline_normalize_line_endings",
    "cline_normalize_new_file_line_endings",
    "cline_create_line_diff",
    "cline_resolve_file_path",
    "cline_editor_apply",
    "cline_apply_patch_changes",
]


class ReplayError(Exception):
    """The recorded call would have failed at runtime (or could not be replayed)."""


# ---------------------------------------------------------------------------
# JavaScript primitive semantics
# ---------------------------------------------------------------------------

# ECMAScript WhiteSpace + LineTerminator. Note U+FEFF is whitespace in JS but
# not in Python, and Python's str.strip() additionally strips U+001C-U+001F,
# which JS does not. So the trim has to be hand-rolled.
JS_WHITESPACE = (
    "\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)


def js_trim_end(text: str) -> str:
    i = len(text)
    while i > 0 and text[i - 1] in JS_WHITESPACE:
        i -= 1
    return text[:i]


def js_trim(text: str) -> str:
    start, end = 0, len(text)
    while start < end and text[start] in JS_WHITESPACE:
        start += 1
    while end > start and text[end - 1] in JS_WHITESPACE:
        end -= 1
    return text[start:end]


def js_index_of(haystack: str, needle: str) -> int:
    """String.prototype.indexOf. Returns a Python index (same occurrence)."""
    if needle == "":
        return 0
    return haystack.find(needle)


def js_count_occurrences(content: str, needle: str) -> int:
    """`content.split(needle).length - 1` (non-overlapping, JS semantics)."""
    if needle == "":
        return len(content) - 1
    return content.count(needle)


def cline_count_occurrences(content: str, needle: str) -> int:
    """Cline's countOccurrences: an empty needle counts zero occurrences."""
    if needle == "":
        return 0
    return content.count(needle)


# ---------------------------------------------------------------------------
# Pi (pi-coding-agent) semantics
# ---------------------------------------------------------------------------


def pi_detect_line_ending(content: str) -> str:
    crlf_idx = content.find("\r\n")
    lf_idx = content.find("\n")
    if lf_idx == -1:
        return "\n"
    if crlf_idx == -1:
        return "\n"
    return "\r\n" if crlf_idx < lf_idx else "\n"


def pi_normalize_to_lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def pi_restore_line_endings(text: str, ending: str) -> str:
    return text.replace("\n", "\r\n") if ending == "\r\n" else text


_PI_SMART_SINGLE = re.compile("[\u2018\u2019\u201a\u201b]")
_PI_SMART_DOUBLE = re.compile("[\u201c\u201d\u201e\u201f]")
_PI_DASHES = re.compile("[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")
_PI_SPACES = re.compile("[\u00a0\u2002-\u200a\u202f\u205f\u3000]")


def pi_normalize_for_fuzzy_match(text: str) -> str:
    """Exact port of normalizeForFuzzyMatch in edit-diff.js."""
    text = unicodedata.normalize("NFKC", text)
    text = "\n".join(js_trim_end(line) for line in text.split("\n"))
    text = _PI_SMART_SINGLE.sub("'", text)
    text = _PI_SMART_DOUBLE.sub('"', text)
    text = _PI_DASHES.sub("-", text)
    text = _PI_SPACES.sub(" ", text)
    return text


def pi_split_bom(content: str) -> Tuple[str, str]:
    """Exact port of splitBom in utils/text.js."""
    if content.startswith("\\ufeff"):
        return "\\ufeff", content[1:]
    return "", content


_LINE_WITH_ENDING = re.compile(r"[^\n]*\n|[^\n]+")


def _split_lines_with_endings(content: str) -> List[str]:
    return _LINE_WITH_ENDING.findall(content)


def _get_line_spans(content: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    offset = 0
    for line in _split_lines_with_endings(content):
        spans.append((offset, offset + len(line)))
        offset += len(line)
    return spans


def pi_fuzzy_find_text(content: str, old_text: str) -> Dict[str, Any]:
    """Exact port of fuzzyFindText in edit-diff.js."""
    exact_index = js_index_of(content, old_text)
    if exact_index != -1:
        return {
            "found": True,
            "index": exact_index,
            "match_length": len(old_text),
            "used_fuzzy_match": False,
            "content_for_replacement": content,
        }
    fuzzy_content = pi_normalize_for_fuzzy_match(content)
    fuzzy_old_text = pi_normalize_for_fuzzy_match(old_text)
    fuzzy_index = js_index_of(fuzzy_content, fuzzy_old_text)
    if fuzzy_index == -1:
        return {
            "found": False,
            "index": -1,
            "match_length": 0,
            "used_fuzzy_match": False,
            "content_for_replacement": content,
        }
    return {
        "found": True,
        "index": fuzzy_index,
        "match_length": len(fuzzy_old_text),
        "used_fuzzy_match": True,
        "content_for_replacement": fuzzy_content,
    }


def pi_count_occurrences(content: str, old_text: str) -> int:
    """Exact port of countOccurrences in edit-diff.js (fuzzy space)."""
    fuzzy_content = pi_normalize_for_fuzzy_match(content)
    fuzzy_old_text = pi_normalize_for_fuzzy_match(old_text)
    if fuzzy_old_text == "":
        return js_count_occurrences(fuzzy_content, fuzzy_old_text)
    return fuzzy_content.count(fuzzy_old_text)


def _get_replacement_line_range(
    lines: Sequence[Tuple[int, int]], match_index: int, match_length: int
) -> Dict[str, int]:
    replacement_start = match_index
    replacement_end = match_index + match_length
    start_line = -1
    for i, (line_start, line_end) in enumerate(lines):
        if replacement_start >= line_start and replacement_start < line_end:
            start_line = i
            break
    if start_line == -1:
        raise ReplayError("Replacement range is outside the base content.")
    end_line = start_line
    while end_line < len(lines) and lines[end_line][1] < replacement_end:
        end_line += 1
    if end_line >= len(lines):
        raise ReplayError("Replacement range is outside the base content.")
    return {"start_line": start_line, "end_line": end_line + 1}


def _apply_replacements(
    content: str, replacements: Sequence[Dict[str, Any]], offset: int = 0
) -> str:
    result = content
    for i in range(len(replacements) - 1, -1, -1):
        replacement = replacements[i]
        match_index = replacement["match_index"] - offset
        result = (
            result[:match_index]
            + replacement["new_text"]
            + result[match_index + replacement["match_length"] :]
        )
    return result


def _apply_replacements_preserving_unchanged_lines(
    original_content: str, base_content: str, replacements: Sequence[Dict[str, Any]]
) -> str:
    original_lines = _split_lines_with_endings(original_content)
    base_lines = _get_line_spans(base_content)
    if len(original_lines) != len(base_lines):
        raise ReplayError(
            "Cannot preserve unchanged lines because the base content has a different line count."
        )
    groups: List[Dict[str, Any]] = []
    sorted_replacements = sorted(replacements, key=lambda r: r["match_index"])
    for replacement in sorted_replacements:
        rng = _get_replacement_line_range(
            base_lines, replacement["match_index"], replacement["match_length"]
        )
        current = groups[-1] if groups else None
        if current and rng["start_line"] < current["end_line"]:
            current["end_line"] = max(current["end_line"], rng["end_line"])
            current["replacements"].append(replacement)
            continue
        groups.append(
            {
                "start_line": rng["start_line"],
                "end_line": rng["end_line"],
                "replacements": [replacement],
            }
        )
    original_line_index = 0
    result = ""
    for group in groups:
        result += "".join(original_lines[original_line_index : group["start_line"]])
        group_start_offset = base_lines[group["start_line"]][0]
        group_end_offset = base_lines[group["end_line"] - 1][1]
        result += _apply_replacements(
            base_content[group_start_offset:group_end_offset],
            group["replacements"],
            group_start_offset,
        )
        original_line_index = group["end_line"]
    result += "".join(original_lines[original_line_index:])
    return result


def _pi_not_found_error(path: str, edit_index: int, total_edits: int) -> str:
    if total_edits == 1:
        return (
            f"Could not find the exact text in {path}. The old text must match "
            "exactly including all whitespace and newlines."
        )
    return (
        f"Could not find edits[{edit_index}] in {path}. The oldText must match "
        "exactly including all whitespace and newlines."
    )


def _pi_duplicate_error(
    path: str, edit_index: int, total_edits: int, occurrences: int
) -> str:
    if total_edits == 1:
        return (
            f"Found {occurrences} occurrences of the text in {path}. The text must "
            "be unique. Please provide more context to make it unique."
        )
    return (
        f"Found {occurrences} occurrences of edits[{edit_index}] in {path}. Each "
        "oldText must be unique. Please provide more context to make it unique."
    )


def _pi_empty_old_text_error(path: str, edit_index: int, total_edits: int) -> str:
    if total_edits == 1:
        return f"oldText must not be empty in {path}."
    return f"edits[{edit_index}].oldText must not be empty in {path}."


def _pi_no_change_error(path: str, total_edits: int) -> str:
    if total_edits == 1:
        return (
            f"No changes made to {path}. The replacement produced identical content. "
            "This might indicate an issue with special characters or the text not "
            "existing as expected."
        )
    return f"No changes made to {path}. The replacements produced identical content."


def pi_apply_edits_to_normalized_content(
    normalized_content: str, edits: Sequence[Dict[str, Any]], path: str
) -> Dict[str, str]:
    """Exact port of applyEditsToNormalizedContent in edit-diff.js."""
    normalized_edits = []
    for edit in edits:
        if not isinstance(edit, dict):
            raise ReplayError(f"Invalid edit entry in {path}: not an object.")
        old_text = edit.get("oldText")
        new_text = edit.get("newText")
        if not isinstance(old_text, str) or not isinstance(new_text, str):
            raise ReplayError(
                f"Invalid edit entry in {path}: oldText and newText must be strings "
                f"(got {type(old_text).__name__} and {type(new_text).__name__})."
            )
        normalized_edits.append(
            {
                "oldText": pi_normalize_to_lf(old_text),
                "newText": pi_normalize_to_lf(new_text),
            }
        )
    for i, edit in enumerate(normalized_edits):
        if len(edit["oldText"]) == 0:
            raise ReplayError(_pi_empty_old_text_error(path, i, len(normalized_edits)))

    initial_matches = [
        pi_fuzzy_find_text(normalized_content, e["oldText"]) for e in normalized_edits
    ]
    used_fuzzy_match = any(m["used_fuzzy_match"] for m in initial_matches)
    replacement_base_content = (
        pi_normalize_for_fuzzy_match(normalized_content)
        if used_fuzzy_match
        else normalized_content
    )

    matched_edits: List[Dict[str, Any]] = []
    for i, edit in enumerate(normalized_edits):
        match_result = pi_fuzzy_find_text(replacement_base_content, edit["oldText"])
        if not match_result["found"]:
            raise ReplayError(_pi_not_found_error(path, i, len(normalized_edits)))
        occurrences = pi_count_occurrences(replacement_base_content, edit["oldText"])
        if occurrences > 1:
            raise ReplayError(
                _pi_duplicate_error(path, i, len(normalized_edits), occurrences)
            )
        matched_edits.append(
            {
                "editIndex": i,
                "match_index": match_result["index"],
                "match_length": match_result["match_length"],
                "new_text": edit["newText"],
            }
        )

    matched_edits.sort(key=lambda m: m["match_index"])
    for i in range(1, len(matched_edits)):
        previous = matched_edits[i - 1]
        current = matched_edits[i]
        if previous["match_index"] + previous["match_length"] > current["match_index"]:
            raise ReplayError(
                f"edits[{previous['editIndex']}] and edits[{current['editIndex']}] overlap "
                f"in {path}. Merge them into one edit or target disjoint regions."
            )

    base_content = normalized_content
    new_content = (
        _apply_replacements_preserving_unchanged_lines(
            normalized_content, replacement_base_content, matched_edits
        )
        if used_fuzzy_match
        else _apply_replacements(replacement_base_content, matched_edits)
    )
    if base_content == new_content:
        raise ReplayError(_pi_no_change_error(path, len(normalized_edits)))
    return {"base_content": base_content, "new_content": new_content}


def _is_single_edit_input(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return isinstance(value.get("oldText"), str) and isinstance(
        value.get("newText"), str
    )


def pi_prepare_edit_arguments(args: Any) -> Any:
    """Exact port of prepareEditArguments in edit.js."""
    if not isinstance(args, dict):
        return args
    args = dict(args)
    edits = args.get("edits")
    if isinstance(edits, str):
        try:
            parsed = json.loads(edits)
        except Exception:
            parsed = None
        if isinstance(parsed, list):
            args["edits"] = parsed
        elif _is_single_edit_input(parsed):
            args["edits"] = [parsed]
    elif _is_single_edit_input(edits):
        args["edits"] = [edits]

    legacy = args
    if not isinstance(legacy.get("oldText"), str) or not isinstance(
        legacy.get("newText"), str
    ):
        return args
    legacy_edits = (
        list(legacy["edits"]) if isinstance(legacy.get("edits"), list) else []
    )
    legacy_edits.append({"oldText": legacy["oldText"], "newText": legacy["newText"]})
    rest = {k: v for k, v in legacy.items() if k not in ("oldText", "newText")}
    rest["edits"] = legacy_edits
    return rest


def pi_validate_edit_input(args: Any) -> Dict[str, Any]:
    """Exact port of validateEditInput in edit.js."""
    edits = args.get("edits") if isinstance(args, dict) else None
    if not isinstance(edits, list) or len(edits) == 0:
        raise ReplayError(
            "Edit tool input is invalid. edits must contain at least one replacement."
        )
    return {"path": args.get("path"), "edits": edits}


def pi_apply_edit(base_text: str, args: Any, path: str) -> Dict[str, Any]:
    """Replay one Pi `edit` call against a known base file content.

    base_text is the file content before the call (as text, BOM included).
    Returns the file content the runtime would have written.
    """
    prepared = pi_prepare_edit_arguments(args)
    validated = pi_validate_edit_input(prepared)
    bom, content = pi_split_bom(base_text)
    original_ending = pi_detect_line_ending(content)
    normalized_content = pi_normalize_to_lf(content)
    result = pi_apply_edits_to_normalized_content(
        normalized_content, validated["edits"], path
    )
    final_content = bom + pi_restore_line_endings(
        result["new_content"], original_ending
    )
    return {
        "content": final_content,
        "base_content": result["base_content"],
        "new_content": result["new_content"],
        "bom": bom,
        "original_ending": original_ending,
        "edits_applied": len(validated["edits"]),
    }


def pi_apply_write(content: Any) -> str:
    """Replay one Pi `write` call: the content is written verbatim."""
    if not isinstance(content, str):
        raise ReplayError("Write tool input is invalid. content must be a string.")
    return content


# ---------------------------------------------------------------------------
# Unified diff (jsdiff createTwoFilesPatch) applier
# ---------------------------------------------------------------------------

_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse_unified_patch(patch_text: str) -> List[Dict[str, Any]]:
    """Parse a jsdiff createTwoFilesPatch output into hunks."""
    if not isinstance(patch_text, str):
        raise ReplayError("Patch is not a string.")
    lines = _split_lines_with_endings(patch_text)
    hunks: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for line in lines:
        if line.startswith("@@"):
            match = _HUNK_HEADER.match(line)
            if not match:
                raise ReplayError(f"Unparseable hunk header: {line.strip()!r}")
            current = {
                "old_start": int(match.group(1)),
                "old_count": int(match.group(2)) if match.group(2) is not None else 1,
                "new_start": int(match.group(3)),
                "new_count": int(match.group(4)) if match.group(4) is not None else 1,
                "lines": [],
            }
            hunks.append(current)
            continue
        if current is None:
            continue
        body = line
        if body.startswith("\\"):  # "\ No newline at end of file"
            continue
        if body == "":
            current["lines"].append((" ", ""))
            continue
        tag = body[0]
        if tag in (" ", "-", "+"):
            current["lines"].append((tag, body[1:]))
            continue
        # Anything else ends the patch body.
        break
    return hunks


def _locate_sequence(
    base_lines: Sequence[str], needle: Sequence[str], expected: int
) -> int:
    if not needle:
        return max(0, min(expected, len(base_lines)))
    n = len(needle)
    limit = len(base_lines) - n
    # near search
    for delta in range(0, 400):
        for cand in (expected - delta, expected + delta):
            if 0 <= cand <= limit and list(base_lines[cand : cand + n]) == list(needle):
                return cand
    # whole file search
    for i in range(0, limit + 1):
        if list(base_lines[i : i + n]) == list(needle):
            return i
    return -1


def apply_unified_patch(base_text: str, patch_text: str) -> str:
    """Apply a jsdiff createTwoFilesPatch to base_text and return the result.

    The base is expected to be LF-normalized and BOM-free, exactly like the
    content Pi diffs against. Raises ReplayError when the patch does not apply.
    """
    hunks = parse_unified_patch(patch_text)
    base_lines = _split_lines_with_endings(base_text)
    out: List[str] = []
    cursor = 0
    for hunk in hunks:
        old_side = [text for tag, text in hunk["lines"] if tag in (" ", "-")]
        new_side = [text for tag, text in hunk["lines"] if tag in (" ", "+")]
        expected = max(hunk["old_start"] - 1, 0)
        pos = _locate_sequence(base_lines, old_side, expected)
        if pos < 0:
            raise ReplayError(
                "Patch does not apply to the candidate base content "
                f"(hunk at old line {hunk['old_start']})."
            )
        out.extend(base_lines[cursor:pos])
        out.extend(new_side)
        cursor = pos + len(old_side)
    out.extend(base_lines[cursor:])
    return "".join(out)


# ---------------------------------------------------------------------------
# Cline semantics
# ---------------------------------------------------------------------------


def cline_detect_line_ending(content: str) -> str:
    return "\r\n" if "\r\n" in content else "\n"


def cline_normalize_line_endings(text: str, eol: str) -> str:
    return re.sub(r"\r\n|\n", eol, text)


def cline_normalize_new_file_line_endings(content: str) -> str:
    """normalizeNewFileLineEndings - a no-op on macOS/Linux (os.EOL == "\\n")."""
    return content


def cline_create_line_diff(
    old_content: str, new_content: str, max_lines: int = 200
) -> str:
    """Exact port of createLineDiff in the upstream Cline editor executor."""
    old_lines = re.split(r"\r\n|\n", old_content)
    new_lines = re.split(r"\r\n|\n", new_content)

    start = 0
    while (
        start < len(old_lines)
        and start < len(new_lines)
        and old_lines[start] == new_lines[start]
    ):
        start += 1
    old_end = len(old_lines)
    new_end = len(new_lines)
    while (
        old_end > start
        and new_end > start
        and old_lines[old_end - 1] == new_lines[new_end - 1]
    ):
        old_end -= 1
        new_end -= 1

    removed_count = old_end - start
    added_count = new_end - start
    removed_budget = removed_count
    added_budget = added_count
    if removed_count + added_count > max_lines:
        removed_budget = min(
            removed_count, max(math.ceil(max_lines / 2), max_lines - added_count)
        )
        added_budget = min(added_count, max_lines - removed_budget)

    out = ["```diff"]
    for i in range(start, start + removed_budget):
        out.append(f"-{i + 1}: {old_lines[i]}")
    for i in range(start, start + added_budget):
        out.append(f"+{i + 1}: {new_lines[i]}")

    omitted_removed = removed_count - removed_budget
    omitted_added = added_count - added_budget
    if omitted_removed > 0 or omitted_added > 0:
        out.append(
            f"... diff truncated ({omitted_removed} more removed, "
            f"{omitted_added} more added lines) ..."
        )
    out.append("```")
    return "\n".join(out)


def cline_resolve_file_path(
    cwd: str, input_path: str, restrict_to_cwd: bool = True
) -> str:
    """Exact port of resolveFilePath (editor + apply_patch)."""
    if not isinstance(input_path, str) or not input_path:
        raise ReplayError("Path is required.")
    if os.path.isabs(input_path):
        resolved = os.path.normpath(input_path)
    else:
        resolved = os.path.normpath(os.path.join(cwd or os.getcwd(), input_path))
    if not restrict_to_cwd or os.path.isabs(input_path):
        return resolved
    rel = os.path.relpath(resolved, cwd or os.getcwd())
    if rel.startswith("..") or os.path.isabs(rel):
        raise ReplayError(f"Path must stay within cwd: {input_path}")
    return resolved


def cline_editor_apply(
    input_args: Dict[str, Any], cwd: str, fs_read, max_diff_lines: int = 200
) -> Dict[str, Any]:
    """Replay one Cline `editor` call.

    fs_read(absolute_path) returns the current file content as text, or None
    when the file does not exist. Returns a dict with the resulting content and
    the message the runtime would have returned.
    """
    path = input_args.get("path")
    file_path = cline_resolve_file_path(cwd, path, True)
    insert_line = input_args.get("insert_line")

    if insert_line is not None:
        content = fs_read(file_path)
        if content is None:
            raise ReplayError(f"ENOENT: no such file or directory, open '{file_path}'")
        eol = cline_detect_line_ending(content)
        lines = re.split(r"\r\n|\n", content)
        max_boundary_line = len(lines) + 1
        if (
            not isinstance(insert_line, int)
            or isinstance(insert_line, bool)
            or insert_line < 1
            or insert_line > max_boundary_line
        ):
            raise ReplayError(
                f"Invalid insert_line: {insert_line}. insert_line must be a positive "
                f"one-based boundary line in the range 1-{max_boundary_line}. "
                f"Use {max_boundary_line} to append at EOF."
            )
        new_text = input_args.get("new_text")
        if not isinstance(new_text, str):
            raise ReplayError("new_text must be a string for insert_line.")
        insert_index = insert_line - 1
        lines[insert_index:insert_index] = re.split(r"\r\n|\n", new_text)
        updated = eol.join(lines)
        return {
            "action": "insert",
            "path": file_path,
            "content": updated,
            "message": f"Inserted content at line {insert_line} in {file_path}.",
            "diff": None,
        }

    content = fs_read(file_path)
    if content is None:
        new_text = input_args.get("new_text")
        if not isinstance(new_text, str):
            raise ReplayError(f"Cannot create {file_path} with no content")
        return {
            "action": "create",
            "path": file_path,
            "content": cline_normalize_new_file_line_endings(new_text),
            "message": f"File created successfully at: {file_path}",
            "diff": None,
        }

    if input_args.get("old_text") is None:
        state = "null" if input_args.get("old_text", "missing") is None else "omitted"
        raise ReplayError(
            f"{file_path} already exists, but `old_text` was {state}. To edit an existing "
            "file, set `old_text` to the exact text in the file that `new_text` should "
            "replace (read the file first if needed). To insert instead, provide "
            "`insert_line`. Do not re-send this call unchanged."
        )

    old_str = input_args["old_text"]
    if not isinstance(old_str, str):
        raise ReplayError("old_text must be a string.")
    eol = cline_detect_line_ending(content)
    normalized_old_str = cline_normalize_line_endings(old_str, eol)
    new_text = input_args.get("new_text")
    normalized_new_str = cline_normalize_line_endings(
        new_text if isinstance(new_text, str) else "", eol
    )

    occurrences = cline_count_occurrences(content, normalized_old_str)
    if occurrences == 0:
        raise ReplayError(f"No replacement performed: text not found in {file_path}.")
    if occurrences > 1:
        raise ReplayError(
            f"No replacement performed: multiple occurrences of text found in {file_path}."
        )

    index = content.find(normalized_old_str)
    updated = (
        content[:index]
        + normalized_new_str
        + content[index + len(normalized_old_str) :]
    )
    diff = cline_create_line_diff(content, updated, max_diff_lines)
    return {
        "action": "replace",
        "path": file_path,
        "content": updated,
        "message": f"Edited {file_path}\n{diff}",
        "diff": diff,
    }


# --- Cline apply_patch -----------------------------------------------------

PATCH_BEGIN = "*** Begin Patch"
PATCH_END = "*** End Patch"
PATCH_ADD = "*** Add File: "
PATCH_UPDATE = "*** Update File: "
PATCH_DELETE = "*** Delete File: "
PATCH_MOVE = "*** Move to: "
PATCH_END_FILE = "*** End of File"
BASH_WRAPPERS = ("%%bash", "apply_patch", "EOF", "```")

_CLINE_PUNCTUATION = {
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u00ab": '"',
    "\u00bb": '"',
    "\u2018": "'",
    "\u2019": "'",
    "\u201b": "'",
    "\u00a0": " ",
    "\u202f": " ",
}


def cline_canonicalize(text: str) -> str:
    """Exact port of canonicalize in apply-patch-parser.ts."""
    text = unicodedata.normalize("NFC", text)
    text = "".join(_CLINE_PUNCTUATION.get(ch, ch) for ch in text)
    text = text.replace("\\`", "`").replace("\\'", "'").replace('\\"', '"')
    return text


def _cline_split_patch_input_lines(input_text: str) -> List[str]:
    return [re.sub(r"\r$", "", line) for line in input_text.split("\n")]


def _cline_is_wrapper_line(line: str) -> bool:
    if line.strip() == "":
        return False
    return any(line.startswith(wrapper) for wrapper in BASH_WRAPPERS)


def _cline_trim_wrapper_lines(lines: List[str]) -> List[str]:
    start, end = 0, len(lines)
    while start < end and _cline_is_wrapper_line(lines[start]):
        start += 1
    while end > start and _cline_is_wrapper_line(lines[end - 1]):
        end -= 1
    return lines[start:end]


def cline_normalize_patch_input(input_text: str) -> List[str]:
    """Exact port of normalizePatchInput."""
    raw_lines = _cline_split_patch_input_lines(input_text)
    begin_index = -1
    for i, line in enumerate(raw_lines):
        if line.startswith(PATCH_BEGIN):
            begin_index = i
            break
    end_index = -1
    for i in range(len(raw_lines) - 1, -1, -1):
        if raw_lines[i].startswith(PATCH_END):
            end_index = i
            break
    if begin_index != -1 or end_index != -1:
        if begin_index == -1 or end_index == -1 or end_index < begin_index:
            raise ReplayError(
                "Invalid patch text - incomplete sentinels. Try breaking it into smaller patches."
            )
        return raw_lines[begin_index : end_index + 1]
    stripped = _cline_trim_wrapper_lines(raw_lines)
    while stripped and stripped[0] == "":
        stripped.pop(0)
    while stripped and stripped[-1] == "":
        stripped.pop()
    return [PATCH_BEGIN] + stripped + [PATCH_END]


def _cline_levenshtein(str1: str, str2: str) -> int:
    rows = len(str2) + 1
    cols = len(str1) + 1
    matrix = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        matrix[i][0] = i
    for j in range(cols):
        matrix[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            if str2[i - 1] == str1[j - 1]:
                matrix[i][j] = matrix[i - 1][j - 1]
            else:
                matrix[i][j] = 1 + min(
                    matrix[i - 1][j - 1], matrix[i][j - 1], matrix[i - 1][j]
                )
    return matrix[len(str2)][len(str1)]


def _cline_similarity(str1: str, str2: str) -> float:
    longer = str1 if len(str1) > len(str2) else str2
    shorter = str2 if len(str1) > len(str2) else str1
    if len(longer) == 0:
        return 1.0
    distance = _cline_levenshtein(shorter, longer)
    return (len(longer) - distance) / len(longer)


def _cline_find_context(
    lines: List[str], context: List[str], start: int, eof: bool
) -> Tuple[int, int, float]:
    if not context:
        return start, 0, 1.0
    best_similarity = 0.0

    def find_core(start_idx: int) -> Tuple[int, int, float]:
        nonlocal best_similarity
        canonical_context = cline_canonicalize("\n".join(context))
        for i in range(start_idx, len(lines)):
            segment = cline_canonicalize("\n".join(lines[i : i + len(context)]))
            if segment == canonical_context:
                return i, 0, 1.0
            similarity = _cline_similarity(segment, canonical_context)
            if similarity > best_similarity:
                best_similarity = similarity
        canonical_trimmed = cline_canonicalize(
            "\n".join(js_trim_end(line) for line in context)
        )
        for i in range(start_idx, len(lines)):
            segment = cline_canonicalize(
                "\n".join(js_trim_end(line) for line in lines[i : i + len(context)])
            )
            if segment == canonical_trimmed:
                return i, 1, 1.0
        canonical_trimmed2 = cline_canonicalize(
            "\n".join(js_trim(line) for line in context)
        )
        for i in range(start_idx, len(lines)):
            segment = cline_canonicalize(
                "\n".join(js_trim(line) for line in lines[i : i + len(context)])
            )
            if segment == canonical_trimmed2:
                return i, 100, 1.0
        threshold = 0.66
        for i in range(start_idx, len(lines)):
            segment = cline_canonicalize("\n".join(lines[i : i + len(context)]))
            similarity = _cline_similarity(segment, canonical_context)
            if similarity >= threshold:
                return i, 1000, similarity
            if similarity > best_similarity:
                best_similarity = similarity
        return -1, 0, best_similarity

    if eof:
        new_index, fuzz, similarity = find_core(max(0, len(lines) - len(context)))
        if new_index != -1:
            return new_index, fuzz, similarity
        new_index, fuzz, similarity = find_core(start)
        return new_index, fuzz + 10000, similarity
    return find_core(start)


def _cline_peek(lines: List[str], initial_index: int):
    index = initial_index
    old: List[str] = []
    del_lines: List[str] = []
    ins_lines: List[str] = []
    chunks: List[Dict[str, Any]] = []
    mode = "keep"
    stop_markers = (
        "@@",
        PATCH_END,
        PATCH_UPDATE,
        PATCH_DELETE,
        PATCH_ADD,
        PATCH_END_FILE,
    )

    while index < len(lines):
        source_line = lines[index]
        if not source_line or any(
            source_line.startswith(m.strip()) for m in stop_markers
        ):
            break
        if source_line == "***":
            break
        if source_line.startswith("***"):
            raise ReplayError(f"Invalid line: {source_line}")
        index += 1
        previous_mode = mode
        line = source_line
        if line[0] == "+":
            mode = "add"
        elif line[0] == "-":
            mode = "delete"
        elif line[0] == " ":
            mode = "keep"
        else:
            mode = "keep"
            line = " " + line
        line = line[1:]
        if mode == "keep" and previous_mode != mode:
            if ins_lines or del_lines:
                chunks.append(
                    {
                        "origIndex": len(old) - len(del_lines),
                        "delLines": del_lines,
                        "insLines": ins_lines,
                    }
                )
            del_lines = []
            ins_lines = []
        if mode == "delete":
            del_lines.append(line)
            old.append(line)
        elif mode == "add":
            ins_lines.append(line)
        else:
            old.append(line)

    if ins_lines or del_lines:
        chunks.append(
            {
                "origIndex": len(old) - len(del_lines),
                "delLines": del_lines,
                "insLines": ins_lines,
            }
        )

    if index < len(lines) and lines[index] == PATCH_END_FILE:
        index += 1
        return old, chunks, index, True
    return old, chunks, index, False


class _ClinePatchParser:
    """Exact port of PatchParser in apply-patch-parser.ts."""

    def __init__(self, lines: List[str], current_files: Dict[str, str]):
        self.lines = lines
        self.current_files = current_files
        self.actions: Dict[str, Dict[str, Any]] = {}
        self.warnings: List[Dict[str, Any]] = []
        self.index = 0
        self.fuzz = 0
        self.current_path: Optional[str] = None

    def parse(self) -> Dict[str, Any]:
        self._skip_begin_sentinel()
        while self._has_more_lines() and not self._is_end_marker():
            self._parse_next_action()
        return {"actions": self.actions, "warnings": self.warnings, "fuzz": self.fuzz}

    def _add_warning(self, warning: Dict[str, Any]) -> None:
        self.warnings.append(warning)

    def _skip_begin_sentinel(self) -> None:
        if self.index < len(self.lines) and self.lines[self.index].startswith(
            PATCH_BEGIN
        ):
            self.index += 1

    def _has_more_lines(self) -> bool:
        return self.index < len(self.lines)

    def _is_end_marker(self) -> bool:
        return self.index < len(self.lines) and self.lines[self.index].startswith(
            PATCH_END
        )

    def _parse_next_action(self) -> None:
        line = self.lines[self.index] if self.index < len(self.lines) else None
        if line is not None and line.startswith(PATCH_UPDATE):
            self._parse_update(line[len(PATCH_UPDATE) :].strip())
            return
        if line is not None and line.startswith(PATCH_DELETE):
            self._parse_delete(line[len(PATCH_DELETE) :].strip())
            return
        if line is not None and line.startswith(PATCH_ADD):
            self._parse_add(line[len(PATCH_ADD) :].strip())
            return
        raise ReplayError(f"Unknown line while parsing: {line}")

    def _check_duplicate(self, path: str, operation: str) -> None:
        if path in self.actions:
            raise ReplayError(f"Duplicate {operation} for file: {path}")

    def _parse_update(self, path: str) -> None:
        self._check_duplicate(path, "update")
        self.current_path = path
        self.index += 1
        move_path = None
        if self.index < len(self.lines) and self.lines[self.index].startswith(
            PATCH_MOVE
        ):
            self.index += 1
            move_path = (
                self.lines[self.index] if self.index < len(self.lines) else ""
            )[len(PATCH_MOVE) :].strip()
            self.index += 1
        if path not in self.current_files:
            raise ReplayError(f"Update File Error: Missing File: {path}")
        text = self.current_files.get(path, "")
        action = self._parse_update_file(text, path)
        action["move_path"] = move_path
        self.actions[path] = action
        self.current_path = None

    def _parse_update_file(self, text: str, path: str) -> Dict[str, Any]:
        action: Dict[str, Any] = {"type": "update", "chunks": []}
        file_lines = text.split("\n")
        index = 0
        stop_markers = (
            PATCH_END,
            PATCH_UPDATE,
            PATCH_DELETE,
            PATCH_ADD,
            PATCH_END_FILE,
        )

        while True:
            if self.index >= len(self.lines):
                break
            if any(self.lines[self.index].startswith(m.strip()) for m in stop_markers):
                break
            current_line = self.lines[self.index]
            def_str = current_line[3:] if current_line.startswith("@@ ") else None
            section_str = current_line if current_line == "@@" else None

            if def_str is not None or section_str is not None:
                self.index += 1
            elif index != 0:
                raise ReplayError(f"Invalid Line:\n{self.lines[self.index]}")

            if def_str and def_str.strip():
                canon_def_str = cline_canonicalize(def_str.strip())
                for i in range(index, len(file_lines)):
                    file_line = file_lines[i]
                    if file_line and (
                        cline_canonicalize(file_line) == canon_def_str
                        or cline_canonicalize(file_line.strip()) == canon_def_str
                    ):
                        index = i + 1
                        if (
                            cline_canonicalize(file_line.strip()) == canon_def_str
                            and cline_canonicalize(file_line) != canon_def_str
                        ):
                            self.fuzz += 1
                        break

            next_chunk_context, chunks, end_patch_index, eof = _cline_peek(
                self.lines, self.index
            )
            new_index, fuzz, similarity = _cline_find_context(
                file_lines, next_chunk_context, index, eof
            )

            if new_index == -1:
                context_text = "\n".join(next_chunk_context)
                self._add_warning(
                    {
                        "path": self.current_path or path,
                        "chunkIndex": len(action["chunks"]),
                        "message": (
                            f"Could not find matching context (similarity: "
                            f"{similarity:.2f}). Chunk skipped."
                        ),
                        "context": (context_text[:200] + "...")
                        if len(context_text) > 200
                        else context_text,
                    }
                )
                self.index = end_patch_index
            else:
                self.fuzz += fuzz
                for chunk in chunks:
                    chunk["origIndex"] += new_index
                    action["chunks"].append(chunk)
                index = new_index + len(next_chunk_context)
                self.index = end_patch_index
        return action

    def _parse_delete(self, path: str) -> None:
        self._check_duplicate(path, "delete")
        if path not in self.current_files:
            raise ReplayError(f"Delete File Error: Missing File: {path}")
        self.actions[path] = {"type": "delete", "chunks": []}
        self.index += 1

    def _parse_add(self, path: str) -> None:
        self._check_duplicate(path, "add")
        if path in self.current_files:
            raise ReplayError(f"Add File Error: File already exists: {path}")
        self.index += 1
        lines: List[str] = []
        stop_markers = (PATCH_END, PATCH_UPDATE, PATCH_DELETE, PATCH_ADD)
        while self.index < len(self.lines):
            if any(self.lines[self.index].startswith(m.strip()) for m in stop_markers):
                break
            line = self.lines[self.index]
            self.index += 1
            if not line.startswith("+"):
                raise ReplayError(f"Invalid Add File line (missing '+'): {line}")
            lines.append(line[1:])
        self.actions[path] = {
            "type": "add",
            "newFile": "\n".join(lines),
            "chunks": [],
        }


def _cline_apply_chunks(
    content: str, chunks: List[Dict[str, Any]], file_path: str
) -> str:
    if not chunks:
        return content
    lines = content.split("\n")
    result: List[str] = []
    current_index = 0
    for chunk in chunks:
        if chunk["origIndex"] > len(lines):
            raise ReplayError(
                f"{file_path}: chunk.origIndex {chunk['origIndex']} > lines.length {len(lines)}"
            )
        if current_index > chunk["origIndex"]:
            raise ReplayError(
                f"{file_path}: currentIndex {current_index} > chunk.origIndex {chunk['origIndex']}"
            )
        result.extend(lines[current_index : chunk["origIndex"]])
        result.extend(chunk["insLines"])
        current_index = chunk["origIndex"] + len(chunk["delLines"])
    result.extend(lines[current_index:])
    return "\n".join(result)


def cline_format_skipped_hunk_failure(warnings: List[Dict[str, Any]]) -> str:
    lines = [
        f"Patch could not be applied because {len(warnings)} hunk"
        f"{'' if len(warnings) == 1 else 's'} did not match the current file content."
    ]
    for warning in warnings:
        hunk_number = (
            "unknown"
            if warning.get("chunkIndex") is None
            else str(warning["chunkIndex"] + 1)
        )
        lines.append(f"{warning['path']}: hunk {hunk_number}: {warning['message']}")
        if warning.get("context"):
            lines.append(f"Context:\n{warning['context']}")
    return "\n".join(lines)


def cline_apply_patch_changes(
    patch_text: str, cwd: str, fs_read, restrict_to_cwd: bool = True
) -> Dict[str, Any]:
    """Replay one Cline `apply_patch` call.

    fs_read(absolute_path) returns the current content or None when absent.
    Returns {"changes": {path: {...}}, "fuzz": int, "touched": [str]}.
    """
    lines = cline_normalize_patch_input(patch_text)

    files: Dict[str, str] = {}
    eols: Dict[str, str] = {}
    resolved: Dict[str, str] = {}

    for marker in (PATCH_UPDATE, PATCH_DELETE):
        for line in lines:
            if line.startswith(marker):
                file_path = line[len(marker) :].strip()
                if file_path in files:
                    continue
                absolute = cline_resolve_file_path(cwd, file_path, restrict_to_cwd)
                content = fs_read(absolute)
                if content is None:
                    raise ReplayError(f"File not found: {file_path}")
                files[file_path] = content.replace("\r\n", "\n")
                eols[file_path] = cline_detect_line_ending(content)
                resolved[file_path] = absolute

    for line in lines:
        if line.startswith(PATCH_ADD):
            file_path = line[len(PATCH_ADD) :].strip()
            if file_path in files:
                continue
            absolute = cline_resolve_file_path(cwd, file_path, restrict_to_cwd)
            content = fs_read(absolute)
            if content is not None:
                files[file_path] = content
                eols[file_path] = cline_detect_line_ending(content)
                resolved[file_path] = absolute

    parser = _ClinePatchParser(lines, files)
    parsed = parser.parse()
    if parsed["warnings"]:
        raise ReplayError(cline_format_skipped_hunk_failure(parsed["warnings"]))

    changes: Dict[str, Dict[str, Any]] = {}
    for file_path, action in parsed["actions"].items():
        if action["type"] == "delete":
            changes[file_path] = {
                "type": "delete",
                "old_content": cline_normalize_line_endings(
                    files.get(file_path, ""), eols.get(file_path, "\n")
                ),
                "new_content": None,
                "move_path": None,
                "absolute_path": resolved.get(file_path),
            }
        elif action["type"] == "add":
            changes[file_path] = {
                "type": "add",
                "old_content": None,
                "new_content": cline_normalize_new_file_line_endings(action["newFile"]),
                "move_path": None,
                "absolute_path": resolved.get(file_path)
                or cline_resolve_file_path(cwd, file_path, restrict_to_cwd),
            }
        else:
            original = files.get(file_path, "")
            changes[file_path] = {
                "type": "update",
                "old_content": cline_normalize_line_endings(
                    original, eols.get(file_path, "\n")
                ),
                "new_content": cline_normalize_line_endings(
                    _cline_apply_chunks(original, action["chunks"], file_path),
                    eols.get(file_path, "\n"),
                ),
                "move_path": action.get("move_path"),
                "absolute_path": resolved.get(file_path),
            }

    touched: List[str] = []
    for file_path, change in changes.items():
        if change["type"] == "delete":
            touched.append(f"{file_path}: [deleted]")
        elif change["type"] == "add":
            touched.append(file_path)
        else:
            if change.get("move_path"):
                touched.append(f"{file_path} -> {change['move_path']}")
            else:
                touched.append(file_path)

    return {"changes": changes, "fuzz": parsed["fuzz"], "touched": touched}
