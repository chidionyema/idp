import os, json, urllib.request
from .http_webhook_base import HTTPWebhookSurface
from .. import ledger


class LinearSurface(HTTPWebhookSurface):
    id = "linear"

    def __init__(self):
        super().__init__()
        self.key = os.environ.get("LINEAR_API_KEY")

    def parse(self, payload):
        data = payload.get("data", {})
        title = data.get("title") or data.get("description", "")
        if not title:
            return None
        return (title, data.get("id", "linear_user"))

    def deliver(self, order, message):
        if not self.key:
            return {"delivered": False, "reason": "NO_LINEAR_KEY"}
        query = """
        mutation Comment($issueId: String!, $body: String!) {
          commentCreate(input: {issueId: $issueId, body: $body}) {
            success comment { id }
          }
        }"""
        body = json.dumps(
            {
                "query": query,
                "variables": {"issueId": order["chat_id"], "body": message},
            }
        ).encode()
        req = urllib.request.Request(
            "https://api.linear.app/graphql",
            method="POST",
            data=body,
            headers={"Authorization": self.key, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                resp = json.loads(r.read())
            ok = resp.get("data", {}).get("commentCreate", {}).get("success", False)
            ledger.write(
                "deliveries",
                {"order_id": order["order_id"], "surface": self.id, "delivered": ok},
            )
            return {"delivered": ok}
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
