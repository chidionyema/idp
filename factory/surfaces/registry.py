import os
from .cli import CLISurface


def all_surfaces() -> list:
    out = []
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        from .telegram import TelegramSurface

        out.append(TelegramSurface())
    if os.environ.get("TWILIO_ACCOUNT_SID"):
        from .whatsapp import WhatsAppSurface

        out.append(WhatsAppSurface())
        from .voice import VoiceSurface

        out.append(VoiceSurface())
    if os.environ.get("SLACK_BOT_TOKEN"):
        from .slack import SlackSurface

        out.append(SlackSurface())
    if os.environ.get("NOTION_TOKEN"):
        from .notion import NotionSurface

        out.append(NotionSurface())
    if os.environ.get("LINEAR_API_KEY"):
        from .linear import LinearSurface

        out.append(LinearSurface())
    if os.environ.get("STRIPE_WEBHOOK_SECRET"):
        from .stripe import StripeSurface

        out.append(StripeSurface())
    if os.environ.get("GITHUB_TOKEN"):
        from .github_surface import GitHubSurface

        out.append(GitHubSurface())
    if os.environ.get("GOOGLE_CALENDAR_TOKEN"):
        from .gcal import GoogleCalendarSurface

        out.append(GoogleCalendarSurface())
    if os.environ.get("IMAP_HOST"):
        from .email import EmailSurface

        out.append(EmailSurface())
    if os.environ.get("WS_URL"):
        from .websocket import WebSocketSurface

        out.append(WebSocketSurface())
    if os.environ.get("MQTT_BROKER"):
        from .mqtt import MQTTSurface

        out.append(MQTTSurface())
    if os.environ.get("BLE_DEVICE"):
        from .ble import BLESurface

        out.append(BLESurface())
    if os.environ.get("SERIAL_PORT"):
        from .serial_surface import SerialSurface

        out.append(SerialSurface())
    if os.environ.get("FACTORY_EXPRESSION") or not out:
        out.append(CLISurface())
    return out
