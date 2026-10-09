"""Generate the L3 per-panel Playwright spec FROM the same inventory surfaces.py uses.

The no-gap law: the spec is generated from code, not hand-written. A panel added to
room/ui without a covering entry here is impossible — the generator enumerates every
non-test .tsx and requires a signature (data-testid, aria-label, title, or a text
regex / canvas fallback), else it FAILS generation, which fails the gate.

Usage: python3 -m probes.gen_panels_spec > panels.spec.ts
Exit 1 if any panel lacks a discoverable signature (that is a gap, and gaps are red).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

_UI = "backstage/packages/app/src/modules/room/ui"
_MODULES = "backstage/packages/app/src/modules"

# Panels verified by tag/text when they carry no attribute signature.
TEXT_HOOKS = {
    "Cost": r"/\\$\\d+\\.\\d+/ or \\/\\d+\\.\\d+g\\/",  # $0.0011 · 0.4g readout
    "Waveform": "canvas",
    "SpatialCanvas": "canvas",
}
# Containers of other panels, not themselves mounted panels on /fleet.
SKIP = {
    "FleetReactorOriginal"
}  # mounted on /fleet-original, verified by its own testid there
# Interaction-triggered panels: NOT present on load; their generated test drives the real
# interaction (click an agent -> dialog -> Escape releases it).
TRIGGERED = {
    "Spotlight",
    "RadialMenu",
}  # RadialMenu: scrim only exists while the menu is open; opened by right-click


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout


def _imports(src: str, base: str) -> set[str]:
    """Resolve relative imports in a source file to repo paths (best effort)."""
    out = set()
    import posixpath

    d = base.rsplit("/", 1)[0]
    for m in re.finditer(r"from '(\.[^']+)'|import\('(\.[^']+)'", src):
        rel = m.group(1) or m.group(2)
        if not rel:
            continue
        for cand in (rel, f"{rel}.tsx", f"{rel}.ts", f"{rel}/index.ts"):
            p = posixpath.normpath(f"{d}/{cand}")
            try:
                _git("cat-file", "-e", f"HEAD:{p}")
                out.add(p)
                break
            except subprocess.CalledProcessError:
                continue
    return out


def _reachable_from(entry: str) -> set[str]:
    seen, queue = set(), [entry]
    while queue:
        f = queue.pop()
        if f in seen:
            continue
        seen.add(f)
        queue.extend(_imports(_git("show", f"HEAD:{f}"), f) - seen)
    return seen


def _face_block() -> str:
    """The /face voice-path spec, generated from the page's own strings.

    The no-gap law applies to /face too: the labels asserted here are read from
    FacePage.tsx and useEstateVoice.ts at generation time, and the utterance from
    probes/voice.py's own SCRIPTS table. If the page's words change, generation
    refuses rather than grading strings that no longer exist.
    """
    face = _git("show", f"HEAD:{_MODULES}/home/FacePage.tsx")
    hook = _git("show", f"HEAD:{_MODULES}/home/useEstateVoice.ts")

    def grab(pat: str, src: str, what: str) -> str:
        m = re.search(pat, src)
        if not m:
            print(
                f"// GENERATION FAILED — {what} not found in the /face sources",
                file=sys.stderr,
            )
            sys.exit(1)
        return m.group(1)

    idle = grab(r"off: '([^']+)'", face, "the idle button label")
    unavailable = grab(r": '(Voice[^']*)'", face, "the unavailable text")
    for needle, what in (
        ("microphone blocked", "the mic-blocked detail"),
        ("voice libraries missing (", "the voice-libraries detail"),
    ):
        if needle not in hook:
            print(
                f"// GENERATION FAILED — {what} not found in useEstateVoice.ts",
                file=sys.stderr,
            )
            sys.exit(1)
    utter = grab(
        r'\("fleet-status\.wav", "([^"]+)"',
        (Path(__file__).resolve().parent / "voice.py").read_text(),
        "the fleet-status utterance in probes/voice.py",
    )
    # The mic control on each page that talks: read from the source, so a renamed control
    # fails generation instead of a test that clicks nothing.
    fleet = _git("show", f"HEAD:{_MODULES}/room/ui/FleetReactorApp.tsx")
    talking_pages = [
        ("/face", grab(r'data-testid="(face-mic)"', face, "the /face mic control")),
        ("/fleet", grab(r'data-testid="(fleet-mic)"', fleet, "the /fleet mic control")),
    ]

    return f"""
