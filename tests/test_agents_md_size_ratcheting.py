"""Independent negative-falsifier tests for live workflow's actual Bash body."""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

WORKFLOW = Path(__file__).with_name('agents-md-gate-candidate.yml')
if not WORKFLOW.is_file():
    WORKFLOW = Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'agents-md-gate.yml'


def guard_script():
    data = WORKFLOW.read_text(encoding='utf-8')
    m = re.search(r'^        run: \|\n((?:^          .*\n)+)', data, re.M)
    assert m, 'No standalone Bash guard in workflow'
    return ''.join(x[10:] for x in m.group(1).splitlines(keepends=True))


class AgentsMdRatchet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self._git('init', '-q')
        self._git('config', 'user.email', 'offline-test@example.invalid')
        self._git('config', 'user.name', 'Offline Falsifier')
        self.write(935)
        self._git('add', 'AGENTS.md')
        self._git('commit', '-q', '-m', 'baseline')
        self.base = self._git('rev-parse', 'HEAD').stdout.strip()

    def _git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    def write(self, n):
        (self.root/'AGENTS.md').write_text('law: keep truth\n'*n)

    def run_guard(self, base=None):
        env = dict(os.environ, BASE_SHA=self.base if base is None else base)
        return subprocess.run(['bash', '-c', guard_script()],cwd=self.root,env=env,text=True,capture_output=True)

    def test_inherited_935_warns_never_false_compliant(self):
        r=self.run_guard()
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('LEGACY_DEBT',r.stdout)
        self.assertNotIn('PASS:',r.stdout)

    def test_current_936_fails(self):
        self.write(936)
        r=self.run_guard()
        self.assertEqual(r.returncode,1,(r.stdout,r.stderr))
        self.assertIn('error',r.stdout)

    def test_300_passes(self):
        self.write(300)
        r=self.run_guard()
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertIn('PASS:',r.stdout)

    def test_after_consolidation_reexpansion_to_301_fails(self):
        self.write(300)
        self._git('add','AGENTS.md')
        self._git('commit','-q','-m','shrink')
        self.base=self._git('rev-parse','HEAD').stdout.strip()
        self.write(301)
        r=self.run_guard()
        self.assertEqual(r.returncode,1,(r.stdout,r.stderr))
        self.assertIn('regressed',r.stdout)

    def test_no_growth_from_partial_reduction(self):
        self.write(500)
        self._git('add','AGENTS.md')
        self._git('commit','-q','-m','reduce')
        self.base=self._git('rev-parse','HEAD').stdout.strip()
        self.write(501)
        r=self.run_guard()
        self.assertEqual(r.returncode,1,(r.stdout,r.stderr))

    def test_blind_on_invalid_baseline(self):
        r=self.run_guard(base='untrusted-input; true')
        self.assertEqual(r.returncode,2,(r.stdout,r.stderr))

    def test_blind_when_base_object_absent(self):
        r=self.run_guard(base='0'*40)
        self.assertEqual(r.returncode,2,(r.stdout,r.stderr))

    def test_blind_when_file_missing(self):
        (self.root/'AGENTS.md').unlink()
        r=self.run_guard()
        self.assertEqual(r.returncode,2,(r.stdout,r.stderr))

    def test_no_escaped_shell_variables(self):
        self.assertNotIn('\\$lines',guard_script())
        self.assertNotIn('\\$baseline',guard_script())


if __name__=='__main__':
    unittest.main()
