import { deviceVoice, speakWithDevice } from './useEstateVoice';

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

  it('lets the turn go on when the browser never says the clause ended', async () => {
    jest.useFakeTimers();
    try {
      (window as any).speechSynthesis.speak = (u: any) => spoken.push(u.text);
      let settled = false;
      const done = speakWithDevice('ten chars.').then(() => {
        settled = true;
      });
      await jest.advanceTimersByTimeAsync(3000);
      expect(settled).toBe(false);
      await jest.advanceTimersByTimeAsync(800);
      await done;
      expect(settled).toBe(true);
    } finally {
      jest.useRealTimers();
    }
  });

  it('resolves at once where the browser has no voice', async () => {
    delete (window as any).speechSynthesis;
    await expect(speakWithDevice('anything')).resolves.toBeUndefined();
  });

  it("speaks with a woman's voice where the device has one, matching the face", async () => {
    const voices = [
      { name: 'Microsoft David', lang: 'en-US' },
      { name: 'Microsoft Zira', lang: 'en-US' },
    ];
    (window as any).speechSynthesis.getVoices = () => voices;
    let used: any;
    const speak = (window as any).speechSynthesis.speak;
    (window as any).speechSynthesis.speak = (u: any) => {
      used = u.voice;
      speak(u);
    };
    await speakWithDevice('hello');
    expect(used?.name).toBe('Microsoft Zira');
  });

  it("leaves the voice to the device when it has no woman's voice it can name", () => {
    expect(
      deviceVoice({
        getVoices: () => [{ name: 'Daniel', lang: 'en-GB' }],
      } as any),
    ).toBeUndefined();
    expect(deviceVoice({} as any)).toBeUndefined();
  });
});
