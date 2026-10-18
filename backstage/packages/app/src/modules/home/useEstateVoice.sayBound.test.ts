/**
 * THE SAY BOUND -- the client half of the 2.5s first-audio SLO (2026-10-16).
 *
 * A hung /voice/say used to hold each clause open indefinitely: the fetch carried only the
 * turn's abort signal, and nothing fires that when the founder is simply waiting. The bound is
 * the contract "a clause either speaks within SAY_TIMEOUT_MS or degrades at once to the device
 * voice", and the pod rest shrank from ten minutes to one so one hiccup costs one clause, not
 * the whole morning.
 */
import { describe, it, expect } from '@jest/globals';
import { fetchBounded, SAY_TIMEOUT_MS, POD_VOICE_REST_MS } from './useEstateVoice';

const res = (body: BodyInit = new ArrayBuffer(8)) => new Response(body, { status: 200 });

describe('fetchBounded', () => {
  it('returns the response when the fetch answers inside the bound', async () => {
    const out = await fetchBounded('http://x/voice/say', {}, 500, async () => res());
    expect(out.ok).toBe(true);
  });

  it('rejects when the fetch hangs past the bound, even with nobody aborting', async () => {
    await expect(
      fetchBounded(
        'http://x/voice/say',
        {},
        20,
        (_u, i) =>
          new Promise<Response>((_, reject) => {
            // The abort the timer fires is the only thing that ends this fetch.
            i.signal?.addEventListener('abort', () =>
              reject(new DOMException('aborted', 'AbortError')),
            );
          }),
      ),
    ).rejects.toThrow('aborted');
  });

  it("the founder's own barge still wins immediately", async () => {
    const turn = new AbortController();
    const pending = fetchBounded(
      'http://x/voice/say',
      { signal: turn.signal },
      60_000,
      (_u, i) =>
        new Promise<Response>((_, reject) => {
          i.signal?.addEventListener('abort', () =>
            reject(new DOMException('aborted', 'AbortError')),
          );
        }),
    );
    turn.abort();
    await expect(pending).rejects.toThrow('aborted');
  });
});

describe("the bound's constants", () => {
  it('a clause waits at most 4s for the pod voice', () => {
    expect(SAY_TIMEOUT_MS).toBeLessThanOrEqual(4000);
  });

  it('a pod failure rests the voice for a minute, not the old ten', () => {
    expect(POD_VOICE_REST_MS).toBe(60 * 1000);
  });
});
