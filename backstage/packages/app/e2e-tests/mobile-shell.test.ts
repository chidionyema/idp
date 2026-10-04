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
