import { speakWithDevice } from './useEstateVoice';

// 2026-10-09: the estate's voice was out of quota and every clause came back with no audio; the
// founder saw the answer and heard nothing. The device's voice now speaks it instead.
describe('speakWithDevice', () => {
  let spoken: string[];
  let cancelled: number;

  beforeEach(() => {
    spoken = [];
    cancelled = 0;
    (window as any).SpeechSynthesisUtterance = function U(
      this: any,
      text: string,
    ) {
      this.text = text;
    };
    (window as any).speechSynthesis = {
      speak: (u: any) => {
        spoken.push(u.text);
        setTimeout(() => u.onend?.(), 0);
      },
      cancel: () => {
        cancelled += 1;
      },
    };
  });

  afterEach(() => {
    delete (window as any).speechSynthesis;
    delete (window as any).SpeechSynthesisUtterance;
  });

  it('speaks the clause and resolves when it ends', async () => {
    await speakWithDevice('twelve agents are running');
    expect(spoken).toEqual(['twelve agents are running']);
  });

  it('stops speaking when the turn is interrupted', async () => {
    (window as any).speechSynthesis.speak = (u: any) => spoken.push(u.text);
    const turn = new AbortController();
    const done = speakWithDevice('a long answer', turn.signal);
    turn.abort();
    await done;
    expect(cancelled).toBe(1);
  });

  it('resolves at once where the browser has no voice', async () => {
    delete (window as any).speechSynthesis;
    await expect(speakWithDevice('anything')).resolves.toBeUndefined();
  });
});
