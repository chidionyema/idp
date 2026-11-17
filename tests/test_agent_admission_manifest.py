import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

HELPER = Path(__file__).resolve().parents[1] / 'bin/idp-agent-base-apply.py'


def git(repo, *args):
    return subprocess.check_output(['git', *args], cwd=repo)


def call(repo, *args):
    return subprocess.run([sys.executable, '-B', str(HELPER), *map(str, args)], cwd=repo, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path/'repo'
    r.mkdir()
    git(r, 'init', '-q', '-b', 'main')
    git(r, 'config', 'user.name', 'test')
    git(r, 'config', 'user.email', 'test@example.invalid')
    (r/'bin').mkdir()
    for p in ('a.py', 'b.py'):
        (r/'bin'/p).write_text('old\n')
    git(r, 'add', '.')
    git(r, 'commit', '-qm', 'baseline')
    git(r, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
    return r


@pytest.mark.parametrize('paths,error', [
    (['.github/actions/github-app-token/action.yml', '.github/workflows/greenlane.yml'], 'protected paths'),
    (['catalog/issue-classes.json','docs/evidence/a.md','tests/browser/test.py'], 'Cross-subsystem'),
    ([f'bin/f{i}' for i in range(7)], 'MAX_FILES_PER_CHANGE'),
    (['AGENTS.md'], 'Guarded path'),
    (['catalog/dof-registry.json'], 'Guarded path'),
    (['bin/../.github/workflows/x.yml'], 'noncanonical'),
    (['bin/a.py','bin/a.py'], 'duplicate'),
    ([], 'Empty file set'),
    (['bin/a,b.py'], 'noncanonical'),
    (['bin/a b.py'], 'noncanonical'),
])
def test_preflight_refuses_without_mutation(repo, paths, error):
    before = git(repo, 'rev-parse', 'HEAD')
    p = call(repo, '--admit-paths-json', json.dumps(paths))
    assert p.returncode == 2 and error in p.stderr, (p.stdout,p.stderr)
    assert git(repo,'rev-parse','HEAD') == before
    assert git(repo,'status','--porcelain') == b''


def staged(repo, tmp_path, permitted, changed, *, tamper=False, mismatch=False):
    p = call(repo, '--admit-paths-json', json.dumps(permitted))
    assert p.returncode == 0, p.stderr
    scope = tmp_path/'scope.json'
    scope.write_text(p.stdout)
    digest = hashlib.sha256(scope.read_bytes()).hexdigest()
    if tamper:
        scope.write_text(p.stdout+' ')
    if mismatch:
        data = json.loads(p.stdout); data['policy_sha256']='f'*64
        scope.write_text(json.dumps(data)); digest=hashlib.sha256(scope.read_bytes()).hexdigest()
    base = tmp_path/'base'
    base.write_bytes(git(repo,'rev-parse','HEAD'))
    for path in changed:
        (repo/path).write_text('new\n')
    patch=tmp_path/'patch'
    patch.write_bytes(git(repo,'diff','--binary'))
    git(repo,'reset','--hard','HEAD')
    return call(repo,'--base-file',base,'--patch',patch,'--scope-file',scope,'--scope-sha256',digest)


def test_valid_subset(repo,tmp_path):
    p=staged(repo,tmp_path,['bin/a.py','bin/b.py'],['bin/a.py'])
    assert p.returncode==0,p.stderr
    assert json.loads(p.stdout)['changed_files']==['bin/a.py']


def test_out_of_scope(repo,tmp_path):
    p=staged(repo,tmp_path,['bin/a.py'],['bin/b.py'])
    assert p.returncode==2 and 'exceeds admitted scope' in p.stderr


def test_manifest_tamper(repo,tmp_path):
    p=staged(repo,tmp_path,['bin/a.py'],['bin/a.py'],tamper=True)
    assert p.returncode==2 and 'digest mismatch' in p.stderr


def test_policy_drift(repo,tmp_path):
    p=staged(repo,tmp_path,['bin/a.py'],['bin/a.py'],mismatch=True)
    assert p.returncode==2 and 'policy changed' in p.stderr
