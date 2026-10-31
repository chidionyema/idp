import importlib.machinery
import importlib.util
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "bin", "estate-landed-digest")
_loader = importlib.machinery.SourceFileLoader("estate_landed_digest", TOOL)
_spec = importlib.util.spec_from_loader("estate_landed_digest", _loader)
mod = importlib.util.module_from_spec(_spec)
_loader.exec_module(mod)


def repo_with(subjects):
    d = tempfile.mkdtemp()
    env = dict(
        os.environ,
        GIT_AUTHOR_NAME="a",
        GIT_AUTHOR_EMAIL="a@x",
        GIT_COMMITTER_NAME="a",
        GIT_COMMITTER_EMAIL="a@x",
    )
    subprocess.run(["git", "init", "-q", "-b", "main", d], check=True)
    for i, s in enumerate(subjects):
        subprocess.run(
            ["git", "-C", d, "commit", "-q", "--allow-empty", "-m", s, "--no-verify"],
            check=True,
            env=env,
        )
    return d


class T(unittest.TestCase):
    def test_noise_is_counted_not_listed(self):
        d = repo_with(
            [
                "feat(x): real work",
                "platform: image update -> main-1",
                "chore(registry): regenerate the capability witness",
            ]
        )
        text = "\n".join(mod.digest(mod.landed("main", 14, d), 14, "main"))
        self.assertIn("3 commits (1 listed, 2 image/registry noise)", text)
        self.assertIn("feat(x): real work", text)
        self.assertNotIn("image update -> main-1", text)

    def test_long_digest_is_split_under_the_telegram_limit(self):
        blocks = ["day\n" + "\n".join("- abc %s" % ("x" * 100) for _ in range(200))]
        msgs = mod.chunks(blocks)
        self.assertGreater(len(msgs), 1)
        self.assertTrue(all(len(m) <= 4096 for m in msgs))

    def test_send_refuses_by_name_when_secrets_are_missing(self):
        self.assertEqual(mod.send(["hi"], env={}), 2)

    def test_dry_run_is_the_default_and_sends_nothing(self):
        d = repo_with(["feat(y): z"])
        r = subprocess.run(
            [TOOL, "--ref", "main", "--repo", d], capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("feat(y): z", r.stdout)


if __name__ == "__main__":
    unittest.main()
