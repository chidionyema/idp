"""The one browser driver for vendor self-setup (the bin/idp-bootstrap-cloudflare pattern,
generalised): a persistent headful profile per vendor, declarative steps from consoles.yaml.
It waits for a person at sign-in, 2FA, CAPTCHA and terms, and never clicks a consent control
itself. log() receives step descriptions only, never page text or values.
"""

from __future__ import annotations

import datetime
import pathlib
import re
import time

from vendor_setup import SetupError, pattern, render, scrub


def _what(spec: dict) -> str:
    if spec.get("why"):
        return spec["why"]
    if spec.get("role"):
        return f'{spec["role"]} "{spec.get("name", "")}"'
    return f'label "{spec["label"]}"'


def _locator(page, spec):
    if "label" in spec:
        return page.get_by_label(pattern(spec["label"]))
    if "name" in spec:
        return page.get_by_role(spec["role"], name=pattern(spec["name"]))
    return page.get_by_role(spec["role"])


def run_steps(
    steps: list,
    profile_dir,
    vendor: str,
    *,
    headless: bool = False,
    wait_s: int = 300,
    log=print,
    today: datetime.date | None = None,
) -> dict[str, str]:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    today = today or datetime.date.today()
    profile = pathlib.Path(profile_dir)
    profile.mkdir(parents=True, exist_ok=True, mode=0o700)
    captured: dict[str, str] = {}

    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                str(profile), headless=headless, viewport={"width": 1280, "height": 900}
            )
            try:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                for step in steps:
                    ((action, spec),) = step.items()

                    if action == "goto":
                        log(f"goto {spec}")
                        page.goto(spec, wait_until="domcontentloaded")

                    elif action == "wait":
                        limit = int(spec.get("wait_s", wait_s))
                        what = _what(spec)
                        log(f"waiting for {what} (up to {limit}s)")
                        loc = _locator(page, spec)
                        deadline = time.monotonic() + limit
                        while True:
                            try:
                                visible = loc.count() > 0 and loc.first.is_visible()
                            except PlaywrightError:
                                # the page may be mid-navigation while a person signs in
                                visible = False
                            if visible:
                                break
                            if time.monotonic() >= deadline:
                                raise SetupError(
                                    f"waiting for {what}: not there after {limit}s"
                                )
                            time.sleep(1)

                    elif action == "click":
                        log(f"click {_what(spec)}")
                        _locator(page, spec).first.click(timeout=30_000)
                        page.wait_for_load_state("domcontentloaded")

                    elif action == "fill":
                        log(f"fill {_what(spec)}")
                        _locator(page, spec).first.fill(
                            render(spec["value"], vendor, today), timeout=30_000
                        )

                    elif action == "capture":
                        field, rx = spec["field"], re.compile(spec["regex"])
                        deadline = time.monotonic() + min(15, wait_s)
                        while True:
                            m = rx.search(page.inner_text("body"))
                            if m:
                                captured[field] = (
                                    m.group(1) if rx.groups else m.group(0)
                                )
                                log(f"captured {field}")
                                break
                            if time.monotonic() >= deadline:
                                raise SetupError(
                                    f"{field} not found on the page "
                                    "(the capture regex matched nothing)"
                                )
                            time.sleep(0.5)
            finally:
                ctx.close()
    except SetupError as e:
        raise SetupError(scrub(str(e), captured.values())) from None
    except Exception as e:  # noqa: BLE001 -- any failure after a capture holds the value in scope
        # Not only PlaywrightError: whatever raises once a field is captured is scrubbed here,
        # because the caller never sees `captured` and cannot scrub it.
        raise SetupError(
            scrub(
                f"{type(e).__name__}: {str(e).splitlines()[0][:200] if str(e) else ''}",
                captured.values(),
            )
        ) from None

    return captured
