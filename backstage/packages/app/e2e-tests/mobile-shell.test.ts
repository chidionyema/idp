/*
 * The mobile face and fleet pages: does a phone get the app at all, and can it reach the microphone?
 *
 * WHY. The founder uses /face and /fleet from a phone. The estate had no mobile browser check, so
 * every claim about the mobile experience was a desktop measurement wearing a phone's name.
 * The defect, measured 2026-10-04 in a real browser: /fleet served the app, then threw
 * `TypeError: Cannot read properties of undefined (reading 'toFixed')` while rendering (the live
 * /fleetview/efficiency payload carried no cache_hit_pct, and the hook cast it `as Frame`), which
 * unmounted the Reactor before its mic control mounted -- 0 canvases, getUserMedia never called.
 * An earlier `GET /fleet` 302 to the Oracle login wall was a separate, already-fixed symptom, not
 * this cause. This test is what proves the fix, on the engines a phone actually runs.
 *
 * WHAT IT PROVES, AND WHAT IT DOES NOT. Chromium fake-mic flags (--use-fake-ui-for-media-stream,
 * --use-fake-device-for-media-stream) do not exist in WebKit, and a phone's own permission prompt
 * cannot be answered by an automated run. So this test does NOT claim a spoken turn completes on a
 * phone. It proves the two things that ARE decidable here, and that the founder's defect was made
 * of: (1) the phone is served the app instead of a login redirect, and (2) the page reaches a real
 * getUserMedia call, with the refusal named exactly if one happens. A test that asserted more would
 * be the assertion-instead-of-proof defect this estate keeps paying for.
 *
 * RUN: CI only (ubuntu-latest). Playwright does not build WebKit or Chromium for macOS 13, so this
 * cannot run on the founder's laptop -- measured 2026-10-04 from the installer.
 *   yarn playwright test --config playwright.mobile.config.ts
 */
import { test, expect } from '@playwright/test';

// The app serves its shell on /face and /fleet to a signed-out browser. Anything that redirects to
// an identity provider is the wall, named so a failure is readable.
const LOGIN_WALL =
  /oraclecloud\.com|idcs-|identity\.oraclecloud|\/oauth2\/|\/login/i;

test.describe('mobile shell', () => {
  for (const path of ['/fleet', '/face']) {
    test(`a phone is served ${path}, not a login redirect`, async ({
      page,
    }) => {
      const res = await page.goto(path, { waitUntil: 'domcontentloaded' });
      expect(page.url(), `${path} redirected to ${page.url()}`).not.toMatch(
        LOGIN_WALL,
      );
      expect(res?.status(), `${path} status`).toBeLessThan(400);
      // The document is the app, not an identity provider's page.
      const html = await page.content();
      expect(html).not.toMatch(LOGIN_WALL);
      // The app mounts something: Backstage's root plus our own canvases.
      await expect(page.locator('body')).toBeVisible();
    });
  }
});

