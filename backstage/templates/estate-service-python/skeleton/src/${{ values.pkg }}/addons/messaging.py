{%- if 'messaging' in values.addons %}
"""Messaging through Apprise, the estate notifier (STANDARDS.md notifications row).
The target URLs live in the vault entry as key `apprise-urls`, one per line."""
import apprise

from .. import secrets


def notify(title: str, body: str) -> bool:
    urls = (secrets.read("apprise-urls") or "").split()
    ap = apprise.Apprise()
    for u in urls:
        ap.add(u)
    return ap.notify(title=title, body=body) if urls else False
{%- else %}
"""Messaging not ticked at creation. Re-run the template with Messaging ticked to add it."""
{%- endif %}
