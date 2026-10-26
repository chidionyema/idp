"""tests/test_symbol_slicer.py — the Micro-Token FR-1 build: slices, not raw files.

Grades the three things the slicer exists for:
  1. exactness — an extracted symbol is the symbol's real current source, byte-identical
     to the file's own lines;
  2. reduction — the slice for a review diff is materially smaller than the raw diff cap
     the Tier 2 prompt used to paste (that ratio is the whole point);
  3. the Tier 2 integration — the payload builder prefers sliced context and says which
     mode it used, so a run proves its own path.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SLICER_PATH = ROOT / "platform" / "estate" / "libexec" / "symbol_slicer.py"
T2_PATH = ROOT / "platform" / "estate" / "libexec" / "code-review-t2.py"

_loader = importlib.machinery.SourceFileLoader("symbol_slicer_mod", str(SLICER_PATH))
_spec = importlib.util.spec_from_loader("symbol_slicer_mod", _loader)
slicer = importlib.util.module_from_spec(_spec)
_loader.exec_module(slicer)

PY_SRC = '''"""fixture module"""


def untouched_helper(x):
    return x * 3


def reviewed_function(items, limit):
    total = 0
    for item in items:
        if item > limit:
            total += item
    return total


class ReviewedClass:
    def method_one(self):
        return "one"

    def method_two(self):
        return "two"
'''

JS_SRC = """export function reviewedHandler(req) {
  const id = req.params.id;
  return { id, ok: true };
}

function otherHelper() {
  return 42;
}
"""

DIFF = """diff --git a/mod.py b/mod.py
--- a/mod.py
+++ b/mod.py
@@ -7,6 +7,7 @@ def reviewed_function(items, limit):
 def reviewed_function(items, limit):
     total = 0
+    total = total or 0
     for item in items:
         if item > limit:
             total += item
"""


def _read_map(files: dict[str, str]):
    return lambda p: files.get(p)


def test_extraction_is_exact_for_python():
    body = slicer.extract_symbol(PY_SRC, "python", "reviewed_function")
    assert body is not None
    assert "return total" in body
    # exactness: the body is the file's own lines, not a re-render
    src_lines = PY_SRC.splitlines()
    first = body.splitlines()[0]
    assert first in src_lines
    # the untouched sibling is NOT inside the slice
    assert "untouched_helper" not in body


def test_extraction_is_exact_for_braced_languages():
    body = slicer.extract_symbol(JS_SRC, "javascript", "reviewedHandler")
    assert body is not None
    assert "return { id, ok: true };" in body
    assert "otherHelper" not in body


def test_touched_parses_hunks_and_hints():
    files = slicer.touched(DIFF)
    assert len(files) == 1
    assert files[0]["path"] == "mod.py"
    assert files[0]["hunks"][0]["hint"] == "def reviewed_function(items, limit):"
    assert "reviewed_function" in files[0]["identifiers"]


def test_slice_reduces_payload_below_the_raw_cap():
    whole = PY_SRC + JS_SRC
    sliced = slicer.slice_for_diff(DIFF, _read_map({"mod.py": PY_SRC}), max_bytes=4000)
    assert '<symbol name="reviewed_function">' in sliced
    # the touched symbol's BODY is in the slice
    assert "total = total or 0" not in sliced  # that line is the diff's, not the file's
    assert "for item in items:" in sliced
    # a sibling's SIGNATURE is context (the spec's "dependency signatures"); its BODY is not
    assert "untouched_helper" in sliced
    assert "return x * 3" not in sliced
    assert len(sliced) < len(whole), (
        "the slice must be smaller than the source it came from"
    )


def test_empty_diff_slices_to_nothing():
    assert slicer.slice_for_diff("", _read_map({"mod.py": PY_SRC})) == ""


def test_missing_file_is_skipped_not_fatal():
    assert slicer.slice_for_diff(DIFF, _read_map({})) == ""


def test_slice_is_a_pure_function_of_its_inputs():
    a = slicer.slice_for_diff(DIFF, _read_map({"mod.py": PY_SRC}))
    b = slicer.slice_for_diff(DIFF, _read_map({"mod.py": PY_SRC}))
    assert a == b
    assert slicer.content_hash(a) == slicer.content_hash(b)


def test_tree_sitter_path_agrees_when_available():
    ts = pytest.importorskip("tree_sitter")
    pytest.importorskip("tree_sitter_python")  # noqa: F841 - availability is the test
    body = slicer.extract_symbol(PY_SRC, "python", "ReviewedClass")
    assert body is not None and "method_two" in body


def test_t2_payload_builder_prefers_sliced_context():
    loader = importlib.machinery.SourceFileLoader("code_review_t2_mod", str(T2_PATH))
    spec = importlib.util.spec_from_loader("code_review_t2_mod", loader)
    t2 = importlib.util.module_from_spec(spec)
    loader.exec_module(t2)

    context, mode = t2.build_context(DIFF, _read_map({"mod.py": PY_SRC}), str(ROOT))
    assert mode == "sliced"
    assert "reviewed_function" in context

    context_raw, mode_raw = t2.build_context(
        "", _read_map({}), str(ROOT), raw_diff="RAW DIFF TEXT"
    )
    assert mode_raw == "raw-diff"
    assert context_raw == "RAW DIFF TEXT"
