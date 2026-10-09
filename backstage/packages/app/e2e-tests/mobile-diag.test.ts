/* DIAGNOSTIC ONLY (#5560) -- draft PR, never merged. */
import { test, expect, type Page } from '@playwright/test';

// The app serves its shell on /face and /fleet to a signed-out browser. Anything that redirects to
// an identity provider is the wall, named so a failure is readable.
const LOGIN_WALL =
  /oraclecloud\.com|idcs-|identity\.oraclecloud|\/oauth2\/|\/login/i;

// PRESS THE GUEST WALL'S Enter, WAITING FOR WHICHEVER OF IT OR THE MIC DRAWS FIRST (2026-10-09).
// This used to be `if (await enter.isVisible({ timeout: 20_000 }))`, and `isVisible` IGNORES its
// timeout: it reads the page once. Measured on ubuntu-latest WebKit (the iPhone project) against
// live catalogue.mumchimp.com: at `load` the body is still empty, so the check said "no wall",
// Enter was never pressed, and the page sat on "Enter as a Guest User" for the full 90s -- every
// iPhone mic test red, and Pixel red whenever its paint lost the same race. Waiting on
// `enter.or(mic)` presses Enter when the wall shows and skips it when a session already exists.
async function enterAsGuest(page: Page, testid: string) {
  const enter = page.getByRole('button', { name: /^Enter$/ });
  await enter
    .or(page.getByTestId(testid))
    .first()
    .waitFor({ state: 'visible', timeout: 60_000 });
  if (await enter.count()) await enter.first().click({ timeout: 15_000 });
}
test.describe('DIAG original verbatim', () => {
  // Both pages the founder uses from a phone carry the same control and the same contract. /face's
  // mic was unreachable by test because its button had no stable handle (measured 2026-10-04: only
  // FleetReactorApp's button carried `data-testid`, FacePage's carried none), so every claim about
  // /face on a phone was a claim nothing could check. The handle now exists and both pages are
  // judged by the same rule below.
  for (const [path, testid] of [
    ['/fleet', 'fleet-mic'],
    
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
        const w = window as any; w.__d = { proto: 0 };
        const P = (window as any).MediaDevices?.prototype;
        if (P && P.getUserMedia) { const o = P.getUserMedia; P.getUserMedia = function (c: any) { w.__d.proto++; return o.call(this, c); }; }
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

      // STEP THROUGH THE FRONT DOOR, the way a person does.
      //
      // MEASURED 2026-10-04, in CI on ubuntu-latest AND reproduced in a browser on this laptop:
      // this test failed `8 failed, 4 passed` with "never rendered its mic control (testid
      // fleet-mic)" on BOTH /fleet and /face, on BOTH engines. The cause was not the microphone and
      // not the message. `/fleet` and `/face` sit behind sign-in, so a signed-out visit renders the
      // WALL -- the body reads "Bytesync | Guest | Enter as a Guest User" -- and this test never
      // pressed Enter, so it waited 90 seconds for a control that could not exist yet. src/modules/
      // signin/index.tsx documents the same measurement from the app's side: "before Enter the body
      // reads 'Bytesync | Guest | Enter as a Guest User', after it the board renders".
      //
      // This is why the test is written to ENTER first and judge the mic second: a page can only
      // reach for a microphone once the app is mounted, and pressing this button is what mounts it.
      // The button carries no data-testid (the wall is Backstage's own SignInPage), so it is found
      // by its exact visible name. The wall is best-effort: a run that is already signed in (the
      // session persists in localStorage, per the same file) shows no button, and then there is
      // nothing to press -- not a failure.
      await enterAsGuest(page, testid);
      await expect(
        page.getByTestId(testid),
        `${path} still showed the sign-in wall after pressing Enter; body said: ` +
          (await page.evaluate(() =>
            (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 200),
          )),
      ).toBeVisible({ timeout: 90_000 });

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

      // The mic lives inside the FleetReactor canvas, which mounts after the bundle boots AND after
      // the front door is entered (see above) -- so wait for the control itself, not for the document.
      // The `expect` on the previous line already proved it mounted; this handle is what the tap uses.
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
        console.log(`DIAG i=${i} ` + await page.evaluate(() => JSON.stringify({ calls: (window as any).__mic?.calls?.length, proto: (window as any).__d?.proto, same: (window as any).__mic && navigator.mediaDevices.getUserMedia.toString().slice(0,60), t: document.querySelector('[data-testid="fleet-mic"]')?.getAttribute('title') })));
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
      //   (b) it refused BEFORE calling, which is only correct when it says so on screen.
      // Silence is never acceptable: `tapped=false calls=0` with nothing said is the exact defect the
      // founder reported, and the earlier version of this test PASSED on it (measured in CI
      // 2026-10-04). Reachability alone was not the claim; a decided outcome is.
      //
      // WHAT IS DELIBERATELY NOT ASSERTED HERE (2026-10-05). An earlier revision matched
      // /padlock|denied|microphone (blocked|unavailable)/, which is the vocabulary of the OLD bundle
      // -- the one that answered a tap with a settings walkthrough. The founder refused that outright
      // ("we are not going to be telling users to set anything on safari"), so a test that DEMANDS
      // those words keeps the defect alive and goes red the moment the fix deploys. What this asserts
      // is the durable contract instead: a tap is either answered by the device or answered in words,
      // and the words are about the microphone. The settings-chore half is asserted as a REFUSAL by
      // the test below, on both descriptors, which is where it belongs.
      const namedFix =
        /microphone|mic\b/i.test(detail);
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
