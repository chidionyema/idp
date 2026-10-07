/*
 * Which device does the mic message speak to?
 *
 * WHY. The founder reads /fleet and /face from a phone, and every refusal message used to name
 * macOS ("System Settings → Privacy & Security → Microphone → turn Chrome ON"). On a phone that
 * instruction cannot be followed, so the founder was told to do something impossible and the real
 * fix stayed invisible. `micPlatform()` is what chooses the wording, so it is tested directly
 * rather than only through a browser run that needs a CI runner to reproduce.
 *
 * The iPad cases are here because iPadOS 13+ reports `Macintosh` in its user agent and would
 * otherwise be served the Mac instruction -- the same bug, one device over. A real Mac never
 * reports touch points, which is the only thing that separates them.
 */
import { micPlatform, siteSettingFix } from './useEstateVoice';

const UA = {
  iphone:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  ipod: 'Mozilla/5.0 (iPod touch; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
  // iPadOS 13+ desktop-class UA: it says Macintosh and is NOT a Mac.
  ipad: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
  android:
    'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
  macChrome:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  linuxChrome:
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
};

function withUa(ua: string, maxTouchPoints: number, fn: () => void) {
  const realUa = navigator.userAgent;
  const realTp = navigator.maxTouchPoints;
  Object.defineProperty(navigator, 'userAgent', {
    value: ua,
    configurable: true,
  });
  Object.defineProperty(navigator, 'maxTouchPoints', {
    value: maxTouchPoints,
    configurable: true,
  });
  try {
    fn();
  } finally {
    Object.defineProperty(navigator, 'userAgent', {
      value: realUa,
      configurable: true,
    });
    Object.defineProperty(navigator, 'maxTouchPoints', {
      value: realTp,
      configurable: true,
    });
  }
}

describe('micPlatform', () => {
  it('says ios for an iPhone', () => {
    withUa(UA.iphone, 5, () => expect(micPlatform()).toBe('ios'));
  });

  it('says ios for an iPod touch', () => {
    withUa(UA.ipod, 5, () => expect(micPlatform()).toBe('ios'));
  });

  it('says ios for an iPad that claims to be a Macintosh', () => {
    // The trap: iPadOS 13+ UAs contain "Macintosh". maxTouchPoints is what saves it.
    withUa(UA.ipad, 5, () => expect(micPlatform()).toBe('ios'));
  });

  it('does NOT say ios for a real Mac, which has no touch points', () => {
    withUa(UA.ipad, 0, () => expect(micPlatform()).toBe('desktop'));
  });

  it('says android for a Pixel', () => {
    withUa(UA.android, 5, () => expect(micPlatform()).toBe('android'));
  });

  it('says desktop for Mac Chrome', () => {
    withUa(UA.macChrome, 0, () => expect(micPlatform()).toBe('desktop'));
  });

  it('says desktop for Linux Chrome', () => {
    withUa(UA.linuxChrome, 0, () => expect(micPlatform()).toBe('desktop'));
  });

  it('says desktop when the user agent is empty, rather than throwing', () => {
    withUa('', 0, () => expect(micPlatform()).toBe('desktop'));
  });

  // ---------------------------------------------------------------------------
  // The sentence itself, which is what the person actually reads.
  // ---------------------------------------------------------------------------

  it('NEVER sends an iOS person into Safari settings', () => {
    // cf35fb207 required the opposite of this and put the Settings tour back on main. The estate's
    // owner forbade it in his own words -- "we are not going to be telling users to set anything on
    // safari", "safari should promt the user" -- and the Playwright mobile suite already asserts
    // NOT /Settings|padlock|chrome:\/\/settings/i. This test was the one gate defending the defect.
    withUa(UA.iphone, 5, () => {
      const s = siteSettingFix();
      expect(s).not.toMatch(/Settings/);
      expect(s).not.toMatch(/Safari/);
      expect(s).not.toMatch(/Allow/);
    });
  });

  it('names the device on iOS, and asserts nothing it did not measure', () => {
    // The old string named Safari as the cause. Safari is not always the holder -- the OS can be,
    // and so can a policy. Naming iOS is the strongest claim the code can actually support.
    withUa(UA.iphone, 5, () => {
      expect(siteSettingFix()).toMatch(/iOS/);
      expect(siteSettingFix()).toMatch(/microphone/i);
    });
  });

  it('says the same thing as osRefusalFix, because they answer one refusal', () => {
    // On main these two disagreed: one said "tap the mic again", the other "open Safari settings",
    // for the same refusal in the same file. siteSettingFix now delegates, so they cannot drift.
    withUa(UA.iphone, 5, () => {
      expect(siteSettingFix()).toMatch(/tap the mic again/);
    });
  });

  it('still offers the tap on a platform where the re-prompt is real', () => {
    withUa(UA.linuxChrome, 0, () => {
      expect(siteSettingFix()).toMatch(/tap the mic again/);
    });
  });

  // ---------------------------------------------------------------------------
  // The home-screen icon: a different refusal, because the re-prompt is NOT real there
  // (bugs.webkit.org 185448, 215884, 252465). isStandaloneHomeScreen() is not exported, so this
  // goes through the one function that already delegates to it.
  // ---------------------------------------------------------------------------

  function withStandalone(value: boolean | undefined, fn: () => void) {
    const real = (navigator as any).standalone;
    Object.defineProperty(navigator, 'standalone', { value, configurable: true });
    try {
      fn();
    } finally {
      Object.defineProperty(navigator, 'standalone', { value: real, configurable: true });
    }
  }

  it('does NOT offer "tap again" on an iOS home-screen icon -- that retry cannot work there', () => {
    withUa(UA.iphone, 5, () => {
      withStandalone(true, () => {
        expect(siteSettingFix()).not.toMatch(/tap the mic again/);
        expect(siteSettingFix()).toMatch(/home-screen icon/i);
      });
    });
  });

  it('still says "tap the mic again" on an iOS Safari tab, where it IS real', () => {
    withUa(UA.iphone, 5, () => {
      withStandalone(false, () => {
        expect(siteSettingFix()).toMatch(/tap the mic again/);
      });
      withStandalone(undefined, () => {
        expect(siteSettingFix()).toMatch(/tap the mic again/);
      });
    });
  });

  it('never calls an iPhone "standalone" on Android or desktop, where the flag is irrelevant', () => {
    // Guards against a future refactor reading `navigator.standalone` for a platform where no
    // browser sets it meaningfully and it would read as a false positive.
    withUa(UA.android, 5, () => {
      withStandalone(true, () => {
        expect(siteSettingFix()).toMatch(/tap the mic again/);
      });
    });
  });
});
