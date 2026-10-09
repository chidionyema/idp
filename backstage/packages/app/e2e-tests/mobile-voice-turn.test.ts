/*
 * A spoken question on /fleet, on a phone's engine: heard, transcribed, and answered.
 *
 * WHY. mobile-shell.test.ts stops at "the page reached getUserMedia", because WebKit has no
 * fake-microphone flag and nobody can answer a phone's permission prompt in CI. That left the
 * founder's complaint -- "the mic is still not working" (2026-10-09) -- with no browser proof
 * either way. Measured that day against live catalogue.mumchimp.com in WebKit with an iPhone
 * profile: the voice libraries loaded, MicVAD started, and a recorded question came back as
 * "› the fleet dashboard showing right now, please tell me the current status of the fleet."
 * followed by the fleet's spoken answer (first words 16.6s, reply 49.0s).
 *
 * HOW THE MICROPHONE IS REPLACED. Only the hardware. `MediaDevices.prototype.getUserMedia` returns
 * a MediaStream that plays the fixture WAV in a loop. It must be the PROTOTYPE: patching the
 * `navigator.mediaDevices` instance left WebKit calling the native method, which waited forever on
 * a permission prompt and showed "loading voice libraries…" -- a harness fault that looks exactly
 * like the product bug. The loop matters too: WebKit's VAD missed a single play that began before
 * its worklet loaded, so the speech repeats until the page posts /voice/hear, then stops so it
 * cannot barge in on the answer. Everything after the stream -- the loader, ort, the Silero VAD
 * worklet, /voice/hear, /voice/stream, the transcript and reply on screen -- is the real page
 * against the real backend.
 *
 * WHAT IT DOES NOT PROVE. A physical iPhone: iOS Safari's real permission prompt, its audio-session
 * rules, and real microphone hardware are not exercised. Nor that sound reaches a speaker -- the
 * assertion is on the reply text the page renders.
 */
import fs from 'fs';
import path from 'path';
import { test, expect, type Page } from '@playwright/test';

const WAV = fs
  .readFileSync(path.join(__dirname, 'fixtures', 'fleet-status-question.wav'))
  .toString('base64');

async function enterAsGuest(page: Page) {
  const enter = page.getByRole('button', { name: /^Enter$/ });
  await enter
    .or(page.getByTestId('fleet-mic'))
    .first()
    .waitFor({ state: 'visible', timeout: 60_000 });
  if (await enter.count()) await enter.first().click({ timeout: 15_000 });
}

test('/fleet hears a spoken question and answers it', async ({ page }) => {
  test.setTimeout(240_000);
  await page.addInitScript(b64 => {
    const sources: AudioBufferSourceNode[] = [];
    const fetch0 = window.fetch;
    window.fetch = function (input: RequestInfo | URL, init?: RequestInit) {
      const url = String((input as Request)?.url ?? input);
      if (/\/voice\/hear/.test(url)) {
        sources.forEach(s => {
          try {
            s.stop();
          } catch {
            /* already stopped */
          }
        });
      }
      return fetch0(input, init);
    };
    MediaDevices.prototype.getUserMedia = async function () {
      const ac = new AudioContext();
      await ac.resume();
      const bin = Uint8Array.from(atob(b64), ch => ch.charCodeAt(0)).buffer;
      const speech = await ac.decodeAudioData(bin);
      // 6s of speech in an 8s loop: the VAD needs the silence to call the utterance finished.
      const loop = ac.createBuffer(1, ac.sampleRate * 8, ac.sampleRate);
      loop.copyToChannel(
        speech.getChannelData(0).slice(0, ac.sampleRate * 6),
        0,
      );
      const src = ac.createBufferSource();
      src.buffer = loop;
      src.loop = true;
      const dst = ac.createMediaStreamDestination();
      src.connect(dst);
      src.start(ac.currentTime + 1);
      sources.push(src);
      return dst.stream;
    };
  }, WAV);

  // Into the CI log: where a failing run stopped (libraries, VAD, hear, stream) is otherwise a guess.
  page.on('console', m => {
    if (/voice|vad|mic|ort|onnx|audio|hear/i.test(m.text())) {
      console.log(`[page ${m.type()}] ${m.text().slice(0, 300)}`);
    }
  });
  page.on('pageerror', e =>
    console.log(`[page error] ${e.message.slice(0, 300)}`),
  );

  const answered = page.waitForResponse(
    r => /\/voice\/stream/.test(r.url()) && r.request().method() === 'POST',
    { timeout: 120_000 },
  );
  await page.goto('/fleet', { waitUntil: 'domcontentloaded' });
  await enterAsGuest(page);
  await page.getByTestId('fleet-mic').tap();

  // Heard: the page renders the final transcript of the utterance.
  await expect(
    page.getByText(/current status of the fleet/i).first(),
  ).toBeVisible({
    timeout: 90_000,
  });
  // Answered: the brain's reply streams back and the page renders it with its timing.
  expect((await answered).status()).toBe(200);
  await expect(page.getByText(/reply \d+(\.\d+)?s/).first()).toBeVisible({
    timeout: 120_000,
  });
});
