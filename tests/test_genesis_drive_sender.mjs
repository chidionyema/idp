// Node's built-in test runner models Google Apps Script boundaries deterministically.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash, createHmac} from 'node:crypto';
import {runInNewContext} from 'node:vm';

const script = readFileSync(new URL('../integrations/gemini-drive-relay/Code.gs', import.meta.url), 'utf8');
const name = 'GENESIS_V051_ED25519_CERTIFIER_PATCH.md';
const docId = 'drivefile-12345678';
const contents = 'safe source bytes: Gemini Web canary';
const secret = 'verified-sender-key-for-test-suite-32-bytes';

function signedBytes(algorithm, text, key) {
  const buf = key ? createHmac('sha256', key).update(text).digest() :
                    createHash('sha256').update(text).digest();
  return Array.from(buf, x => x > 127 ? x - 256 : x);
}

function harness({token = 'opaque-github-token', signer = secret,
                  dispatchCode = 204, ackConclusion = null,
                  ackStatus = 'completed', receiptMatches = true, artifactPresent = true} = {}) {
  const settings = new Map([
    ['GENESIS_DRIVE_FOLDER_ID', 'private-folder'],
    ['GENESIS_GITHUB_TOKEN', token],
    ['GENESIS_DRIVE_RELAY_HMAC_KEY', signer],
  ]);
  const requests = [];
  const source = {
    getName: () => name,
    getId: () => docId,
    getBlob: () => ({
      getSize: () => Buffer.byteLength(contents, 'utf8'),
      getDataAsString: () => contents,
    }),
  };
  const env = {
    Utilities: {
      unzip: () => {
        const dispatch = requests.find(r => r.url.includes('/dispatches'));
        const e = JSON.parse(dispatch.options.payload).client_payload;
        return [{
          getName: () => 'receipt.json',
          getDataAsString: () => JSON.stringify({
            status: 'QUARANTINED_AUTHENTICATED_REVIEW_ONLY',
            event_id: e.event_id,
            source_sha256: receiptMatches ? e.source_sha256 : 'b'.repeat(64),
            document_id: e.document_id,
            target_repo: 'chidionyema/idp',
          }),
        }];
      },
      DigestAlgorithm: {SHA_256: 'sha256'},
      Charset: {UTF_8: 'UTF-8'},
      computeDigest: (_algo, text) => signedBytes(_algo, text),
      computeHmacSha256Signature: (_text, _key) => signedBytes(_algoUnused(), _text, _key),
    },
    PropertiesService: {
      getScriptProperties: () => ({
        getProperty: key => settings.get(key) || null,
        setProperty: (key, value) => {settings.set(key, value);},
      }),
    },
    DriveApp: {
      getFolderById: () => ({
        getFiles: () => {
          let visited = false;
          return {hasNext: () => !visited, next: () => {visited = true; return source;}};
        },
      }),
    },
    LockService: {getScriptLock: () => ({tryLock: () => true, releaseLock: () => {}})},
    UrlFetchApp: {
      fetch: (url, options) => {
        requests.push({url, options});
        if (url.includes('/dispatches'))
          return {getResponseCode: () => dispatchCode};
        if (url.includes('/runs?')) {
          const dispatch = requests.find(r => r.url.includes('/dispatches'));
          const eventId = dispatch ? JSON.parse(dispatch.options.payload).client_payload.event_id : 'none';
          return {
            getResponseCode: () => 200,
            getContentText: () => JSON.stringify({
              workflow_runs: ackConclusion === null ? [] : [{
                display_title: 'Gemini Drive receipt ' + eventId,
                event: 'repository_dispatch',
                status: ackStatus,
                conclusion: ackConclusion,
                id: 12345,
              }],
            }),
          };
        }
        if (url.includes('/runs/12345/artifacts'))
          return {getResponseCode: () => 200, getContentText: () => JSON.stringify({
            artifacts: artifactPresent ? [{id: 678, name: 'gemini-drive-quarantine-receipt', expired: false}] : []
          })};
        if (url.includes('/artifacts/678/zip'))
          return {getResponseCode: () => 302, getHeaders: () => ({Location: 'https://signed-archive.example/zip'})};
        if (url === 'https://signed-archive.example/zip')
          return {getResponseCode: () => 200, getBlob: () => ({})};
        throw new Error('Unexpected mocked URL: ' + url);
      },
    },
    ScriptApp: {getProjectTriggers: () => [], newTrigger: () => ({
      timeBased: () => ({everyMinutes: () => ({create: () => {}})}),
    })},
    console: {log: () => {}},
  };
  // The mocked digest never touches the network or real credentials.
  function _algoUnused() {return 'sha256';}
  const context = runInNewContext(script + '\n({relayGenesisDriveOnce,installGenesisDriveRelayTrigger})', env);
  return {context, settings, requests};
}

