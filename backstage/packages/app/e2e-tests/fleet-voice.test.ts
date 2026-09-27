// /fleet voice, end to end: a spoken question goes in through the microphone, voice-router hears
// it, the brain answers, the answer is spoken, and the turn is recorded with its timings.
//
// WHY. A voice path proved by a unit test or a synthetic probe is not proved (AGENTS.md §3). This
// gives Chrome a real recording as its microphone, clicks the real mic on /fleet, and reads the
// router's own turn record for the result. Nothing in the path is mocked.
//
// Needs: the local stack (fleet-regression's stack-up step) and voice-router on 127.0.0.1:8091
// with its brain reachable. Run: platform/estate/intents/fleet-regression.yaml.
import { execFileSync } from 'child_process';
import { test, expect } from '@playwright/test';

const ROUTER = 'http://127.0.0.1:8091';
const WAV = '/tmp/fleet-voice-utterance.wav';
const SAID = 'how many sessions are running';

// macOS speaks the question; 30 s of silence follows it. Chrome loops a fake microphone file from
// the moment the browser starts, so the page joins the loop at an unknown point: the test waits
// for a whole question, and the silence lets its answer finish before the next repeat barges in.
execFileSync('say', ['-o', '/tmp/fleet-voice-utterance.aiff', SAID]);
execFileSync('afconvert', ['-f', 'WAVE', '-d', 'LEI16@16000', '-c', '1', '/tmp/fleet-voice-utterance.aiff', WAV]);
execFileSync('python3', ['-c', `
import wave
r = wave.open("${WAV}"); p = r.getparams(); f = r.readframes(r.getnframes()); r.close()
w = wave.open("${WAV}", "wb"); w.setparams(p); w.writeframes(f + b"\\0\\0" * p.framerate * 30); w.close()
`]);

test.use({
  channel: 'chrome',
  launchOptions: {
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      `--use-file-for-fake-audio-capture=${WAV}`,
      '--autoplay-policy=no-user-gesture-required',
    ],
  },
});

test('/fleet hears a spoken question and voice-router answers it, timed', async ({ page, request }) => {
  test.setTimeout(200_000);
  const before = (await (await request.get(`${ROUTER}/voice/turns`)).json()).summary.turns;

  const turnsRead = page.waitForResponse(r => r.url() === `${ROUTER}/voice/turns` && r.status() === 200);
  await page.goto('/fleet', { waitUntil: 'commit' });
  await page.getByRole('button', { name: 'Enter' }).click();
  await turnsRead; // the page found the router, so the mic is voice-router's

  await page.getByTestId('fleet-mic').click();

  // The whole question, heard: the page shows the final transcript of each utterance.
  await expect(page.getByText(/how many sessions are running/i).first()).toBeVisible({ timeout: 60_000 });

  // The router's record is the verdict: that question's turn (five words) completed, with an
  // answer spoken. An empty brain reply is a failure -- the person hears silence.
  let turn: any;
  await expect
    .poll(
      async () => {
        const body = await (await request.get(`${ROUTER}/voice/turns`)).json();
        if (body.summary.turns <= before) return 'no new turn';
        turn = body.recent.find((t: any) => t.kind === 'ask' && t.words >= 5);
        return turn ? `${turn.outcome}${turn.detail ? `: ${turn.detail}` : ''}` : 'whole question not recorded';
      },
      { timeout: 60_000, intervals: [1_000] },
    )
    .toBe('ok');
  expect(turn.first_audio_s).toBeGreaterThan(0);
  expect(turn.clauses).toBeGreaterThan(0);
  console.log(`voice turn: asr_s=${turn.asr_s} llm_first_s=${turn.llm_first_s} first_audio_s=${turn.first_audio_s} words=${turn.words} clauses=${turn.clauses}`);
});
