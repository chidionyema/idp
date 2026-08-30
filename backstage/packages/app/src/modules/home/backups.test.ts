import {
  backupsSentence,
  isStale,
  parseBackups,
  size,
} from './backups';

const doc = {
  taken: '2026-08-30T10:30Z',
  bucket: 'prospector-backup',
  state: 'ok' as const,
  sources: [
    {
      name: 'engine-db',
      newest: 'db/prospector-2026-08-23.db.gz',
      newest_at: '2026-08-23T00:00:00Z',
      age_hours: 178.5,
      copies: 12,
      bytes: 5,
    },
    {
      name: 'money-db',
      newest: 'offsite/money-db/store-20260829T025019Z.db',
      newest_at: '2026-08-29T02:50:19Z',
      age_hours: 31.7,
      copies: 30,
      bytes: 4702208,
    },
    {
      name: 'engine-repo',
      newest: 'repo/2026-08-30T024107Z.bundle',
      newest_at: '2026-08-30T02:41:07Z',
      age_hours: 7.8,
      copies: 14,
      bytes: 1024 * 1024 * 40,
    },
  ],
};

describe('backups.json', () => {
  it('parses the shape estate-backups writes and refuses another', () => {
    expect(parseBackups(doc).sources).toHaveLength(3);
    expect(() => parseBackups({ taken: 'x' })).toThrow('not the shape');
  });

  it('counts the stale sources in the sentence', () => {
    expect(backupsSentence(doc)).toBe('3 sources backed up, 2 older than 30h.');
    expect(isStale(doc.sources[2])).toBe(false);
  });

  it('says nothing is known when the bucket could not be listed', () => {
    expect(
      backupsSentence({
        ...doc,
        state: 'BLIND',
        reason: 'rclone lsjson exit 3',
        sources: [],
      }),
    ).toBe(
      'The backup bucket could not be listed, so no backup is known to exist. rclone lsjson exit 3',
    );
  });

  it('prints sizes a person reads', () => {
    expect(size(5)).toBe('5 B');
    expect(size(4702208)).toBe('4.5 MB');
    expect(size(1024 * 1024 * 40)).toBe('40.0 MB');
  });
});
