// /fleet voice controls a person uses before saying a word: the voice list, and the mic on one
// agent. Both were cut out on 2026-09-27 when the page switched to voice-router, and nothing
// noticed, because the only voice test asked the fleet one question.
//
// Needs the local stack (fleet-regression's stack-up step). Run: platform/estate/intents/fleet-regression.yaml.
import { test, expect } from '@playwright/test';

test.use({
  channel: 'chrome',
  launchOptions: { args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] },
});

async function openFleet(page: any, errors: string[]) {
  page.on('pageerror', (e: Error) => errors.push(e.message));
  await page.goto('/fleet', { waitUntil: 'commit' });
  await page.getByRole('button', { name: 'Enter' }).click();
}

test('/fleet renders without an uncaught error', async ({ page }) => {
  const errors: string[] = [];
  await openFleet(page, errors);
  await expect(page.getByTestId('fleet-mic')).toBeVisible({ timeout: 60_000 });
  await page.waitForTimeout(3_000);
  expect(errors).toEqual([]);
});

test('/fleet lists the installed voices and switches to the one picked', async ({ page }) => {
  const errors: string[] = [];
  await openFleet(page, errors);
  const picker = page.getByTestId('voice-picker');
  await page.getByTestId('voice-picker-chip').click();
  const local = page.locator('[data-voice^="kokoro:"], [data-voice^="say:"], [data-voice^="piper:"]');
  await expect(local.first()).toBeVisible({ timeout: 60_000 });
  const count = await local.count();
  console.log(`voice list: ${count} local voices`);
  expect(count).toBeGreaterThan(1);

  const before = await picker.getAttribute('data-value');
  const values = await local.evaluateAll((els: Element[]) => els.map((e) => e.getAttribute('data-voice')));
  const other = values.find((v) => v && v !== before)!;
  await page.locator(`[data-voice="${other}"]`).click();
  await expect(picker).toHaveAttribute('data-value', other, { timeout: 20_000 });

  // Put the founder's voice back.
  if (before && values.includes(before)) {
    await page.getByTestId('voice-picker-chip').click();
    await page.locator(`[data-voice="${before}"]`).click();
    await expect(picker).toHaveAttribute('data-value', before, { timeout: 20_000 });
  }
  expect(errors).toEqual([]);
});

test('/fleet talks to one agent on its own mic, never through voice-router', async ({ page }) => {
  const errors: string[] = [];
  const routerSockets: string[] = [];
  page.on('websocket', (ws: any) => { if (ws.url().includes(':8091')) routerSockets.push(ws.url()); });
  // Streaming chosen: the case that broke. Addressing an agent must still bypass the router.
  await page.addInitScript(() => window.localStorage.setItem('fleet.voice.streaming', '1'));
  await openFleet(page, errors);

  const talk = page.locator('[data-testid^="talk-"]').first();
  if (!(await talk.isVisible().catch(() => false))) await page.getByTestId('panel-open').click();
  await expect(talk).toBeVisible({ timeout: 60_000 });
  const id = ((await talk.getAttribute('data-testid')) || '').slice('talk-'.length);
  await talk.click();

  const addressee = page.getByTestId('voice-addressee');
  await expect(addressee).toBeVisible({ timeout: 30_000 });
  await expect(addressee).not.toHaveText('the fleet');
  console.log(`talking to: ${await addressee.textContent()} (${id})`);
  expect(routerSockets).toEqual([]);

  await talk.click(); // stop
  expect(errors).toEqual([]);
});
