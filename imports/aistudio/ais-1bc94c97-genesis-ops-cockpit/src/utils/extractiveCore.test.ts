import test from 'node:test';
import assert from 'node:assert/strict';
import {
  computeSha256Hex,
  parseJsonlLogs,
  extractSessionBrief,
  RawLogRecord,
} from './extractiveCore';

test('computeSha256Hex produces valid 64-char hex hash', () => {
  const hash1 = computeSha256Hex('genesis-ops-brief');
  assert.equal(typeof hash1, 'string');
  assert.equal(hash1.length, 64);
  assert.match(hash1, /^[0-9a-f]{64}$/);

  // Determinism check
  const hash2 = computeSha256Hex('genesis-ops-brief');
  assert.equal(hash1, hash2);

  // Different inputs yield distinct hashes
  const hash3 = computeSha256Hex('genesis-ops-brief-modified');
  assert.notEqual(hash1, hash3);
});

test('parseJsonlLogs correctly parses valid JSONL and handles non-JSON lines gracefully', () => {
  const rawInput = [
    JSON.stringify({ timestamp: '2026-11-09T14:00:00Z', level: 'info', agent: 'legion-alpha', action: 'Spawned runner' }),
    JSON.stringify({ timestamp: '2026-11-09T14:05:00Z', level: 'milestone', agent: 'legion-alpha', action: 'Shipped PR #412', commitHash: 'a7b8c9d' }),
    'Plain text log line from runtime stdout',
    JSON.stringify({ timestamp: '2026-11-09T14:15:00Z', level: 'error', agent: 'legion-alpha', action: 'Blocked on dof-gate', details: 'Queued behind credential unblock', blocker: true, needsFounder: true }),
  ].join('\n');

  const records = parseJsonlLogs(rawInput);
  assert.equal(records.length, 4);
  assert.equal(records[0].agent, 'legion-alpha');
  assert.equal(records[1].level, 'milestone');
  assert.equal(records[1].commitHash, 'a7b8c9d');
  assert.equal(records[2].level, 'info');
  assert.equal(records[3].blocker, true);
  assert.equal(records[3].needsFounder, true);
});

test('extractSessionBrief generates 60-90s spoken script, extracts triage categories, and assigns sha256 receipt', () => {
  const testLogs: RawLogRecord[] = [
    {
      timestamp: '2026-11-09T14:00:00Z',
      level: 'milestone',
      agent: 'alpha-kernel',
      action: 'Merged PR #412: Genesis ARM VM Piper TTS lane',
      details: 'Piper runs fast neural voices on 4 cores at zero dollar estate cost',
      commitHash: 'e3f4a12',
      prNumber: 412,
    },
    {
      timestamp: '2026-11-09T14:10:00Z',
      level: 'error',
      agent: 'alpha-kernel',
      action: 'DOF-Gate synchronization locked',
      details: 'Queued behind credential unblock before automated PR landing',
      blocker: true,
      needsFounder: true,
    },
    {
      timestamp: '2026-11-09T14:20:00Z',
      level: 'warn',
      agent: 'alpha-kernel',
      action: 'Review and promote Piper ARM VM lane',
      details: 'Requires founder approval to switch primary spooler lane',
      needsFounder: true,
    },
  ];

  const brief = extractSessionBrief('Legion Alpha (Kernel)', testLogs);

  // Assertions on structural extraction
  assert.equal(brief.title, 'Legion Alpha (Kernel) Executive Brief');
  assert.equal(typeof brief.sha256Receipt, 'string');
  assert.equal(brief.sha256Receipt.length, 64);

  // Check whatShipped
  assert.ok(brief.whatShipped.length >= 1);
  assert.ok(brief.whatShipped[0].text.includes('Piper') || brief.whatShipped[0].text.includes('PR #412'));

  // Check whatIsBlocked
  assert.ok(brief.whatIsBlocked.length >= 1);
  assert.equal(brief.whatIsBlocked[0].blockerType, 'dof-gate');

  // Check needsFounder
  assert.ok(brief.needsFounder.length >= 1);
  assert.equal(brief.needsFounder[0].status, 'pending');

  // Check spoken script & duration
  assert.ok(brief.wordCount > 30);
  assert.ok(brief.estimatedDurationSec >= 30 && brief.estimatedDurationSec <= 120);
  assert.ok(brief.spokenScript.includes('What shipped'));
  assert.ok(brief.spokenScript.includes('What is blocked'));
  assert.ok(brief.spokenScript.includes('Action required'));

  // Check karaoke lines timing
  assert.ok(brief.karaokeLines.length > 0);
  assert.equal(brief.karaokeLines[0].startTime, 0);
  assert.ok(brief.karaokeLines[brief.karaokeLines.length - 1].endTime <= brief.estimatedDurationSec + 2);
});
