import os, json
from .http_webhook_base import HTTPWebhookSurface
from .. import ledger
from ..net import open_https, https_request


class NotionSurface(HTTPWebhookSurface):
    id = "notion"

    def __init__(self):
        super().__init__()
        self.token = os.environ.get("NOTION_TOKEN")

    def parse(self, payload):
        # Notion sends page.created / database.row.created, etc.
        props = payload.get("properties", {})
        title = ""
        for v in props.values():
            if v.get("type") == "title":
                title = "".join(t.get("plain_text", "") for t in v.get("title", []))
                break
        if not title:
            return None
        return (title, payload.get("id", "notion_user"))

    def deliver(self, order, message):
        if not self.token or not order.get("chat_id"):
            return {"delivered": False, "reason": "NO_NOTION_TOKEN"}
        # Append a comment to the page
        body = json.dumps(
            {
                "parent": {"page_id": order["chat_id"]},
                "rich_text": [{"type": "text", "text": {"content": message}}],
            }
        ).encode()
        req = https_request(
            "https://api.notion.com/v1/comments",
            method="POST",
            data=body,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            },
        )
        try:
            with open_https(req, timeout=30) as r:
                resp = json.loads(r.read())
            ledger.write(
                "deliveries",
                {"order_id": order["order_id"], "surface": self.id, "delivered": True},
            )
            return {"delivered": True, "comment_id": resp.get("id")}
        except Exception as e:
            ledger.write(
                "dead_letters",
                {
                    "order_id": order["order_id"],
                    "surface": self.id,
                    "error": str(e)[:200],
                },
            )
            return {"delivered": False, "reason": type(e).__name__}
