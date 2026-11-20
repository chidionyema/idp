"""Local Git fixtures; no network, deployment, credentials, or real repo mutation."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from recover_meridian import Refused, SCOPE, prepare


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Recovery Test")
        self.git("config", "user.email", "test@example.invalid")
        self.write(SCOPE[1], "old css\n")
        self.write(SCOPE[4], "old nav\n")
        self.base = self.save("base")
        for path in SCOPE:
            self.write(path, "candidate " + path + "\n")
        self.source = self.save("source")
        self.git("checkout", "--detach", self.base)
        self.write("unrelated.txt", "new main\n")
        self.target = self.save("target")

    def git(self, *args, data=None):
        return subprocess.run(["git", "-C", str(self.repo), *args], input=data,
                              capture_output=True, check=True).stdout

    def write(self, path, content):
        p = self.repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def save(self, message):
        self.git("add", "-A")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD").decode().strip()

    def test_exact_patch_preserves_unrelated_main_and_source(self):
        patch, pending = prepare(self.repo, self.base, self.source, self.target)
        self.assertEqual(pending, SCOPE)
        self.assertEqual(self.git("status", "--porcelain"), b"")
        self.git("apply", "--check", "--index", "-", data=patch)
        self.git("apply", "--index", "-", data=patch)
        for path in SCOPE:
            self.assertEqual((self.repo / path).read_bytes(), self.git("show", self.source + ":" + path))
        self.assertEqual((self.repo / "unrelated.txt").read_text(), "new main\n")

    def test_partial_already_present(self):
        self.write(SCOPE[0], "candidate " + SCOPE[0] + "\n")
        target = self.save("partially landed")
        patch, pending = prepare(self.repo, self.base, self.source, target)
        self.assertNotIn(SCOPE[0], pending)
        self.assertEqual(len(pending), 4)
        self.git("apply", "--check", "--index", "-", data=patch)

    def test_all_already_present(self):
        for path in SCOPE:
            self.write(path, "candidate " + path + "\n")
        target = self.save("already landed")
        self.assertEqual(prepare(self.repo, self.base, self.source, target), (b"", ()))

    def test_divergent_target_refused(self):
        self.write(SCOPE[1], "new independent CSS\n")
        with self.assertRaisesRegex(Refused, "independent changes"):
            prepare(self.repo, self.base, self.source, self.save("conflict"))

    def test_extra_scope_refused(self):
        self.git("checkout", "--detach", self.source)
        self.write(".github/workflows/no.yml", "unexpected\n")
        with self.assertRaisesRegex(Refused, "five-path"):
            prepare(self.repo, self.base, self.save("extra"), self.target)

    def test_symlink_refused(self):
        self.git("checkout", "--detach", self.source)
        (self.repo / SCOPE[0]).unlink()
        (self.repo / SCOPE[0]).symlink_to("/tmp/not-a-public-file")
        with self.assertRaisesRegex(Refused, "non-regular"):
            prepare(self.repo, self.base, self.save("symlink"), self.target)

    def test_symbolic_ref_refused(self):
        with self.assertRaisesRegex(Refused, "exact 40"):
            prepare(self.repo, self.base, self.source, "HEAD")

    def test_missing_object_refused(self):
        with self.assertRaises(Refused):
            prepare(self.repo, self.base, self.source, "f" * 40)


if __name__ == "__main__":
    unittest.main()