test.describe('mobile microphone reachability', () => {
  // Both pages the founder uses from a phone carry the same control and the same contract. /face's
  // mic was unreachable by test because its button had no stable handle (measured 2026-10-04: only
  // FleetReactorApp's button carried `data-testid`, FacePage's carried none), so every claim about
  // /face on a phone was a claim nothing could check. The handle now exists and both pages are
  // judged by the same rule below.
  for (const [path, testid] of [
    ['/fleet', 'fleet-mic'],
    ['/face', 'face-mic'],
  ] as const) {
    test(`${path} reaches getUserMedia, or names the refusal`, async ({
      page,
      context,
    }) => {
      // The one permission an automated run CAN grant. On a phone this prompt is the user's; here it
      // stands in for a granted prompt so the code path past the permission is exercised.
      await context.grantPermissions(['microphone'], {
        origin: new URL(
          process.env.PLAYWRIGHT_URL ?? 'https://catalogue.mumchimp.com',
        ).origin,
      });

      await page.addInitScript(() => {
        const w = window as any;
        w.__mic = {
          hasMediaDevices: false,
          hasGetUserMedia: false,
          secure: false,
          calls: [],
        };
        const md = navigator.mediaDevices;
        w.__mic.hasMediaDevices = !!md;
        w.__mic.hasGetUserMedia = !!(md && md.getUserMedia);
        w.__mic.secure = window.isSecureContext;
        if (md && md.getUserMedia) {
          const orig = md.getUserMedia.bind(md);
          md.getUserMedia = async (c: MediaStreamConstraints) => {
            const rec: any = {
              audio: !!(c && c.audio),
              ok: null,
              errName: null,
              err: null,
            };
            w.__mic.calls.push(rec);
            try {
              const s = await orig(c);
              rec.ok = true;
              rec.tracks = s.getAudioTracks().map((t: MediaStreamTrack) => ({
                label: t.label,
                state: t.readyState,
              }));
              return s;
            } catch (e: any) {
              rec.ok = false;
              rec.errName = e?.name ?? 'Error';
              rec.err = String(e?.message ?? e);
              throw e;
            }
          };
        }
      });

      await page.goto(path, { waitUntil: 'load' });
      expect(page.url(), `${path} redirected to ${page.url()}`).not.toMatch(
        LOGIN_WALL,
      );

      // Pin the payload that crashes this page onto the route, so the test does not depend on
      // which way the live /efficiency call happens to land. Measured 2026-10-04: the endpoint is
      // bearer-guarded, and an unmocked run gets either this named-absence body or an auth failure
      // depending on session state -- a test whose verdict moves with the auth wall measures the
      // wall, not the page. Replayed here, the body is the exact 200 JSON the live /fleet receives
      // (curl, 2026-10-04): {"since":"1h","error":"efficiency report not in this image: /app/bin/
      // estate-efficiency-report","available":false}. It carries no cache_hit_pct, so before the
      // normaliser the page threw `TypeError ... reading 'toFixed'` while rendering and unmounted
      // the Reactor before the mic mounted. With the fix, the control below must still appear.
      await page.route('**/efficiency*', route =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            since: '1h',
            error:
              'efficiency report not in this image: /app/bin/estate-efficiency-report',
            available: false,
          }),
        }),
      );
      await page.reload({ waitUntil: 'load' });

      // The mic lives inside the FleetReactor canvas, which mounts after the bundle boots -- so wait
      // for the control itself, not for the document. Measured 2026-10-04 in CI: with only
      // domcontentloaded the run reached the tap with the app still booting, found nothing, reported
      // tapped=false calls=0 and PASSED on the weaker assertion. That is the assertion-instead-of-
      // proof defect: the test was green while the thing it names had not happened. The control is
      // now waited for and asserted, so a fleet page that never renders its mic is RED, not quiet.
      const micButton = page.getByTestId(testid);
      // The budget is generous on purpose, and it is not the assertion. /fleet lazily loads its
      // route chunks -- measured 2026-10-04 from the deployed runtime map:
      // `loader:()=>Promise.all([a.e("9371"),a.e("9804")])`, 474KB + 102KB -- and only then mounts
      // React and the canvas overlay that holds the control. On a cold, uncached CI runner against
      // the live site that is tens of seconds before the button exists. The earlier 30s deadline
      // was a cold-boot race dressed as a contract: it failed while the page was still downloading
      // its own bundle, which says nothing about the microphone. The contract is the decided outcome
      // asserted below; this wait only has to outlast the download.
      await expect(
        micButton,
        `${path} never rendered its mic control (testid ${testid}); a phone cannot ask for the microphone on a page that has no control to tap`,
      ).toBeVisible({ timeout: 90_000 });

      // Ask the page for the mic the way a person does: a tap. Mobile engines require a user
      // gesture, so this is the only shape that can work on a phone.
      await micButton.first().click({ timeout: 15_000 });
      const tapped = true;

      // Give the page time to reach a decided state. Not a bare sleep: `start()` pre-flights the
      // permission, then DOWNLOADS the voice libraries (VOICE_ASSETS) before opening the device, so a
      // tap on a cold page legitimately needs more than a moment. We poll for the page's own words.
      // `window.__mic.calls` is the instrumented getUserMedia; `voiceDetail` is what the UI says.
      let mic: any = null;
      let detail = '';
      for (let i = 0; i < 30; i++) {
        mic = await page.evaluate(() => (window as any).__mic);
        detail = await page.evaluate(id => {
          const el = document.querySelector(
            `[data-testid="${id}"]`,
          ) as HTMLElement | null;
          return (
            (el?.getAttribute('title') ?? '') +
            ' ' +
            (document.body.innerText || '')
          );
        }, testid);
        if (
          mic.calls.length > 0 ||
          /microphone|mic|blocked|denied|not-allowed|https/i.test(detail)
        ) {
          break;
        }
        await page.waitForTimeout(1_000);
      }

      // What must be true on every engine: the API exists and the origin is a secure context. Without
      // these the page could never ask for a phone microphone at all.
      expect(mic.hasMediaDevices, 'navigator.mediaDevices is missing').toBe(
        true,
      );
      expect(
        mic.hasGetUserMedia,
        'navigator.mediaDevices.getUserMedia is missing',
      ).toBe(true);
      expect(
        mic.secure,
        'not a secure context -- a phone refuses the mic outright',
      ).toBe(true);

      // If the page asked, the refusal (if any) must be named, never blank.
      for (const call of mic.calls) {
        if (!call.ok) {
          expect(
            call.errName,
            'a refused mic must carry its error name',
          ).toBeTruthy();
        }
      }

      // THE DECISIVE ASSERTION. A person tapped the mic, so the page must arrive at ONE of exactly
      // two decided states, and this is the whole contract:
      //   (a) it called getUserMedia -- and then it must have a live track or a NAMED error, or
      //   (b) it refused BEFORE calling, which is only correct when it names the fix on screen.
      // Silence is never acceptable: `tapped=false calls=0` with nothing said is the exact defect the
      // founder reported, and the earlier version of this test PASSED on it (measured in CI
      // 2026-10-04). Reachability alone was not the claim; a decided outcome is.
      const namedFix =
        /microphone (blocked|unavailable)|not on https|padlock|denied|not-allowed/i.test(
          detail,
        );
      if (mic.calls.length === 0) {
        expect(
          namedFix,
          `tapped the mic, the page never called getUserMedia, and it named no reason ` +
            `(tapped=${tapped}); a tap that reaches no device and says nothing is the defect. ` +
            `page said: ${detail.slice(0, 300)}`,
        ).toBe(true);
      } else {
        // (a) The refusal must be named, and a grant must carry a live track -- "asked" and "got it"
        // are different facts.
        const call = mic.calls[mic.calls.length - 1];
        if (call.ok) {
          expect(
            (call.tracks ?? []).length,
            'getUserMedia resolved but returned no audio track',
          ).toBeGreaterThan(0);
        } else {
          expect(
            call.errName,
            'a refused mic must carry its error name',
          ).toBeTruthy();
        }
      }

      // The decisive line, printed so a run's log says what happened rather than only pass/fail.
      console.log(
        `mobile mic ${path}: tapped=${tapped} calls=${mic.calls.length} ` +
          (mic.calls
            .map((c: any) => (c.ok ? 'granted' : c.errName))
            .join(',') || 'none'),
      );
    });
  }
});

