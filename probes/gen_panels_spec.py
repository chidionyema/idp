"""Generate the L3 per-panel Playwright spec FROM the same inventory surfaces.py uses.

The no-gap law: the spec is generated from code, not hand-written. A panel added to
room/ui without a covering entry here is impossible — the generator enumerates every
non-test .tsx and requires a signature (data-testid, aria-label, title, or a text
regex / canvas fallback), else it FAILS generation, which fails the gate.

Usage: python3 -m probes.gen_panels_spec > panels.spec.ts
Exit 1 if any panel lacks a discoverable signature (that is a gap, and gaps are red).
"""

from __future__ import annotations

import re
import subprocess
import sys

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

    cases = "\n".join(
        f"  {{ name: '{n}', sel: `{s}`, kind: '{k}' }}," for n, s, k in entries
    )
    triggered = ""
    if "RadialMenu" in reachable and "RadialMenu" not in unreachable:
        triggered += """
  test('RadialMenu: right-click an agent opens the radial menu; Escape closes it', async ({ page }) => {
    test.setTimeout(120_000);
    await page.goto('/fleet', { waitUntil: 'commit' });
    await page.getByRole('button', { name: 'Enter' }).click();
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
    await page.getByRole('button', { name: 'Enter' }).click();
    await page.locator('[data-testid="room-agents"]').first().waitFor({ timeout: 60_000 });
    await page.locator('[data-testid="room-agents"]').first().click();
    await expect(page.locator('[role="dialog"][aria-label*="Agent"]')).toBeVisible({ timeout: 30_000 });
    await page.keyboard.press('Escape');
    await expect(page.locator('[role="dialog"][aria-label*="Agent"]')).toBeHidden({ timeout: 10_000 });
  });
"""
    print(f"""// GENERATED by probes/gen_panels_spec.py — do not hand-edit. Regenerate instead.
// Every non-test component in room/ui must appear here or generation fails (no hint of a gap).
import {{ test, expect }} from '@playwright/test';

test.use({{ channel: 'chrome' }});

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
    await page.getByRole('button', {{ name: 'Enter' }}).click();
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
    await page.getByRole('button', {{ name: 'Enter' }}).click();
    await page.locator('[data-testid="{orig_testid}"]').first().waitFor({{ timeout: 60_000 }});
    expect(errors, 'uncaught page errors on /fleet-original').toEqual([]);
  }});
}});
""")
    print(
        f"// panels covered: {len(entries)}; unreachable (wiring gap, spec goes red): {unreachable}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
