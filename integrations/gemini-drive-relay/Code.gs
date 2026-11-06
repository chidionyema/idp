/**
 * Gemini Web source -> private Google Drive outbox -> GitHub quarantine workflow.
 * The file body never leaves Drive: only a digest and signed provenance envelope.
 * A successful repository_dispatch returns 204, which is TRANSPORT only.
 *
 * Required private Script Properties:
 * GENESIS_DRIVE_FOLDER_ID; GENESIS_GITHUB_TOKEN; GENESIS_DRIVE_RELAY_HMAC_KEY
 * Set key to a random >=32-byte value; same value in GitHub Actions Secret.
 */
const GENESIS_SOURCE_RE = /^GENESIS_[A-Za-z0-9_.-]{1,100}\.(md|txt)$/;
const GENESIS_DISPATCH_URL = 'https://api.github.com/repos/chidionyema/idp/dispatches';

function relayHex_(bytes) {
  return bytes.map(function(x) { return ('0' + (x & 255).toString(16)).slice(-2); }).join('');
}
function relayDigest_(value) {
  return relayHex_(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,
                    value, Utilities.Charset.UTF_8));
}
function relayMac_(value, key) {
  return relayHex_(Utilities.computeHmacSha256Signature(value, key,
                    Utilities.Charset.UTF_8));
}
function relayGitHubAck_(eventId, token) {
  // One authoritative completion check; an HTTP 204 dispatch is never an ACK.
  const url = 'https://api.github.com/repos/chidionyema/idp/actions/workflows/' +
              'genesis-drive-intake.yml/runs?event=repository_dispatch&per_page=100';
  const response = UrlFetchApp.fetch(url, {
    method: 'get',
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28'
    },
    muteHttpExceptions: true
  });
  if (response.getResponseCode() !== 200)
    throw new Error('GITHUB_ACK_QUERY_HTTP_' + response.getResponseCode());
  const runs = JSON.parse(response.getContentText()).workflow_runs || [];
  const expected = 'Gemini Drive receipt ' + eventId;
  for (const run of runs) {
    if (run.display_title === expected)
      return {status: run.status, conclusion: run.conclusion, runId: run.id};
  }
  return null;
}

function relayGenesisDriveOnce() {
  const props = PropertiesService.getScriptProperties();
  const folderId = props.getProperty('GENESIS_DRIVE_FOLDER_ID');
  const token = props.getProperty('GENESIS_GITHUB_TOKEN');
  const signingKey = props.getProperty('GENESIS_DRIVE_RELAY_HMAC_KEY');
  if (!folderId || !token || !signingKey || signingKey.length < 32)
    throw new Error('GENESIS_DRIVE_RELAY_NOT_CONFIGURED');
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    const files = DriveApp.getFolderById(folderId).getFiles();
    let sent = 0;
    const start = Date.now();
    while (files.hasNext() && sent < 20 && Date.now() - start < 180000) {
      const file = files.next();
      if (!GENESIS_SOURCE_RE.test(file.getName())) continue;
      const docId = file.getId();
      if (!/^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$/.test(docId)) continue;
      const blob = file.getBlob();
      if (blob.getSize() > 32768) throw new Error('GENESIS_FILE_TOO_LARGE');
      const digest = relayDigest_(blob.getDataAsString('UTF-8'));
      const eventId = 'gemini-' + relayDigest_(docId + '\n' + digest).slice(0, 40);
      const stateKey = 'dispatched_' + eventId;
      const stored = props.getProperty(stateKey);
      let state = null;
      if (stored) {
        try { state = JSON.parse(stored); } catch (ignored) { state = null; }
      }
      if (state && state.sha === digest && state.state === 'ACKNOWLEDGED') continue;
      if (state && state.sha === digest && state.state === 'DISPATCHED_UNCONFIRMED') {
        const ack = relayGitHubAck_(eventId, token);
        if (ack && ack.status === 'completed' && ack.conclusion === 'success') {
          props.setProperty(stateKey, JSON.stringify({
            sha: digest, state: 'ACKNOWLEDGED', runId: ack.runId,
            verifiedAt: new Date().toISOString()
          }));
          continue;
        }
        if (ack && ack.status === 'completed' && ack.conclusion !== 'success')
          throw new Error('GITHUB_RECEIVER_FAILED_' + ack.conclusion);
        // Backoff: GitHub may accept the dispatch yet queue its workflow.
        if (Date.now() - state.dispatchedAt < 300000) continue;
      }
      const issuedAt = Math.floor(Date.now() / 1000);
      const envelope = {
        schema_version: 1,
        event_id: eventId,
        source: 'gemini-web-drive',
        source_sha256: digest,
        document_id: docId,
        target_repo: 'chidionyema/idp',
        intent: 'review-only',
        issued_at: issuedAt
      };
      const canonical = [envelope.schema_version, envelope.event_id, envelope.source,
                         envelope.source_sha256, envelope.document_id, envelope.target_repo,
                         envelope.intent, envelope.issued_at].join('\n');
      envelope.signature = relayMac_(canonical, signingKey);
      const response = UrlFetchApp.fetch(GENESIS_DISPATCH_URL, {
        method: 'post',
        contentType: 'application/json',
        headers: {
          Authorization: 'Bearer ' + token,
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28'
        },
        payload: JSON.stringify({event_type: 'genesis_drive_review_v1',
                                client_payload: envelope}),
        muteHttpExceptions: true
      });
      if (response.getResponseCode() !== 204)
        throw new Error('GITHUB_DISPATCH_HTTP_' + response.getResponseCode());
      // DISPATCHED does not mean verified, approved, merged, or deployed.
      props.setProperty(stateKey, JSON.stringify({
        sha: digest, state: 'DISPATCHED_UNCONFIRMED', dispatchedAt: Date.now()
      }));
      sent++;
    }
    console.log(JSON.stringify({status: 'dispatch_submitted_ack_pending', files_sent: sent}));
  } finally {
    lock.releaseLock();
  }
}

function installGenesisDriveRelayTrigger() {
  // Installation needs the authenticated script owner to authorize OAuth scopes.
  const triggers = ScriptApp.getProjectTriggers();
  triggers.filter(function(t) { return t.getHandlerFunction() === 'relayGenesisDriveOnce'; })
          .forEach(function(t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('relayGenesisDriveOnce').timeBased().everyMinutes(1).create();
}