test('first send is HMAC-signed and only DISPATCHED_UNCONFIRMED', () => {
  const h = harness();
  h.context.relayGenesisDriveOnce();
  const dispatch = h.requests.filter(x => x.url.includes('/dispatches'));
  assert.equal(dispatch.length, 1);
  const event = JSON.parse(dispatch[0].options.payload);
  assert.equal(event.event_type, 'genesis_drive_review_v1');
  const payload = event.client_payload;
  assert.equal(payload.intent, 'review-only');
  assert.equal(payload.source_sha256, createHash('sha256').update(contents).digest('hex'));
  const canonical = [
    payload.schema_version, payload.event_id, payload.source, payload.source_sha256,
    payload.document_id, payload.target_repo, payload.intent, payload.issued_at,
  ].join('\n');
  assert.equal(payload.signature, createHmac('sha256', secret).update(canonical).digest('hex'));
  assert.ok(Array.from(h.settings.values()).some(x => String(x).includes('DISPATCHED_UNCONFIRMED')));
});

test('receiver success is independently confirmed before ACK and no second dispatch', () => {
  const h = harness({ackConclusion: 'success'});
  h.context.relayGenesisDriveOnce();
  h.context.relayGenesisDriveOnce();
  h.context.relayGenesisDriveOnce();
  assert.equal(h.requests.filter(x => x.url.includes('/dispatches')).length, 1);
  assert.ok(Array.from(h.settings.values()).some(x => String(x).includes('ACKNOWLEDGED')));
});

test('failed GitHub receiver must not mark ACK', () => {
  const h = harness({ackConclusion: 'failure'});
  h.context.relayGenesisDriveOnce();
  assert.throws(() => h.context.relayGenesisDriveOnce(), /GITHUB_RECEIVER_FAILED/);
  assert.ok(!Array.from(h.settings.values()).some(x => String(x).includes('ACKNOWLEDGED')));
});

test('no credentials fails closed without GitHub request', () => {
  const h = harness({signer: ''});
  assert.throws(() => h.context.relayGenesisDriveOnce(), /NOT_CONFIGURED/);
  assert.equal(h.requests.length, 0);
});

test('dispatch HTTP error leaves outbox unacknowledged', () => {
  const h = harness({dispatchCode: 500});
  assert.throws(() => h.context.relayGenesisDriveOnce(), /GITHUB_DISPATCH_HTTP_500/);
  assert.ok(!Array.from(h.settings.values()).some(x => String(x).includes('ACKNOWLEDGED')));
});

test('source document content is not present in dispatch metadata', () => {
  const h = harness();
  h.context.relayGenesisDriveOnce();
  const req = h.requests.find(x => x.url.includes('/dispatches'));
  assert.ok(!req.options.payload.includes(contents));
  assert.ok(!req.options.payload.includes(secret));
});

test('Actions success without an exact validated receipt is never ACK', () => {
  const h = harness({ackConclusion: 'success', receiptMatches: false});
  h.context.relayGenesisDriveOnce();
  assert.throws(() => h.context.relayGenesisDriveOnce(), /GITHUB_RECEIPT_CONTENT_MISMATCH/);
  assert.ok(!Array.from(h.settings.values()).some(x => String(x).includes('ACKNOWLEDGED')));
});

test('Actions success without a receipt artifact is never ACK', () => {
  const h = harness({ackConclusion: 'success', artifactPresent: false});
  h.context.relayGenesisDriveOnce();
  assert.throws(() => h.context.relayGenesisDriveOnce(), /GITHUB_RECEIPT_MISSING/);
});

test('GitHub token is never sent to the redirected artifact host', () => {
  const h = harness({ackConclusion: 'success'});
  h.context.relayGenesisDriveOnce();
  h.context.relayGenesisDriveOnce();
  const redirectRequest = h.requests.find(x => x.url === 'https://signed-archive.example/zip');
  assert.ok(redirectRequest);
  assert.equal(redirectRequest.options.headers, undefined);
});
