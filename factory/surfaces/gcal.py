import os, json, logging, time, urllib.parse
from pathlib import Path
from datetime import datetime, timezone
from .base import Surface
from .. import llm, ledger
from ..net import open_https, https_request

log = logging.getLogger("factory.surfaces.gcal")


class GoogleCalendarSurface(Surface):
    id = "gcal"

    def __init__(self):
        self.token = os.environ.get("GOOGLE_CALENDAR_TOKEN")
        self.cal_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
        self.state = Path(".gcal_state.json")

    def _last(self) -> str:
        if self.state.exists():
            try:
                return json.loads(self.state.read_text()).get("updatedMin", "")
            except Exception as e:
                log.debug("cannot read gcal state: %s", e)
                return ""
        return ""

    def intake(self):
        if not self.token:
            return None
        params = {"maxResults": "5", "singleEvents": "true", "orderBy": "startTime"}
        last = self._last()
        if last:
            params["updatedMin"] = last
        url = (
            f"https://www.googleapis.com/calendar/v3/calendars/"
            f"{urllib.parse.quote(self.cal_id)}/events?"
            + urllib.parse.urlencode(params)
        )
        req = https_request(url, headers={"Authorization": f"Bearer {self.token}"})
        try:
            with open_https(req, timeout=30) as r:
                data = json.loads(r.read())
        except Exception as e:
            ledger.write("errors", {"where": "gcal.poll", "err": str(e)[:200]})
            return None
        items = data.get("items", [])
        if not items:
            return None
        latest = items[-1]
        summary = latest.get("summary", "")
        desc = latest.get("description", "")
        if not (summary or desc):
            return None
        self.state.write_text(
            json.dumps(
                {
                    "updatedMin": data.get("updated")
                    or datetime.now(timezone.utc).isoformat()
                }
            )
        )
        p = llm.decompose(f"{summary} {desc}".strip(), tenant="per_calendar")
        oid = (
            "ord_"
            + __import__("hashlib")
            .sha256(f"gcal:{time.time()}".encode())
            .hexdigest()[:26]
            .upper()
        )
        return {
            "order_id": oid,
            "tenant_id": "per_calendar",
            "goal": p["goal"],
            "capabilities": p["capabilities"],
            "chat_id": latest.get("id"),
            "surface": self.id,
            "raw": f"{summary} {desc}",
        }

    def deliver(self, order, message):
        # Log only; Google Calendar writes are out of scope for v1
        ledger.write(
            "deliveries",
            {
                "order_id": order["order_id"],
                "surface": self.id,
                "delivered": True,
                "note": "recorded only — no outbound calendar write",
            },
        )
        return {"delivered": True, "note": "recorded_only"}
