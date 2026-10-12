/*
 * Which fleet milestones the face is allowed to SPEAK, and when it stays quiet.
 *
 * WHY THE GATE IS A FILE AND NOT AN `if`. idp#5737, item 3: "milestones spoken on /face --
 * claims verified, lanes landed, deploys rolled; explicit toggle + quiet hours + rate cap (the
 * cap is the design)". The cap is the design because a face that narrates every land, deploy and
 * claim is worse than a silent one: it is noise the founder learns to ignore, and an ignored
 * alert is an absent alert. So the interesting half of this feature is not the speaking -- it is
 * the refusing, and refusing is a decision, which is a function, which is what this file is.
 *
 * THE EVENTS ALREADY FLOW. Nothing here publishes or derives a milestone. The news stream already
 * carries them: the bus subject is `n.<channel>` and `subscribe_stories` yields `(on, story)`,
 * `serve.py` frames that as `{type: 'story', on: <channel>, story}` on `/fleetview/stream`, and
 * `test_news_stories.py` already asserts a `deploys` frame. This module is the missing gate
 * between that stream and `voice.speak`.
 *
 * WHY PURE. Quiet hours wrap midnight, the cap is measured over a sliding hour, and the toggle is
 * off by default -- three off-by-one opportunities on a path whose failure is "the face talked
 * when it should have been silent", which is exactly the failure that is not noticed until it is
 * annoying. Every branch is decided here, by a function with no clock, no storage and no network,
 * so each one can be pinned by a test rather than by listening to the face at 11pm.
 *
 * WHAT THIS DOES NOT DO. It does not decide the SENTENCE (the story's own words are spoken, so
 * the face cannot hallucinate a milestone that did not happen) and it does not schedule or queue.
 * `shouldSpeak` answers one question about one milestone at one instant, and the caller owns the
 * stream, the clock and the memory of what has already been said.
 */

/** The channels that count as milestones. Any other story is news, and news is not spoken. */
export const MILESTONE_CHANNELS = ['deploys', 'lanes', 'claims'] as const;

export type MilestoneChannel = (typeof MILESTONE_CHANNELS)[number];

export interface Milestone {
  channel: MilestoneChannel;
  /** The story's own sentence, spoken verbatim. Never composed here. */
  text: string;
  /** When the milestone happened, epoch ms. Used only for the cap. */
  at: number;
}

export interface MilestonePrefs {
  /** The explicit toggle. OFF until the founder turns it on: a face that starts talking unasked
   *  is the one thing worse than a quiet one. */
  enabled: boolean;
  /** Quiet hours, local time, `[quietFromHour, quietToHour)`. 23 and 7 means "nothing between
   *  11pm and 7am", which is the window that wraps midnight -- the case a plain `<` gets wrong. */
  quietFromHour: number;
  quietToHour: number;
  /** The cap: at most this many spoken milestones in any sliding 60 minutes. */
  maxPerHour: number;
}

export const DEFAULT_MILESTONE_PREFS: MilestonePrefs = {
  enabled: false,
  quietFromHour: 23,
  quietToHour: 7,
  maxPerHour: 6,
};

/** Why the face stayed silent. Named, so a quiet face is auditable and not a mystery. */
export type SilenceReason =
  | 'not-a-milestone'
  | 'malformed-frame'
  | 'disabled'
  | 'quiet-hours'
  | 'rate-cap';

export type MilestoneVerdict =
  | { speak: true; text: string }
  | { speak: false; reason: SilenceReason };

const isMilestoneChannel = (on: string): on is MilestoneChannel =>
  (MILESTONE_CHANNELS as readonly string[]).includes(on);

/**
 * Read one SSE `data:` payload and return a milestone, or null.
 *
 * Total by construction: a stream is untrusted input and a frame that is not a milestone story is
 * the common case, not an error. Returns null (rather than throwing) for a non-story frame, a
 * story on a channel that is not a milestone, a story with no speakable sentence, and malformed
 * JSON alike -- so the caller's `onmessage` never needs a try/catch around a stranger's bytes.
 */
export function milestoneFromFrame(data: string): Milestone | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(data);
  } catch {
    return null;
  }
  if (typeof parsed !== 'object' || parsed === null) return null;
  const frame = parsed as Record<string, unknown>;
  if (frame.type !== 'story') return null;
  const on = frame.on;
  if (typeof on !== 'string' || !isMilestoneChannel(on)) return null;
  const text = sentenceOf(frame.story);
  if (!text) return null;
  return { channel: on, text, at: Date.now() };
}

/** The story's speakable sentence: its own words, first one that is a non-empty string. */
function sentenceOf(story: unknown): string | null {
  if (typeof story === 'string') return story.trim() || null;
  if (typeof story !== 'object' || story === null) return null;
  const s = story as Record<string, unknown>;
  for (const key of ['title', 'headline', 'summary', 'text', 'message']) {
    const value = s[key];
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return null;
}

/**
 * Is `now` inside the quiet window?
 *
 * The wrapping case is the whole point: a window of 23 -> 7 must be quiet at 23:30 AND at 06:30,
 * which a `hour >= from && hour < to` test would get exactly backwards. When `from === to` the
 * window is empty (quiet at no hour) -- a zero-width window is "no quiet hours", the useful
 * reading, and not "quiet always", which would silence the face forever.
 */
export function inQuietHours(prefs: MilestonePrefs, now: number): boolean {
  const hour = new Date(now).getHours();
  const { quietFromHour: from, quietToHour: to } = prefs;
  if (from === to) return false;
  return from < to ? hour >= from && hour < to : hour >= from || hour < to;
}

/** Drop spoken stamps older than the sliding hour, so the memory stays bounded and honest. */
export function pruneSpoken(
  spokenAt: readonly number[],
  now: number,
): number[] {
  return spokenAt.filter(at => now - at < 60 * 60 * 1000);
}

/**
 * Should the face speak this milestone, now? The one decision, in order of precedence:
 *
 *   1. the toggle      -- off means silent, whatever else is true
 *   2. quiet hours     -- the founder is asleep; a land can wait for morning
 *   3. the cap         -- already at `maxPerHour` in the sliding hour, so this one is dropped
 *
 * The cap DROPS the milestone rather than queueing it: a queue delivers the storm late, which is
 * the same noise with worse timing. Dropped is the honest outcome, and the count is returned so
 * the caller can say so.
 */
export function shouldSpeak(
  milestone: Milestone,
  prefs: MilestonePrefs,
  spokenAt: readonly number[],
  now: number,
): MilestoneVerdict {
  if (!prefs.enabled) return { speak: false, reason: 'disabled' };
  if (inQuietHours(prefs, now)) return { speak: false, reason: 'quiet-hours' };
  if (pruneSpoken(spokenAt, now).length >= prefs.maxPerHour) {
    return { speak: false, reason: 'rate-cap' };
  }
  return { speak: true, text: milestone.text };
}
