/**
 * Gemini Web Drive outbox → GitHub quarantine-only repository_dispatch.
 * Source-controlled template: installation and live trigger are NOT claimed.
 * Script Properties: GENESIS_DRIVE_FOLDER_ID, GENESIS_GITHUB_TOKEN.
 * GitHub PAT must have minimal dispatch permission on chidionyema/idp.
 */
function relayGenesisDriveOnce() {
  const props = PropertiesService.getScriptProperties();
  const folderId = props.getProperty('GENESIS_DRIVE_FOLDER_ID');
  const token = props.getProperty('GENESIS_GITHUB_TOKEN');
  if (!folderId || !token) throw new Error('Missing configured folder or token');
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    const files = DriveApp.getFolderById(folderId).getFiles();
    let processed = 0;
    while (files.hasNext() && processed < 20) {
      const file = files.next();
      if (!/^GENESIS_[A-Za-z0-9_.-]+\.json$/.test(file.getName())) continue;
      if (file.getSize() > 32768) throw new Error('Oversized envelope: ' + file.getId());
      const text = file.getBlob().getDataAsString('UTF-8');
      const obj = JSON.parse(text);
      const keys = Object.keys(obj).sort().join(',');
      if (keys !== 'document_id,event_id,intent,schema_version,source,source_sha256,target_repo') throw new Error('Schema mismatch');
      if (obj.schema_version !== 1 || obj.source !== 'gemini-web-drive' ||
          obj.intent !== 'review-only' || obj.target_repo !== 'chidionyema/idp' ||
          obj.document_id !== file.getId() ||
          !/^[a-f0-9]{64}$/.test(obj.source_sha256) ||
          !/^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$/.test(obj.event_id)) throw new Error('Invalid envelope');
      const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, text);
      const envelopeHash = digest.map(x => ('0' + (x & 255).toString(16)).slice(-2)).join('');
      const key = 'ack_' + envelopeHash;
      if (props.getProperty(key)) continue;
      const response = UrlFetchApp.fetch('https://api.github.com/repos/chidionyema/idp/dispatches', {
        method: 'post',
        contentType: 'application/json',
        headers: {Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json'},
        payload: JSON.stringify({event_type: 'genesis_drive_review_v1', client_payload: obj}),
        muteHttpExceptions: true
      });
      if (response.getResponseCode() !== 204) {
        throw new Error('GitHub dispatch failed HTTP ' + response.getResponseCode());
      }
      // Dispatch 204 is transport acceptance only; no code approval or execution.
      props.setProperty(key, new Date().toISOString());
      processed++;
    }
  } finally { lock.releaseLock(); }
}
