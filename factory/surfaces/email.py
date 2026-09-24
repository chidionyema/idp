import os, imaplib, smtplib, json, hashlib, time
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default as email_policy
from .base import Surface
from .. import llm, ledger


class EmailSurface(Surface):
    id = "email"

    def __init__(self):
        self.imap_host = os.environ.get("IMAP_HOST")
        self.imap_user = os.environ.get("IMAP_USER")
        self.imap_pass = os.environ.get("IMAP_PASS")
        self.smtp_host = os.environ.get("SMTP_HOST")
        self.smtp_user = os.environ.get("SMTP_USER")
        self.smtp_pass = os.environ.get("SMTP_PASS")
        self.smtp_from = os.environ.get("SMTP_FROM") or self.smtp_user

    def intake(self):
        if not (self.imap_host and self.imap_user and self.imap_pass):
            return None
        try:
            M = imaplib.IMAP4_SSL(self.imap_host)
            M.login(self.imap_user, self.imap_pass)
            M.select("INBOX")
            typ, data = M.search(None, "UNSEEN")
            ids = data[0].split()
            if not ids:
                M.logout()
                return None
            uid = ids[-1]
            typ, msg_data = M.fetch(uid, "(RFC822)")
            raw = msg_data[0][1]
            msg = BytesParser(policy=email_policy).parsebytes(raw)
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_content()
                        break
            else:
                body = msg.get_content()
            sender = msg.get("From", "")
            subject = msg.get("Subject", "")
            M.store(uid, "+FLAGS", "\\Seen")
            M.logout()
            expression = f"{subject}\n{body}".strip()[:2000]
            p = llm.decompose(expression, tenant=f"per_{sender}")
            oid = "ord_" + hashlib.sha256(f"em:{uid}".encode()).hexdigest()[:26].upper()
            return {
                "order_id": oid,
                "tenant_id": f"per_{sender}",
                "goal": p["goal"],
                "capabilities": p["capabilities"],
                "chat_id": sender,
                "surface": self.id,
                "raw": expression,
            }
        except Exception as e:
            ledger.write("errors", {"where": "email.imap", "err": str(e)[:200]})
            return None

    def deliver(self, order, message):
        if not (
            self.smtp_host
            and self.smtp_user
            and self.smtp_pass
            and order.get("chat_id")
        ):
            return {"delivered": False, "reason": "SMTP_NOT_CONFIGURED"}
        try:
            msg = EmailMessage()
            msg["From"] = self.smtp_from
            msg["To"] = order["chat_id"]
            msg["Subject"] = f"Factory {order['order_id']}"
            msg.set_content(message)
            with smtplib.SMTP_SSL(self.smtp_host, 465) as s:
                s.login(self.smtp_user, self.smtp_pass)
                s.send_message(msg)
            ledger.write(
                "deliveries",
                {"order_id": order["order_id"], "surface": self.id, "delivered": True},
            )
            return {"delivered": True}
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
