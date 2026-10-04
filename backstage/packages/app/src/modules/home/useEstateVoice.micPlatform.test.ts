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
import { micPlatform } from './useEstateVoice';

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
});
