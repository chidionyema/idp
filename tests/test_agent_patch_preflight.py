"""Actual Git index adversarial tests for cloud agent staged-patch acceptance."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-agent-patch-preflight.py"
spec = importlib.util.spec_from_file_location("idp_agent_preflight", SCRIPT)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class AgentPatchPreflightTests(unittest.TestCase):
    def setUp(self):
        self.old_dir = Path.cwd()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.chdir, self.old_dir)
        os.chdir(self.tmp.name)
        self.cmd("init", "-q")
        self.cmd("config", "user.email", "test@example.invalid")
        self.cmd("config", "user.name", "Test")
        self.cmd("commit", "-q", "--allow-empty", "-m", "baseline")

    def cmd(self, *args):
        return subprocess.run(["git", *args], check=True, capture_output=True).stdout

    def add(self, path, content):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        self.cmd("add", "--", path)
        return p

    def inspect(self, repair=False, allow_governance=False, allow_empty=False):
        args = [sys.executable, str(SCRIPT)]
        if repair:
            args.append("--repair-evidence-docs")
        if allow_governance:
            args.append("--allow-governance-paths")
        if allow_empty:
            args.append("--allow-empty")
        completed = subprocess.run(args, capture_output=True, text=True)
        return completed.returncode, json.loads(completed.stdout)

    def test_universal_precommit_retains_deliberate_empty_commit(self):
        rc, out = self.inspect(allow_empty=True)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["reason"], "EMPTY_COMMIT_ALLOWED")
        self.assertEqual(out["authority"], "PREFLIGHT_ONLY")

    def test_ascii_source_passes(self):
        self.add("bin/source.py", "print('hello')\n")
        rc, out = self.inspect()
        self.assertEqual(rc, 0)
        self.assertTrue(out["ok"])
        self.assertEqual(out["repairs"], [])

    def test_empty_patch_refuses(self):
        rc, out = self.inspect()
        self.assertEqual(rc, 3)
        self.assertEqual(out["reason"], "EMPTY_PATCH")

    def test_non_ascii_source_refuses_unchanged(self):
        p = self.add("src/example.py", "x = '\u2014'\n")
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 3)
        self.assertEqual(out["failed_paths"][0]["class"], "ADDED_NON_ASCII")
        self.assertEqual(self.cmd("show", ":src/example.py"), p.read_bytes())

    def test_new_evidence_markdown_typography_repaired_in_index(self):
        p = self.add(
            "docs/evidence/test/README.md",
            "# Evidence \u2014 verified\n\u201cValue\u201d \u2192 complete\n",
        )
        original = p.read_bytes()
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(out["repairs"]), 1)
        self.assertEqual(
            p.read_bytes(), b'# Evidence -- verified\n"Value" -> complete\n'
        )
        self.assertEqual(
            self.cmd("show", ":docs/evidence/test/README.md"), p.read_bytes()
        )
        self.assertNotEqual(original, p.read_bytes())
        self.assertEqual(len(out["repairs"][0]["before_sha256"]), 64)

    def test_semantic_checkmark_cannot_be_forged_into_pass(self):
        p = self.add("docs/evidence/x/README.md", "Canary \u2713\n")
        original = p.read_bytes()
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 3)
        self.assertEqual(out["repairs"], [])
        self.assertEqual(p.read_bytes(), original)
        self.assertNotIn(b"[PASS]", p.read_bytes())
        self.assertEqual(out["failed_paths"][0]["class"], "ADDED_NON_ASCII")

    def test_no_repairs_without_explicit_flag(self):
        p = self.add("docs/evidence/test/README.md", "Evidence \u2014 incomplete\n")
        rc, out = self.inspect()
        self.assertEqual(rc, 3)
        self.assertEqual(out["repairs"], [])
        self.assertIn(b"\xe2\x80\x94", p.read_bytes())

    def test_code_fence_never_rewritten(self):
        p = self.add(
            "docs/evidence/x/README.md",
            "# Evidence\n" + chr(96) * 3 + "python\nx='\u2014'\n" + chr(96) * 3 + "\n",
        )
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 3)
        self.assertEqual(out["repairs"], [])
        self.assertIn(b"\xe2\x80\x94", p.read_bytes())

    def test_unknown_unicode_refuses_without_data_loss(self):
        p = self.add("docs/evidence/x/README.md", "Name: \u00e9tude\n")
        before = p.read_bytes()
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 3)
        self.assertEqual(p.read_bytes(), before)
        self.assertEqual(out["failed_paths"][0]["class"], "ADDED_NON_ASCII")

    def test_modified_evidence_document_is_immutable(self):
        p = self.add("docs/evidence/x/README.md", "Existing document\n")
        self.cmd("commit", "-q", "-m", "docs baseline")
        p.write_text("Existing document\nNew: \u2014\n", encoding="utf-8")
        self.cmd("add", "--", str(p))
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 3)
        self.assertEqual(out["repairs"], [])
        self.assertEqual(out["failed_paths"][0]["class"], "ADDED_NON_ASCII")

    def test_unstaged_edits_cannot_be_overwritten(self):
        p = self.add("docs/evidence/x/README.md", "Punctuation \u2014\n")
        p.write_text("Different unstaged text\n", encoding="utf-8")
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 3)
        self.assertEqual(p.read_text(), "Different unstaged text\n")
        self.assertIn(b"\xe2\x80\x94", self.cmd("show", ":docs/evidence/x/README.md"))

    def test_existing_nonascii_untouched_lines_do_not_block_edit(self):
        p = self.add("docs/evidence/x/README.md", "Existing: \u2014\n")
        self.cmd("commit", "-q", "-m", "existing legacy UTF8")
        p.write_text("Existing: \u2014\nAdded: ASCII only\n", encoding="utf-8")
        self.cmd("add", "--", str(p))
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["repairs"], [])

    def test_protected_paths_refused(self):
        self.add(".github/workflows/evil.yml", "name: no\n")
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 3)
        self.assertEqual(out["failed_paths"][0]["class"], "PROTECTED_PATH")

    def test_hook_modification_refused(self):
        self.add(".githooks/pre-push", "#!/bin/sh\n")
        rc, out = self.inspect()
        self.assertEqual(rc, 3)
        self.assertEqual(out["failed_paths"][0]["class"], "PROTECTED_PATH")

    def test_staged_whitespace_refused_early(self):
        self.add("docs/evidence/x/README.md", "Trailing whitespace   \n")
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 3)
        self.assertIn("GIT_DIFF_CHECK", {e["class"] for e in out["failed_paths"]})

    def test_filename_with_spaces_handled_as_one_index_entry(self):
        self.add("docs/evidence/some space/README.md", "One \u2192 two\n")
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["staged_files"], 1)

    def test_multiple_files_report_all_rejected_path_classes(self):
        self.add("src/a.py", "text='\u00e9'\n")
        self.add(".github/workflows/x.yml", "name: bad\n")
        self.add("docs/evidence/one/README.md", "Good \u2014 prose\n")
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 3)
        self.assertEqual(len(out["repairs"]), 1)
        self.assertEqual(
            {x["class"] for x in out["failed_paths"]},
            {"ADDED_NON_ASCII", "PROTECTED_PATH"},
        )

    def test_subsequent_inspection_idempotent(self):
        self.add("docs/evidence/x/README.md", "Hello \u2026\n")
        rc, result = self.inspect(repair=True)
        self.assertEqual(rc, 0, result)
        rc, result = self.inspect(repair=True)
        self.assertEqual(rc, 0, result)
        self.assertEqual(result["repairs"], [])

    def test_symbolic_link_never_normalised(self):
        p = Path("docs/evidence/x")
        p.mkdir(parents=True)
        (p / "source.md").write_text("Content", encoding="utf-8")
        (p / "README.md").symlink_to("source.md")
        self.cmd("add", "--", str(p / "README.md"))
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["repairs"], [])

    def test_authorized_governance_is_not_blocked_by_untrusted_runner_rule(self):
        self.add(".github/workflows/valid.yml", "name: valid\n")
        rc, out = self.inspect(repair=True, allow_governance=True)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["authority"], "PREFLIGHT_ONLY")
        # Authorization is established by the separate existing signed gate,
        # not by a pre-commit syntax/encoding acceptance.

    def test_governance_unicode_remains_rejected_even_with_scope_flag(self):
        self.add(".github/workflows/y.yml", "name: \u2014\n")
        rc, out = self.inspect(repair=True, allow_governance=True)
        self.assertEqual(rc, 3)
        self.assertEqual(out["failed_paths"][0]["class"], "ADDED_NON_ASCII")

    def test_global_commit_and_cloud_submit_use_committed_head_source(self):
        hook = (ROOT / ".githooks" / "pre-commit").read_text()
        workflow = (ROOT / ".github/workflows" / "agent-sandbox.yml").read_text()
        self.assertIn('git show "HEAD:bin/idp-agent-patch-preflight.py"', hook)
        self.assertIn("--allow-governance-paths", hook)
        self.assertLess(
            hook.index('git show "HEAD:bin/idp-agent-patch-preflight.py"'),
            hook.index("staged_py=$("),
        )
        self.assertIn("git show HEAD:bin/idp-agent-patch-preflight.py", workflow)
        self.assertLess(
            workflow.index("Validate and safely repair staged patch"),
            workflow.index("Claim the work on an issue"),
        )

    def test_explicit_control_code_not_rewritten(self):
        self.add("src/lib.js", "const s='\u201cno\u201d';\n")
        rc, out = self.inspect(repair=True)
        self.assertEqual(rc, 3)
        self.assertEqual(out["repairs"], [])


if __name__ == "__main__":
    unittest.main()
