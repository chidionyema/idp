/**
 * How old what the face says is, said out loud on the face (idp#6784: "the info face gives me
 * appears stale and inaccurate").
 *
 * WHY. The findings strip showed the research department's NEWEST claim with nothing about when
 * it was made, and the vitals line showed "main green" from an envelope that carries its own
 * `generated_at` which the page never read. Both therefore wore a fresh label whatever their age:
 * a claim from last week and a cached /estate from this morning read exactly like live news. The
 * data was not necessarily wrong -- the face just had no way to say how old it was, so the founder
 * could not tell fresh from stale and (reasonably) trusted none of it.
 *
 * WHAT. A plain age ("4 min ago", "3 h ago", "2 d ago"), and a verdict per source: `fresh` inside
 * its own window, `stale` past it, `unknown` when the source gave no usable time. `unknown` is its
 * own answer and is never rounded to fresh -- a source that cannot date itself has not earned the
 * word. The windows are per source because a claim is allowed to be a day old and a green lane is
 * not allowed to be ten minutes old.
 */

export type Freshness = 'fresh' | 'stale' | 'unknown';

/** The vitals line is read every REFRESH_MS; past this it is being served from a cache. */
export const ESTATE_STALE_MS = 10 * 60 * 1000;
/** A verified claim is a finding, not a heartbeat: a day old is normal, older is called out. */
export const CLAIM_STALE_MS = 24 * 60 * 60 * 1000;

/** Epoch ms of an ISO time, or null when it is missing or not a time. */
export function atMs(iso: string | undefined | null): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  return Number.isFinite(t) ? t : null;
}

/** "just now" / "4 min ago" / "3 h ago" / "2 d ago". A time in the future reads as just now. */
export function ageLabel(iso: string | undefined | null, now: number): string | null {
  const t = atMs(iso);
  if (t === null) return null;
  const s = Math.max(0, Math.round((now - t) / 1000));
  if (s < 60) return 'just now';
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 48) return `${h} h ago`;
  return `${Math.round(h / 24)} d ago`;
}

/** Fresh inside the window, stale past it, unknown when the source gave no usable time. */
export function freshness(
  iso: string | undefined | null,
  now: number,
  staleAfterMs: number,
): Freshness {
  const t = atMs(iso);
  if (t === null) return 'unknown';
  return now - t > staleAfterMs ? 'stale' : 'fresh';
}