/*
 * THE REFUSAL MUST SPEAK THE LANGUAGE OF THE DEVICE THAT REFUSED (2026-10-04).
 *
 * WHY. `micRefusalDetail()` ended unconditionally at "System Settings → Privacy & Security →
 * Microphone → turn Chrome ON", and `micBlocker()`'s site-setting branch pointed at the padlock
 * and at `chrome://settings/content/microphone`. The founder reads the fleet from a PHONE: no
 * macOS System Settings, no Chrome settings URL, and (on iOS) no padlock. So a phone-side refusal
 * rendered a fix that cannot be followed -- while ASSERTING macOS as the cause. A message that
 * guesses the platform is the same defect as a gate that cannot fail, and it is why "microphone
 * blocked" survived being "fixed" repeatedly.
 *
 * WHAT THIS PROVES. The tests above grant permission, so the mic SUCCEEDS there and no refusal
 * string is ever rendered -- asserting the message inside them would assert nothing. This test
 * forces the one state that renders a fix (getUserMedia absent on the page) and reads the page's
 * own words back, ON THE DESCRIPTOR'S OWN PLATFORM. The Playwright device descriptors set a real
 * iPhone/Pixel user-agent, so `micPlatform()` genuinely branches; nothing here is stubbed to a
 * string we then check for.
 *
 * DECIDABLE ACROSS ENGINES, deliberately: this asserts TEXT the app chose, not a device result, so
 * it means the same thing on WebKit (no fake-mic flags) as on Chromium. It does not claim a
 * spoken turn completes, and it does not claim the founder's phone has granted anything -- that
 * lives in the phone's own settings and no browser test can read it.
 */
