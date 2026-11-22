import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  SUBMIT_REF, MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES,
  safeSourcePath, validateFiles, gitBlobSha, admittedMode, admittedBase, submissionReceipt,
} from '../src/aistudio-fence.js';
const asBytes = (path, content) => ({ path, bytes: new TextEncoder().encode(content) });

test('source files under explicitly allowed roots are admitted', () => {
  for (const p of ['src/engine/x.ts','tests/a.test.js','packages/sub/src/a.rs','platform/lifeboat/src/b.js','docs/guide.md','bin/cli','scripts/a.sh']) {
    assert.equal(safeSourcePath(p), true, p);
  }
  assert.equal(validateFiles([asBytes('src/example.ts','export const n = 42;\n')]),true);
});
test('absolute/parent/repeated slashes and hidden gate dirs refused', () => {
  for(const p of ['/etc/passwd','../evil.ts','src/../../.github/workflows/ci.yml','src//x.ts','src/./x.ts','src/x\\key','evil.ts','.github/workflows/key.yml','src/.github/workflows/ci.yml','src/.githooks/pre-commit']) {
    assert.equal(safeSourcePath(p),false,p);
  }
});
test('secrets and credential paths refused before GitHub is touched', () => {
  for(const p of ['src/.env','src/.env.production','platform/secrets/key.txt','src/foo.pem','src/foo.key','src/credentials/access.txt','src/.vault/item','src/private/agent.ts']) {
    assert.equal(safeSourcePath(p),false,p);
  }
});
test('duplicate paths and too many files fail as one atomic intake', () => {
  assert.throws(()=>validateFiles([asBytes('src/x.ts','a'),asBytes('src/x.ts','b')]),/DUPLICATE_PATH/);
  assert.throws(()=>validateFiles(Array.from({length:MAX_FILES+1},(_,i)=>asBytes('src/'+i+'.ts','x'))),/FILE_COUNT/);
});
test('single and total byte budgets enforced', () => {
  assert.throws(()=>validateFiles([asBytes('src/x.ts','a'.repeat(MAX_FILE_BYTES+1))]),/UNTRUSTED_BYTES/);
  assert.throws(()=>validateFiles(Array.from({length:4},(_,i)=>asBytes('src/'+i+'.ts','x'.repeat(MAX_TOTAL_BYTES/4+1)))),/TOTAL_BYTES/);
});
test('token-like source content fails closed', () => {
  assert.throws(()=>validateFiles([asBytes('src/auth.ts','const t = "github_pat_12345678901234567890123";')]),/SENSITIVE_SOURCE/);
  assert.throws(()=>validateFiles([asBytes('src/auth.ts','Authorization: Bearer abcdef')]),/SENSITIVE_SOURCE/);
});
test('binary and invalid UTF-8 cannot be mistaken for source', () => {
  assert.throws(()=>validateFiles([{path:'src/x.ts',bytes:new Uint8Array([0xff,0xfe,0xfd])}]),/BINARY_SOURCE/);
  assert.throws(()=>validateFiles([asBytes('src/x.ts','a\0b')]),/SENSITIVE_SOURCE/);
});
test('correct Git blob object hash differs from SHA256 content hash', async () => {
  const bytes=new TextEncoder().encode('hello world\n');
  assert.equal(await gitBlobSha(bytes),'3b18e512dba79e4c8300dd08aeb37f8e728b8dad');
  assert.notEqual(await gitBlobSha(bytes),createHash('sha256').update(bytes).digest('hex'));
});
test('existing 100755 stays executable and 100644 stays non-executable', () => {
  assert.equal(admittedMode({type:'blob',mode:'100755'}),'100755');
  assert.equal(admittedMode({type:'blob',mode:'100644'}),'100644');
  assert.equal(admittedMode(null),'100644');
});
test('symlink and submodule are rejected', () => {
  assert.throws(()=>admittedMode({type:'blob',mode:'120000'}),/EXISTING_FILE_MODE/);
  assert.throws(()=>admittedMode({type:'commit',mode:'160000'}),/EXISTING_FILE_MODE/);
});
test('first commit must extend exact trusted main, never an orphan root', () => {
  const main='a'.repeat(40), head='b'.repeat(40);
  assert.equal(admittedBase(null,main),main);
  assert.equal(admittedBase(head,main),head);
  assert.throws(()=>admittedBase(null,'unknown'),/MAIN_SHA_UNVERIFIED/);
  assert.throws(()=>admittedBase('fake',main),/INVALID_SUBMIT_HEAD/);
});
test('source submission cannot claim gate pass, deployment or final yield', () => {
  assert.equal(SUBMIT_REF,'submit/aistudio-auto-intake');
  const x=submissionReceipt({commit:'c'.repeat(40)});
  assert.equal(x.phase,'SUBMIT_SOURCE_ONLY');
  assert.equal(x.gate_verified,false);
  assert.equal(x.greenlane_landed,false);
  assert.equal(x.operational_yield,false);
});
