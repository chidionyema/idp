// WHY. The ratchet is a gate, and a gate that cannot fail is not a gate. On 2026-10-24 this
// guard refused a lane for violations main itself had added -- the lane had touched nothing --
// which is how a guard teaches its users to ignore it. These tests pin the three rules it now
// judges by, and the two fallbacks:
//
//   cap    a path above max(budget, main's own count) is refused.
//   teeth  a branch that adds violations in the files it touched is refused, even when the cap
//          is loose enough to hide it, and even for a file main does not have.
//   base   main's own violations never make a branch red.
//
//   fresh  a cap looser than main's own count is reported, not silently honoured.
//   none   with no base in the checkout the cap alone is the judge, and it says so.
//
// Each test measures a scratch git repository with the same rules the guard measures this one.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const guard = join(here, 'purity.mjs');

const mkRepo = () => {
  const dir = mkdtempSync(join(tmpdir(), 'estate-purity-test-'));
  const init = spawnSync('git', ['init', '-b', 'main'], { cwd: dir, encoding: 'utf8' });
  assert.equal(init.status, 0, init.stderr);
  return dir;
};
const write = (repo, rel, content) => {
  const p = join(repo, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, content);
};
const git = (repo, ...args) => spawnSync('git', args, { cwd: repo, encoding: 'utf8' });
const commit = (repo, message) => {
  git(repo, 'add', '-A');
  const r = git(repo, '-c', 'user.email=guard@estate', '-c', 'user.name=guard', 'commit', '-m', message);
  assert.equal(r.status, 0, r.stdout + r.stderr);
};
const runGuard = (repo, budget, base = 'main') => {
  const budgetPath = join(repo, 'budget.json');
  writeFileSync(budgetPath, JSON.stringify(budget));
  const r = spawnSync(process.execPath, [guard, '--budget', budgetPath], {
    cwd: repo,
    encoding: 'utf8',
    env: { ...process.env, ESTATE_PURITY_ROOT: repo, ESTATE_PURITY_BASE: base },
  });
  return { code: r.status, out: (r.stdout ?? '') + (r.stderr ?? '') };
};

test("main's own violations never make a branch red", (t) => {
  const repo = mkRepo();
  t.after(() => rmSync(repo, { recursive: true, force: true }));
  write(repo, 'app/x.css', '.a { color: #ff0000; }\n.b { color: #00ff00; }\n.c { color: #0000ff; }\n');
  commit(repo, 'base');
  // The branch adds nothing: this is the tree main holds, and the cap is below main's count.
  // The old guard refused here -- that is the failure these tests exist to prevent.
  const { code, out } = runGuard(repo, { app: 1 });
  assert.equal(code, 0, out);
  assert.match(out, /ok\s+app: 3\/3 violations, main 3/);
});

test('a path above the cap is refused', (t) => {
  const repo = mkRepo();
  t.after(() => rmSync(repo, { recursive: true, force: true }));
  write(repo, 'app/x.css', '.a { color: #ff0000; }\n');
  commit(repo, 'base');
  git(repo, 'checkout', '-b', 'lane');
  write(repo, 'app/x.css', '.a { color: #ff0000; }\n.b { color: #00ff00; }\n');
  commit(repo, 'lane adds one');
  const { code, out } = runGuard(repo, { app: 1 }, 'main');
  assert.equal(code, 1, out);
  assert.match(out, /REFUSE app: 2 violations, cap 1 \(budget 1, main 1\)/);
});

test('a branch that adds a violation is refused even when the cap is loose', (t) => {
  const repo = mkRepo();
  t.after(() => rmSync(repo, { recursive: true, force: true }));
  write(repo, 'app/x.css', '.a { color: #ff0000; }\n');
  commit(repo, 'base');
  git(repo, 'checkout', '-b', 'lane');
  write(repo, 'app/x.css', '.a { color: #ff0000; }\n.b { color: #00ff00; }\n');
  commit(repo, 'lane adds one');
  const { code, out } = runGuard(repo, { app: 5 }, 'main');
  assert.equal(code, 1, out);
  assert.match(out, /REFUSE app: the branch added 1 violation\(s\) in the files it touched/);
  assert.match(out, /app\/x\.css \(\+1\)/);
});

test('a file main does not have is measured against zero', (t) => {
  const repo = mkRepo();
  t.after(() => rmSync(repo, { recursive: true, force: true }));
  write(repo, 'app/x.css', '.a { color: #ff0000; }\n');
  commit(repo, 'base');
  git(repo, 'checkout', '-b', 'lane');
  write(repo, 'app/new.css', '.b { color: #00ff00; }\n');
  commit(repo, 'lane adds a file');
  const { code, out } = runGuard(repo, { app: 5 }, 'main');
  assert.equal(code, 1, out);
  assert.match(out, /REFUSE app: the branch added 1 violation\(s\) in the files it touched/);
});

test('a cap looser than main is reported', (t) => {
  const repo = mkRepo();
  t.after(() => rmSync(repo, { recursive: true, force: true }));
  write(repo, 'app/x.css', '.a { color: #ff0000; }\n');
  commit(repo, 'base');
  const { code, out } = runGuard(repo, { app: 5 }, 'main');
  assert.equal(code, 0, out);
  assert.match(out, /stale\s+app: .*looser than main's own 1/);
});

test('with no base the cap alone is the judge', (t) => {
  const repo = mkRepo();
  t.after(() => rmSync(repo, { recursive: true, force: true }));
  write(repo, 'app/x.css', '.a { color: #ff0000; }\n.b { color: #00ff00; }\n');
  commit(repo, 'base');
  const { code, out } = runGuard(repo, { app: 1 }, 'no-such-ref');
  assert.equal(code, 1, out);
  assert.match(out, /note\s+no base \(no-such-ref\) in this checkout: judging the cap alone/);
  assert.match(out, /REFUSE app: 2 violations, cap 1/);
});

test('a nested entry owns its own files', (t) => {
  const repo = mkRepo();
  t.after(() => rmSync(repo, { recursive: true, force: true }));
  write(repo, 'app/x.css', '.a { color: #ff0000; }\n');
  write(repo, 'app/sub/y.css', '.b { color: #00ff00; }\n');
  commit(repo, 'base');
  const { code, out } = runGuard(repo, { app: 1, 'app/sub': 1 }, 'main');
  assert.equal(code, 0, out);
  assert.match(out, /ok\s+app: 1\/1 violations, main 1/);
  assert.match(out, /ok\s+app\/sub: 1\/1 violations, main 1/);
});
