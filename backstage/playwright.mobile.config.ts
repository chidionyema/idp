/*
 * Mobile Playwright projects: iPhone (WebKit) and Pixel (Chromium).
 *
 * WHY THIS FILE EXISTS. The founder tests /face and /fleet from a phone, not a laptop
 * (2026-10-04). Every browser proof the estate ran before this file came from desktop Chrome via
 * `channel: 'chrome'`, and a desktop result is not evidence about a phone -- measured: the desktop
 * run reported `NotAllowedError: Permission denied by system` and the agent read it as a macOS TCC
 * refusal, which cannot be the founder's cause because a phone has no macOS System Settings.
 *
 * WHY A SEPARATE CONFIG. backstage/playwright.config.ts runs the desktop suite the way Backstage
 * ships it (`generateProjects()`), and it is not this file's job to change that. This config runs
 * the mobile checks only, on the same Playwright the estate already uses.
 *
 * WHERE IT CAN RUN. Playwright's WebKit and Chromium binaries are built for Linux, macOS 14+ and
 * Windows; they are NOT built for macOS 13. Measured on the founder's laptop 2026-10-04, from
 * Playwright's own installer: `ERROR: Playwright does not support webkit on mac13` and
 * `ERROR: Playwright does not support chromium on mac13`. So this config runs in CI
 * (ubuntu-latest), never on that laptop, which is also what makes the proof remote rather than
 * laptop-bound.
 */
import { defineConfig, devices } from '@playwright/test';

const BASE = process.env.PLAYWRIGHT_URL ?? 'https://catalogue.mumchimp.com';

export default defineConfig({
  testDir: './packages/app/e2e-tests',
  testMatch: /mobile-.*\.test\.ts$/,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  forbidOnly: !!process.env.CI,
  retries: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'e2e-mobile-report' }]],
  outputDir: 'node_modules/.cache/e2e-mobile-results',
  use: {
    baseURL: BASE,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },
  projects: [
    {
      // Safari's engine. The permission query and getUserMedia shape the founder's iPhone sees.
      name: 'iphone',
      use: { ...devices['iPhone 13'] },
    },
    {
      name: 'pixel',
      use: { ...devices['Pixel 7'] },
    },
  ],
});
