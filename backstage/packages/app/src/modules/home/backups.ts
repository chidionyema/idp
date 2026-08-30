// The Backups tile's data (founder 2026-08-30: "all of our backups in backoffice with
// timestamp"), as bin/estate-backups writes docs/backups.json on the render schedule from one
// recursive listing of the backup bucket. Pure: no fetch here.
export type BackupSource = {
  name: string;
  newest: string;
  newest_at: string;
  copies: number;
  bytes: number;
};
export type BackupsData = {
  taken: string;
  bucket: string;
  state: 'ok' | 'BLIND';
  reason?: string;
  sources: BackupSource[];
};

/** The path under the estate-state proxy; the same branch founder.json lives on. */
export const BACKUPS_JSON = '/estate-state/docs/backups.json';

/** A source whose newest copy is older than this is stale; the offsite declaration's widest interval is 30h. */
export const STALE_AFTER_HOURS = 30;

export const parseBackups = (raw: unknown): BackupsData => {
  const o = (raw ?? {}) as Partial<BackupsData>;
  if (!o.taken || !o.bucket || (o.state !== 'ok' && o.state !== 'BLIND'))
    throw new Error('backups.json is not the shape estate-backups writes');
  return {
    taken: o.taken,
    bucket: o.bucket,
    state: o.state,
    reason: o.reason,
    sources: Array.isArray(o.sources) ? o.sources : [],
  };
};

/** Hours since the newest copy, on the viewer's clock; undefined when the stamp does not parse. */
export const ageHours = (s: BackupSource, now: number): number | undefined => {
  const t = Date.parse(s.newest_at);
  return Number.isNaN(t) ? undefined : Math.round(((now - t) / 3600000) * 10) / 10;
};

/** A stamp that does not parse is stale: nothing proves the copy is fresh. */
export const isStale = (s: BackupSource, now: number) => {
  const h = ageHours(s, now);
  return h === undefined || h > STALE_AFTER_HOURS;
};

export const backupsSentence = (d: BackupsData, now: number) => {
  if (d.state === 'BLIND')
    return `The backup bucket could not be listed, so no backup is known to exist. ${d.reason ?? ''}`.trim();
  if (d.sources.length === 0) return `Nothing is backed up in ${d.bucket}.`;
  const stale = d.sources.filter(s => isStale(s, now)).length;
  const n = d.sources.length;
  return stale === 0
    ? `${n} source${n === 1 ? '' : 's'} backed up, every one fresh.`
    : `${n} source${n === 1 ? '' : 's'} backed up, ${stale} older than ${STALE_AFTER_HOURS}h.`;
};

/** "4.7 MB" from bytes; the page never shows a raw byte count. */
export const size = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
};