test.describe('mobile microphone refusal names the device', () => {
  for (const [path, testid] of [
    ['/fleet', 'fleet-mic'],
    ['/face', 'face-mic'],
  ] as const) {
    test(`${path} names a fix this device can follow`, async ({ page }) => {
      // Hide getUserMedia BEFORE the bundle runs. This is the `!isSecureContext || !mediaDevices`
      // branch of micBlocker() -- the one path that renders a pre-flight fix without needing a
      // refusal from an OS we cannot control from CI.
      await page.addInitScript(() => {
        Object.defineProperty(navigator, 'mediaDevices', {
          configurable: true,
          get: () => undefined,
        });
      });

      await page.goto(path, { waitUntil: 'load' });
      expect(page.url(), `${path} redirected to ${page.url()}`).not.toMatch(
        LOGIN_WALL,
      );

      // The same named-absence replay the reachability test pins, so this test cannot be taken
      // down by the live /efficiency payload; see the comment there for the measured body.
      await page.route('**/efficiency*', route =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            since: '1h',
            error:
              'efficiency report not in this image: /app/bin/estate-efficiency-report',
            available: false,
          }),
        }),
      );
      await page.reload({ waitUntil: 'load' });

      const micButton = page.getByTestId(testid);
      await expect(
        micButton,
        `${path} never rendered its mic control (testid ${testid})`,
      ).toBeVisible({ timeout: 90_000 });

      // Read the device the page believes it is on -- the same UA the app branches from.
      const ua = await page.evaluate(() => navigator.userAgent);
      const platform = /iPhone|iPad|iPod/i.test(ua)
        ? 'ios'
        : /Android/i.test(ua)
          ? 'android'
          : 'desktop';
      // A descriptor that reports desktop would make the assertion below meaningless, so it is
      // itself asserted rather than assumed.
      expect(
        platform,
        `this project must run a phone descriptor to test the phone message; UA was: ${ua}`,
      ).not.toBe('desktop');

      await micButton.first().click({ timeout: 15_000 });

      // Poll for the page's own words: `start()` names the block in `voice.detail`, surfaced on the
      // control's title.
      let detail = '';
      for (let i = 0; i < 30; i++) {
        detail = await page.evaluate(id => {
          const el = document.querySelector(
            `[data-testid="${id}"]`,
          ) as HTMLElement | null;
          return (
            (el?.getAttribute('title') ?? '') +
            ' ' +
            (document.body.innerText || '')
          );
        }, testid);
        if (/microphone/i.test(detail)) break;
        await page.waitForTimeout(1_000);
      }

      // THE FIRST ASSERTION, and the one this test was missing. The old version asserted only
      // `/microphone (blocked|unavailable)/`, which the WRONG message also matches: measured on LIVE
      // production 2026-10-04, an iPhone and a Pixel descriptor were both told "this page is not on
      // https" while the page WAS on https (https://catalogue.mumchimp.com). The test was green
      // while the page named a cause that was false and a fix that was impossible to follow. The
      // page under test here is served over https by construction, so a message that blames the URL
      // is itself the defect.
      expect(
        detail,
        `the page is on https and told a phone to move to https -- the message names a cause that ` +
          `is not the cause. page said: ${detail.slice(0, 300)}`,
      ).not.toMatch(/not on https/i);

      // A named block, and the name must fit the platform that rendered it.
      expect(
        detail,
        `tapped the mic with no mediaDevices and the page named no cause; page said: ${detail.slice(0, 300)}`,
      ).toMatch(/microphone (blocked|unavailable)/i);

      // The exact defect: a Mac-only instruction shown to a phone. These strings cannot be
      // followed on iOS or Android, so their presence on a phone descriptor is the bug.
      expect(
        detail,
        'a phone was told to open macOS System Settings -- that instruction cannot be followed ' +
          `on ${platform}. page said: ${detail.slice(0, 300)}`,
      ).not.toMatch(/System Settings → Privacy & Security → Microphone/i);
      expect(
        detail,
        `a phone was told to use chrome://settings/content/microphone, which ${platform} has no ` +
          `such surface for. page said: ${detail.slice(0, 300)}`,
      ).not.toMatch(/chrome:\/\/settings/i);

      // And it must name the platform's OWN path, not merely avoid the Mac one. This is the
      // positive half: silence about the real fix is as useless as the wrong fix.
      if (platform === 'ios') {
        expect(
          detail,
          `an iOS device must be told the iOS Settings path. page said: ${detail.slice(0, 300)}`,
        ).toMatch(/Settings → Safari → Microphone/i);
      } else {
        expect(
          detail,
          `an Android device must be told the Android permission path. page said: ${detail.slice(0, 300)}`,
        ).toMatch(/Permissions/i);
      }

      console.log(
        `mobile mic refusal ${path}: platform=${platform} said=${detail
          .replace(/\s+/g, ' ')
          .slice(0, 160)}`,
      );
    });
  }
});