test.describe('/face: the voice path a founder actually takes — mic included', () => {{
  // GENERATED from FacePage.tsx's own labels; if the page's words change, regeneration
  // fails rather than asserting strings that no longer exist (the no-gap law).
  const IDLE = {idle!r};
  const UNAVAILABLE = {unavailable!r};
  const BTN = /{idle.lower()}|{unavailable.lower()}/i;

  async function launchFace(args: string[]) {{
    // Per-test launch args: the mic flags belong to the BROWSER, not the context, so each
    // /face test launches its own Chrome instead of using the fixture browser.
    const b = await chromium.launch({{ channel: 'chrome', args }});
    const ctx = await b.newContext({{
      permissions: ['microphone'],
      ...(BEARER ? {{ extraHTTPHeaders: {{ authorization: `Bearer ${{BEARER}}` }} }} : {{}}),
    }});
    const page = await ctx.newPage();
    return {{ b, page }};
  }}

  test('tap-to-talk opens the microphone and the face reaches Listening', async () => {{
    test.setTimeout(120_000);
    // The fake device keeps this deterministic on any runner (CI has no audio hardware)
    // while exercising the real getUserMedia -> VAD -> state machine path on the page.
    const {{ b, page }} = await launchFace(['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream']);
    const errors: string[] = [];
    page.on('pageerror', e => errors.push(e.message));
    try {{
      await page.goto('/face', {{ waitUntil: 'commit' }});
      if (!BEARER) await page.getByRole('button', {{ name: 'Enter' }}).click();
      const btn = page.getByRole('button', {{ name: BTN }});
      await expect(btn, 'the voice service door — /voice/voices through the proxy').toBeEnabled({{ timeout: 60_000 }});
      await btn.click();
      await expect.poll(async () => (await btn.innerText()).trim(), {{ timeout: 60_000 }}).not.toBe(IDLE);
      const body = await page.locator('body').innerText();
      expect(body, 'microphone blocked — the bug the founder hit 7 times').not.toContain('microphone blocked');
      expect(body).not.toContain(UNAVAILABLE);
      expect(body).not.toContain('voice libraries missing');
      expect(errors, 'uncaught page errors on /face').toEqual([]);
    }} finally {{ await b.close(); }}
  }});

  // A WHOLE SPOKEN TURN, IN A REAL BROWSER, ON EVERY PAGE THAT TALKS. The same WAV L4 grades
  // server-side, driven through the fake MICROPHONE into the real page:
  //   mic -> VAD -> POST /voice/hear (transcript rendered) -> POST /voice/stream (the answer)
  //   -> POST /voice/say (the answer spoken).
  // Stopping at the transcript is how 2026-10-08 slipped through: hear can pass while the
  // answer and the speech fail behind it, so every leg's status is asserted, not just the text.
  for (const [route, micTestId] of {json.dumps(talking_pages)} as [string, string][]) {{
    test(`real speech through the page: ${{route}} hears, answers and speaks`, async () => {{
      test.setTimeout(240_000);
      const wav = [process.env.SURFACES_VOICE_WAV, 'probes/fixtures/fleet-status.wav',
                   '../../../probes/fixtures/fleet-status.wav', '../../probes/fixtures/fleet-status.wav']
        .find(p => p && fs.existsSync(p));
      expect(wav, 'voice fixture not found — set SURFACES_VOICE_WAV').toBeTruthy();
      if (!wav) return;
      // --use-fake-device-for-media-stream is what makes Chrome read the file at all: without it
      // the file flag is ignored and the real microphone opens (none on a runner), so the page
      // listened to silence and /voice/hear was never called -- measured 2026-10-08.
      const {{ b, page }} = await launchFace([
        '--use-fake-device-for-media-stream',
        `--use-file-for-fake-audio-capture=${{wav}}`,
        '--use-fake-ui-for-media-stream',
      ]);
      // Chrome's audio processing turns the fake FILE device to silence: with echoCancellation,
      // noiseSuppression and autoGainControl on (the VAD library's default request) the page's
      // stream peaked at 0.0000 while the same file unprocessed peaked at 1.02 -- measured
      // 2026-10-08, the VAD never fired. Processing a file is meaningless, so it is switched off
      // here and only here; everything after the mic (VAD, hear, stream, say) is the real page.
      // What this does NOT exercise: Chrome's echo canceller on a real microphone.
      await page.addInitScript(() => {{
        const md = navigator.mediaDevices;
        const gum = md.getUserMedia.bind(md);
        md.getUserMedia = (c?: MediaStreamConstraints) => {{
          const a = c && typeof c.audio === 'object' ? c.audio : {{}};
          return gum({{ ...c, audio: {{ ...a, echoCancellation: false, noiseSuppression: false, autoGainControl: false }} }});
        }};
      }});
      const errors: string[] = [];
      page.on('pageerror', e => errors.push(e.message));
      // Every status seen per leg; a later success cannot paint over an earlier failure.
      const legs: Record<string, number[]> = {{ hear: [], stream: [], say: [] }};
      page.on('response', r => {{
        const m = r.url().match(/\\/voice\\/(hear|stream|say)(?:[?#]|$)/);
        if (m) legs[m[1]].push(r.status());
      }});
      try {{
        await page.goto(route, {{ waitUntil: 'commit' }});
        if (!BEARER) await page.getByRole('button', {{ name: 'Enter' }}).click();
        const mic = page.getByTestId(micTestId);
        await expect(mic, `${{route}} mic control`).toBeVisible({{ timeout: 90_000 }});
        await mic.click();
        // On failure, name the leg that broke: a transcript that never renders is a 500 on
        // hear far more often than a rendering bug, and the statuses say which.
        const heard = await expect(page.locator('body'))
          .toContainText(new RegExp({utter!r}, 'i'), {{ timeout: 90_000 }})
          .then(() => true, () => false);
        expect(heard, `${{route}} never rendered the heard words; voice statuses ${{JSON.stringify(legs)}}`).toBe(true);
        await expect.poll(() => legs.say.length, {{ message: `${{route}} never called /voice/say`, timeout: 90_000 }})
          .toBeGreaterThan(0);
        for (const leg of ['hear', 'stream', 'say']) {{
          expect(legs[leg].length, `${{route}} /voice/${{leg}} was never called`).toBeGreaterThan(0);
          expect(legs[leg].filter(s => s !== 200), `${{route}} /voice/${{leg}} statuses ${{legs[leg]}}`).toEqual([]);
        }}
        const body = await page.locator('body').innerText();
        expect(body, 'microphone blocked on the live surface').not.toContain('microphone blocked');
        expect(body).not.toContain('voice libraries missing');
        expect(errors, `uncaught page errors on ${{route}}`).toEqual([]);
      }} finally {{ await b.close(); }}
    }});
  }}
}});
"""


def main() -> int:
    files = [
        f
        for f in _git("ls-tree", "-r", "HEAD", "--name-only", _UI).splitlines()
        if f.endswith(".tsx") and not f.endswith(".test.tsx")
    ]
    entries = []
    gaps = []
    # The mount graph: room/ui components reachable from the route table (homeModule)
    # are graded in the browser; unreachable ones are a wiring gap and the spec goes red
    # naming them — a component that exists but no route can render is a hint of a gap.
    reachable = _reachable_from(f"{_MODULES}/home/homeModule.tsx")
    unreachable = []
    for f in files:
        name = f.split("/")[-1].removesuffix(".tsx")
        if name in SKIP or name in TRIGGERED:
            continue
        if f"{_UI}/{name}.tsx" not in reachable:
            unreachable.append(name)
            continue
        src = _git("show", f"HEAD:{f}")
        m = re.search(r'data-testid="([a-z0-9-]+)"', src)
        # A testid on an error branch (harv-error, keys-error) is absent when the panel is
        # HEALTHY — prefer the always-rendered aria-label for presence grading.
        if m and m.group(1).endswith("-error"):
            m = None
        if m:
            entries.append((name, f'[data-testid="{m.group(1)}"]', "testid"))
            continue
        m = re.search(r'aria-label="([A-Za-z0-9 _-]+)"', src)
        if m:
            entries.append((name, f'[aria-label="{m.group(1)}"]', "testid"))
            continue
        if name in TEXT_HOOKS:
            entries.append(
                (
                    name,
                    TEXT_HOOKS[name],
                    "text" if "canvas" not in TEXT_HOOKS[name] else "tag",
                )
            )
            continue
        gaps.append(name)

    if gaps:
        print(
            f"// GENERATION FAILED — panels without a verifiable signature: {gaps}",
            file=sys.stderr,
        )
        return 1

    # /fleet-original keeps its own route with its own presence assertion — the "before"
    # picture beside the rewrite must stay green too, graded on the route that mounts it.
    orig_path = f"{_UI}/FleetReactorOriginal.tsx"
    orig_src = _git("show", f"HEAD:{orig_path}")
    mo = re.search(r'data-testid="([a-z0-9-]+)"', orig_src)
    if "FleetReactorOriginal" in unreachable or not mo:
        print(
            "// GENERATION FAILED — FleetReactorOriginal must be reachable at /fleet-original "
            "with a data-testid",
            file=sys.stderr,
        )
        return 1
    orig_testid = mo.group(1)

    face_block = _face_block()

    cases = "\n".join(
        f"  {{ name: '{n}', sel: `{s}`, kind: '{k}' }}," for n, s, k in entries
    )
    triggered = ""
    if "RadialMenu" in reachable and "RadialMenu" not in unreachable:
        triggered += """
  test('RadialMenu: right-click an agent opens the radial menu; Escape closes it', async ({ page }) => {
    test.setTimeout(120_000);
    await page.goto('/fleet', { waitUntil: 'commit' });
    if (!BEARER) await page.getByRole('button', { name: 'Enter' }).click();
    await page.locator('[data-testid="room-agents"]').first().waitFor({ timeout: 60_000 });
    await page.locator('[data-testid="room-agents"]').first().click({ button: 'right' });
    await expect(page.locator('[data-testid="radial-scrim"]')).toBeVisible({ timeout: 30_000 });
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-testid="radial-scrim"]')).toBeHidden({ timeout: 10_000 });
  });
"""
    if "Spotlight" in reachable and "Spotlight" not in unreachable:
        triggered += """
  test('Spotlight: click an agent, it detaches and speaks; Escape releases', async ({ page }) => {
    test.setTimeout(120_000);
    await page.goto('/fleet', { waitUntil: 'commit' });
    if (!BEARER) await page.getByRole('button', { name: 'Enter' }).click();
    await page.locator('[data-testid="room-agents"]').first().waitFor({ timeout: 60_000 });
    await page.locator('[data-testid="room-agents"]').first().click();
    await expect(page.locator('[role="dialog"][aria-label*="Agent"]')).toBeVisible({ timeout: 30_000 });
    await page.keyboard.press('Escape');
    await expect(page.locator('[role="dialog"][aria-label*="Agent"]')).toBeHidden({ timeout: 10_000 });
  });
"""
    print(f"""// GENERATED by probes/gen_panels_spec.py — do not hand-edit. Regenerate instead.
// Every non-test component in room/ui must appear here or generation fails (no hint of a gap).
import {{ test, expect, chromium }} from '@playwright/test';
import * as fs from 'fs';

test.use({{ channel: 'chrome' }});
// Live runs carry the prover's machine identity through the public gate (the same door
// probes/backstage.py uses): the proxy forwards the Bearer, the app grades it. Local runs
// (built app, no gate) use the app's own Enter door instead.
const BEARER = process.env.SURFACES_BEARER || '';
if (BEARER) test.use({{ extraHTTPHeaders: {{ authorization: `Bearer ${{BEARER}}` }} }});

const PANELS = [
{cases}
];

test.describe('/fleet panels: every component in room/ui renders on the real page', () => {{
  test('each panel is present and no page errors', async ({{ page }}) => {{
    test.setTimeout(120_000);
    const errors: string[] = [];
    page.on('pageerror', e => errors.push(e.message));
    const live = page.waitForResponse(
      r => new URL(r.url()).pathname === '/api/proxy/fleetview/sessions' && r.status() === 200,
    );
    await page.goto('/fleet', {{ waitUntil: 'commit' }});
    if (!BEARER) await page.getByRole('button', {{ name: 'Enter' }}).click();
    await live;
    await page.waitForTimeout(5_000); // panels stream in after sessions land

    const missing: string[] = [];
    for (const p of PANELS) {{
      if (p.kind === 'testid') {{
        const n = await page.locator(p.sel).count();
        if (n === 0) missing.push(p.name);
      }} else if (p.kind === 'tag') {{
        const n = await page.locator('canvas').count();
        if (n === 0) missing.push(p.name);
      }} else {{
        const body = (await page.locator('body').innerText()).match(/\\$\\d+\\.\\d+/);
        if (!body) missing.push(p.name);
      }}
    }}
    expect(missing, 'panels that did not render on /fleet').toEqual([]);
    expect(errors, 'uncaught page errors').toEqual([]);
  }});

  test('wiring: every room/ui component is reachable from a route', async () => {{
    // Generated from the mount graph. A component here exists but no route can render it —
    // wire it or delete it; leaving it is a gap the founder refused to tolerate.
    const unreachable: string[] = {unreachable!r};
    expect(unreachable, 'room/ui components unreachable from any route').toEqual([]);
  }});
{triggered}}});

test.describe('/fleet-original: the before picture beside the rewrite', () => {{
  test('FleetReactorOriginal renders on /fleet-original', async ({{ page }}) => {{
    test.setTimeout(120_000);
    const errors: string[] = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('/fleet-original', {{ waitUntil: 'commit' }});
    if (!BEARER) await page.getByRole('button', {{ name: 'Enter' }}).click();
    await page.locator('[data-testid="{orig_testid}"]').first().waitFor({{ timeout: 60_000 }});
    expect(errors, 'uncaught page errors on /fleet-original').toEqual([]);
  }});
}});
{face_block}""")
    print(
        f"// panels covered: {len(entries)}; unreachable (wiring gap, spec goes red): {unreachable}; voice-path tests: 3 (/face listening; /face and /fleet full spoken turn)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
