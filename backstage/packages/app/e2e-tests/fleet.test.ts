// /fleet regression: the page the founder watches must load live data and never throw.
//
// WHY. 2026-09-27 a backend restart left an open /fleet tab sending a token the new backend's
// keys rejected: every /api/proxy/fleetview read went 401 and the board went dead, and nothing
// failed, because no test had ever loaded /fleet. This drives the real page in a real browser
// against the running stack and fails on the things the founder would see: no live data, a read
// that stays refused, an uncaught error.
//
// Run: platform/estate/intents/fleet-regression.yaml (estate-execute fleet-regression).
import { test, expect, type Response } from '@playwright/test';

// The installed Chrome: the laptop has no Playwright browser download and no room for one.
test.use({ channel: 'chrome' });

test('/fleet loads live sessions and reloads clean', async ({ page }) => {
  // The dev server compiles /fleet on first hit; a cold load takes most of a minute.
  test.setTimeout(110_000);
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  const last = new Map<string, number>();
  page.on('response', (r: Response) => {
    const u = new URL(r.url());
    if (u.pathname.startsWith('/api/proxy/fleetview/')) last.set(u.pathname, r.status());
  });

  const sessions = page.waitForResponse(
    r => new URL(r.url()).pathname === '/api/proxy/fleetview/sessions' && r.status() === 200,
  );
  await page.goto('/fleet', { waitUntil: 'commit' });
  // Local `yarn start` shows the guest sign-in to a fresh browser profile; a test profile is fresh.
  await page.getByRole('button', { name: 'Enter' }).click();
  const body = await (await sessions).json();
  expect(Array.isArray(body.sessions ?? body)).toBe(true);

  // A reload is what the founder does when the board looks stuck; it must come back live.
  const again = page.waitForResponse(
    r => new URL(r.url()).pathname === '/api/proxy/fleetview/sessions' && r.status() === 200,
  );
  // /fleet holds streams open, so `load` may never settle; the data answer is the signal.
  await page.reload({ waitUntil: 'commit' });
  await again;
  await page.waitForTimeout(3_000);

  const refused = [...last].filter(([, s]) => s >= 400);
  expect(refused, 'fleetview reads whose latest answer was a refusal').toEqual([]);
  expect(errors, 'uncaught page errors').toEqual([]);
});
