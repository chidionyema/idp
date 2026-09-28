import os, json
from .http_webhook_base import HTTPWebhookSurface
from .. import ledger
from ..net import open_https, https_request


class GitHubSurface(HTTPWebhookSurface):
    id = "github"

    def __init__(self):
        super().__init__()
        self.token = os.environ.get("GITHUB_TOKEN")

    def parse(self, payload):
        # issue.opened, pull_request.opened, issue_comment.created
        issue = payload.get("issue") or payload.get("pull_request") or {}
        title = issue.get("title") or payload.get("comment", {}).get("body", "")
        repo = payload.get("repository", {}).get("full_name", "")
        num = issue.get("number")
        if not title or not repo or not num:
            return None
        return (title, f"{repo}#{num}")

    def deliver(self, order, message):
        if not self.token or "#" not in order.get("chat_id", ""):
            return {"delivered": False, "reason": "NO_GITHUB_TOKEN_OR_TARGET"}
        repo, num = order["chat_id"].rsplit("#", 1)
        url = f"https://api.github.com/repos/{repo}/issues/{num}/comments"
        body = json.dumps({"body": message}).encode()
        req = https_request(
            url,
            method="POST",
            data=body,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
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
