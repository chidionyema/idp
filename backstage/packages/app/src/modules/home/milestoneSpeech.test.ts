// The face must be silent for the RIGHT reason, and these cases name each one.
//
// idp#5737 item 3: "milestones spoken on /face ... explicit toggle + quiet hours + rate cap (the
// cap is the design)". A test that only proved "a deploy gets spoken" would pass against an
// implementation that also speaks at 3am, speaks with the toggle off, and speaks a hundred times
// an hour -- which is the failure the item exists to prevent. So every refusal is pinned too, and
// the wrapping quiet window (23 -> 7, the one a plain `<` gets backwards) is pinned hardest.
import {
  DEFAULT_MILESTONE_PREFS,
  inQuietHours,
  milestoneFromFrame,
  pruneSpoken,
  shouldSpeak,
  type Milestone,
  type MilestonePrefs,
} from './milestoneSpeech';

const ON: MilestonePrefs = {
  enabled: true,
  quietFromHour: 23,
  quietToHour: 7,
  maxPerHour: 6,
};

/** A local wall-clock instant, because quiet hours are local by definition. */
const at = (hour: number, minute = 0) =>
  new Date(2026, 9, 12, hour, minute, 0, 0).getTime();

const frame = (on: string, story: unknown) =>
  JSON.stringify({ type: 'story', on, story });

const milestone = (
  text = 'idp#5737 landed',
  when: number = at(12),
): Milestone => ({
  channel: 'deploys',
  text,
  at: when,
});

describe('only milestone stories become milestones', () => {
  it('a deploys story is a milestone, spoken in its own words', () => {
    expect(
      milestoneFromFrame(frame('deploys', { title: 'idp#5737 is live' })),
    ).toMatchObject({ channel: 'deploys', text: 'idp#5737 is live' });
  });

  it('every milestone channel is accepted', () => {
    for (const on of ['deploys', 'lanes', 'claims']) {
      expect(milestoneFromFrame(frame(on, { title: 'x' }))?.channel).toBe(on);
    }
  });

  it('news on another channel is not spoken', () => {
    expect(milestoneFromFrame(frame('news', { title: 'x' }))).toBeNull();
  });

  it('a non-story frame is not spoken', () => {
    expect(milestoneFromFrame(JSON.stringify({ type: 'cue' }))).toBeNull();
  });

  it('malformed bytes are not an error, just silence', () => {
    expect(milestoneFromFrame('{not json')).toBeNull();
    expect(milestoneFromFrame('')).toBeNull();
    expect(milestoneFromFrame('null')).toBeNull();
  });

  it('a milestone with nothing to say is not spoken', () => {
    expect(milestoneFromFrame(frame('deploys', { title: '   ' }))).toBeNull();
    expect(milestoneFromFrame(frame('deploys', {}))).toBeNull();
    expect(milestoneFromFrame(frame('deploys', null))).toBeNull();
  });
});

describe('quiet hours wrap midnight', () => {
  it('is quiet late at night and early in the morning, and loud midday', () => {
    expect(inQuietHours(ON, at(23, 30))).toBe(true);
    expect(inQuietHours(ON, at(3))).toBe(true);
    expect(inQuietHours(ON, at(6, 59))).toBe(true);
    expect(inQuietHours(ON, at(7))).toBe(false);
    expect(inQuietHours(ON, at(12))).toBe(false);
    expect(inQuietHours(ON, at(22, 59))).toBe(false);
  });

  it('a daytime window does not wrap', () => {
    const day: MilestonePrefs = { ...ON, quietFromHour: 9, quietToHour: 17 };
    expect(inQuietHours(day, at(10))).toBe(true);
    expect(inQuietHours(day, at(18))).toBe(false);
    expect(inQuietHours(day, at(8))).toBe(false);
  });

  it('a zero-width window is no quiet hours, not eternal silence', () => {
    expect(
      inQuietHours({ ...ON, quietFromHour: 0, quietToHour: 0 }, at(3)),
    ).toBe(false);
  });
});

describe('the cap is the design', () => {
  it('speaks under the cap', () => {
    expect(shouldSpeak(milestone(), ON, [], at(12))).toEqual({
      speak: true,
      text: 'idp#5737 landed',
    });
  });

  it('drops the one that exceeds it, naming the cap', () => {
    const spoken = [at(12, 0), at(12, 1), at(12, 2)];
    expect(
      shouldSpeak(milestone(), { ...ON, maxPerHour: 3 }, spoken, at(12, 3)),
    ).toEqual({
      speak: false,
      reason: 'rate-cap',
    });
  });

  it('the cap slides: last hour only', () => {
    const spoken = [at(10, 58), at(11, 30), at(11, 45)];
    // At 12:00 the 10:58 stamp is outside the hour, so two of three remain and one is room.
    expect(
      shouldSpeak(milestone(), { ...ON, maxPerHour: 3 }, spoken, at(12, 0))
        .speak,
    ).toBe(true);
    expect(pruneSpoken(spoken, at(12, 0))).toEqual([at(11, 30), at(11, 45)]);
  });

  it('the window is half-open: a stamp exactly an hour old has already left it', () => {
    // A decision, not an accident. Exactly 60 minutes old is the boundary, and the boundary is
    // the one case where "at most N per hour" can be read two ways; the read here is that the
    // hour that just ended has closed, so the slot is free again. Pinned so a later
    // `<=`-for-`<` tweak is caught rather than shipped silently.
    expect(pruneSpoken([at(11, 0)], at(12, 0))).toEqual([]);
  });
});

describe('the toggle and the window refuse before the cap', () => {
  it('is silent when the toggle is off, whatever else is true', () => {
    expect(
      shouldSpeak(milestone(), { ...ON, enabled: false }, [], at(12)),
    ).toEqual({
      speak: false,
      reason: 'disabled',
    });
  });

  it('is silent in the quiet window even with room under the cap', () => {
    expect(shouldSpeak(milestone(), ON, [], at(3))).toEqual({
      speak: false,
      reason: 'quiet-hours',
    });
  });

  it('ships off, so the face never starts talking unasked', () => {
    expect(DEFAULT_MILESTONE_PREFS.enabled).toBe(false);
  });
});
