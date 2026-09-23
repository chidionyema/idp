// Device access: the four states, the one button, and the copy the founder approved.
//
// The words are asserted verbatim because they were chosen deliberately. The rejected
// phrasings are asserted ABSENT, which is the part that keeps this tile from drifting back
// into a terminal: a future change that adds "run bin/..." or "tap your phone" must fail here
// rather than ship.
import {
  DeviceAccess,
  canReadProduction,
  deviceAction,
  deviceSentence,
  dotColour,
  humanise,
  parseStatus,
  stateWord,
} from './deviceAccess';

const base: DeviceAccess = {
  state: 'not_provisioned',
  scope: 'read-only',
  expiresIn: null,
  subject: 'system:serviceaccount:agents:agent-reader',
  reason: null,
};

describe('deviceAccess states', () => {
  it('names each state in words a non-engineer reads', () => {
    expect(stateWord('not_provisioned')).toBe('Not provisioned');
    expect(stateWord('active')).toBe('Active');
    expect(stateWord('expiring')).toBe('Expiring');
    expect(stateWord('expired')).toBe('Expired');
    expect(stateWord('unreadable')).toBe('Unreadable');
  });

  it('uses green only when reads genuinely work', () => {
    expect(dotColour('active')).toBe('#3fb950');
    // Amber for the two that need attention but are not failures.
    expect(dotColour('expiring')).toBe('#d29922');
    expect(dotColour('expired')).toBe('#d29922');
    // Grey, not red: not-provisioned is a normal state for a new laptop, not an alarm.
    expect(dotColour('not_provisioned')).toBe('#8b949e');
    // Red only for the one thing that is actually a fault.
    expect(dotColour('unreadable')).toBe('#f85149');
  });

  it('claims production reads only while a live token exists', () => {
    expect(canReadProduction({ ...base, state: 'active' })).toBe(true);
    expect(canReadProduction({ ...base, state: 'expiring' })).toBe(true);
    expect(canReadProduction({ ...base, state: 'expired' })).toBe(false);
    expect(canReadProduction({ ...base, state: 'not_provisioned' })).toBe(false);
    expect(canReadProduction({ ...base, state: 'unreadable' })).toBe(false);
  });
});

describe('the approved copy, per state', () => {
  it('says exactly what the review approved when not provisioned', () => {
    expect(deviceSentence({ ...base, state: 'not_provisioned' })).toBe(
      'This device cannot read production. Only you can authorize it.',
    );
  });

  it('says the access renews itself when active', () => {
    expect(deviceSentence({ ...base, state: 'active', expiresIn: 2580 })).toBe(
      'Read-only access, expires in 43 min. Renews itself.',
    );
  });

  it('says renewal is happening, not that the reader must act', () => {
    expect(deviceSentence({ ...base, state: 'expiring', expiresIn: 240 })).toBe(
      'Read-only access, expires in 4 min. Renewing now.',
    );
  });

  it('never asks the reader to do anything about an expired token', () => {
    const s = deviceSentence({ ...base, state: 'expired', expiresIn: 0 });
    expect(s).toBe(
      'Read-only access expired. It renews itself; if it does not, check the log.',
    );
    // The point of the sentence: no instruction addressed to the reader.
    expect(s).not.toMatch(/\b(run|renew it|tap|click|please)\b/i);
  });

  it('carries the reason when it could not read, rather than guessing a state', () => {
    expect(
      deviceSentence({ ...base, state: 'unreadable', reason: 'status timed out after 10s' }),
    ).toContain('status timed out after 10s');
  });
});

describe('the single button', () => {
  it('offers the one owner-only action when the device has never been provisioned', () => {
    expect(deviceAction({ ...base, state: 'not_provisioned' })).toBe(
      'Authorize this device',
    );
  });

  it('offers NOTHING in every other state, because the timer handles them', () => {
    // This is the load-bearing assertion: a [Renew] button here would re-make the CEO the
    // mechanism, which the review rejected as "the CEO is not a cron job".
    expect(deviceAction({ ...base, state: 'active' })).toBeNull();
    expect(deviceAction({ ...base, state: 'expiring' })).toBeNull();
    expect(deviceAction({ ...base, state: 'expired' })).toBeNull();
    expect(deviceAction({ ...base, state: 'unreadable' })).toBeNull();
  });
});

describe('the rejected phrasings never appear', () => {
  const everyState: DeviceAccess['state'][] = [
    'not_provisioned',
    'active',
    'expiring',
    'expired',
    'unreadable',
  ];

  it('never tells the reader to run a command', () => {
    for (const state of everyState) {
      const s = deviceSentence({ ...base, state, expiresIn: 60, reason: 'x' });
      expect(s).not.toMatch(/bin\//);
      expect(s).not.toMatch(/\brun\b/i);
      expect(s).not.toMatch(/terminal/i);
      expect(s).not.toMatch(/command/i);
    }
  });

  it('never sends a renewal to the phone or implies a tap', () => {
    for (const state of everyState) {
      const s = deviceSentence({ ...base, state, expiresIn: 60, reason: 'x' });
      expect(s).not.toMatch(/\bphone\b/i);
      expect(s).not.toMatch(/\btap\b/i);
      expect(s).not.toMatch(/\bapprove\b/i);
    }
  });
});

describe('humanise', () => {
  it('never shows a raw second count', () => {
    expect(humanise(null)).toBe('');
    expect(humanise(0)).toBe('expired');
    expect(humanise(30)).toBe('less than a minute');
    expect(humanise(60)).toBe('1 min');
    expect(humanise(2580)).toBe('43 min');
    expect(humanise(3600)).toBe('1 hr');
    expect(humanise(7800)).toBe('2 hr 10 min');
  });
});

describe('parseStatus', () => {
  it('reads the backend shape into the tile shape', () => {
    expect(
      parseStatus({
        state: 'active',
        scope: 'read-only',
        expires_in: 2580,
        subject: 'system:serviceaccount:agents:agent-reader',
      }),
    ).toEqual({
      state: 'active',
      scope: 'read-only',
      expiresIn: 2580,
      subject: 'system:serviceaccount:agents:agent-reader',
      reason: null,
    });
  });

  it('maps anything it cannot read to unreadable, never to a permissive state', () => {
    expect(parseStatus(null).state).toBe('unreadable');
    expect(parseStatus({}).state).toBe('unreadable');
    expect(parseStatus({ state: 'something-new' }).state).toBe('unreadable');
    // The failure mode this guards: an unknown state defaulting to 'active' would claim
    // production reads work when nobody knows whether they do.
    expect(parseStatus({ state: 'something-new' }).state).not.toBe('active');
  });

  it('keeps the reason so the reader is told why, not just that it failed', () => {
    expect(parseStatus({ state: 'unreadable', error: 'bin/idp-jit does not exist' }).reason).toBe(
      'bin/idp-jit does not exist',
    );
  });
});
