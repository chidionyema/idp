// The four states must be drawn as four DIFFERENT motions, and never as a spinner.
//
// A council of three independent frontier models converged on this: an agent silent for ten
// minutes is four states, and the interface's whole value is discriminating them. Measured on the
// running board before this existed: 22 of 23 agents shared one static amber dot.
//
// These cases pin the MECHANISM the research named, because the tempting refactor -- "use one
// pulse for all live states, it looks tidier" -- would quietly restore the single dot:
//
//   thinking  breathes slowly     (it is producing)
//   waiting   DRIFTS toward what it waits on   (the drift IS the tell)
//   stuck     JITTERS fast        (caught pre-attentively)
//   finished  DOES NOT MOVE       (stillness is the signal)
import {
  ACTIVITY_SENTENCE,
  ACTIVITY_WORD,
  motionFor,
  needsAPerson,
  ringStyleFor,
  type Activity,
} from './fleetMotion';

const ALL: Activity[] = ['thinking', 'waiting', 'stuck', 'finished', 'unknown'];

describe('each state gets its own motion', () => {
  it('breathes when producing', () => {
    expect(motionFor('thinking')).toContain('fleet-breathe');
  });

  it('drifts when blocked', () => {
    expect(motionFor('waiting')).toContain('fleet-drift');
  });

  it('jitters when stuck, fast and stepped', () => {
    const m = motionFor('stuck')!;
    expect(m).toContain('fleet-jitter');
    // 125ms is 8Hz, and `steps` rather than an ease: a smooth wobble reads as gentle and this
    // must read as WRONG.
    expect(m).toContain('0.125s');
    expect(m).toContain('steps');
  });

  it('does NOT move when finished — stillness is the signal', () => {
    expect(motionFor('finished')).toBeUndefined();
  });

  it('never uses a spinner, for any state', () => {
    // A spinner means "working" and would collapse all four back into one signal. This is the
    // regression guard, and it is the whole finding in one assertion.
    for (const a of ALL) {
      expect(motionFor(a) ?? '').not.toMatch(/spin|rotate/i);
    }
  });

  it('gives the four real states four different motions', () => {
    const real = ['thinking', 'waiting', 'stuck', 'finished'] as Activity[];
    const motions = real.map(a => motionFor(a) ?? 'STILL');
    expect(new Set(motions).size).toBe(4);
  });
});

describe('the ring carries what motion cannot', () => {
  it('is dashed while blocked and solid while alive', () => {
    expect(ringStyleFor('waiting').borderStyle).toBe('dashed');
    expect(ringStyleFor('thinking').borderStyle).toBe('solid');
    expect(ringStyleFor('stuck').borderStyle).toBe('solid');
  });

  it('fades a finished node, because a faded thing reads as over', () => {
    expect(ringStyleFor('finished').opacity).toBeLessThan(1);
    expect(ringStyleFor('thinking').opacity).toBe(1);
  });

  it('dashes an unknown node rather than pretending it is well', () => {
    // `unknown` means no timestamp. Drawing it as healthy would be the green dot again.
    expect(ringStyleFor('unknown').opacity).toBeLessThan(1);
    expect(ringStyleFor('unknown').borderStyle).not.toBe('solid');
  });
});

describe('only one state needs a person', () => {
  it('flags stuck, and nothing else', () => {
    expect(needsAPerson('stuck')).toBe(true);
    for (const a of ['thinking', 'waiting', 'finished', 'unknown'] as Activity[]) {
      expect(needsAPerson(a)).toBe(false);
    }
  });
});

describe('every state is spoken, because motion alone is not available to everyone', () => {
  it('has a word and a sentence for all five', () => {
    for (const a of ALL) {
      expect(ACTIVITY_WORD[a]).toBeTruthy();
      expect(ACTIVITY_SENTENCE[a]).toBeTruthy();
      // A bare word beside a bare dot is the thing the founder complained about, so the sentence
      // must be a sentence.
      expect(ACTIVITY_SENTENCE[a].length).toBeGreaterThan(20);
    }
  });

  it('says what waiting means, because it is the most common and least obvious', () => {
    expect(ACTIVITY_SENTENCE.waiting).toMatch(/CI|API|person/);
  });
});
