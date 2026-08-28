"""Incident 2026-08-25: launchd-lint (agent-guard) went RED on three idp jobs. Nice=5 let an
hourly job compete with the founder's foreground work on a 16 GB Mac (load 236 on 2026-08-25),
and RunAtLoad on an hourly job fired every periodic job at once after a reboot.
Rule (rung 4): every periodic template carries Nice >= 10, and a template with
StartInterval >= 3600 does not also RunAtLoad. Same rule as agent-guard bin/launchd-lint, applied
to the templates so the defect is refused before install, not found on the machine."""
import pathlib
import plistlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATES = sorted((ROOT / "launchd").glob("*.plist.tmpl"))


def _load(path):
    text = re.sub(r"\$\{[A-Z_]+\}|\{\{[^}]+\}\}", "x", path.read_text())
    return plistlib.loads(text.encode())


def _violations(d):
    out = []
    periodic = "StartInterval" in d or "StartCalendarInterval" in d
    if periodic and d.get("Nice", 0) < 10:
        out.append(f"Nice={d.get('Nice')} (< 10)")
    if d.get("StartInterval", 0) >= 3600 and d.get("RunAtLoad"):
        out.append(f"RunAtLoad with StartInterval={d['StartInterval']}")
    return out


def test_no_template_can_storm_the_cpu():
    assert TEMPLATES, "no launchd templates"
    bad = {t.name: v for t in TEMPLATES if (v := _violations(_load(t)))}
    assert bad == {}, bad


def test_the_incident_shape_is_refused():
    assert _violations({"StartInterval": 3600, "RunAtLoad": True, "Nice": 5}) == [
        "Nice=5 (< 10)", "RunAtLoad with StartInterval=3600"]
    assert _violations({"StartInterval": 600, "RunAtLoad": True, "Nice": 10}) == []
